import copy
import json
from unittest import mock

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile

from poms.instruments.models import PricingPolicy, PriceHistory
from poms.celery_tasks.models import CeleryTask
from poms.common.common_base_test import BaseTestCase
from poms.csv_import.handlers import SimpleImportProcess
from poms.csv_import.models import CsvField, CsvImportScheme, EntityField
from poms.csv_import.tasks import simple_import
from poms.csv_import.tests.common_test_data import (
    PRICE_HISTORY,
    PRICE_HISTORY_ITEM,
    SCHEME_20,
    SCHEME_20_ENTITIES,
    SCHEME_20_FIELDS,
)
from poms.instruments.models import Instrument

FILE_CONTENT = json.dumps(PRICE_HISTORY).encode("utf-8")
FILE_NAME = "price_history.json"


class ImportPriceHistoryTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.realm_code = "realm0000"
        self.space_code = "space0000"
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/import/csv/"
        self.scheme_20 = self.create_scheme_20()
        self.storage = mock.Mock()
        self.storage.save.return_value = None
        self.instrument = self.create_instrument_for_price_history(
            isin=PRICE_HISTORY[0]["Instrument"]
        )
        self.pricing_policy = PricingPolicy.objects.using(settings.DB_DEFAULT).create(
            master_user=self.master_user,
            owner=self.member,
            user_code="com.finmars.standard-pricing:standard",
            configuration_code="com.finmars.standard-pricing",
            name="Standard",
            short_name="Standard",
            is_enabled=True,
        )

    def create_scheme_20(self):
        content_type = ContentType.objects.using(settings.DB_DEFAULT).get(
            app_label="instruments",
            model="pricehistory",
        )
        scheme_data = SCHEME_20.copy()
        scheme_data.update(
            {
                "content_type_id": content_type.id,
                "master_user_id": self.master_user.id,
                "owner_id": self.member.id,
            }
        )
        scheme = CsvImportScheme.objects.using(settings.DB_DEFAULT).create(
            **scheme_data
        )

        for field_data in SCHEME_20_FIELDS:
            field_data["scheme"] = scheme
            CsvField.objects.create(**field_data)

        for entity_data in SCHEME_20_ENTITIES:
            entity_data["scheme"] = scheme
            EntityField.objects.using(settings.DB_DEFAULT).create(**entity_data)

        return scheme

    def create_task(self, remove_accrued_and_factor=False):
        items = copy.deepcopy(PRICE_HISTORY)
        if remove_accrued_and_factor:
            for item in items:
                item.pop("Accrued Price", None)
                item.pop("Factor", None)

        options_object = {
            "file_path": FILE_NAME,
            "filename": FILE_NAME,
            "scheme_id": self.scheme_20.id,
            "execution_context": None,
            "items": items,
        }
        return CeleryTask.objects.using(settings.DB_DEFAULT).create(
            master_user=self.master_user,
            member=self.member,
            options_object=options_object,
            verbose_name="Simple Import",
            type="simple_import",
        )

    def create_instrument_for_price_history(self, isin: str) -> Instrument:
        instrument = self.create_instrument()
        instrument.user_code = isin
        instrument.short_name = isin
        instrument.save()
        self.create_accrual(instrument)
        return instrument

    @mock.patch("poms.csv_import.views.simple_import.apply_async")
    @mock.patch("poms.csv_import.serializers.storage")
    def test_view(self, mock_storage, mock_async):
        file_content = SimpleUploadedFile(FILE_NAME, FILE_CONTENT)
        mock_storage.return_value = self.storage
        request_data = {"file": file_content, "scheme": self.scheme_20.id}

        response = self.client.post(
            path=self.url,
            data=request_data,
            format="multipart",
        )
        self.assertEqual(response.status_code, 200, response.content)

        mock_async.assert_called_once()

        response_json = response.json()
        self.assertIn("task_id", response_json)
        self.assertIn("task_status", response_json)
        self.assertEqual(response_json["task_status"], CeleryTask.STATUS_INIT)

        celery_task = CeleryTask.objects.get(pk=response_json["task_id"])
        options = celery_task.options_object

        self.assertEqual(options["filename"], FILE_NAME)
        self.assertEqual(options["scheme_id"], self.scheme_20.id)

    @mock.patch("poms.csv_import.handlers.SimpleImportProcess")
    def test_simple_import_task(self, mock_import_process):
        task = self.create_task()
        simple_import(task_id=task.id)

        mock_import_process.assert_called()

        task.refresh_from_db()
        self.assertEqual(task.status, CeleryTask.STATUS_PENDING)

        self.assertEqual(task.progress_object["description"], "Preprocess items")

    @mock.patch("poms.csv_import.handlers.send_system_message")
    def test_create_and_run_simple_import_process(self, mock_send_message):
        """
        Imitate all steps to handle file with price history datta
        """
        self.assertFalse(bool(PriceHistory.objects.all()))

        task = self.create_task()
        import_process = SimpleImportProcess(task_id=task.id)

        mock_send_message.assert_called()

        self.assertEqual(import_process.result.task.id, task.id)
        self.assertEqual(import_process.result.scheme.id, self.scheme_20.id)
        self.assertEqual(import_process.process_type, "JSON")

        import_process.fill_with_file_items()
        self.assertEqual(import_process.file_items, PRICE_HISTORY)

        import_process.fill_with_raw_items()
        self.assertEqual(import_process.raw_items, [PRICE_HISTORY_ITEM])

        import_process.apply_conversion_to_raw_items()
        conversion_item = import_process.conversion_items[0]
        self.assertEqual(conversion_item.conversion_inputs, PRICE_HISTORY_ITEM)
        self.assertEqual(conversion_item.row_number, 1)
        # print(
        #     conversion_item.file_inputs,
        #     conversion_item.raw_inputs,
        #     conversion_item.conversion_inputs,
        #     conversion_item.row_number,
        # )

        import_process.preprocess()
        item = import_process.items[0]
        self.assertEqual(item.inputs, PRICE_HISTORY_ITEM)
        self.assertEqual(item.row_number, 1)
        # print(
        #     item.row_number,
        #     item.file_inputs,
        #     item.raw_inputs,
        #     item.conversion_inputs,
        #     item.inputs,
        #     item.final_inputs,
        # )

        import_process.process()
        result = import_process.task.result_object["items"][0]

        self.assertNotEqual(result["status"], "error", result["error_message"])
        # {
        #     "accrued_price": 0.0,
        #     "date": "2024-01-05",
        #     "factor": 1.0,
        #     "instrument": "USP37341AA50",
        #     "pricing_policy": "com.finmars.standard-pricing:standard",
        #     "principal_price": 109.72,
        # }
        self.assertIn("final_inputs", result)
        self.assertEqual(result["final_inputs"]["accrued_price"], 0.0)
        self.assertEqual(result["final_inputs"]["factor"], 1.0)

        ph: PriceHistory = list(PriceHistory.objects.all())[0]
        self.assertEqual(ph.instrument.user_code, PRICE_HISTORY_ITEM["instrument"])
        self.assertEqual(ph.accrued_price, 0.0)
        self.assertEqual(ph.factor, 1.0)

    @mock.patch("poms.csv_import.handlers.send_system_message")
    def test_run_simple_import_process_missing_fields(self, mock_send_message):
        """
        Imitate all steps to handle file with price history datta
        """
        self.assertFalse(bool(PriceHistory.objects.all()))

        task = self.create_task(remove_accrued_and_factor=True)

        import_process = SimpleImportProcess(task_id=task.id)

        mock_send_message.assert_called()

        self.assertEqual(import_process.result.task.id, task.id)
        self.assertEqual(import_process.result.scheme.id, self.scheme_20.id)
        self.assertEqual(import_process.process_type, "JSON")

        import_process.fill_with_file_items()

        import_process.fill_with_raw_items()
        self.assertEqual(import_process.raw_items, [PRICE_HISTORY_ITEM])

        import_process.apply_conversion_to_raw_items()
        conversion_item = import_process.conversion_items[0]
        self.assertEqual(conversion_item.conversion_inputs, PRICE_HISTORY_ITEM)
        self.assertEqual(conversion_item.row_number, 1)
        # print(
        #     conversion_item.file_inputs,
        #     conversion_item.raw_inputs,
        #     conversion_item.conversion_inputs,
        #     conversion_item.row_number,
        # )

        import_process.preprocess()
        item = import_process.items[0]
        self.assertEqual(item.inputs, PRICE_HISTORY_ITEM)
        self.assertEqual(item.row_number, 1)
        # print(
        #     item.row_number,
        #     item.file_inputs,
        #     item.raw_inputs,
        #     item.conversion_inputs,
        #     item.inputs,
        #     item.final_inputs,
        # )

        import_process.process()
        result = import_process.task.result_object["items"][0]

        self.assertNotEqual(result["status"], "error", result["error_message"])
        # {
        #     "accrued_price": 0.0,
        #     "date": "2024-01-05",
        #     "factor": 1.0,
        #     "instrument": "USP37341AA50",
        #     "pricing_policy": "com.finmars.standard-pricing:standard",
        #     "principal_price": 109.72,
        # }
        self.assertIn("final_inputs", result)
        self.assertEqual(result["final_inputs"]["accrued_price"], 0.0)
        self.assertEqual(result["final_inputs"]["factor"], 1.0)

        ph: PriceHistory = list(PriceHistory.objects.all())[0]
        self.assertEqual(ph.instrument.user_code, PRICE_HISTORY_ITEM["instrument"])
        self.assertEqual(ph.accrued_price, 0.0)
        self.assertEqual(ph.factor, 1.0)
