import json
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest import mock

from poms.common.common_base_test import BaseTestCase
from poms.celery_tasks.models import CeleryTask
from poms.csv_import.models import CsvImportScheme
from poms.csv_import.tests.instrument_data import INSTRUMENT

API_URL = f"/{settings.BASE_API_URL}/api/v1/import"

FILE_CONTENT = json.dumps(INSTRUMENT).encode("utf-8")


class DummyStorage:
    def save(self):
        return


class ComplexTransactionCsvFileImportViewSetTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = f"{API_URL}/csv/"
        self.scheme = CsvImportScheme.objects.create(
            user_code=self.random_string(length=5),
            master_user=self.master_user,
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
