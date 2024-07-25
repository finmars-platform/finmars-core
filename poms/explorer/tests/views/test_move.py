from unittest import mock

from poms.common.common_base_test import BaseTestCase
from poms.common.storage import FinmarsS3Storage
from poms.explorer.models import (
    DIR_SUFFIX,
    ROOT_PATH,
    AccessLevel,
    FinmarsDirectory,
    FinmarsFile,
)
from poms.explorer.policy_handlers import get_or_create_access_policy_to_path
from poms.explorer.tests.mixin import CreateUserMemberMixin


class MoveViewSetTest(CreateUserMemberMixin, BaseTestCase):
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
        ("same_dir", {"target_directory_path": "test", "paths": ["test/file.txt"]}),
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

    def test__no_permission(self):
        user, member = self.create_user_member()
        self.client.force_authenticate(user=user)

        data = {"target_directory_path": "/test", "paths": ["file.txt"]}

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, 403)

    def test__has_root_permission(self):
        user, member = self.create_user_member()
        to_dir = "test/next"
        file_name = "file.txt"
        paths = [file_name]
        data = {"target_directory_path": to_dir, "paths": paths}

        root = FinmarsDirectory.objects.create(path=ROOT_PATH)
        get_or_create_access_policy_to_path(ROOT_PATH, member, AccessLevel.READ)
        get_or_create_access_policy_to_path(ROOT_PATH, member, AccessLevel.WRITE)

        FinmarsDirectory.objects.create(path=f"{to_dir}{DIR_SUFFIX}", parent=root)
        FinmarsFile.objects.create(path=file_name, size=333, parent=root)

        self.client.force_authenticate(user=user)

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, 200)
