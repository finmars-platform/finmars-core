from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile

from poms.common.common_base_test import BaseTestCase
from poms.common.storage import FinmarsS3Storage
from poms.explorer.models import (
    DIR_SUFFIX,
    AccessLevel,
    StorageObject,
    get_root_path,
)
from poms.explorer.policy_handlers import get_or_create_access_policy_to_path
from poms.explorer.tests.mixin import CreateUserMemberMixin


class ExplorerUploadViewSetTest(CreateUserMemberMixin, BaseTestCase):
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

    @staticmethod
    def create_text_file(name: str = "test.txt"):
        return SimpleUploadedFile(name, b"This is a test file")

    @staticmethod
    def create_json_file(name: str = "test.json"):
        return SimpleUploadedFile(
            name,
            b'{"on_create": {"expression_procedure": []}}',
            content_type="application/json",
        )

    def test__no_path_no_files(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 200)

    def test__upload_one_file(self):
        file = self.create_text_file()
        response = self.client.post(self.url, {"file": file})
        self.assertEqual(response.status_code, 200)
        self.storage_mock.save.assert_called_once()

    @BaseTestCase.cases(
        ("test", "test"),
        ("test_test", "test/test"),
    )
    def test__with_path(self, path):
        file = self.create_text_file()

        response = self.client.post(self.url, {"path": path, "file": file})

        self.assertEqual(response.status_code, 200)
        self.storage_mock.save.assert_called_once()

        response_data = response.json()
        self.assertEqual(response_data["status"], "ok")
        self.assertEqual(response_data["path"], f"{self.space_code}/{path}")
        self.assertEqual(len(response_data["files"]), 1)

    def test__import_path(self):
        self.storage_mock.open.return_value = self.create_json_file()

        response = self.client.post(self.url, {"path": "import"})

        self.assertEqual(response.status_code, 200)
        self.storage_mock.save.assert_not_called()
        self.storage_mock.open.assert_called_once()

        response_data = response.json()
        self.assertEqual(response_data["path"], f"{self.space_code}/import")
        self.assertEqual(len(response_data["files"]), 0)

    def test__no_permission(self):
        user, member = self.create_user_member()
        self.client.force_authenticate(user=user)
        dir_name = f"{self.random_string()}{DIR_SUFFIX}"

        response = self.client.post(self.url, {"path": dir_name})

        self.assertEqual(response.status_code, 403)

    def test__has_root_permission(self):
        self.storage_mock.open.return_value = self.create_json_file()
        user, member = self.create_user_member()

        root_path = get_root_path()
        root = StorageObject.objects.create(path=root_path)
        get_or_create_access_policy_to_path(root_path, member, AccessLevel.WRITE)

        dir_name = f"{self.random_string()}{DIR_SUFFIX}"
        StorageObject.objects.create(path=dir_name, parent=root)

        self.client.force_authenticate(user=user)

        response = self.client.post(self.url, {"path": dir_name})

        self.assertEqual(response.status_code, 200)
