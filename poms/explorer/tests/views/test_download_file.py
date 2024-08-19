from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile

from poms.common.common_base_test import BaseTestCase
from poms.common.storage import FinmarsS3Storage
from poms.explorer.models import ROOT_PATH, AccessLevel, FinmarsDirectory, FinmarsFile
from poms.explorer.policy_handlers import get_or_create_access_policy_to_path
from poms.explorer.tests.mixin import CreateUserMemberMixin


class ExplorerDownloadFileViewSetTest(CreateUserMemberMixin, BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.realm_code = "realm00000"
        self.space_code = "space00000"
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/explorer/download/"

        self.storage_patch = mock.patch(
            "poms.explorer.views.storage",
            spec=FinmarsS3Storage,
        )
        self.storage_mock = self.storage_patch.start()
        self.addCleanup(self.storage_patch.stop)

    def test__no_path(self):
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, 400)

    def test__path_invalid(self):
        path = self.random_string()
        self.storage_mock.open.side_effect = FileNotFoundError("No such file")

        response = self.client.post(self.url, {"path": path}, format="json")
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

        response = self.client.post(self.url, {"path": path}, format="json")
        self.assertEqual(response.status_code, 200)

    def test__no_permission(self):
        user, member = self.create_user_member()
        self.client.force_authenticate(user=user)
        file_name = f"{self.random_string()}.{self.random_string(3)}"

        response = self.client.post(self.url, {"path": file_name}, format="json")

        self.assertEqual(response.status_code, 403)

    def test__has_root_permission(self):
        content = b"file content"
        path = f"{self.random_string()}.txt"
        mock_file = SimpleUploadedFile(
            path,
            content,
            content_type="text/plain",
        )
        self.storage_mock.open.return_value = mock_file
        user, member = self.create_user_member()

        root = FinmarsDirectory.objects.create(path=ROOT_PATH)
        get_or_create_access_policy_to_path(ROOT_PATH, member, AccessLevel.READ)

        FinmarsFile.objects.create(path=path, size=888, parent=root)

        self.client.force_authenticate(user=user)

        response = self.client.post(self.url, {"path": path}, format="json")

        self.assertEqual(response.status_code, 200)
