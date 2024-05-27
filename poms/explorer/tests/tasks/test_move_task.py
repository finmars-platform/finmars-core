from unittest import mock

from poms.common.common_base_test import BaseTestCase
from poms.common.storage import FinmarsS3Storage
from poms.explorer.serializers import MoveSerializer
from poms.celery_tasks.models import CeleryTask
from poms.explorer.tasks import move_directory_in_storage


class MoveViewSetTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.realm_code = "realm00000"
        self.space_code = "space00000"

        self.storage_patch = mock.patch(
            "poms.explorer.views.storage",
            spec=FinmarsS3Storage,
        )
        self.storage_mock = self.storage_patch.start()
        self.addCleanup(self.storage_patch.stop)

    def test__ok(self):
        request_data = {"target_directory_path": "test", "items": ["file.txt"]}
        context = {"storage": self.storage_mock, "space_code": self.space_code}
        serializer = MoveSerializer(data=request_data, context=context)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        celery_task = CeleryTask.objects.create(
            master_user=self.master_user,
            member=self.member,
            verbose_name="Move directory in storage",
            type="move_directory_in_storage",
            options_object=validated_data,
        )

        move_directory_in_storage(task_id=celery_task.id, context=context)

        file_content = "file_content"
        self.storage_mock.open.return_value.read.return_value = file_content
        self.storage_mock.listdir.return_value = ([], ["file.txt"])

        self.storage_mock.listdir.assert_called_once()
        self.storage_mock.open.assert_called_once()
        self.storage_mock.save.assert_called_once()
        self.storage_mock.delete.assert_called_once()
