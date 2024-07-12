from poms.common.common_base_test import BaseTestCase
from poms.explorer.models import FinmarsDirectory, FinmarsFile
from poms.explorer.policy_templates import create_default_access_policy, RESOURCE
from poms.configuration.utils import get_default_configuration_code


EXPECTED_POLICY = {
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

    def test__file_access_policy_created(self):
        extension = self.random_string(3)
        name = f"{self.random_string()}.{extension}"
        path = (
            f"/{self.random_string()}/{self.random_string(5)}/{self.random_string(7)}/"
        )
        size = self.random_int()
        file = FinmarsFile.objects.create(name=name, path=path, size=size)

        access_policy = create_default_access_policy(file)

        self.assertEqual(access_policy.name, file.resource)
        self.assertEqual(
            access_policy.configuration_code, get_default_configuration_code()
        )
        self.assertEqual(access_policy.owner.username, "finmars_bot")

        expected_user_code = (
            f"local.poms.space00000:finmars:explorer:file:{file.fullpath}-full"
        )
        self.assertEqual(access_policy.user_code, expected_user_code)

        EXPECTED_POLICY["Statement"][0]["Resource"] = RESOURCE.format(resource=file.resource)
        self.assertEqual(
            access_policy.policy, EXPECTED_POLICY, msg=access_policy.policy
        )


# class DirAccessPolicyTest(BaseTestCase):
#     databases = "__all__"
#
#     def setUp(self):
#         super().setUp()
#         self.init_test_case()
#
#     def test__dir_access_policy_created(self):
#         extension = self.random_string(3)
#         name = f"{self.random_string()}.{extension}"
#         path = (
#             f"/{self.random_string()}/{self.random_string(5)}/{self.random_string(7)}/"
#         )
#         size = self.random_int()
#         file = FinmarsDirectory.objects.create(name=name, path=path, size=size)
#
#         self.assertIsNotNone(file)
#         self.assertEqual(file.name, name)
#         self.assertEqual(file.path, path)
#         self.assertEqual(file.size, size)
#         self.assertEqual(file.extension, extension)
#         self.assertIsNotNone(file.created)
#         self.assertIsNotNone(file.modified)
