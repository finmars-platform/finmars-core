import json
from unittest import mock

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile

from poms.celery_tasks.models import CeleryTask
from poms.common.common_base_test import BaseTestCase
from poms.csv_import.models import CsvImportScheme
from poms.csv_import.tests.instrument_data import INSTRUMENT

API_URL = f"/{settings.BASE_API_URL}/api/v1/import"
FILE_CONTENT = json.dumps(INSTRUMENT).encode("utf-8")
FILE_NAME = "instrument.json"


class DummyStorage:
    def save(self):
        return


class CsvDataImportViewSetTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = f"{API_URL}/csv/"
        self.scheme = CsvImportScheme.objects.create(
            content_type=ContentType.objects.first(),
            master_user=self.master_user,
            owner=self.finmars_bot,
            user_code=self.random_string(length=5),
        )

    def test__get_405(self):
        response = self.client.get(path=self.url)
        self.assertEqual(response.status_code, 405, response.content)

    @mock.patch("poms.csv_import.serializers.storage")
    def test__create(self, storage):
        file_content = SimpleUploadedFile(FILE_NAME, FILE_CONTENT)
        storage.return_value = DummyStorage()
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

        self.assertEqual(options["filename"], FILE_NAME)
        self.assertEqual(options["scheme_id"], self.scheme.id)
        self.assertIsNone(options["execution_context"])
