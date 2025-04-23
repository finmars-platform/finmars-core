from unittest import mock

from poms.common.common_base_test import BaseTestCase
from poms.common.storage import FinmarsS3Storage
from poms.explorer.tests.mixin import CreateUserMemberMixin


class ExplorerDeleteFolderViewTest(CreateUserMemberMixin, BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()

        self.url = (
            f"/{self.realm_code}/{self.space_code}/api/v1/explorer/delete-folder/"
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

    def test__chunk_ok(self):
        path = "/dummy/path"
        response = self.client.post(self.url, {"path": path})
        self.assertEqual(response.status_code, 200)

        self.storage_mock.delete_directory.assert_called_with(
            f"{self.space_code}{path}"
        )
