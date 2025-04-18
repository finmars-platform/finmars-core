from unittest import mock

from django.test import override_settings

from poms.common.common_base_test import BaseTestCase
from poms.common.storage import FinmarsS3Storage
from poms.explorer.tests.mixin import CreateUserMemberMixin


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class CopyViewSetTest(CreateUserMemberMixin, BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.realm_code = "realm00000"
        self.space_code = "space00000"
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/explorer/copy/"

        self.storage_patch = mock.patch(
            "poms.explorer.views.storage",
            spec=FinmarsS3Storage,
        )
        self.storage_mock = self.storage_patch.start()
        self.addCleanup(self.storage_patch.stop)

    @BaseTestCase.cases(
        ("no_data", {}),
        ("no_required_data", {"action": "copy"}),
        ("no_items", {"target_directory_path": "test"}),
        ("empty_target", {"target_directory_path": "", "paths": ["other/file.txt"]}),
        ("no_target", {"paths": ["test/file.txt"]}),
    )
    def test__invalid_data(self, request_data):
        self.storage_mock.listdir.return_value = [], []
        response = self.client.post(self.url, request_data, format="json")
        self.assertEqual(response.status_code, 400)

    def test__path_does_not_exist(self):
        request_data = {"target_directory_path": "invalid", "paths": ["file.txt"]}
        self.storage_mock.dir_exists.return_value = False
        self.storage_mock.exists.return_value = False
        response = self.client.post(self.url, request_data, format="json")
        self.assertEqual(response.status_code, 400)

    @BaseTestCase.cases(
        ("target_1", {"target_directory_path": "/test", "paths": ["file.txt"]}),
        ("target_2", {"target_directory_path": "test/", "paths": ["file.txt"]}),
        ("target_3", {"target_directory_path": "/test/", "paths": ["file.txt"]}),
        ("item_1", {"target_directory_path": "test", "paths": ["/file.txt"]}),
        ("item_2", {"target_directory_path": "test", "paths": ["file.txt/"]}),
        ("item_3", {"target_directory_path": "test", "paths": ["/file.txt/"]}),
        ("no_slashes", {"target_directory_path": "test", "paths": ["file.txt"]}),
    )
    def test__valid_data(self, request_data):
        response = self.client.post(self.url, request_data, format="json")
        response_json = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_json["status"], "ok")
        self.assertIn("task_id", response_json)
        self.assertIsNotNone(response_json["task_id"])
