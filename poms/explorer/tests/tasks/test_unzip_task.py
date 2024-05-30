import io
import zipfile
from unittest import mock

from poms.celery_tasks.models import CeleryTask
from poms.common.common_base_test import BaseTestCase
from poms.common.storage import FinmarsS3Storage
from poms.explorer.serializers import UnZipSerializer
from poms.explorer.tasks import unzip_file_in_storage


class UnzipTaskTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.realm_code = "realm00000"
        self.space_code = "space00000"

        self.storage_patch = mock.patch(
            "poms.explorer.tasks.storage",
            spec=FinmarsS3Storage,
        )
        self.storage_mock = self.storage_patch.start()
        self.addCleanup(self.storage_patch.stop)

        self.mock_is_file_patch = mock.patch(
            "poms.explorer.serializers.path_is_file",
            return_value=True,
        )
        self.mock_is_file = self.mock_is_file_patch.start()
        self.addCleanup(self.mock_is_file_patch.stop)

        self.file1 = io.BytesIO()
        self.file2 = io.BytesIO()
        self.file1.write(b"This is file 1.")
        self.file2.write(b"This is file 2.")

        self.zip_file = io.BytesIO()
        with zipfile.ZipFile(
            self.zip_file, mode="w", compression=zipfile.ZIP_DEFLATED
        ) as zf:
            zf.writestr("file1.txt", self.file1.getvalue())
            zf.writestr("file2.txt", self.file2.getvalue())

        self.file1.seek(0)
        self.file2.seek(0)
        self.zip_file.seek(0)

    def test__ok(self):
        request_data = {"target_directory_path": "test", "file_path": "file.zip"}
        context = {"storage": self.storage_mock, "space_code": self.space_code}
        serializer = UnZipSerializer(data=request_data, context=context)
        serializer.is_valid(raise_exception=True)

        celery_task = CeleryTask.objects.create(
            master_user=self.master_user,
            member=self.member,
            verbose_name="Unzip file in storage",
            type="unzip_file_in_storage",
            options_object=serializer.validated_data,
        )

        self.storage_mock.open.return_value = self.zip_file

        unzip_file_in_storage(task_id=celery_task.id, context=context)

        celery_task.refresh_from_db()

        self.assertEqual(celery_task.status, CeleryTask.STATUS_DONE)
        self.assertEqual(
            celery_task.verbose_result,
            "unzip space00000/file.zip to space00000/test/",
        )
        self.assertEqual(
            celery_task.progress_object,
            {
                "current": 2,
                "total": 2,
                "percent": 100,
                "description": "unzip_file_in_storage finished",
            },
        )
