from poms.common.common_base_test import BaseTestCase
from poms.explorer.models import DIR_SUFFIX, AccessLevel, StorageObject

expected_response = {
    "id": 2,
    "configuration_code": "local.poms.space00000",
    "created_at": "2024-07-15T19:12:50.769611Z",
    "modified_at": "2024-07-15T19:12:50.769622Z",
    "name": "file:/test/next/test.pdf",
    "user_code": "local.poms.space00000:finmars:explorer:/test/next/test.pdf",
    "description": "file:/test/next/test.pdf : read access policy",
    "policy": {
        "Version": "2023-01-01",
        "Statement": [
            {
                "Action": ["finmars:explorer:read"],
                "Effect": "Allow",
                "Resource": "frn:finmars:explorer:/test/next/test.pdf",
                "Principal": "*",
            }
        ],
    },
    "owner": 2,
    "members": [],
    "resource_group": None,
    # "meta": {
    #     "execution_time": 10,
    #     "request_id": "33e86689-5ed9-4422-908e-9cd45a008451",
    # },
}


class FinmarsFileViewSetTest(BaseTestCase):
    databases = "__all__"
    maxDiff = None

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.realm_code = "realm00000"
        self.space_code = "space00000"
        self.url = (
            f"/{self.realm_code}/{self.space_code}/api/v1/explorer/set-access-policy/"
        )
        self.dirpath = f"/test/next{DIR_SUFFIX}"
        self.filepath = "/test/next/test.pdf"
        self.directory = StorageObject.objects.create(path=self.dirpath)
        self.file = StorageObject.objects.create(
            path=self.filepath, size=111, is_file=True
        )

    @BaseTestCase.cases(
        ("read", AccessLevel.READ),
        ("write", AccessLevel.WRITE),
    )
    def test__file_access_policy_created_at(self, access):
        data = {
            "path": self.filepath,
            "access": access,
            "username": "finmars_bot",
        }
        response = self.client.post(path=self.url, data=data, format="json")
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        self.assertEqual(set(response_json.keys()), set(expected_response.keys()))
        expected_user_code = (
            f"local.poms.space00000:finmars:explorer:{self.filepath}-{access}"
        )
        self.assertEqual(response_json["user_code"], expected_user_code)

        actions = response_json["policy"]["Statement"][0]["Action"]

        if access == AccessLevel.READ:
            self.assertEqual(len(actions), 1)
            self.assertIn("finmars:explorer:read", actions)
        else:
            self.assertEqual(len(actions), 2)
            self.assertIn(f"finmars:explorer:{AccessLevel.READ}", actions)
            self.assertIn(f"finmars:explorer:{AccessLevel.WRITE}", actions)

    @BaseTestCase.cases(
        ("read", AccessLevel.READ),
        ("write", AccessLevel.WRITE),
    )
    def test__directory_access_policy_created_at(self, access):
        data = {
            "path": self.dirpath,
            "access": access,
            "username": "finmars_bot",
        }
        response = self.client.post(path=self.url, data=data, format="json")
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        self.assertEqual(set(response_json.keys()), set(expected_response.keys()))
        expected_user_code = (
            f"local.poms.space00000:finmars:explorer:{self.dirpath}-{access}"
        )
        self.assertEqual(response_json["user_code"], expected_user_code)

        actions = response_json["policy"]["Statement"][0]["Action"]

        if access == AccessLevel.READ:
            self.assertEqual(len(actions), 1)
            self.assertIn("finmars:explorer:read", actions)
        else:
            self.assertEqual(len(actions), 2)
            self.assertIn(f"finmars:explorer:{AccessLevel.READ}", actions)
            self.assertIn(f"finmars:explorer:{AccessLevel.WRITE}", actions)
