from unittest import mock

from poms.common.common_base_test import BaseTestCase
from poms.common.storage import FinmarsS3Storage
from poms.explorer.models import StorageObject
from poms.explorer.utils import sync_file, sync_storage_objects


class SyncFileInDatabaseTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.storage_patch = mock.patch(
            "poms.explorer.views.storage",
            spec=FinmarsS3Storage,
        )
        self.storage = self.storage_patch.start()
        self.addCleanup(self.storage_patch.stop)
        self.directory = StorageObject.objects.create(path="/test/next")

    def test__created_new_object(self):
        name = "file.doc"
        filepath = f"{self.directory.path}/{name}"
        size = self.random_int(1000, 1000000)
        self.storage.size.return_value = size

        sync_file(self.storage, filepath, self.directory)

        file = StorageObject.objects.filter(path=filepath, is_file=True).first()
        self.assertIsNotNone(file)
        self.assertEqual(file.size, size)
        self.assertEqual(file.path, filepath)
        self.assertEqual(file.extension, ".doc")

    def test__update_existing_object(self):
        name = "file.doc"
        filepath = f"{self.directory.path}/{name}"
        old_size = self.random_int(10, 100000000)
        self.storage.size.return_value = old_size

        sync_file(self.storage, filepath, self.directory)

        file = StorageObject.objects.filter(path=filepath, is_file=True).first()
        self.assertEqual(file.size, old_size)

        # test that new size will be used in existing File
        new_size = self.random_int(100000, 100000000000)
        self.storage.size.return_value = new_size

        sync_file(self.storage, filepath, self.directory)

        file = StorageObject.objects.filter(path=filepath, is_file=True).first()
        self.assertEqual(file.size, new_size)


class SyncFilesTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.storage_patch = mock.patch(
            "poms.common.storage",
            spec=FinmarsS3Storage,
        )
        self.storage = self.storage_patch.start()
        self.addCleanup(self.storage_patch.stop)
        self.directory = StorageObject.objects.create(path="/root")

    def test__files_created(self):
        # Mock the listdir return values
        f1 = "file.xls"
        f2 = "file.zip"
        filepath_1 = f"{self.directory.path}/{f1}"
        filepath_2 = f"{self.directory.path}/{f2}"
        size = self.random_int(10000, 100000000)
        self.storage.listdir.return_value = ([], [filepath_1, filepath_2])
        self.storage.size.return_value = size

        sync_storage_objects(self.storage, self.directory)

        files = StorageObject.objects.filter(is_file=True).all()

        self.assertEqual(files.count(), 2)

    def test__directories_created(self):
        # Mock the listdir return values
        dirpath_1 = f"{self.directory.path}/dir1"
        dirpath_2 = f"{self.directory.path}/dir2"
        self.storage.listdir.side_effect = [
            ([dirpath_1, dirpath_2], []),
            ([], []),
            ([], []),
        ]
        sync_storage_objects(self.storage, self.directory)

        directories = StorageObject.objects.all()

        self.assertEqual(directories.count(), 3)
