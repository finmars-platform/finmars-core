from unittest import mock
from datetime import datetime

from poms.common.common_base_test import BaseTestCase

from poms.common.storage import FinmarsS3Storage


class ExplorerViewSetTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.realm_code = "realm00000"
        self.space_code = "space00000"
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/explorer/explorer/"

    @mock.patch("poms.explorer.views.storage")
    def test__no_path(self, storage):
        storage.return_value = mock.MagicMock(spec=FinmarsS3Storage)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 400)

    @BaseTestCase.cases(
        ("1", "test/"),
        ("2", "/test"),
        ("3", "/test/"),
    )
    @mock.patch("poms.explorer.views.storage")
    def test__path_ends_with_slash(self, path, storage):
        storage.return_value = mock.MagicMock(spec=FinmarsS3Storage)

        response = self.client.get(self.url, {"path": path})
        self.assertEqual(response.status_code, 400)

    @BaseTestCase.cases(
        ("test", "test"),
        ("test_test", "test/test"),
    )
    @mock.patch("poms.explorer.views.storage")
    def test__with_empty_path(self, path, storage):
        storage.return_value = mock.MagicMock(spec=FinmarsS3Storage)
        storage.listdir.return_value = [], []

        response = self.client.get(self.url, {"path": path})

        self.assertEqual(response.status_code, 200)

        storage.listdir.assert_called_once()

        response_data = response.json()

        self.assertEqual(response_data["path"], f"{self.space_code}/{path}/")
        self.assertEqual(response_data["results"], [])

    @mock.patch("poms.explorer.views.mimetypes.guess_type")
    @mock.patch("poms.explorer.views.storage")
    def test__path(self, storage, mock_guess_type):
        mock_guess_type.return_value = "text/plain", "utf-8"
        storage.return_value = mock.MagicMock(spec=FinmarsS3Storage)
        directories = ["first", "second"]
        files = ["file.csv", "file.txt", "file.json"]
        path = self.random_string(10)
        storage.listdir.return_value = directories, files
        storage.get_created_time.return_value = datetime.now()
        storage.get_modified_time.return_value = datetime.now()
        size = self.random_int(10000, 50000)
        storage.size.return_value = size
        storage.convert_size.return_value = f"{size // 1024}KB"

        response = self.client.get(self.url, {"path": path})

        self.assertEqual(response.status_code, 200)

        storage.listdir.assert_called_once()

        response_data = response.json()
        print(response_data)
        self.assertEqual(response_data["path"], f"{self.space_code}/{path}/")
        self.assertEqual(len(response_data["results"]), len(directories) + len(files))
