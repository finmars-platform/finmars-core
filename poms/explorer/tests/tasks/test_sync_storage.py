from unittest import mock

# from poms.celery_tasks.models import CeleryTask
from poms.common.common_base_test import BaseTestCase
from poms.common.storage import FinmarsS3Storage
from poms.explorer.models import FinmarsDirectory, FinmarsFile
from poms.explorer.utils import (
    sync_file_in_database,
    sync_storage_objects,
)


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
        self.directory = FinmarsDirectory.objects.create(path="/test/next")

    def test__created_new_object(self):
        name = "file.doc"
        filepath = f"{self.directory.path}/{name}"
        size = self.random_int(1000, 1000000)
        self.storage.size.return_value = size

        sync_file_in_database(self.storage, filepath, self.directory)

        file = FinmarsFile.objects.filter(name=name).first()
        self.assertIsNotNone(file)
        self.assertEqual(file.size, size)
        self.assertEqual(file.fullpath, filepath)
        self.assertEqual(file.extension, "doc")

    def test__update_existing_object(self):
        name = "file.doc"
        filepath = f"{self.directory.path}/{name}"
        old_size = self.random_int(10, 100000000)
        self.storage.size.return_value = old_size

        sync_file_in_database(self.storage, filepath, self.directory)

        file = FinmarsFile.objects.filter(name=name).first()
        self.assertEqual(file.size, old_size)

        # test that new size will be used in existing File
        new_size = self.random_int(100000, 100000000000)
        self.storage.size.return_value = new_size

        sync_file_in_database(self.storage, filepath, self.directory)

        file = FinmarsFile.objects.filter(name=name).first()
        self.assertEqual(file.size, new_size)


class SyncFilesTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.storage_patch = mock.patch(
            "poms.explorer.views.storage",
            spec=FinmarsS3Storage,
        )
        self.storage = self.storage_patch.start()
        self.addCleanup(self.storage_patch.stop)
        self.directory = FinmarsDirectory.objects.create(path="/root")

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

        files = FinmarsFile.objects.all()

        self.assertEqual(files.count(), 2)
