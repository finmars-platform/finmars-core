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


class ExplorerDeletePathViewTest(CreateUserMemberMixin, BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()

        self.realm_code = "realm00000"
        self.space_code = "space00000"
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

    def test__no_permission_file(self):
        user, member = self.create_user_member()
        self.client.force_authenticate(user=user)

        file_name = f"{self.random_string()}.{self.random_string(3)}"

        response = self.client.post(f"{self.url}?path={file_name}&is_dir=false")

        self.assertEqual(response.status_code, 403)

    def test__no_permission_dir(self):
        user, member = self.create_user_member()
        self.client.force_authenticate(user=user)

        dir_name = f"{self.random_string()}/{self.random_string()}"

        response = self.client.post(f"{self.url}?path={dir_name}&is_dir=true")

        self.assertEqual(response.status_code, 403)

    def test__has_root_permission_file(self):
        user, member = self.create_user_member()

        root = FinmarsDirectory.objects.create(path=ROOT_PATH)
        get_or_create_access_policy_to_path(ROOT_PATH, member, AccessLevel.WRITE)

        file_name = f"{self.random_string()}.{self.random_string(3)}"
        FinmarsFile.objects.create(path=file_name, parent=root, size=555)

        self.client.force_authenticate(user=user)

        response = self.client.post(f"{self.url}?path={file_name}&is_dir=false")

        self.assertEqual(response.status_code, 200)

    def test__has_root_permission_dir(self):
        user, member = self.create_user_member()

        root = FinmarsDirectory.objects.create(path=ROOT_PATH)
        get_or_create_access_policy_to_path(ROOT_PATH, member, AccessLevel.WRITE)

        dir_name = f"{self.random_string()}/{self.random_string()}"
        FinmarsDirectory.objects.create(path=f"{dir_name}{DIR_SUFFIX}", parent=root)

        self.client.force_authenticate(user=user)

        response = self.client.post(f"{self.url}?path={dir_name}&is_dir=true")

        self.assertEqual(response.status_code, 200)
