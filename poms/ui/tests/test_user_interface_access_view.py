from poms.common.common_base_test import BaseTestCase
from poms.ui.models import UserInterfaceAccessModel


EXPECTED_DATA = {
    "id": 1,
    "name": "Data Manager Access Menu",
    "role": "com.finmars.standard-iam:base-data-manager",
    "user_code": "local.poms.space00000:data_manager_access_menu",
    "configuration_code": "local.poms.space00000",
    "allowed_items": ["dashboard", "transaction", "portfolio", "transaction_type"],
    "created_at": "2024-10-28T09:25:17.140606Z",
    "modified_at": "2024-10-28T09:25:17.140615Z",
    "owner": {"id": 2, "username": "workflow_admin"},
    "deleted_user_code": None,
    "meta": {
        "content_type": "ui.userinterfaceaccessmodel",
        "app_label": "ui",
        "model_name": "userinterfaceaccessmodel",
        "space_code": "space00000",
        "realm_code": "realme00000",
    },
}

CREATE_DATA = {
    "name": "Data Manager Access Menu",
    "role": "com.finmars.standard-iam:base-data-manager",
    "user_code": "local.poms.space00000:data_manager_access_menu",
    "configuration_code": "local.poms.space00000",
    "allowed_items": ["dashboard", "transaction", "portfolio", "transaction_type"],
}


class MemberLayoutViewSetTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.realm_code = "realm00000"
        self.space_code = "space00000"
        self.url = (
            f"/{self.realm_code}/{self.space_code}/api/v1/ui/user-interface-access/"
        )

    def prepare_data(self, user_code):
        UserInterfaceAccessModel.objects.create(
            user_code=user_code,
            configuration_code=CREATE_DATA["configuration_code"],
            name=self.random_string(),
            json_data=self.random_string(),
            role=self.random_string(),
            owner=self.member,
            member=self.member,
        )

    def test__list(self):
        self.prepare_data(user_code=self.random_string())

        response = self.client.get(path=self.url)
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()
        access = response_json["results"][0]
        self.assertEqual(access.keys(), EXPECTED_DATA.keys())

    def test__create(self):
        access = UserInterfaceAccessModel.objects.filter(
            user_code=EXPECTED_DATA["user_code"],
        )
        self.assertFalse(access.exists())

        response = self.client.post(path=self.url, format="json", data=CREATE_DATA)
        self.assertEqual(response.status_code, 201, response.content)

        access = UserInterfaceAccessModel.objects.filter(
            user_code=EXPECTED_DATA["user_code"]
        )
        self.assertTrue(access.exists())

    def test__create_uniqueness_error(self):
        self.prepare_data(user_code=CREATE_DATA["user_code"])
        access = UserInterfaceAccessModel.objects.filter(
            user_code=CREATE_DATA["user_code"],
        )
        self.assertTrue(access.exists())

        response = self.client.post(path=self.url, format="json", data=CREATE_DATA)
        self.assertEqual(response.status_code, 400, response.content)
