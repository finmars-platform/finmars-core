from datetime import datetime
from unittest import mock

from poms.common.common_base_test import BaseTestCase
from poms.common.storage import FinmarsS3Storage
from poms.explorer.tests.mixin import CreateUserMemberMixin


class ExplorerViewSetTest(CreateUserMemberMixin, BaseTestCase):
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
        self.assertEqual(response_data["count"], 0)
        self.assertIsNone(response_data["next"])
        self.assertIsNone(response_data["previous"])

    @BaseTestCase.cases(
        ("null", ""),
        ("test", "test"),
        ("test_1", "test/"),
        ("test_2", "/test"),
        ("test_3", "/test/"),
        ("test_test", "test/test"),
        ("test_test_1", "/test/test/"),
        ("test_test_2", "/test/test"),
        ("test_test_3", "test/test/"),
    )
    def test__path(self, path):
        directories = ["first", "second"]
        files = ["file.csv", "file.txt", "file.json"]
        size = self.random_int(10000, 50000)
        items_amount = len(directories) + len(files)

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
            self.assertEqual(
                response_data["path"], f"{self.space_code}/{path.strip('/')}/"
            )
        else:
            self.assertEqual(response_data["path"], f"{self.space_code}/")
        self.assertEqual(len(response_data["results"]), items_amount)
        self.assertEqual(response_data["count"], items_amount)
        self.assertIsNone(response_data["next"])
        self.assertIsNone(response_data["previous"])

    @BaseTestCase.cases(
        ("4_1", 4, 1),
        ("4_2", 4, 2),
    )
    def test__pagination(self, page_size, page):
        directories = ["one", "two", "three", "four", "five"]
        files = ["one.csv", "two.txt", "three.json", "four.csv", "five.txt"]
        total_items = len(directories) + len(files)
        size = self.random_int(1000000, 666000000)

        self.storage_mock.listdir.return_value = directories, files
        self.storage_mock.get_created_time.return_value = datetime.now()
        self.storage_mock.get_modified_time.return_value = datetime.now()
        self.storage_mock.size.return_value = size
        self.storage_mock.convert_size.return_value = f"{size // 1024}KB"

        response = self.client.get(
            self.url, {"path": "test_path", "page": page, "page_size": page_size}
        )

        self.assertEqual(response.status_code, 200)
        response_data = response.json()

        print("next", response_data["next"])
        print("previous", response_data["previous"])

        self.assertEqual(len(response_data["results"]), page_size)
        self.assertEqual(response_data["count"], total_items)
        if page > 1:
            self.assertIsNotNone(response_data["previous"])

        self.assertIsNotNone(response_data["next"])
