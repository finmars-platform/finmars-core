from unittest import mock

from poms.common.common_base_test import BaseTestCase
from poms.common.storage import FinmarsS3Storage
from poms.explorer.tests.mixin import CreateUserMemberMixin


class ExplorerDeletePathViewTest(CreateUserMemberMixin, BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()

        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/explorer/delete/"

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
    def test__path_error(self, path):
        response = self.client.post(
            f"{self.url}?path={path}",
        )
        self.assertEqual(response.status_code, 400)

    @BaseTestCase.cases(
        ("1", ""),
        ("2", "false"),
        ("3", "0"),
    )
    def test__delete_file(self, is_dir):
        response = self.client.post(
            f"{self.url}?path=sokol-1/test-create-2.txt&is_dir={is_dir}",
        )
        self.assertEqual(response.status_code, 200)
        self.storage_mock.delete.assert_called_once()
        self.storage_mock.delete_directory.assert_not_called()

    @BaseTestCase.cases(
        ("1", "1"),
        ("2", "true"),
        ("3", "yes"),
    )
    def test__delete_directory(self, is_dir):
        response = self.client.post(
            f"{self.url}?path=sokol-1/test&is_dir={is_dir}",
        )

        self.assertEqual(response.status_code, 200)
        self.storage_mock.delete_directory.assert_called_once()
        self.storage_mock.delete.assert_not_called()
