from unittest import mock

from poms.celery_tasks.models import CeleryTask
from poms.common.common_base_test import BaseTestCase
from poms.common.storage import FinmarsS3Storage
from poms.explorer.models import FinmarsFile
from poms.explorer.utils import (
    define_content_type,
    join_path,
    last_dir_name,
    move_dir,
    sync_file_in_database,
    sync_files,
)


class DefineContentTypeTest(BaseTestCase):
    @BaseTestCase.cases(
        ("none", "file.pdf.html.csv.txt.xxx", None),
        ("no_extension", "file.pdf.html.csv.txt.", None),
        ("html", "file.pdf.html", "text/html"),
        ("text", "file.html.txt", "plain/text"),
        ("js", "file.css.js", "text/javascript"),
        ("csv", "file.html.csv", "text/csv"),
        ("json", "file.pdf.json", "application/json"),
        ("yml", "file.pdf.yml", "application/yaml"),
        ("yaml", "file.pdf.yaml", "application/yaml"),
        ("py", "file.js.py", "text/x-python"),
        ("png", "file.pdf.png", "image/png"),
        ("jpg", "file.png.jpg", "image/jpeg"),
        ("jpeg", "file.pdf.jpeg", "image/jpeg"),
        ("pdf", "file.html.pdf", "application/pdf"),
        ("doc", "file.pdf.doc", "application/msword"),
        ("docx", "file.pdf.docx", "application/msword"),
        ("css", "file.pdf.css", "text/css"),
        ("xls", "file.txt.xls", "application/vnd.ms-excel"),
        (
            "xlsx",
            "file.csv.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ),
    )
    def test__content_type(self, filename, content_type):
        self.assertEqual(define_content_type(filename), content_type)


class JoinPathTest(BaseTestCase):
    @BaseTestCase.cases(
        ("1", "realm0000.space0000", "path", "realm0000.space0000/path"),
        ("2", "realm0000.space0000", "/path", "realm0000.space0000/path"),
        ("3", "realm0000.space0000/", "/path", "realm0000.space0000/path"),
        ("4", "realm0000.space0000/", "path", "realm0000.space0000/path"),
        ("empty", "realm0000.space0000/", "", "realm0000.space0000"),
        ("null", "realm0000.space0000/", None, "realm0000.space0000"),
    )
    def test__content_type(self, space_code, path, result):
        self.assertEqual(join_path(space_code, path), result)


class TestMoveFolder(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.storage_patch = mock.patch(
            "poms.explorer.views.storage",
            spec=FinmarsS3Storage,
        )
        self.storage = self.storage_patch.start()
        self.addCleanup(self.storage_patch.stop)

        self.celery_task = CeleryTask.objects.create(
            master_user=self.master_user,
            member=self.member,
            verbose_name="Move directory in storage",
            type="move_directory_in_storage",
            options_object={},
            progress_object={
                "current": 0,
                "total": 100,
                "percent": 0,
                "description": "move_directory_in_storage starting ...",
            },
        )

    def test_move_empty_folder(self):
        self.storage.listdir.return_value = ([], [])
        source_folder = "empty_folder"
        destination_folder = "destination/folder"

        move_dir(self.storage, source_folder, destination_folder, self.celery_task)

        self.storage.listdir.assert_called_with(source_folder)

    def test_move_folder_with_subdirectories(self):
        source_folder = "source_folder"
        destination_folder = "destination/folder"

        # Mock the listdir return values
        self.storage.listdir.side_effect = [
            (["subdir1", "subdir2"], []),
            ([], []),
            ([], []),
        ]

        move_dir(self.storage, source_folder, destination_folder, self.celery_task)

        # Assert the recursive move of subdirectories
        self.assertEqual(self.storage.listdir.call_count, 3)
        expected_args = [
            ("source_folder",),
            ("source_folder/subdir1",),
            ("source_folder/subdir2",),
        ]
        for i in range(3):
            self.assertEqual(
                self.storage.listdir.call_args_list[i][0], expected_args[i]
            )

    def test_move_folder_with_files(self):
        source_folder = "from_folder"
        destination_folder = "destination/to_folder"
        file_content = b"file-content-12345"

        # Mock the listdir return values
        self.storage.listdir.return_value = ([], ["file1.txt"])
        self.storage.dir_exists.return_value = True
        self.storage.open.return_value.read.return_value = file_content
        move_dir(self.storage, source_folder, destination_folder, self.celery_task)

        # Assert the move of files
        self.storage.listdir.assert_called_with(source_folder)
        self.storage.open.assert_called_with(f"{source_folder}/file1.txt")
        self.storage.save.assert_called_once()
        self.storage.delete.assert_called_with(f"{source_folder}/file1.txt")
        args, kwargs = self.storage.save.call_args_list[0]
        self.assertEqual(args[0], f"{destination_folder}/file1.txt")


class LastDirTest(BaseTestCase):
    @BaseTestCase.cases(
        ("empty", "", ""),
        ("end_slash", "space0000/test/source/", "source/"),
        ("no_end_slash", "space0000/test/sp/source", "source/"),
    )
    def test__content_type(self, path, result):
        self.assertEqual(last_dir_name(path), result)


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

        sync_files(self.storage, "/test/next")

        files = FinmarsFile.objects.all()

        self.assertEqual(files.count(), 2)
