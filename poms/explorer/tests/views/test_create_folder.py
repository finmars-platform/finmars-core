from unittest import mock

from poms.common.common_base_test import BaseTestCase
from poms.common.storage import FinmarsS3Storage
from poms.explorer.models import ROOT_PATH, AccessLevel, FinmarsDirectory
from poms.explorer.policy_handlers import get_or_create_access_policy_to_path
from poms.explorer.tests.mixin import CreateUserMemberMixin


class ExplorerCreateFolderViewTest(CreateUserMemberMixin, BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()

        self.realm_code = "realm00000"
        self.space_code = "space00000"
        self.url = (
            f"/{self.realm_code}/{self.space_code}/api/v1/explorer/" f"create-folder/"
        )

        self.storage_patch = mock.patch(
            "poms.explorer.views.storage",
            spec=FinmarsS3Storage,
        )
        self.storage_mock = self.storage_patch.start()
        self.addCleanup(self.storage_patch.stop)

    def test__no_path(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 400)

    @BaseTestCase.cases(
        ("1_test_test", "test/test"),
        ("2_test_test", "/test/test"),
        ("2_test_test", "/test/test/"),
        ("2_test_test", "test/test/"),
    )
    def test__create_folder_path(self, path):
        response = self.client.post(self.url, {"path": path})

        self.assertEqual(response.status_code, 200)
        self.storage_mock.save.assert_called_once()

        response_data = response.json()
        self.assertEqual(response_data["path"], f"{self.space_code}/test/test/")

    def test__no_permission(self):
        user, member = self.create_user_member()
        self.client.force_authenticate(user=user)

        dir_name = f"{self.random_string()}/{self.random_string()}"

        response = self.client.post(self.url, {"path": dir_name})

        self.assertEqual(response.status_code, 403)

    def test__has_root_permission(self):
        user, member = self.create_user_member()

        FinmarsDirectory.objects.create(path=ROOT_PATH)
        get_or_create_access_policy_to_path(ROOT_PATH, member, AccessLevel.WRITE)

        dir_name = f"{self.random_string()}/{self.random_string()}"

        self.client.force_authenticate(user=user)

        response = self.client.post(self.url, {"path": dir_name})

        self.assertEqual(response.status_code, 200)
