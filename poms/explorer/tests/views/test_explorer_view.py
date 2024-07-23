from datetime import datetime
from unittest import mock

from django.contrib.auth.models import User

from poms.common.common_base_test import BaseTestCase
from poms.common.storage import FinmarsS3Storage
from poms.explorer.models import ROOT_PATH, AccessLevel, FinmarsDirectory
from poms.explorer.policy_handlers import get_or_create_access_policy_to_path
from poms.users.models import Member


class ExplorerViewSetTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()

        self.realm_code = "realm00000"
        self.space_code = "space00000"
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/explorer/explorer/"

        self.storage_patch = mock.patch(
            "poms.explorer.views.storage",
            spec=FinmarsS3Storage,
        )
        self.storage_mock = self.storage_patch.start()
        self.addCleanup(self.storage_patch.stop)

        self.mimetypes_patch = mock.patch(
            "poms.explorer.views.mimetypes.guess_type",
            return_value=("text/plain", "utf-8"),
        )
        self.mimetypes_mock = self.mimetypes_patch.start()
        self.addCleanup(self.mimetypes_patch.stop)

    @BaseTestCase.cases(
        ("null", ""),
        ("test", "test"),
        ("test_test", "test/test"),
    )
    def test__with_empty_path(self, path):
        self.storage_mock.listdir.return_value = [], []

        response = self.client.get(self.url, {"path": path})

        self.assertEqual(response.status_code, 200)
        self.storage_mock.listdir.assert_called_once()

        response_data = response.json()
        if path:
            self.assertEqual(response_data["path"], f"{self.space_code}/{path}/")
        else:
            self.assertEqual(response_data["path"], f"{self.space_code}/")
        self.assertEqual(response_data["results"], [])

    @BaseTestCase.cases(
        ("null", ""),
        ("test", "test"),
        ("test_1", "test/"),
        ("test_2", "/test"),
        ("test_3", "/test/"),
        ("test_test", "test/test"),
        ("test_test_1", "/test/test/"),
        ("test_test_2", "/test/test"),
        ("test_test_3", "test/test/"),
    )
    def test__path(self, path):
        directories = ["first", "second"]
        files = ["file.csv", "file.txt", "file.json"]
        size = self.random_int(10000, 50000)

        self.storage_mock.listdir.return_value = directories, files
        self.storage_mock.get_created_time.return_value = datetime.now()
        self.storage_mock.get_modified_time.return_value = datetime.now()
        self.storage_mock.size.return_value = size
        self.storage_mock.convert_size.return_value = f"{size // 1024}KB"

        response = self.client.get(self.url, {"path": path})

        self.assertEqual(response.status_code, 200)
        self.storage_mock.listdir.assert_called_once()

        response_data = response.json()
        if path:
            self.assertEqual(
                response_data["path"], f"{self.space_code}/{path.strip('/')}/"
            )
        else:
            self.assertEqual(response_data["path"], f"{self.space_code}/")
        self.assertEqual(len(response_data["results"]), len(directories) + len(files))

    def create_user_member(self):
        user = User.objects.create_user(username="testuser")
        member, _ = Member.objects.get_or_create(
            user=user,
            master_user=self.master_user,
            username="testuser",
            defaults=dict(
                is_admin=False,
                is_owner=False,
            ),
        )
        user.member = member
        user.save()
        self.client.force_authenticate(user=user)
        return user, member

    def test__no_permission(self):
        user, member = self.create_user_member()
        self.client.force_authenticate(user=user)
        dir_name = f"{self.random_string()}/*"

        response = self.client.get(self.url, {"path": dir_name})

        self.assertEqual(response.status_code, 403)

    def test__has_root_permission(self):
        self.storage_mock.listdir.return_value = [], []
        root = FinmarsDirectory.objects.create(path=ROOT_PATH)
        dir_name = f"{self.random_string()}/*"
        FinmarsDirectory.objects.create(path=dir_name, parent=root)
        user, member = self.create_user_member()
        get_or_create_access_policy_to_path(ROOT_PATH, member, AccessLevel.READ)
        self.client.force_authenticate(user=user)

        response = self.client.get(self.url, {"path": dir_name})

        self.assertEqual(response.status_code, 200)
