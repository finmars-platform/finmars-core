from unittest import mock

from poms.common.common_base_test import BaseTestCase
from poms.common.storage import FinmarsS3Storage


class StorageSaveTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.storage = FinmarsS3Storage()

    @mock.patch("FinmarsS3Storage.save")
    @mock.patch("poms.explorer.tasks.start_update_create_path_in_storage")
    def test__created_new_object(self, super_save, start_task):
        self.storage.save(path="file.txt", content="test")
        super_save.assert_called_once_with(path="file.txt", contents="test")
        start_task.assert_called_once_with(path="file.txt", contents="test")
