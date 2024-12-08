from unittest import mock

from poms.common.common_base_test import BaseTestCase
from poms.common.storage import FinmarsS3Storage


class StorageSaveTest(BaseTestCase):
    def setUp(self):
        super().setUp()

    @mock.patch("poms.common.storage.FinmarsStorageMixin.save")
    @mock.patch("poms.explorer.tasks.start_update_create_path_in_storage")
    def test__two_saves_called(self, start_task, super_save):
        FinmarsS3Storage().save(path="file.txt", content="test")
        super_save.assert_called_once_with(path="file.txt", content="test")
        start_task.assert_called_once_with(path="file.txt", content="test")

    @mock.patch("poms.common.storage.FinmarsStorageMixin.save")
    @mock.patch("poms.explorer.tasks.start_update_create_path_in_storage")
    def test__one_save_called(self, super_save, start_task):
        self.storage.save(path="check/.init", content=None)
        super_save.assert_called_once_with(path="check/.init", content=None)
        start_task.assert_not_called()
