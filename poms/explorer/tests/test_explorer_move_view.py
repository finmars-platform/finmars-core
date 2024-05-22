from unittest import mock

from poms.common.common_base_test import BaseTestCase
from poms.common.storage import FinmarsS3Storage


class MoveViewSetTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.realm_code = "realm00000"
        self.space_code = "space00000"
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/explorer/move/"

        self.storage_patch = mock.patch(
            "poms.explorer.views.storage",
            spec=FinmarsS3Storage,
        )
        self.storage_mock = self.storage_patch.start()
        self.addCleanup(self.storage_patch.stop)

    @BaseTestCase.cases(
        ("no_data", {}),
        ("no_required_data", {"action": "move"}),
        ("no_items", {"target_directory_path": "test"}),
        ("empty_items", {"target_directory_path": "test", "items": []}),
        ("inv_target_1", {"target_directory_path": "/test", "items": ["file.txt"]}),
        ("inv_target_2", {"target_directory_path": "test/", "items": ["file.txt"]}),
        ("inv_item_1", {"target_directory_path": "test", "items": ["/file.txt"]}),
        ("inv_item_2", {"target_directory_path": "test", "items": ["test/file.txt"]}),
        ("empty_target", {"target_directory_path": "", "items": ["test/file.txt"]}),
        ("no_target", {"items": ["test/file.txt"]}),
    )
    def test__invalid_data(self, request_data):
        self.storage_mock.exists.return_value = True
        response = self.client.post(self.url, request_data)
        self.assertEqual(response.status_code, 400)

    def test__path_does_not_exist(self):
        request_data = {"target_directory_path": "test", "items": ["file.txt"]}
        self.storage_mock.exists.return_value = False
        response = self.client.post(self.url, request_data)
        self.assertEqual(response.status_code, 400)

    def test__valid_data(self):
        request_data = {"target_directory_path": "test", "items": ["file.txt"]}
        self.storage_mock.exists.return_value = True
        self.storage_mock.listdir.return_value = ([], ["file.txt"])
        response = self.client.post(self.url, request_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"status": "ok"})
