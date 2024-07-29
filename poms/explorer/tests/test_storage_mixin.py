from poms.common.common_base_test import BaseTestCase

from poms.explorer.models import FinmarsFile
from poms.common.storage import FinmarsLocalFileSystemStorage


class StorageFileObjMixinTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.storage = FinmarsLocalFileSystemStorage()

    def test__save(self):
        path = self.random_string()
        self.assertEqual(self.storage.save(path, "content"), path)

    def test__delete(self):
        path = self.random_string()
        self.assertEqual(self.storage.delete(path), path)
