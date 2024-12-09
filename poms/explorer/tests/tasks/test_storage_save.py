from unittest import mock

from poms.celery_tasks.models import CeleryTask
from poms.common.common_base_test import BaseTestCase
from poms.common.storage import FinmarsS3Storage
from poms.explorer.tasks import start_update_create_path_in_storage


class StorageSaveTest(BaseTestCase):
    @mock.patch("poms.common.storage.FinmarsStorageMixin.save")
    @mock.patch("poms.explorer.tasks.start_update_create_path_in_storage")
    def test__file_two_saves_called(self, start_task, super_save):
        FinmarsS3Storage().save(path="file.txt", content="test")
        super_save.assert_called_once_with("file.txt", "test")
        start_task.assert_called_once_with("file.txt", 4)

    @mock.patch("poms.common.storage.FinmarsStorageMixin.save")
    @mock.patch("poms.explorer.tasks.start_update_create_path_in_storage")
    def test__dir_two_saves_called(self, start_task, super_save):
        FinmarsS3Storage().save(path="dir", content=None)
        super_save.assert_called_once_with("dir", None)
        start_task.assert_called_once_with("dir", 0)

    @mock.patch("poms.common.storage.FinmarsStorageMixin.save")
    @mock.patch("poms.explorer.tasks.start_update_create_path_in_storage")
    def test__one_save_called(self, start_task, super_save):
        FinmarsS3Storage().save(path="check/.init", content=None)
        super_save.assert_called_once_with("check/.init", None)
        start_task.assert_not_called()


class StartTaskTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()

    def test__start_task_created(self):
        start_update_create_path_in_storage("file.txt", 4)
        celery_task = CeleryTask.objects.filter(
            type="update_create_path_in_storage"
        ).first()
        self.assertIsNotNone(celery_task)
        self.assertEqual(celery_task.options_object["path"], "file.txt")
        self.assertEqual(celery_task.options_object["size"], 4)
