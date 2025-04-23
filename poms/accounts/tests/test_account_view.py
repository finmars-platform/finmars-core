from copy import deepcopy

from django.conf import settings

from poms.iam.models import ResourceGroup
from poms.accounts.models import AccountType
from poms.common.common_base_test import BaseTestCase
from poms.users.models import Member
# from poms.accounts.tests.common_procs import print_users_and_members


EXPECTED_ACCOUNT = {
    "id": 3,
    "type": None,
    "user_code": "Small",
    "name": "Small",
    "short_name": "Small",
    "public_name": None,
    "notes": None,
    "is_active": True,
    "actual_at": None,
    "source_type": "manual",
    "source_origin": "manual",
    "external_id": None,
    "is_manual_locked": False,
    "is_locked": True,
    "is_valid_for_all_portfolios": True,
    "is_deleted": False,
    "portfolios": [3],
    "is_enabled": True,
    "deleted_user_code": None,
    "attributes": [],
    "type_object": None,
    "portfolios_object": [
        {
            "id": 3,
            "user_code": "Small",
            "name": "Small",
            "short_name": "Small",
            "public_name": None,
            "deleted_user_code": None,
            "meta": {
                "content_type": "portfolios.portfolio",
                "app_label": "portfolios",
                "model_name": "portfolio",
                "space_code": "space00000",
            },
        }
    ],
    "owner": {
        "id": 1,
        "username": "finmars_bot",
        "first_name": "",
        "last_name": "",
        "display_name": "finmars_bot",
        "is_owner": True,
        "is_admin": True,
        "user": 1,
    },
    "meta": {
        "content_type": "accounts.account",
        "app_label": "accounts",
        "model_name": "account",
        "space_code": "space00000",
    },
    "created_at": "20240823T16:41:00.0Z",
    "modified_at": "20240823T16:41:00.0Z",
    "deleted_at": None,
    "resource_groups": [],
    "resource_groups_object": [],
}

CREATE_DATA = {
    "user_code": EXPECTED_ACCOUNT["user_code"],
    "name": EXPECTED_ACCOUNT["name"],
    "short_name": EXPECTED_ACCOUNT["short_name"],
    "public_name": EXPECTED_ACCOUNT["public_name"],
    "notes": EXPECTED_ACCOUNT["notes"],
    "is_deleted": False,
    "is_enabled": True,
    "type": 111111,
}


class AccountViewSetTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()

        self.realm_code = "realm00000"
        self.space_code = "space00000"

        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/accounts/account/"
        self.attribute_type = None
        self.attribute = None
        self.account_type = None

    def prepare_data_for_create(self) -> dict:
        account_type = self.create_account_type()
        create_data = deepcopy(CREATE_DATA)
        create_data["type"] = account_type.id
        create_data["user_code"] = self.random_string()

        return create_data

    def test__list_and_default(self):
        response = self.client.get(path=self.url)
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        self.assertGreater(response_json["count"], 0)  # default accounts in DB
        default_account = response_json["results"][0]

        self.assertEqual(default_account.keys(), EXPECTED_ACCOUNT.keys())

    def test__create_and_retrieve(self):
        account = self.create_account()
        response = self.client.get(path=f"{self.url}{account.id}/")
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        # check attribute
        attribute_dict = response_json["attributes"][0]
        attribute_obj = account.attributes.first()
        self.assertEqual(attribute_dict["value_string"], attribute_obj.value_string)

        # check account
        self.assertEqual(response_json["user_code"], account.user_code)

    def test__list_attributes(self):
        response = self.client.get(path=f"{self.url}attributes/")
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()
        self.assertEqual(len(response_json["results"]), 6)

    def test__get_filters(self):  # sourcery skip: extract-duplicate-method
        account = self.create_account()
        response = self.client.get(path=f"{self.url}?user_code={account.user_code}")
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()
        self.assertEqual(response_json["count"], 1)

        response = self.client.get(path=f"{self.url}?user_code=xxxxxxx")
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()
        self.assertEqual(response_json["count"], 0)

    def test__create(self):
        create_data = self.prepare_data_for_create()

        response = self.client.post(path=self.url, format="json", data=create_data)
        self.assertEqual(response.status_code, 201, response.content)

        account = AccountType.objects.filter(name=create_data["name"])
        self.assertIsNotNone(account)

    def test__update_put(self):
        create_data = self.prepare_data_for_create()

        response = self.client.post(path=self.url, format="json", data=create_data)
        self.assertEqual(response.status_code, 201, response.content)
        response_json = response.json()
        account_id = response_json["id"]

        new_name = "new_name"
        update_data = deepcopy(create_data)
        update_data["name"] = new_name
        response = self.client.put(
            path=f"{self.url}{account_id}/", format="json", data=update_data
        )
        self.assertEqual(response.status_code, 200, response.content)

        response = self.client.get(path=f"{self.url}?name={new_name}")
        response_json = response.json()
        self.assertEqual(response_json["count"], 1)

    def test__update_patch(self):
        create_data = self.prepare_data_for_create()

        response = self.client.post(path=self.url, format="json", data=create_data)
        self.assertEqual(response.status_code, 201, response.content)
        response_json = response.json()
        account_id = response_json["id"]

        new_name = "new_name"
        update_data = {"name": new_name}
        response = self.client.patch(
            path=f"{self.url}{account_id}/", format="json", data=update_data
        )
        self.assertEqual(response.status_code, 200, response.content)

        response = self.client.get(path=f"{self.url}?name={new_name}")
        response_json = response.json()
        self.assertEqual(response_json["count"], 1)

    def test__delete(self):
        create_data = self.prepare_data_for_create()

        response = self.client.post(path=self.url, format="json", data=create_data)
        self.assertEqual(response.status_code, 201, response.content)
        response_json = response.json()
        account_id = response_json["id"]

        response = self.client.delete(path=f"{self.url}{account_id}/")
        self.assertEqual(response.status_code, 204, response.content)

        response = self.client.get(
            path=f"{self.url}?user_code={create_data['user_code']}"
        )
        response_json = response.json()
        self.assertEqual(response_json["count"], 0)

    def create_group(self, name: str = "test") -> ResourceGroup:
        return ResourceGroup.objects.create(
            name=name,
            user_code=name,
            description=name,
            configuration_code=name,
            owner=Member.objects.all().first(),
        )

    def test_add_resource_group(self):
        response = self.client.post(
            path=self.url, format="json", data=self.prepare_data_for_create()
        )
        self.assertEqual(response.status_code, 201, response.content)
        account_id = response.json()["id"]

        rg_name = self.random_string()
        rg = self.create_group(name=rg_name)
        response = self.client.patch(
            f"{self.url}{account_id}/",
            data={"resource_groups": [rg_name]},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)

        account_data = response.json()
        self.assertIn("resource_groups", account_data)
        self.assertEqual(account_data["resource_groups"], [rg_name])

        self.assertIn("resource_groups_object", account_data)
        resource_group = account_data["resource_groups_object"][0]
        self.assertEqual(resource_group["user_code"], rg.user_code)
        self.assertNotIn("assignments", resource_group)

    def test_update_resource_groups(self):
        response = self.client.post(
            path=self.url, format="json", data=self.prepare_data_for_create()
        )
        self.assertEqual(response.status_code, 201, response.content)
        account_id = response.json()["id"]

        name_1 = self.random_string()
        self.create_group(name=name_1)
        name_2 = self.random_string()
        self.create_group(name=name_2)

        response = self.client.patch(
            f"{self.url}{account_id}/",
            data={"resource_groups": [name_1, name_2]},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)

        account_data = response.json()
        self.assertEqual(len(account_data["resource_groups"]), 2)
        self.assertEqual(len(account_data["resource_groups_object"]), 2)

        response = self.client.patch(
            f"{self.url}{account_id}/",
            data={"resource_groups": [name_2]},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)

        account_data = response.json()
        self.assertEqual(len(account_data["resource_groups"]), 1)
        self.assertEqual(account_data["resource_groups"], [name_2])

        self.assertEqual(len(account_data["resource_groups_object"]), 1)

    def test_remove_resource_groups(self):
        response = self.client.post(
            path=self.url, format="json", data=self.prepare_data_for_create()
        )
        self.assertEqual(response.status_code, 201, response.content)
        account_id = response.json()["id"]

        name_1 = self.random_string()
        self.create_group(name=name_1)
        name_3 = self.random_string()
        self.create_group(name=name_3)

        response = self.client.patch(
            f"{self.url}{account_id}/",
            data={"resource_groups": [name_1, name_3]},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)

        account_data = response.json()
        self.assertEqual(len(account_data["resource_groups"]), 2)
        self.assertEqual(len(account_data["resource_groups_object"]), 2)

        response = self.client.patch(
            f"{self.url}{account_id}/",
            data={"resource_groups": []},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)

        account_data = response.json()
        self.assertEqual(len(account_data["resource_groups"]), 0)
        self.assertEqual(account_data["resource_groups"], [])

        self.assertEqual(len(account_data["resource_groups_object"]), 0)
        self.assertEqual(account_data["resource_groups_object"], [])

    def test_destroy_assignments(self):
        response = self.client.post(
            path=self.url, format="json", data=self.prepare_data_for_create()
        )
        self.assertEqual(response.status_code, 201, response.content)
        account_id = response.json()["id"]

        name_1 = self.random_string()
        rg_1 = self.create_group(name=name_1)
        name_3 = self.random_string()
        rg_3 = self.create_group(name=name_3)

        response = self.client.patch(
            f"{self.url}{account_id}/",
            data={"resource_groups": [name_1, name_3]},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        account_data = response.json()
        self.assertEqual(len(account_data["resource_groups"]), 2)
        self.assertEqual(len(account_data["resource_groups_object"]), 2)

        url = f"/{self.realm_code}/{self.space_code}/api/v1/iam/resource-group/"
        response = self.client.delete(f"{url}{rg_1.id}/")
        self.assertEqual(response.status_code, 204, response.content)

        response = self.client.delete(f"{url}{rg_3.id}/")
        self.assertEqual(response.status_code, 204, response.content)

        response = self.client.get(f"{self.url}{account_id}/")
        self.assertEqual(response.status_code, 200, response.content)

        account_data = response.json()
        self.assertEqual(len(account_data["resource_groups"]), 0)
        self.assertEqual(account_data["resource_groups"], [])
