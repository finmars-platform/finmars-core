from unittest import mock, skip

from django.test import override_settings

from poms.common.common_base_test import BaseTestCase
from poms.common.storage import FinmarsS3Storage
from poms.explorer.models import (
    DIR_SUFFIX,
    get_root_path,
    AccessLevel,
    StorageObject,
)
from poms.explorer.policy_handlers import get_or_create_access_policy_to_path
from poms.explorer.tests.mixin import CreateUserMemberMixin


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class RenameViewSetTest(CreateUserMemberMixin, BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.realm_code = "realm00000"
        self.space_code = "space00000"
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/explorer/rename/"

        self.storage_patch = mock.patch(
            "poms.explorer.views.storage",
            spec=FinmarsS3Storage,
        )
        self.storage_mock = self.storage_patch.start()
        self.addCleanup(self.storage_patch.stop)

    @BaseTestCase.cases(
        ("no_data", {}),
        ("no_required_data", {"action": "rename"}),
        ("no_new_name", {"path": "test"}),
        ("empty_path", {"path": "", "new_name": "file.txt"}),
        ("no_path", {"new_name": "file.txt"}),
    )
    def test__invalid_data(self, request_data):
        self.storage_mock.listdir.return_value = [], []
        response = self.client.post(self.url, request_data, format="json")
        self.assertEqual(response.status_code, 400)

    def test__path_does_not_exist(self):
        request_data = {"path": "invalid", "new_name": "file.txt"}
        self.storage_mock.exists.return_value = False
        response = self.client.post(self.url, request_data, format="json")
        self.assertEqual(response.status_code, 400)

    @BaseTestCase.cases(
        ("path_1", {"path": "/test", "new_name": "file.txt"}),
        ("path_2", {"path": "test/", "new_name": "file.txt"}),
        ("path_3", {"path": "/test/", "new_name": "file.txt"}),
        ("name_1", {"path": "test", "new_name": "/file.txt"}),
        ("name_2", {"path": "test", "new_name": "file.txt/"}),
        ("name_3", {"path": "test", "new_name": "/file.txt/"}),
        ("no_slashes", {"path": "test", "new_name": "file.txt"}),
    )
    def test__valid_data(self, request_data):
        response = self.client.post(self.url, request_data, format="json")
        response_json = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_json["status"], "ok")
        self.assertIn("task_id", response_json)
        self.assertIsNotNone(response_json["task_id"])

    @skip("permissions not implemented")
    def test__no_permission(self):
        user, member = self.create_user_member()
        self.client.force_authenticate(user=user)

        data = {"path": "/test", "new_name": "file.txt"}

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, 403)

    @skip("permissions not implemented")
    def test__has_root_permission(self):
        user, member = self.create_user_member()
        path = "test/file.txt"
        file_name = "file2.txt"
        data = {"path": path, "new_name": file_name}

        root_path = get_root_path()
        root = StorageObject.objects.create(path=root_path)
        get_or_create_access_policy_to_path(root_path, member, AccessLevel.READ)
        get_or_create_access_policy_to_path(root_path, member, AccessLevel.WRITE)

        StorageObject.objects.create(path=f"{path}{DIR_SUFFIX}", parent=root)
        StorageObject.objects.create(path=file_name, size=333, parent=root, is_file=True)

        self.client.force_authenticate(user=user)

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, 200)
