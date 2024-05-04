from unittest import mock

from poms.common.common_base_test import BaseTestCase
from poms.common.storage import FinmarsS3Storage
from django.core.files.uploadedfile import SimpleUploadedFile


class ExplorerUploadViewSetTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()

        self.realm_code = "realm00000"
        self.space_code = "space00000"
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/explorer/upload/"

        self.storage_patch = mock.patch(
            "poms.explorer.views.storage",
            spec=FinmarsS3Storage,
        )
        self.storage_mock = self.storage_patch.start()
        self.addCleanup(self.storage_patch.stop)

    def create_file(self, name: str = "test.txt"):
        file = SimpleUploadedFile(name, b'This is a test file')
        return file

    def test__no_path_no_files(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 200)

    def test__upload_one_file(self):
        file = self.create_file()
        response = self.client.post(self.url, {"file": file})
        self.assertEqual(response.status_code, 200)
        self.storage_mock.save.assert_called_once()

    @BaseTestCase.cases(
        ("test", "test"),
        ("test_test", "test/test"),
    )
    def test__with_path(self, path):
        file = self.create_file()

        response = self.client.post(self.url, {"path": path, "file": file})

        self.assertEqual(response.status_code, 200)
        self.storage_mock.save.assert_called_once()

        response_data = response.json()
        print(response_data)
        self.assertEqual(response_data["path"], f"{self.space_code}/{path}/")

    def test__import_path(self):
        file = self.create_file()
        response = self.client.post(self.url, {"path": "import", "file": file})

        self.assertEqual(response.status_code, 200)
        self.storage_mock.save.assert_called_once()

        response_data = response.json()

    #     self.storage_mock.listdir.return_value = directories, files
    #     self.storage_mock.get_created_time.return_value = datetime.now()
    #     self.storage_mock.get_modified_time.return_value = datetime.now()
    #     self.storage_mock.size.return_value = size
    #     self.storage_mock.convert_size.return_value = f"{size // 1024}KB"
    #
    #     response = self.client.get(self.url, {"path": path})
    #
    #     self.assertEqual(response.status_code, 200)
    #     self.storage_mock.listdir.assert_called_once()
    #
    #     response_data = response.json()
    #     if path:
    #         self.assertEqual(response_data["path"], f"{self.space_code}/{path}/")
    #     else:
    #         self.assertEqual(response_data["path"], f"{self.space_code}/")
    #     self.assertEqual(len(response_data["results"]), len(directories) + len(files))
