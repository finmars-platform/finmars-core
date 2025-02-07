from unittest import mock

from poms.celery_tasks.models import CeleryTask
from poms.common.common_base_test import BaseTestCase
from poms.common.storage import FinmarsS3Storage, by_chunk
from poms.explorer.models import DIR_SUFFIX, StorageObject
from poms.explorer.utils import (
    define_content_type,
    delete_all_file_objects,
    join_path,
    last_dir_name,
    move_dir,
    update_or_create_file_and_parents,
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

        for _ in move_dir(self.storage, source_folder, destination_folder, self.celery_task):
            pass

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

        for _ in move_dir(self.storage, source_folder, destination_folder, self.celery_task):
            pass

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
        for _ in move_dir(self.storage, source_folder, destination_folder, self.celery_task):
            pass

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


class DeleteFilesTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()

    def test__file_objects_deleted(self):
        StorageObject.objects.create(path="next/1.doc", size=1, is_file=True)
        StorageObject.objects.create(path="next/2.txt", size=2, is_file=True)

        self.assertEqual(StorageObject.objects.filter(is_file=True).count(), 2)

        delete_all_file_objects()

        self.assertEqual(StorageObject.objects.filter(is_file=True).count(), 0)


class CreateUpdateFileParentsTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.space = "space00000"

    def test__one_dir(self):
        size = self.random_int(0, 1000)
        update_or_create_file_and_parents(f"{self.space}/d1/file.txt", size)

        self.assertEqual(StorageObject.objects.filter(is_file=True).count(), 1)
        file = StorageObject.objects.filter(is_file=True).first()
        self.assertEqual(file.path, f"{self.space}/d1/file.txt")
        self.assertEqual(file.size, size)

        self.assertEqual(
            StorageObject.objects.filter(is_file=False).count(), 2  # root + d1
        )
        directory = StorageObject.objects.filter(is_file=False).last()
        self.assertEqual(directory.path, f"{self.space}/d1{DIR_SUFFIX}")
        self.assertEqual(directory.size, 0)
        self.assertEqual(directory.parent.path, f"{self.space}{DIR_SUFFIX}")

        self.assertEqual(file.parent, directory)

    def test__two_dir(self):
        size = self.random_int(0, 1000)
        update_or_create_file_and_parents(f"{self.space}/d1/d2/file.txt", size)

        self.assertEqual(StorageObject.objects.filter(is_file=True).count(), 1)
        file = StorageObject.objects.filter(is_file=True).first()
        self.assertEqual(file.path, f"{self.space}/d1/d2/file.txt")
        self.assertEqual(file.size, size)

        self.assertEqual(
            StorageObject.objects.filter(is_file=False).count(), 3
        )  # root + d1 + d2
        directory = StorageObject.objects.filter(is_file=False).last()
        self.assertEqual(directory.path, f"{self.space}/d1/d2{DIR_SUFFIX}")
        self.assertEqual(directory.size, 0)
        self.assertEqual(directory.parent.path, f"{self.space}/d1{DIR_SUFFIX}")

        self.assertEqual(file.parent, directory)

    def test__no_dir(self):
        with self.assertRaises(RuntimeError):
            update_or_create_file_and_parents("file.txt", 11111)

    def test__empty_path(self):
        with self.assertRaises(RuntimeError):
            update_or_create_file_and_parents("", 0)

    def test__first_slash_one_dir(self):
        size = self.random_int(0, 1000)
        update_or_create_file_and_parents(f"/{self.space}/d1/file.txt", size)

        self.assertEqual(StorageObject.objects.filter(is_file=True).count(), 1)
        file = StorageObject.objects.filter(is_file=True).first()
        self.assertEqual(file.path, f"{self.space}/d1/file.txt")
        self.assertEqual(file.size, size)

        self.assertEqual(
            StorageObject.objects.filter(is_file=False).count(), 2  # root + d1
        )
        directory = StorageObject.objects.filter(is_file=False).last()
        self.assertEqual(directory.path, f"{self.space}/d1{DIR_SUFFIX}")
        self.assertEqual(directory.size, 0)
        self.assertEqual(directory.parent.path, f"{self.space}{DIR_SUFFIX}")

        self.assertEqual(file.parent, directory)


class ByChunkTest(BaseTestCase):

    @BaseTestCase.cases(
        ("1", [1,2,3,4,5,6,7,8,9,0], 2, 5),
        ("2", [1,2,3,4,5,6,7,8,9,0], 3, 4),
        ("3", [1,2,3,4,5,6,7,8,9,0], 4, 3),
        ("4", [1,2,3,4,5,6,7,8,9,0], 8, 2),
        ("5", [1,2,3,4,5,6,7,8,9,0], 10, 1),
        ("6", [1,2,3,4,5,6,7,8,9,0], 1, 10),
    )
    def test_chunks(self, items, chunk_size, result):
        count = sum(1 for _ in by_chunk(items, chunk_size))
        self.assertEqual(count, result)
