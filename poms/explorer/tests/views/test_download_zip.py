import tempfile
from unittest import mock

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
        self.url = (
            f"/{self.realm_code}/{self.space_code}/api/v1/explorer/download-as-zip/"
        )

        self.storage_patch = mock.patch(
            "poms.explorer.views.storage",
            spec=FinmarsS3Storage,
        )
        self.storage_mock = self.storage_patch.start()
        self.addCleanup(self.storage_patch.stop)

    def test__no_paths(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 400)

    def test__paths_invalid(self):
        path = self.random_string()
        self.storage_mock.download_paths_as_zip.side_effect = FileNotFoundError(
            "No such file"
        )
        response = self.client.post(self.url, {"paths": [path, path]})
        self.assertEqual(response.status_code, 400)

    def test__valid_files(self):
        path = f"{self.random_string()}.txt"
        # Create a temporary test file
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file_path = temp_file.name
        self.storage_mock.download_paths_as_zip.return_value = temp_file_path

        response = self.client.post(self.url, {"paths": [path]}, format="json")
        self.assertEqual(response.status_code, 200)

    def test__no_permission(self):
        user, member = self.create_user_member()
        self.client.force_authenticate(user=user)

        path = f"{self.random_string()}.txt"

        response = self.client.post(self.url, {"paths": [path]})

        self.assertEqual(response.status_code, 403)

    def test__has_root_permission(self):
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file_path = temp_file.name
        self.storage_mock.download_paths_as_zip.return_value = temp_file_path

        user, member = self.create_user_member()

        root_path = get_root_path()
        root = StorageObject.objects.create(path=root_path)
        get_or_create_access_policy_to_path(root_path, member, AccessLevel.READ)

        path = f"{self.random_string()}.txt"
        StorageObject.objects.create(path=path, size=777, parent=root, is_file=True)

        self.client.force_authenticate(user=user)

        response = self.client.post(self.url, {"paths": [path]}, format="json")

        self.assertEqual(response.status_code, 200)
