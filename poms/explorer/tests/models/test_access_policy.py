from poms.common.common_base_test import BaseTestCase
from poms.explorer.models import FULL, READ, FinmarsDirectory, FinmarsFile
from poms.explorer.policy_handlers import create_default_storage_access_policies
from poms.iam.models import AccessPolicy

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

    def _create_file(self) -> FinmarsFile:
        extension = self.random_string(3)
        name = f"{self.random_string()}.{extension}"
        path = f"/{self.random_string()}/{self.random_string(5)}/{name}/"
        size = self.random_int()
        return FinmarsFile.objects.create(path=path, size=size)

    def test__created_file_default_policies(self):
        create_default_storage_access_policies()

        for access in [READ, FULL]:
            user_code = f"{self.obj.policy_user_code()}-{access}"
            default_policy = AccessPolicy.objects.get(user_code=user_code)
            self.assertIsNotNone(default_policy)

    def test__user_added_to_file_access_policy(self):
        create_default_storage_access_policies()

        for access in [READ, FULL]:
            user_code = f"{self.obj.policy_user_code()}-{access}"
            default_policy = AccessPolicy.objects.get(user_code=user_code)
            default_policy.members.add(self.member)


class DirectoryAccessPolicyTest(FileAccessPolicyTest):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.obj = self._create_directory()

    def _create_directory(self) -> FinmarsDirectory:
        path = f"/{self.random_string()}/{self.random_string(3)}"
        return FinmarsDirectory.objects.create(path=path, parent=None)
