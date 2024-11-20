from unittest import mock

from poms.common.common_base_test import BaseTestCase
from poms.common.storage import FinmarsS3Storage
from poms.explorer.models import AccessLevel, StorageObject, get_root_path
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
        ("3_test_test", "/test/test/"),
        ("4_test_test", "test/test/"),
    )
    def test__create_folder_path(self, path):
        response = self.client.post(self.url, {"path": path})

        self.assertEqual(response.status_code, 200)
        self.storage_mock.save.assert_called_once()

        response_data = response.json()
        self.assertEqual(response_data["path"], f"{self.space_code}/test/test/")
        self.storage_mock.save.assert_called_with(
            f"{self.space_code}/test/test/.init",
            mock.ANY,
        )
