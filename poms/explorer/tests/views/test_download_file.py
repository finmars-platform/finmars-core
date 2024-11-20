from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile

from poms.common.common_base_test import BaseTestCase
from poms.common.storage import FinmarsS3Storage
from poms.explorer.models import get_root_path, AccessLevel, StorageObject
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
