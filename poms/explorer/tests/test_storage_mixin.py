import contextlib

from django.core.files.base import ContentFile

from poms.common.common_base_test import BaseTestCase
from poms.common.storage import FinmarsLocalFileSystemStorage
from poms.explorer.models import DIR_SUFFIX, FinmarsDirectory, FinmarsFile


class StorageFileObjMixinTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.storage = FinmarsLocalFileSystemStorage()
        self.space = "space00000"
        self.parent = f"{self.space}/test"
        self.name = "temp_file.txt"
        self.full_path = f"{self.parent}/{self.name}"
        self.content = "content"

    def tearDown(self):
        super().tearDown()
        with contextlib.suppress(Exception):
            self.storage.delete_directory(self.parent)

    def save_file_to_storage(self):
        self.storage.save(self.full_path, ContentFile(self.content, self.full_path))
        self.assertTrue(self.storage.exists(self.full_path))

    def test__save_create(self):
        self.save_file_to_storage()

        file = FinmarsFile.objects.filter(path=self.full_path).first()
        self.assertIsNotNone(file)
        self.assertEqual(file.path, self.full_path)
        self.assertEqual(file.name, self.name)
        self.assertEqual(file.size, len(self.content))

        directory = FinmarsDirectory.objects.filter(
            path=f"{self.parent}{DIR_SUFFIX}"
        ).first()
        self.assertEqual(file.parent, directory)

        self.assertIsNotNone(directory.parent)
        self.assertEqual(directory.parent.path, f"{self.space}{DIR_SUFFIX}")

    def test__delete(self):
        self.save_file_to_storage()

        self.storage.delete(self.full_path)
        self.assertFalse(self.storage.exists(self.full_path))

        file = FinmarsFile.objects.filter(path=self.full_path).first()
        self.assertIsNone(file)
