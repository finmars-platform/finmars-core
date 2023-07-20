from copy import deepcopy
from datetime import date

from django.conf import settings
from django.contrib.contenttypes.models import ContentType

from poms.accounts.models import AccountType
from poms.obj_attrs.models import GenericAttribute, GenericAttributeType
from poms.common.common_base_test import BaseTestCase


EXPECTED_ACCOUNT_TYPE = {
    "id": 2,
    "user_code": "local.poms.space00000:xjysxfgdbr",
    "configuration_code": "local.poms.space00000",
    "name": "Super",
    "short_name": "GNK",
    "public_name": None,
    "notes": None,
    "show_transaction_details": False,
    "transaction_details_expr": "WVFCPJXQSB",
    "is_deleted": False,
    "is_enabled": True,
    "attributes": [
        {
            "id": 1,
            "attribute_type": 1,
            "value_string": "ZPSWIQCMMG",
            "value_float": 892.0,
            "value_date": "2023-07-18",
            "classifier": None,
            "attribute_type_object": {
                "id": 1,
                "user_code": "",
                "name": "",
                "short_name": "",
                "public_name": None,
                "notes": None,
                "can_recalculate": False,
                "value_type": 20,
                "order": 0,
                "is_hidden": False,
                "kind": 1,
            },
            "classifier_object": None,
        }
    ],
    "deleted_user_code": None,
    "meta": {
        "content_type": "accounts.accounttype",
        "app_label": "accounts",
        "model_name": "accounttype",
        "space_code": "space00000",
    },
}

CREATE_DATA = {
    "user_code": EXPECTED_ACCOUNT_TYPE["user_code"],
    "configuration_code": EXPECTED_ACCOUNT_TYPE["configuration_code"],
    "name": EXPECTED_ACCOUNT_TYPE["name"],
    "short_name": EXPECTED_ACCOUNT_TYPE["short_name"],
    "public_name": EXPECTED_ACCOUNT_TYPE["public_name"],
    "notes": EXPECTED_ACCOUNT_TYPE["notes"],
    "transaction_details_expr": "",
    "is_deleted": False,
    "is_enabled": True,
}


class AccountTypeViewSetTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = f"/{settings.BASE_API_URL}/api/v1/accounts/account-type/"
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

    def test__list_and_default(self):
        response = self.client.get(path=self.url)
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        self.assertEqual(response_json["count"], 1)  # default account "-"
        default_account = response_json["results"][0]
        self.assertEqual(default_account.keys(), EXPECTED_ACCOUNT_TYPE.keys())

    def test__create_and_retrieve(self):
        account_type = self.create_account_type()
        response = self.client.get(path=f"{self.url}{account_type.id}/")
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        # check attribute
        attribute_dict = response_json["attributes"][0]
        attribute_obj = account_type.attributes.first()
        self.assertEqual(attribute_dict["value_string"], attribute_obj.value_string)

    def test__list_attributes(self):
        response = self.client.get(path=f"{self.url}attributes/")
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()
        self.assertEqual(len(response_json["results"]), 7)

    def test__get_filters(self):  # sourcery skip: extract-duplicate-method
        account_type = self.create_account_type()
        response = self.client.get(
            path=f"{self.url}?user_code={account_type.user_code}"
        )
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()
        self.assertEqual(response_json["count"], 1)

        response = self.client.get(path=f"{self.url}?user_code=xxxxxxx")
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()
        self.assertEqual(response_json["count"], 0)

    def test__create(self):
        response = self.client.post(path=self.url, format="json", data=CREATE_DATA)
        self.assertEqual(response.status_code, 201, response.content)

        account_type = AccountType.objects.filter(name=CREATE_DATA["name"])
        self.assertIsNotNone(account_type)

    def test__update_put(self):
        response = self.client.post(path=self.url, format="json", data=CREATE_DATA)
        self.assertEqual(response.status_code, 201, response.content)
        response_json = response.json()
        account_type_id = response_json["id"]

        new_name = "new_name"
        update_data = deepcopy(CREATE_DATA)
        update_data["name"] = new_name
        response = self.client.put(
            path=f"{self.url}{account_type_id}/", format="json", data=update_data
        )
        self.assertEqual(response.status_code, 200, response.content)

        response = self.client.get(path=f"{self.url}?name={new_name}")
        response_json = response.json()
        self.assertEqual(response_json["count"], 1)

    def test__update_patch(self):
        response = self.client.post(path=self.url, format="json", data=CREATE_DATA)
        self.assertEqual(response.status_code, 201, response.content)
        response_json = response.json()
        account_type_id = response_json["id"]

        new_name = "new_name"
        update_data = {"name": new_name}
        response = self.client.patch(
            path=f"{self.url}{account_type_id}/", format="json", data=update_data
        )
        self.assertEqual(response.status_code, 200, response.content)

        response = self.client.get(path=f"{self.url}?name={new_name}")
        response_json = response.json()
        self.assertEqual(response_json["count"], 1)

    def test__delete(self):
        response = self.client.post(path=self.url, format="json", data=CREATE_DATA)
        self.assertEqual(response.status_code, 201, response.content)
        response_json = response.json()
        account_type_id = response_json["id"]

        response = self.client.delete(path=f"{self.url}{account_type_id}/")
        self.assertEqual(response.status_code, 204, response.content)

        response = self.client.get(path=f"{self.url}?name={CREATE_DATA['name']}")
        response_json = response.json()
        self.assertEqual(response_json["count"], 0)
