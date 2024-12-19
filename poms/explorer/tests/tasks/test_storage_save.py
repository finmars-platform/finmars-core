from unittest import mock

from poms.common.common_base_test import BaseTestCase
from poms.common.storage import FinmarsS3Storage


class StorageSaveTest(BaseTestCase):
    @mock.patch("poms.common.storage.FinmarsStorageMixin.save")
    def test__file_two_saves_called(self, super_save):
        FinmarsS3Storage().save(path="file.txt", content="test")
        super_save.assert_called_once_with("file.txt", "test")

    @mock.patch("poms.common.storage.FinmarsStorageMixin.save")
    def test__dir_two_saves_called(self, super_save):
        FinmarsS3Storage().save(path="dir", content=None)
        super_save.assert_called_once_with("dir", None)

    @mock.patch("poms.common.storage.FinmarsStorageMixin.save")
    def test__one_save_called(self, super_save):
        FinmarsS3Storage().save(path="check/.init", content=None)
        super_save.assert_called_once_with("check/.init", None)
