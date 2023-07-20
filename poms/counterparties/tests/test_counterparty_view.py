from copy import deepcopy
from datetime import date

from django.conf import settings
from django.contrib.contenttypes.models import ContentType

from poms.common.common_base_test import BaseTestCase
from poms.counterparties.models import Counterparty, CounterpartyGroup
from poms.obj_attrs.models import GenericAttribute, GenericAttributeType

EXPECTED_COUNTERPARTY = {
    "id": 3,
    "group": 3,
    "group_object": {
        "id": 3,
        "user_code": "EORCJSTZQX",
        "name": "YTPNBOFPYE",
        "short_name": "URU",
        "public_name": None,
    },
    "user_code": "PIYHOURLOJ",
    "name": "ADSXXYDRJF",
    "short_name": "SCW",
    "public_name": None,
    "notes": None,
    "is_valid_for_all_portfolios": True,
    "is_deleted": False,
    "portfolios": [],
    "portfolios_object": [],
    "is_enabled": True,
    "deleted_user_code": None,
    "attributes": [
        {
            "id": 1,
            "attribute_type": 1,
            "value_string": "WBMOXYSNUX",
            "value_float": 7306.0,
            "value_date": "2023-07-19",
            "classifier": None,
            "attribute_type_object": {
                "id": 1,
                "user_code": "local.poms.space00000:auth.permission:znmjh",
                "name": "",
                "short_name": "PD",
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
    "meta": {
        "content_type": "counterparties.counterparty",
        "app_label": "counterparties",
        "model_name": "counterparty",
        "space_code": "space00000",
    },
}

CREATE_DATA = {
    "user_code": "PIYHOURLOJ",
    "name": "ADSXXYDRJF",
    "short_name": "SCW",
    "public_name": "noname",
    "notes": "notes",
}


class CounterpartyViewSetTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = f"/{settings.BASE_API_URL}/api/v1/counterparties/counterparty/"
        self.counterparty = None

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

    def create_counterparty_group(self) -> CREATE_DATA:
        return CounterpartyGroup.objects.create(
            master_user=self.master_user,
            user_code=self.random_string(),
            name=self.random_string(),
            short_name=self.random_string(3),
        )

    def create_counterparty(self) -> Counterparty:
        self.counterparty = Counterparty.objects.create(
            master_user=self.master_user,
            group=self.create_counterparty_group(),
            user_code=self.random_string(),
            name=self.random_string(),
            short_name=self.random_string(3),
        )
        self.counterparty.attributes.set([self.create_attribute()])
        self.counterparty.save()
        return self.counterparty

    def prepare_data_for_create(self) -> dict:
        create_data = deepcopy(CREATE_DATA)
        group = self.create_counterparty_group()
        create_data["user_code"] = self.random_string()
        create_data["name"] = self.random_string(11)
        create_data["short_name"] = self.random_string(3)
        create_data["group"] = group.id
        return create_data

    def test__check_api_url(self):
        response = self.client.get(path=self.url)
        self.assertEqual(response.status_code, 200, response.content)

    def test__create_and_retrieve(self):
        counterparty = self.create_counterparty()

        response = self.client.get(path=f"{self.url}{counterparty.id}/")
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        # check fields
        self.assertEqual(response_json.keys(), EXPECTED_COUNTERPARTY.keys())

        # check values
        self.assertEqual(response_json["group"], counterparty.group.id)

    def test__list_attributes(self):
        response = self.client.get(path=f"{self.url}attributes/")
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()
        self.assertEqual(len(response_json["results"]), 7)

    def test__list_light(self):
        counterparty = self.create_counterparty()
        response = self.client.get(path=f"{self.url}light/")
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()
        self.assertEqual(len(response_json["results"]), 2)  # default + new

    def test__get_filters(self):  # sourcery skip: extract-duplicate-method
        counterparty = self.create_counterparty()
        response = self.client.get(
            path=f"{self.url}?user_code={counterparty.user_code}"
        )
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()
        self.assertEqual(response_json["count"], 1)
        self.assertEqual(
            response_json["results"][0]["user_code"],
            counterparty.user_code,
        )

        response = self.client.get(path=f"{self.url}?name={counterparty.name}")
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()
        self.assertEqual(response_json["count"], 1)
        self.assertEqual(
            response_json["results"][0]["name"],
            counterparty.name,
        )

    def test__create(self):
        create_data = self.prepare_data_for_create()

        response = self.client.post(path=self.url, format="json", data=create_data)
        self.assertEqual(response.status_code, 201, response.content)

        response_json = response.json()

        counterparty_id = response_json["id"]
        counterparty = Counterparty.objects.get(id=counterparty_id)
        self.assertEqual(counterparty.user_code, create_data["user_code"])

    def test__update_put(self):
        create_data = self.prepare_data_for_create()

        response = self.client.post(path=self.url, format="json", data=create_data)
        self.assertEqual(response.status_code, 201, response.content)
        response_json = response.json()

        counterparty_id = response_json["id"]
        new_user_code = self.random_string()
        update_data = deepcopy(create_data)
        update_data["user_code"] = new_user_code
        response = self.client.put(
            path=f"{self.url}{counterparty_id}/", format="json", data=update_data
        )
        self.assertEqual(response.status_code, 200, response.content)

        response = self.client.get(path=f"{self.url}{counterparty_id}/")
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()
        self.assertEqual(response_json["user_code"], new_user_code)

    def test__update_patch(self):
        create_data = self.prepare_data_for_create()

        response = self.client.post(path=self.url, format="json", data=create_data)
        self.assertEqual(response.status_code, 201, response.content)
        response_json = response.json()

        counterparty_id = response_json["id"]
        new_short_name = self.random_string(3)
        update_data = {"short_name": new_short_name}

        response = self.client.patch(
            path=f"{self.url}{counterparty_id}/", format="json", data=update_data
        )
        self.assertEqual(response.status_code, 200, response.content)

        response = self.client.get(path=f"{self.url}{counterparty_id}/")
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()
        self.assertEqual(response_json["short_name"], new_short_name)

    def test__fake_delete(self):
        create_data = self.prepare_data_for_create()

        response = self.client.post(path=self.url, format="json", data=create_data)
        self.assertEqual(response.status_code, 201, response.content)
        response_json = response.json()

        counterparty_id = response_json["id"]

        response = self.client.delete(path=f"{self.url}{counterparty_id}/")
        self.assertEqual(response.status_code, 204, response.content)

        response = self.client.get(path=f"{self.url}{counterparty_id}/")
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()

        self.assertTrue(response_json["is_deleted"])
