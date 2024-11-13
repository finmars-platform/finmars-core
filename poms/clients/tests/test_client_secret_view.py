from django.conf import settings
from poms.clients.models import Client
from poms.clients.models import ClientSecret
from poms.common.common_base_test import BaseTestCase


EXPECTED_DATA = {
    "id": 1,
    "user_code": "user_code",
    "provider": "",
    "portfolio": "",
    "client": "test",
    "client_object": {
        "id": 3,
        "user_code": "test",
        "name": "test1",
        "short_name": "test1",
        "public_name": "test1",
        "notes": "test1",
        "deleted_user_code": None,
        "owner": {
            "id": 1337,
            "username": "finmars_bot",
        },
        "meta": {
            "content_type": "clients.client",
            "app_label": "clients",
            "model_name": "client",
            "space_code": "space00000",
            "realm_code": "realm00000",
        }
    },
    "deleted_user_code": None,
    "owner": {
        "id": 2,
        "username": "workflow_admin",
    },
    "meta": {
        "content_type": "clients.clientsecret",
        "app_label": "clients",
        "model_name": "clientsecret",
        "space_code": "space00000",
        "realm_code": "realm00000",
    }
}


CREATE_DATA = {
    "user_code": EXPECTED_DATA["user_code"],
    "client": EXPECTED_DATA["client"],
}


class ClientViewTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()

        self.master_user = self.master_user
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/clients/client-secret/"
        self.create_client_obj(user_code=CREATE_DATA["client"])
        self.create_client_secret(user_code="m")


    def create_client_secret(self, user_code):
        client = Client.objects.get(user_code=CREATE_DATA["client"])
        return ClientSecret.objects.using(settings.DB_DEFAULT).create(
            master_user=self.master_user,
            owner=self.member,
            user_code=user_code,
            client=client,
        )


    def test__list_and_default(self):
        response = self.client.get(path=self.url)
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()
        self.assertGreater(response_json["count"], 0)

        client = response_json["results"][0]
        self.assertEqual(client.keys(), EXPECTED_DATA.keys())


    def test__get_filters(self):
        client_secret = self.create_client_secret(user_code="test_filter")
        response = self.client.get(path=f"{self.url}?user_code={client_secret.user_code}")
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

        client_secret = ClientSecret.objects.filter(user_code=CREATE_DATA["user_code"])
        self.assertIsNotNone(client_secret)


    def test__update_patch(self):
        response = self.client.post(path=self.url, format="json", data=CREATE_DATA)
        self.assertEqual(response.status_code, 201, response.content)
        response_json = response.json()
        client_secret_id = response_json["id"]

        new_user_code = "new_user_code"
        update_data = {"user_code": new_user_code}
        response = self.client.patch(
            path=f"{self.url}{client_secret_id}/", format="json", data=update_data
        )
        self.assertEqual(response.status_code, 200, response.content)

        response = self.client.get(path=f"{self.url}?user_code={new_user_code}")
        response_json = response.json()
        self.assertEqual(response_json["count"], 1)
        client = response_json["results"][0]
        self.assertEqual(client["user_code"], new_user_code)


    def test__delete(self):
        response = self.client.post(path=self.url, format="json", data=CREATE_DATA)
        self.assertEqual(response.status_code, 201, response.content)
        response_json = response.json()
        client_id = response_json["id"]

        response = self.client.delete(path=f"{self.url}{client_id}/")
        self.assertEqual(response.status_code, 204, response.content)

        response = self.client.get(path=f"{self.url}?user_code={CREATE_DATA['user_code']}")
        response_json = response.json()
        self.assertEqual(response_json["count"], 0)