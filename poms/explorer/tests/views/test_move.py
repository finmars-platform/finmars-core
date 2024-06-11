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
        ("same_dir", {"target_directory_path": "test", "items": ["test/file.txt"]}),
        ("empty_target", {"target_directory_path": "", "items": ["other/file.txt"]}),
        ("no_target", {"items": ["test/file.txt"]}),
    )
    def test__invalid_data(self, request_data):
        self.storage_mock.listdir.return_value = [], []
        response = self.client.post(self.url, request_data)
        self.assertEqual(response.status_code, 400)

    def test__path_does_not_exist(self):
        request_data = {"target_directory_path": "invalid", "items": ["file.txt"]}
        self.storage_mock.dir_exists.return_value = False
        response = self.client.post(self.url, request_data)
        self.assertEqual(response.status_code, 400)

    @BaseTestCase.cases(
        ("target_1", {"target_directory_path": "/test", "items": ["file.txt"]}),
        ("target_2", {"target_directory_path": "test/", "items": ["file.txt"]}),
        ("target_3", {"target_directory_path": "/test/", "items": ["file.txt"]}),
        ("item_1", {"target_directory_path": "test", "items": ["/file.txt"]}),
        ("item_2", {"target_directory_path": "test", "items": ["file.txt/"]}),
        ("item_3", {"target_directory_path": "test", "items": ["/file.txt/"]}),
        ("no_slashes", {"target_directory_path": "test", "items": ["file.txt"]}),
    )
    def test__valid_data(self, request_data):
        response = self.client.post(self.url, request_data)
        response_json = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_json["status"], "ok")
        self.assertIn("task_id", response_json)
        self.assertIsNotNone(response_json["task_id"])
