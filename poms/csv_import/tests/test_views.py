import json
from unittest import mock

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile

from poms.celery_tasks.models import CeleryTask
from poms.common.common_base_test import BaseTestCase
from poms.csv_import.models import CsvImportScheme
from poms.csv_import.tests.common_test_data import INSTRUMENT

FILE_CONTENT = json.dumps(INSTRUMENT).encode("utf-8")
FILE_NAME = "instrument.json"


class DummyStorage:
    def save(self):
        return


class CsvDataImportViewSetTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()

        self.realm_code = 'realm00000'
        self.space_code = 'space00000'

        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/import/csv/"
        self.scheme = CsvImportScheme.objects.create(
            content_type=ContentType.objects.first(),
            master_user=self.master_user,
            owner=self.member,
            user_code=self.random_string(length=5),
        )

    def test__get_405(self):
        response = self.client.get(path=self.url)
        self.assertEqual(response.status_code, 405, response.content)

    @BaseTestCase.cases(
        ("1-dot", "instrument.json"),
        ("2-dots", "instru.ment.json"),
        ("3-dots", "ins.tru.ment.json"),
    )
    @mock.patch("poms.csv_import.serializers.storage")
    def test__create(self, file_name, storage):
        file_content = SimpleUploadedFile(file_name, FILE_CONTENT)
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

        self.assertEqual(options["filename"], file_name)
        self.assertEqual(options["scheme_id"], self.scheme.id)
        self.assertIsNone(options["execution_context"])
