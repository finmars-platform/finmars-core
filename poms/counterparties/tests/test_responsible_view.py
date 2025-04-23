from copy import deepcopy

from django.conf import settings

from poms.common.common_base_test import BaseTestCase
from poms.counterparties.models import Responsible, ResponsibleGroup
from poms.iam.models import ResourceGroup
from poms.users.models import Member

EXPECTED_RESPONSIBLE = {
    "id": 3,
    "group": 3,
    "group_object": {
        "id": 3,
        "user_code": "TJKWZYTXTL",
        "name": "SFPILGJKWE",
        "short_name": "SIX",
        "public_name": None,
    },
    "user_code": "BTCSHCFBQM",
    "name": "WNSDMOIHAI",
    "short_name": "XWY",
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
    "portfolios": [],
    "portfolios_object": [],
    "is_enabled": True,
    "deleted_user_code": None,
    "attributes": [
        {
            "id": 1,
            "attribute_type": 1,
            "value_string": "ATWNGZMXSS",
            "value_float": 980.0,
            "value_date": "2023-07-20",
            "classifier": None,
            "attribute_type_object": {
                "id": 1,
                "user_code": "local.poms.space00000:auth.permission:znjrx",
                "name": "",
                "short_name": "SV",
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
        "content_type": "counterparties.responsible",
        "app_label": "counterparties",
        "model_name": "responsible",
        "space_code": "space00000",
    },
    "created_at": "20240823T16:41:00.0Z",
    "modified_at": "20240823T16:41:00.0Z",
    "deleted_at": None,
    "resource_groups": [],
    "resource_groups_object": [],
}

CREATE_DATA = {
    "user_code": "PIYHOURLOJ",
    "name": "ADSXXYDRJF",
    "short_name": "SCW",
    "public_name": "noname",
    "notes": "notes",
    "group": 11111,
}


class ResponsibleViewSetTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.realm_code = "realm00000"
        self.space_code = "space00000"
        self.url = (
            f"/{self.realm_code}/{self.space_code}/api/v1/counterparties/responsible/"
        )
        self.responsible = None

    def create_responsible_group(self) -> ResponsibleGroup:
        return ResponsibleGroup.objects.create(
            master_user=self.master_user,
            owner=self.member,
            user_code=self.random_string(),
            name=self.random_string(),
            short_name=self.random_string(3),
        )

    def create_responsible(self) -> Responsible:
        self.responsible = Responsible.objects.create(
            master_user=self.master_user,
            owner=self.member,
            group=self.create_responsible_group(),
            user_code=self.random_string(),
            name=self.random_string(),
            short_name=self.random_string(3),
        )
        self.responsible.attributes.set([self.create_attribute()])
        self.responsible.save()
        return self.responsible

    def prepare_data_for_create(self) -> dict:
        create_data = deepcopy(CREATE_DATA)
        group = self.create_responsible_group()
        create_data["user_code"] = self.random_string()
        create_data["name"] = self.random_string(11)
        create_data["short_name"] = self.random_string(3)
        create_data["group"] = group.id
        return create_data

    def test__check_api_url(self):
        response = self.client.get(path=self.url)
        self.assertEqual(response.status_code, 200, response.content)

    def test__create_and_retrieve(self):
        responsible = self.create_responsible()

        response = self.client.get(path=f"{self.url}{responsible.id}/")
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        # check fields
        self.assertEqual(response_json.keys(), EXPECTED_RESPONSIBLE.keys())

        # check values
        self.assertEqual(response_json["group"], responsible.group.id)

    def test__list_attributes(self):
        response = self.client.get(path=f"{self.url}attributes/")
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()
        self.assertEqual(len(response_json["results"]), 7)

    def test__list_light(self):
        responsible = self.create_responsible()
        response = self.client.get(path=f"{self.url}light/")
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()
        self.assertEqual(len(response_json["results"]), 1)
        self.assertEqual(
            response_json["results"][0]["user_code"], responsible.user_code
        )

    def test__get_filters(self):  # sourcery skip: extract-duplicate-method
        responsible = self.create_responsible()
        response = self.client.get(path=f"{self.url}?user_code={responsible.user_code}")
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()
        self.assertEqual(response_json["count"], 1)
        self.assertEqual(
            response_json["results"][0]["user_code"],
            responsible.user_code,
        )

        response = self.client.get(path=f"{self.url}?name={responsible.name}")
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()
        self.assertEqual(response_json["count"], 1)
        self.assertEqual(
            response_json["results"][0]["name"],
            responsible.name,
        )

    def test__create(self):
        create_data = self.prepare_data_for_create()

        response = self.client.post(path=self.url, format="json", data=create_data)
        self.assertEqual(response.status_code, 201, response.content)

        response_json = response.json()

        responsible_id = response_json["id"]
        responsible = Responsible.objects.get(id=responsible_id)
        self.assertEqual(responsible.user_code, create_data["user_code"])

    def test__update_put(self):
        create_data = self.prepare_data_for_create()

        response = self.client.post(path=self.url, format="json", data=create_data)
        self.assertEqual(response.status_code, 201, response.content)
        response_json = response.json()

        responsible_id = response_json["id"]
        new_user_code = self.random_string()
        update_data = deepcopy(create_data)
        update_data["user_code"] = new_user_code
        response = self.client.put(
            path=f"{self.url}{responsible_id}/", format="json", data=update_data
        )
        self.assertEqual(response.status_code, 200, response.content)

        response = self.client.get(path=f"{self.url}{responsible_id}/")
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()
        self.assertEqual(response_json["user_code"], new_user_code)

    def test__update_patch(self):
        create_data = self.prepare_data_for_create()

        response = self.client.post(path=self.url, format="json", data=create_data)
        self.assertEqual(response.status_code, 201, response.content)
        response_json = response.json()

        responsible_id = response_json["id"]
        new_short_name = self.random_string(3)
        update_data = {"short_name": new_short_name}

        response = self.client.patch(
            path=f"{self.url}{responsible_id}/", format="json", data=update_data
        )
        self.assertEqual(response.status_code, 200, response.content)

        response = self.client.get(path=f"{self.url}{responsible_id}/")
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()
        self.assertEqual(response_json["short_name"], new_short_name)

    def test__fake_delete(self):
        create_data = self.prepare_data_for_create()

        response = self.client.post(path=self.url, format="json", data=create_data)
        self.assertEqual(response.status_code, 201, response.content)
        response_json = response.json()

        responsible_id = response_json["id"]

        response = self.client.delete(path=f"{self.url}{responsible_id}/")
        self.assertEqual(response.status_code, 204, response.content)

        response = self.client.get(path=f"{self.url}{responsible_id}/")
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()

        self.assertTrue(response_json["is_deleted"])

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
        responsible_id = response.json()["id"]

        rg_name = self.random_string()
        rg = self.create_group(name=rg_name)
        response = self.client.patch(
            f"{self.url}{responsible_id}/",
            data={"resource_groups": [rg_name]},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)

        instrument_data = response.json()
        self.assertIn("resource_groups", instrument_data)
        self.assertEqual(instrument_data["resource_groups"], [rg_name])

        self.assertIn("resource_groups_object", instrument_data)
        resource_group = instrument_data["resource_groups_object"][0]
        self.assertEqual(resource_group["user_code"], rg.user_code)
        self.assertNotIn("assignments", resource_group)

    def test_remove_resource_groups(self):
        response = self.client.post(
            path=self.url, format="json", data=self.prepare_data_for_create()
        )
        self.assertEqual(response.status_code, 201, response.content)
        responsible_id = response.json()["id"]

        name_1 = self.random_string()
        self.create_group(name=name_1)
        name_3 = self.random_string()
        self.create_group(name=name_3)

        response = self.client.patch(
            f"{self.url}{responsible_id}/",
            data={"resource_groups": [name_1, name_3]},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)

        responsible_data = response.json()
        self.assertEqual(len(responsible_data["resource_groups"]), 2)
        self.assertEqual(len(responsible_data["resource_groups_object"]), 2)

        response = self.client.patch(
            f"{self.url}{responsible_id}/",
            data={"resource_groups": []},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)

        responsible_data = response.json()
        self.assertEqual(len(responsible_data["resource_groups"]), 0)
        self.assertEqual(responsible_data["resource_groups"], [])

        self.assertEqual(len(responsible_data["resource_groups_object"]), 0)
        self.assertEqual(responsible_data["resource_groups_object"], [])

    def test_destroy_assignments(self):
        response = self.client.post(
            path=self.url, format="json", data=self.prepare_data_for_create()
        )
        self.assertEqual(response.status_code, 201, response.content)
        responsible_id = response.json()["id"]

        name_1 = self.random_string()
        rg_1 = self.create_group(name=name_1)
        name_3 = self.random_string()
        rg_3 = self.create_group(name=name_3)

        response = self.client.patch(
            f"{self.url}{responsible_id}/",
            data={"resource_groups": [name_1, name_3]},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        responsible_data = response.json()
        self.assertEqual(len(responsible_data["resource_groups"]), 2)
        self.assertEqual(len(responsible_data["resource_groups_object"]), 2)

        url = f"/{self.realm_code}/{self.space_code}/api/v1/iam/resource-group/"
        response = self.client.delete(f"{url}{rg_1.id}/")
        self.assertEqual(response.status_code, 204, response.content)

        response = self.client.delete(f"{url}{rg_3.id}/")
        self.assertEqual(response.status_code, 204, response.content)

        response = self.client.get(f"{self.url}{responsible_id}/")
        self.assertEqual(response.status_code, 200, response.content)

        responsible_data = response.json()
        self.assertEqual(len(responsible_data["resource_groups"]), 0)
        self.assertEqual(responsible_data["resource_groups"], [])
