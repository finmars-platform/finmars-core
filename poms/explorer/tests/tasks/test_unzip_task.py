from unittest import mock

from poms.common.common_base_test import BaseTestCase
from poms.common.storage import FinmarsS3Storage
from poms.explorer.serializers import UnZipSerializer
from poms.celery_tasks.models import CeleryTask
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

        zipped_mock_content = "zip_content"
        self.storage_mock.open.return_value.read.return_value = zipped_mock_content
        self.storage_mock.listdir.return_value = ([], ["file.txt"])
        self.storage_mock.size.return_value = len(zipped_mock_content)
        self.storage_mock.dir_exists.return_value = False

        # unzip_file_in_storage(task_id=celery_task.id, context=context)
        #
        # celery_task.refresh_from_db()
        #
        # self.assertEqual(celery_task.status, CeleryTask.STATUS_DONE)
        # self.assertEqual(celery_task.verbose_result, f"unzip file.zip to test")
        # self.assertEqual(
        #     celery_task.progress_object,
        #     {
        #         "current": 1,
        #         "total": 1,
        #         "percent": 100,
        #         "description": "unzip_file_in_storage finished",
        #     },
        # )
