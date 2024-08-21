from unittest import mock

from poms.common.common_base_test import BaseTestCase
from poms.common.storage import FinmarsS3Storage
from poms.explorer.models import (
    DIR_SUFFIX,
    AccessLevel,
    FinmarsDirectory,
    FinmarsFile,
    get_root_path,
)
from poms.explorer.policy_handlers import get_or_create_access_policy_to_path
from poms.explorer.tests.mixin import CreateUserMemberMixin


class UnzipViewSetTest(CreateUserMemberMixin, BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()

        self.realm_code = "realm00000"
        self.space_code = "space00000"
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/explorer/unzip/"

        self.storage_patch = mock.patch(
            "poms.explorer.views.storage",
            spec=FinmarsS3Storage,
        )
        self.storage_mock = self.storage_patch.start()
        self.addCleanup(self.storage_patch.stop)

    @BaseTestCase.cases(
        ("no_target_1", {"target_directory_path": "", "file_path": "file"}),
        ("no_target_2", {"file_path": "file"}),
        ("no_file_path_1", {"target_directory_path": "target", "file_path": ""}),
        ("no_file_path_2", {"target_directory_path": "target"}),
    )
    def test__path_ends_or_starts_with_slash(self, request_data):
        response = self.client.post(self.url, request_data, format="json")
        self.assertEqual(response.status_code, 400)

    def test__path_does_not_exist(self):
        request_data = {"target_directory_path": "invalid", "file_path": "file"}
        self.storage_mock.dir_exists.return_value = False
        response = self.client.post(self.url, request_data, format="json")
        self.assertEqual(response.status_code, 400)

    @BaseTestCase.cases(
        ("short_target", {"target_directory_path": "target", "file_path": "file.zip"}),
        ("short_target", {"target_directory_path": "target", "file_path": "/file.zip"}),
        (
            "short_target",
            {"target_directory_path": "target", "file_path": "/abc/file.zip"},
        ),
        ("long_target_1", {"target_directory_path": "/a/b/c", "file_path": "file.zip"}),
        ("long_target_2", {"target_directory_path": "a/b/c/", "file_path": "file.zip"}),
        (
            "long_target_3",
            {"target_directory_path": "/a/b/c/", "file_path": "file.zip"},
        ),
        ("long_target_4", {"target_directory_path": "a/b/c", "file_path": "file.zip"}),
    )
    @mock.patch("poms.explorer.serializers.path_is_file")
    @mock.patch("poms.explorer.views.unzip_file_in_storage.apply_async")
    def test__unzip(self, request_data, mock_unzip, mock_is_file):
        self.storage_mock.dir_exists.return_value = True
        mock_is_file.return_value = True

        response = self.client.post(self.url, request_data, format="json")
        response_json = response.json()

        self.assertEqual(response.status_code, 200)

        mock_is_file.assert_called_once()
        mock_unzip.assert_called_once()

        self.assertIn("status", response_json)
        self.assertEqual(response_json["status"], "ok")
        self.assertIn("task_id", response_json)

        _, passed_kwargs = mock_unzip.call_args_list[0]
        kwargs = passed_kwargs["kwargs"]

        self.assertIn("task_id", kwargs)
        self.assertIn("context", kwargs)
        self.assertEqual(
            kwargs["context"],
            {
                "space_code": "space00000",
                "realm_code": "realm00000",
            },
        )

    def test__no_permission(self):
        user, member = self.create_user_member()
        self.client.force_authenticate(user=user)

        data = {"target_directory_path": "target", "file_path": "file.zip"}

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, 403)

    @mock.patch("poms.explorer.serializers.path_is_file")
    @mock.patch("poms.explorer.views.unzip_file_in_storage.apply_async")
    def test__has_root_permission(self, mock_unzip, mock_is_file):
        self.storage_mock.dir_exists.return_value = True
        mock_is_file.return_value = True
        user, member = self.create_user_member()
        to_dir = "test/next"
        file_name = "file.zip"
        data = {"target_directory_path": to_dir, "file_path": file_name}

        root_path = get_root_path()
        root = FinmarsDirectory.objects.create(path=root_path)
        get_or_create_access_policy_to_path(root_path, member, AccessLevel.READ)
        get_or_create_access_policy_to_path(root_path, member, AccessLevel.WRITE)

        FinmarsDirectory.objects.create(path=f"{to_dir}{DIR_SUFFIX}", parent=root)
        FinmarsFile.objects.create(path=file_name, size=444, parent=root)

        self.client.force_authenticate(user=user)

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, 200)
