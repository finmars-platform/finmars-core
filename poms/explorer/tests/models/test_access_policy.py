from poms.common.common_base_test import BaseTestCase
from poms.configuration.utils import get_default_configuration_code
from poms.explorer.models import FinmarsDirectory, FinmarsFile, READ
from poms.explorer.policy_handlers import (
    RESOURCE,
    create_default_access_policy,
    upsert_storage_obj_access_policy,
)

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

    def _create_file(self) -> FinmarsFile:
        extension = self.random_string(3)
        name = f"{self.random_string()}.{extension}"
        path = (
            f"/{self.random_string()}/{self.random_string(5)}/{name}/"
        )
        size = self.random_int()
        return FinmarsFile.objects.create(path=path, size=size)

    def test__file_access_policy_created(self):
        file = self._create_file()

        access_policy = create_default_access_policy(file)

        self.assertEqual(access_policy.name, file.resource)
        self.assertEqual(
            access_policy.configuration_code, get_default_configuration_code()
        )
        self.assertEqual(access_policy.owner.username, "finmars_bot")

        expected_user_code = (
            f"local.poms.space00000:finmars:explorer:file:{file.path}"
        )
        self.assertEqual(access_policy.user_code, expected_user_code)

        EXPECTED_FULL_POLICY["Statement"][0]["Resource"] = RESOURCE.format(
            resource=file.resource
        )
        self.assertEqual(
            access_policy.policy, EXPECTED_FULL_POLICY, msg=access_policy.policy
        )

    def test__file_access_policy_has_unique_user_code(self):
        file = self._create_file()

        access_policy_1 = create_default_access_policy(file)
        access_policy_2 = create_default_access_policy(file)
        self.assertEqual(access_policy_1.id, access_policy_2.id)
        self.assertEqual(access_policy_1.user_code, access_policy_2.user_code)

    def test__file_access_policy_updated(self):
        file = self._create_file()

        access_policy_1 = create_default_access_policy(file)

        access_policy_2 = upsert_storage_obj_access_policy(
            file, access_policy_1.owner, access=READ
        )
        self.assertEqual(access_policy_1.id, access_policy_2.id)

        self.assertEqual(access_policy_2.name, file.resource)
        self.assertEqual(
            access_policy_2.configuration_code, get_default_configuration_code()
        )
        self.assertEqual(access_policy_2.owner.username, "finmars_bot")

        expected_user_code = (
            f"local.poms.space00000:finmars:explorer:file:{file.path}"
        )
        self.assertEqual(access_policy_2.user_code, expected_user_code)

        EXPECTED_FULL_POLICY["Statement"][0]["Resource"] = RESOURCE.format(
            resource=file.resource
        )
        self.assertEqual(len(access_policy_2.policy["Statement"][0]["Action"]), 1)


class DirectoryAccessPolicyTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()

    def _create_directory(self) -> FinmarsDirectory:
        path = f"/{self.random_string()}/{self.random_string(3)}"
        return FinmarsDirectory.objects.create(path=path, parent=None)

    def test__directory_access_policy_created(self):
        directory = self._create_directory()

        access_policy = create_default_access_policy(directory)
        self.assertEqual(access_policy.name, directory.resource)
        self.assertEqual(
            access_policy.configuration_code, get_default_configuration_code()
        )
        self.assertEqual(access_policy.owner.username, "finmars_bot")

        expected_user_code = (
            f"local.poms.space00000:finmars:explorer:dir:{directory.path}"
        )
        self.assertEqual(access_policy.user_code, expected_user_code)

        EXPECTED_FULL_POLICY["Statement"][0]["Resource"] = RESOURCE.format(
            resource=directory.resource
        )
        self.assertEqual(
            access_policy.policy, EXPECTED_FULL_POLICY, msg=access_policy.policy
        )

    def test__directory_access_policy_has_unique_user_code(self):
        directory = self._create_directory()

        access_policy_1 = create_default_access_policy(directory)
        access_policy_2 = create_default_access_policy(directory)
        self.assertEqual(access_policy_1.id, access_policy_2.id)
        self.assertEqual(access_policy_1.user_code, access_policy_2.user_code)

    def test__directory_access_policy_updated(self):
        directory = self._create_directory()

        access_policy_1 = create_default_access_policy(directory)

        access_policy_2 = upsert_storage_obj_access_policy(
            directory, access_policy_1.owner, access=READ
        )
        self.assertEqual(access_policy_1.id, access_policy_2.id)

        self.assertEqual(access_policy_2.name, directory.resource)
        self.assertEqual(
            access_policy_2.configuration_code, get_default_configuration_code()
        )
        self.assertEqual(access_policy_2.owner.username, "finmars_bot")

        expected_user_code = (
            f"local.poms.space00000:finmars:explorer:dir:{directory.path}"
        )
        self.assertEqual(access_policy_2.user_code, expected_user_code)

        EXPECTED_FULL_POLICY["Statement"][0]["Resource"] = RESOURCE.format(
            resource=directory.resource
        )
        self.assertEqual(len(access_policy_2.policy["Statement"][0]["Action"]), 1)
