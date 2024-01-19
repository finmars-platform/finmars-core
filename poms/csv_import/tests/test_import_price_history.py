import json
from unittest import mock

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile

from poms.celery_tasks.models import CeleryTask
from poms.common.common_base_test import BaseTestCase
from poms.csv_import.models import CsvImportScheme
from poms.csv_import.handlers import SimpleImportProcess
from poms.csv_import.tasks import simple_import
from poms.csv_import.tests.common_test_data import PRICE_HISTORY, SCHEMA_20

API_URL = f"/{settings.BASE_API_URL}/api/v1/import/csv/"
FILE_CONTENT = json.dumps(PRICE_HISTORY).encode("utf-8")
FILE_NAME = "price_history.json"


class ImportPriceHistoryTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = API_URL
        self.scheme_20 = self.create_schema_20()
        self.storage = mock.Mock()
        self.storage.save.return_value = None

    def create_schema_20(self):
        content_type = ContentType.objects.get(
            app_label="instruments",
            model="pricehistory",
        )
        schema_data = SCHEMA_20.copy()
        schema_data.update(
            {
                "content_type_id": content_type.id,
                "master_user_id": self.master_user.id,
                "owner_id": self.member.id,
            }
        )
        return CsvImportScheme.objects.create(**schema_data)

    def create_task(self):
        options_object = {
            "file_path": FILE_NAME,
            "filename": FILE_NAME,
            "scheme_id": self.scheme_20.id,
            "execution_context": None,
        }
        return CeleryTask.objects.create(
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
        mock_instance = mock_import_process.return_value

        task = self.create_task()
        simple_import(task_id=task.id)

        mock_import_process.assert_called()

        task.refresh_from_db()
        self.assertEqual(task.status, CeleryTask.STATUS_PENDING)

        print(f"task.progress_object={task.progress}")
