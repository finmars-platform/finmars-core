import contextlib

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

    def tearDown(self):
        super().tearDown()
        with contextlib.suppress(Exception):
            self.storage.delete_directory(self.parent)

    def test__save_create(self):
        name = self.storage.save(self.full_path, ContentFile("content", self.full_path))
        print(name)
        self.assertTrue(self.storage.exists(self.full_path))
        file = FinmarsFile.objects.filter(name=self.name).first()
        self.assertIsNotNone(file)

    def test__delete(self):
        path = self.random_string()
