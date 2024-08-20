import contextlib
from unittest import skip

from django.core.files.base import ContentFile

from poms.common.common_base_test import BaseTestCase
from poms.common.storage import FinmarsLocalFileSystemStorage
from poms.explorer.models import FinmarsFile


class StorageFileObjMixinTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.storage = FinmarsLocalFileSystemStorage()
        self.name = "temp_file.txt"
        self.parent = "test"
        self.full_path = f"{self.parent}/{self.name}"
        self.content = "content"

    def tearDown(self):
        super().tearDown()
        with contextlib.suppress(Exception):
            self.storage.delete_directory(self.parent)

    def create_file(self):
        name = self.storage.save(
            self.full_path, ContentFile(self.content, self.full_path)
        )
        self.assertEqual(name, self.full_path)
        self.assertTrue(self.storage.exists(self.full_path))

    @skip("till fix the storage.save()")
    def test__save_create(self):
        self.create_file()

        file = FinmarsFile.objects.filter(path=self.full_path).first()
        self.assertIsNotNone(file)
        self.assertEqual(file.path, self.full_path)
        self.assertEqual(file.name, self.name)
        self.assertEqual(file.size, len(self.content))

    def test__delete(self):
        self.create_file()

        self.storage.delete(self.full_path)
        self.assertFalse(self.storage.exists(self.full_path))

        file = FinmarsFile.objects.filter(path=self.full_path).first()
        self.assertIsNone(file)
