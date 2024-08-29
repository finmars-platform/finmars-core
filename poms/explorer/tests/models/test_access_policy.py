from poms.common.common_base_test import BaseTestCase
from poms.explorer.models import DIR_SUFFIX, AccessLevel, StorageObject
from poms.explorer.policy_handlers import get_or_create_storage_access_policy
from poms.users.models import Member

EXPECTED_FULL_POLICY = {
    "Version": "2023-01-01",
    "Statement": [
        {
            "Action": ["finmars:explorer:read", "finmars:explorer:full"],
            "Effect": "Allow",
            "Resource": "",
            "Principal": "*",
        }
    ],
}


class FileAccessPolicyTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.obj = self._create_file()
        self.member_user = self.create_member()

    def create_member(self):
        member, _ = Member.objects.get_or_create(
            master_user=self.master_user,
            username="file_user",
            defaults=dict(
                is_admin=True,
                is_owner=True,
            ),
        )
        return member

    def _create_file(self) -> StorageObject:
        extension = self.random_string(3)
        name = f"{self.random_string()}.{extension}"
        path = f"/{self.random_string()}/{self.random_string(5)}/{name}"
        size = self.random_int()
        return StorageObject.objects.create(path=path, size=size, is_file=True)

    @BaseTestCase.cases(
        ("read", AccessLevel.READ),
        ("write", AccessLevel.WRITE),
    )
    def test__created_obj_access_policies(self, access):
        access_policy = get_or_create_storage_access_policy(
            self.obj, self.member_user, access
        )
        self.assertIsNotNone(access_policy)
        self.assertEqual(access_policy.user_code, self.obj.policy_user_code(access))
        self.assertIn(self.member_user, access_policy.members.all())


class DirectoryAccessPolicyTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.obj = self._create_directory()
        self.member_user = self.create_member()

    def create_member(self):
        member, _ = Member.objects.get_or_create(
            master_user=self.master_user,
            username="directory_user",
            defaults=dict(
                is_admin=True,
                is_owner=True,
            ),
        )
        return member

    def _create_directory(self) -> StorageObject:
        path = f"/{self.random_string()}/{self.random_string(3)}{DIR_SUFFIX}"
        return StorageObject.objects.create(path=path, parent=None)

    @BaseTestCase.cases(
        ("read", AccessLevel.READ),
        ("write", AccessLevel.WRITE),
    )
    def test__created_obj_access_policies(self, access):
        access_policy = get_or_create_storage_access_policy(
            self.obj, self.member_user, access
        )
        self.assertIsNotNone(access_policy)
        self.assertEqual(access_policy.user_code, self.obj.policy_user_code(access))
        self.assertIn(self.member_user, access_policy.members.all())
