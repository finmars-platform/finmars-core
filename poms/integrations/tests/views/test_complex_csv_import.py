import json
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest import mock

from poms.common.common_base_test import BaseTestCase
from poms.celery_tasks.models import CeleryTask
from poms.integrations.models import ComplexTransactionImportScheme

BASE_URL = f"/{settings.BASE_API_URL}/api/v1/import"

JSON_DATA = [
    {
        "Transaction ID": 15989,
        "Transaction Type": "Buy",
        "Reverse": "-",
        "Date (Trade)": "2015-01-22T00:00:00.000",
        "Date (Value)": "2015-01-26T00:00:00.000",
        "Portfolio": "Model_Fn",
        "Account": "VB",
        "Instrument": "CH0123431709",
        "Position size": 300000,
        "Principal price": 86.9826666667,
        "Amount (Accrued)": -10593.75,
        "Amount (Charges)": -149.58,
        "Cash Consideration": -271691.33,
        "Currency (Settlement)": "CHF",
        "Notes": "Lorem ipsum 15989",
        "Reference transaction code": "-",
    }
]
FILE_CONTENT = json.dumps(JSON_DATA).encode("utf-8")


class DummyStorage:
    def save(self):
        return


class ComplexTransactionCsvFileImportViewSetTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = f"{BASE_URL}/complex-transaction-csv-file-import/"
        self.scheme = ComplexTransactionImportScheme.objects.create(
            user_code=self.random_string(length=5),
            master_user=self.master_user,
        )

    def create_task(self, name: str, func: str):
        return CeleryTask.objects.create(
            master_user=self.master_user,
            member=self.member,
            verbose_name=name,
            function_name=func,
            type="transaction_import",
            status=CeleryTask.STATUS_PENDING,
            result="{}",
        )

    def test__get_405(self):
        response = self.client.get(path=self.url, data={})
        self.assertEqual(response.status_code, 405, response.content)

    @mock.patch("poms.integrations.serializers.storage")
    def test__create(self, storage):
        storage.return_value = DummyStorage()
        file_name = "file.json"
        file_content = SimpleUploadedFile(file_name, FILE_CONTENT)
        request_data = {"file": file_content, "scheme": self.scheme.id}
        response = self.client.post(
            path=self.url,
            data=request_data,
            format="multipart",
        )
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()

        self.assertIn("task_id", response_json)
        self.assertIn("task_status", response_json)
        self.assertIn(response_json["task_status"], CeleryTask.STATUS_INIT)

        celery_task = CeleryTask.objects.get(pk=response_json["task_id"])
        options = celery_task.options_object

        self.assertEqual(options["file_name"], file_name)
        self.assertEqual(options["scheme_id"], self.scheme.id)
