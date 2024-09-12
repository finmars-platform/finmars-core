from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile

from poms.common.common_base_test import BaseTestCase
from poms.common.storage import FinmarsS3Storage
from poms.explorer.models import get_root_path, AccessLevel, StorageObject
from poms.explorer.policy_handlers import get_or_create_access_policy_to_path
from poms.explorer.tests.mixin import CreateUserMemberMixin


class ExplorerViewFileViewSetTest(CreateUserMemberMixin, BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.realm_code = "realm00000"
        self.space_code = "space00000"
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/explorer/view/"

        self.storage_patch = mock.patch(
            "poms.explorer.views.storage",
            spec=FinmarsS3Storage,
        )
        self.storage_mock = self.storage_patch.start()
        self.addCleanup(self.storage_patch.stop)

    def test__no_path(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 400)

    def test__path_invalid(self):
        path = self.random_string()
        self.storage_mock.open.side_effect = FileNotFoundError("No such file")

        response = self.client.get(self.url, {"path": path})
        self.assertEqual(response.status_code, 400)

    def test__valid_file(self):
        path = f"{self.random_string()}.txt"
        content = b"file content"
        mock_file = SimpleUploadedFile(
            path,
            content,
            content_type="text/plain",
        )

        self.storage_mock.open.return_value = mock_file

        response = self.client.get(self.url, {"path": path})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, content)

    def test__no_permission(self):
        user, member = self.create_user_member()
        self.client.force_authenticate(user=user)
        file_name = f"{self.random_string()}.{self.random_string(3)}"

        response = self.client.get(self.url, {"path": file_name})

        self.assertEqual(response.status_code, 403)

    def test__has_root_permission(self):
        user, member = self.create_user_member()

        root_path = get_root_path()
        root = StorageObject.objects.create(path=root_path)
        get_or_create_access_policy_to_path(root_path, member, AccessLevel.READ)

        file_name = f"{self.random_string()}.{self.random_string(3)}"
        StorageObject.objects.create(path=file_name, size=1111, parent=root, is_file=True)

        self.client.force_authenticate(user=user)

        response = self.client.get(self.url, {"path": file_name})

        self.assertEqual(response.status_code, 200)
