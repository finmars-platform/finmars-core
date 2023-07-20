from copy import deepcopy
from datetime import date

from django.conf import settings
from django.contrib.contenttypes.models import ContentType

from poms.accounts.models import Account, AccountType
from poms.obj_attrs.models import GenericAttribute, GenericAttributeType
from poms.common.common_base_test import BaseTestCase


EXPECTED_ACCOUNT = {
    "id": 3,
    "type": None,
    "user_code": "Small",
    "name": "Small",
    "short_name": "Small",
    "public_name": None,
    "notes": None,
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
    "meta": {
        "content_type": "accounts.account",
        "app_label": "accounts",
        "model_name": "account",
        "space_code": "space00000",
    },
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
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = f"/{settings.BASE_API_URL}/api/v1/accounts/account/"
        self.attribute_type = None
        self.attribute = None
        self.account_type = None

    def create_attribute_type(self) -> GenericAttributeType:
        self.attribute_type = GenericAttributeType.objects.create(
            master_user=self.master_user,
            content_type=ContentType.objects.first(),
            user_code=self.random_string(5),
            short_name=self.random_string(2),
            value_type=GenericAttributeType.NUMBER,
            kind=GenericAttributeType.USER,
            tooltip=self.random_string(),
            favorites=self.random_string(),
            prefix=self.random_string(3),
            expr=self.random_string(),
        )
        return self.attribute_type

    def create_attribute(self) -> GenericAttribute:
        self.attribute = GenericAttribute.objects.create(
            attribute_type=self.create_attribute_type(),
            content_type=ContentType.objects.last(),
            object_id=self.random_int(),
            value_string=self.random_string(),
            value_float=self.random_int(),
            value_date=date.today(),
        )
        return self.attribute

    def create_account_type(self) -> AccountType:
        self.account_type = AccountType.objects.create(
            master_user=self.master_user,
            user_code=self.random_string(),
            short_name=self.random_string(3),
            transaction_details_expr=self.random_string(),
        )
        self.account_type.attributes.set([self.create_attribute()])
        self.account_type.save()
        return self.account_type

    def create_account(self) -> Account:
        self.account = Account.objects.create(
            master_user=self.master_user,
            type=self.create_account_type(),
            user_code=self.random_string(),
            short_name=self.random_string(3),
        )
        self.account.attributes.set([self.create_attribute()])
        self.account.save()
        return self.account

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

        print(response_json)

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

        response = self.client.get(path=f"{self.url}?user_code={create_data['user_code']}")
        response_json = response.json()
        self.assertEqual(response_json["count"], 0)
