from unittest import mock

from poms.celery_tasks.models import CeleryTask
from poms.common.common_base_test import BaseTestCase
from poms.common.storage import FinmarsS3Storage
from poms.explorer.models import FinmarsFile
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

    def test__created_new_object(self):
        filepath = "/test/super/file.pdf"
        size = self.random_int(1000, 1000000)
        self.storage.size.return_value = size

        sync_file_in_database(self.storage, filepath)

        file = FinmarsFile.objects.filter(name="file.pdf").first()
        self.assertIsNotNone(file)
        self.assertEqual(file.size, size)
        self.assertEqual(file.path, "/test/super")
        self.assertEqual(file.extension, "pdf")

    def test__update_existing_object(self):
        filepath = "/test/next/file.pdf"
        old_size = self.random_int(10, 100000000)
        self.storage.size.return_value = old_size

        sync_file_in_database(self.storage, filepath)

        file = FinmarsFile.objects.filter(name="file.pdf").first()
        self.assertEqual(file.size, old_size)

        # test that new size will be used in existing File
        new_size = self.random_int(100000, 100000000000)
        self.storage.size.return_value = new_size

        sync_file_in_database(self.storage, filepath)

        file = FinmarsFile.objects.filter(name="file.pdf").first()
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

    def test__files_created(self):
        # Mock the listdir return values
        f1 = "/test/next/file_1.doc"
        f2 = "/test/next/file_2.zip"
        size = self.random_int(10000, 100000000)
        self.storage.listdir.return_value = ([], [f1, f2])
        self.storage.size.return_value = size

        sync_storage_objects(self.storage, "/test/next")

        files = FinmarsFile.objects.all()

        self.assertEqual(files.count(), 2)
