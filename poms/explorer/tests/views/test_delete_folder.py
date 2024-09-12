from unittest import mock

from poms.common.common_base_test import BaseTestCase
from poms.common.storage import FinmarsS3Storage
from poms.explorer.models import DIR_SUFFIX, get_root_path, AccessLevel, StorageObject
from poms.explorer.policy_handlers import get_or_create_access_policy_to_path
from poms.explorer.tests.mixin import CreateUserMemberMixin


class ExplorerDeleteFolderViewTest(CreateUserMemberMixin, BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()

        self.realm_code = "realm00000"
        self.space_code = "space00000"
        self.url = (
            f"/{self.realm_code}/{self.space_code}/api/v1/explorer/" f"delete-folder/"
        )

        self.storage_patch = mock.patch(
            "poms.explorer.views.storage",
            spec=FinmarsS3Storage,
        )
        self.storage_mock = self.storage_patch.start()
        self.addCleanup(self.storage_patch.stop)

    @BaseTestCase.cases(
        ("1", ""),
        ("2", "/"),
        ("3", ".system/super"),
    )
    def test__no_path_error(self, path):
        response = self.client.post(self.url, {"path": path})
        self.assertEqual(response.status_code, 400)

    def test__no_permission(self):
        user, member = self.create_user_member()
        self.client.force_authenticate(user=user)

        dir_name = f"{self.random_string()}/{self.random_string()}"

        response = self.client.post(self.url, {"path": dir_name})

        self.assertEqual(response.status_code, 403)

    def test__has_root_permission(self):
        user, member = self.create_user_member()

        root_path = get_root_path()
        root = StorageObject.objects.create(path=root_path)
        get_or_create_access_policy_to_path(root_path, member, AccessLevel.WRITE)

        dir_name = f"{self.random_string()}/{self.random_string()}"
        StorageObject.objects.create(path=f"{dir_name}{DIR_SUFFIX}", parent=root)

        self.client.force_authenticate(user=user)

        response = self.client.post(self.url, {"path": dir_name})

        self.assertEqual(response.status_code, 200)
