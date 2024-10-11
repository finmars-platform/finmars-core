import copy
import json
from unittest import mock

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile

from poms.celery_tasks.models import CeleryTask
from poms.common.common_base_test import BaseTestCase
from poms.csv_import.handlers import SimpleImportProcess
from poms.csv_import.models import CsvField, CsvImportScheme, EntityField
from poms.csv_import.tasks import simple_import
from poms.csv_import.tests.common_test_data import (
    EXPECTED_RESULT_ACCRUAL_CALCULATION,
    SCHEME_20,
    SCHEME_ACCRUAL_CALCULATION_ENTITIES,
    SCHEME_ACCRUAL_CALCULATION_FIELDS,
    ACCRUAL_CALCULATION,
    ACCRUAL_CALCULATION_ITEM
)

from poms.instruments.models import AccrualCalculationSchedule, Instrument

FILE_CONTENT = json.dumps(ACCRUAL_CALCULATION).encode("utf-8")
FILE_NAME = "accrual_calculation.json"


class ImportAccrualCalculationTest(BaseTestCase):
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
        self.instrument = self.prepare_instrument()

    def prepare_instrument(self):
        instrument = self.create_instrument()
        instrument.user_code = "commitment-startup-2-round-a-debt"
        instrument.save()

        return instrument

    def create_scheme_20(self):
        content_type = ContentType.objects.using(settings.DB_DEFAULT).get(
            app_label="instruments",
            model="accrualcalculationschedule",
        )
        scheme_data = SCHEME_20.copy()
        scheme_data.update(
            {
                "content_type_id": content_type.id,
                "master_user_id": self.master_user.id,
                "owner_id": self.member.id,
                "user_code": "com.finmars.standard-import-from-file:instruments.accrualcalculationschedule:accrued_schedule",
                "name": "STD - Accrued Schedule",
                "short_name": "STD - Accrued Schedule",
            }
        )
        scheme = CsvImportScheme.objects.using(settings.DB_DEFAULT).create(
            **scheme_data
        )

        for field_data in SCHEME_ACCRUAL_CALCULATION_FIELDS:
            field_data["scheme"] = scheme
            CsvField.objects.create(**field_data)

        for entity_data in SCHEME_ACCRUAL_CALCULATION_ENTITIES:
            entity_data["scheme"] = scheme
            EntityField.objects.using(settings.DB_DEFAULT).create(**entity_data)

        return scheme

    def create_task(self, remove_instrument=False):
        items = copy.deepcopy(ACCRUAL_CALCULATION)
        options_object = {
            "file_path": FILE_NAME,
            "filename": FILE_NAME,
            "scheme_id": self.scheme_20.id,
            "execution_context": None,
            "items": items,
        }

        if remove_instrument:
            items[0]["instrument"] = None

        return CeleryTask.objects.using(settings.DB_DEFAULT).create(
            master_user=self.master_user,
            member=self.member,
            options_object=options_object,
            verbose_name="Simple Import",
            type="simple_import",
        )

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
        self.assertFalse(bool(AccrualCalculationSchedule.objects.filter(accrual_start_date='2017-11-22')))
        task = self.create_task()
        import_process = SimpleImportProcess(task_id=task.id)

        mock_send_message.assert_called()

        self.assertEqual(import_process.result.task.id, task.id)
        self.assertEqual(import_process.result.scheme.id, self.scheme_20.id)
        self.assertEqual(import_process.process_type, "JSON")

        import_process.fill_with_file_items()
        self.assertEqual(import_process.file_items, ACCRUAL_CALCULATION)

        import_process.fill_with_raw_items()
        self.assertEqual(import_process.raw_items, [ACCRUAL_CALCULATION_ITEM])

        import_process.apply_conversion_to_raw_items()
        conversion_item = import_process.conversion_items[0]
        self.assertEqual(conversion_item.conversion_inputs, ACCRUAL_CALCULATION_ITEM)

        import_process.preprocess()
        item = import_process.items[0]
        self.assertEqual(item.inputs, ACCRUAL_CALCULATION_ITEM)

        import_process.process()
        result = import_process.task.result_object["items"][0]
        self.assertEqual(result["final_inputs"], EXPECTED_RESULT_ACCRUAL_CALCULATION["final_inputs"])

        accrual = AccrualCalculationSchedule.objects.get(accrual_start_date="2017-11-22")
        self.assertEqual(accrual.instrument.user_code, "commitment-startup-2-round-a-debt")

    @mock.patch("poms.csv_import.handlers.send_system_message")
    def test_run_simple_import_process_missing_fields(self, mock_send_message):
        self.assertFalse(bool(AccrualCalculationSchedule.objects.filter(accrual_start_date='2017-11-22')))
        task = self.create_task(remove_instrument=True)
        import_process = SimpleImportProcess(task_id=task.id)

        mock_send_message.assert_called()

        self.assertEqual(import_process.result.task.id, task.id)
        self.assertEqual(import_process.result.scheme.id, self.scheme_20.id)
        self.assertEqual(import_process.process_type, "JSON")

        import_process.fill_with_file_items()
        import_process.fill_with_raw_items()
        import_process.apply_conversion_to_raw_items()
        import_process.preprocess()
        import_process.process()

        with self.assertRaises(AccrualCalculationSchedule.DoesNotExist) as e:
            AccrualCalculationSchedule.objects.get(accrual_start_date="2017-11-22")

