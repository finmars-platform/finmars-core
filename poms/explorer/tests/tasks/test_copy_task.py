from unittest import mock

from poms.common.common_base_test import BaseTestCase
from poms.common.storage import FinmarsS3Storage
from poms.explorer.serializers import CopySerializer
from poms.celery_tasks.models import CeleryTask
from poms.explorer.tasks import copy_directory_in_storage


class CopyTaskTest(BaseTestCase):
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

        self.mock_count_patch = mock.patch(
            "poms.explorer.utils.count_files",
            return_value=1,
        )
        self.mock_count = self.mock_count_patch.start()
        self.addCleanup(self.mock_count_patch.stop)

    def test__ok(self):
        request_data = {"target_directory_path": "test", "paths": ["file.txt"]}
        context = {"storage": self.storage_mock, "space_code": self.space_code}
        serializer = CopySerializer(data=request_data, context=context)
        serializer.is_valid(raise_exception=True)

        celery_task = CeleryTask.objects.create(
            master_user=self.master_user,
            member=self.member,
            verbose_name="Copy directory in storage",
            type="copy_directory_in_storage",
            options_object=serializer.validated_data,
        )

        file_content = "file_content"
        self.storage_mock.open.return_value.read.return_value = file_content
        self.storage_mock.listdir.return_value = ([], ["file.txt"])
        self.storage_mock.size.return_value = len(file_content)
        self.storage_mock.dir_exists.return_value = False
        self.storage_mock.exists.return_value = False

        copy_directory_in_storage(task_id=celery_task.id, context=context)

        celery_task.refresh_from_db()
        self.assertEqual(celery_task.status, CeleryTask.STATUS_DONE)
        self.assertEqual(celery_task.verbose_result, "copied 1 items")
        self.assertEqual(
            celery_task.progress_object,
            {
                "current": 1,
                "total": 1,
                "percent": 100,
                "description": "copy_directory_in_storage finished",
            },
        )