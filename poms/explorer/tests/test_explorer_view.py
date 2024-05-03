from datetime import datetime
from unittest import mock

from poms.common.common_base_test import BaseTestCase
from poms.common.storage import FinmarsS3Storage


class ExplorerViewSetTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()

        self.realm_code = "realm00000"
        self.space_code = "space00000"
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/explorer/explorer/"

        self.storage_patch = mock.patch(
            "poms.explorer.views.storage",
            spec=FinmarsS3Storage,
        )
        self.storage_mock = self.storage_patch.start()
        self.addCleanup(self.storage_patch.stop)

        self.mimetypes_patch = mock.patch(
            "poms.explorer.views.mimetypes.guess_type",
            return_value=("text/plain", "utf-8"),
        )
        self.mimetypes_mock = self.mimetypes_patch.start()
        self.addCleanup(self.mimetypes_patch.stop)

    @BaseTestCase.cases(
        ("1", "test/"),
        ("2", "/test"),
        ("3", "/test/"),
    )
    def test__path_ends_or_starts_with_slash(self, path):
        response = self.client.get(self.url, {"path": path})
        self.assertEqual(response.status_code, 400)

    @BaseTestCase.cases(
        ("null", ""),
        ("test", "test"),
        ("test_test", "test/test"),
    )
    def test__with_empty_path(self, path):
        self.storage_mock.listdir.return_value = [], []

        response = self.client.get(self.url, {"path": path})

        self.assertEqual(response.status_code, 200)
        self.storage_mock.listdir.assert_called_once()

        response_data = response.json()
        if path:
            self.assertEqual(response_data["path"], f"{self.space_code}/{path}/")
        else:
            self.assertEqual(response_data["path"], f"{self.space_code}/")
        self.assertEqual(response_data["results"], [])

    @BaseTestCase.cases(
        ("null", ""),
        ("test", "test"),
        ("test_test", "test/test"),
    )
    def test__path(self, path):
        directories = ["first", "second"]
        files = ["file.csv", "file.txt", "file.json"]
        size = self.random_int(10000, 50000)

        self.storage_mock.listdir.return_value = directories, files
        self.storage_mock.get_created_time.return_value = datetime.now()
        self.storage_mock.get_modified_time.return_value = datetime.now()
        self.storage_mock.size.return_value = size
        self.storage_mock.convert_size.return_value = f"{size // 1024}KB"

        response = self.client.get(self.url, {"path": path})

        self.assertEqual(response.status_code, 200)
        self.storage_mock.listdir.assert_called_once()

        response_data = response.json()
        if path:
            self.assertEqual(response_data["path"], f"{self.space_code}/{path}/")
        else:
            self.assertEqual(response_data["path"], f"{self.space_code}/")
        self.assertEqual(len(response_data["results"]), len(directories) + len(files))
