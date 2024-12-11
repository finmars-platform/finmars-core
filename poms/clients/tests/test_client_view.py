from poms.clients.models import Client
from poms.common.common_base_test import BaseTestCase
from poms.portfolios.models import Portfolio


EXPECTED_CLIENT = {
    "id": 1,
    "user_code": "test",
    "name": "test",
    "short_name": "test",
    "public_name": "test",
    "notes": "test",
    "first_name": "test",
    "last_name": "test",
    "telephone": "+1234567890",
    "email": "test@finmars.com",
    "deleted_user_code": None,
    "portfolios": [],
    "portfolios_object": [],
    "owner": {
        "id": 1318,
        "username": "finmars_bot"
    },
    "meta": {
        "content_type": "clients.client",
        "app_label": "clients",
        "model_name": "client",
        "space_code": "space00000",
        "realm_code": "realm00000",
    },
}


CREATE_DATA = {
    "user_code": EXPECTED_CLIENT["user_code"],
    "name": EXPECTED_CLIENT["name"],
    "short_name": EXPECTED_CLIENT["short_name"],
    "public_name": EXPECTED_CLIENT["public_name"],
    "notes": EXPECTED_CLIENT["notes"],
    "first_name": EXPECTED_CLIENT["first_name"],
    "last_name": EXPECTED_CLIENT["last_name"],
    "telephone": EXPECTED_CLIENT["telephone"],
    "email": EXPECTED_CLIENT["email"],
}


class ClientViewTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()

        self.realm_code = 'realm00000'
        self.space_code = 'space00000'
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/clients/client/"
        self.create_client_obj()

    def test__list_and_default(self):
        response = self.client.get(path=self.url)
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()
        self.assertGreater(response_json["count"], 0)
        
        client = response_json["results"][0]
        self.assertEqual(client.keys(), EXPECTED_CLIENT.keys())

    def test__get_filters(self):  # sourcery skip: extract-duplicate-method
        client = self.create_client_obj()
        response = self.client.get(path=f"{self.url}?user_code={client.user_code}")
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

        client = Client.objects.filter(user_code=CREATE_DATA["user_code"])
        self.assertIsNotNone(client)

    def test__update_patch(self):
        response = self.client.post(path=self.url, format="json", data=CREATE_DATA)
        self.assertEqual(response.status_code, 201, response.content)
        response_json = response.json()
        client_id = response_json["id"]

        new_name = "new_name"
        update_data = {"name": new_name}
        response = self.client.patch(
            path=f"{self.url}{client_id}/", format="json", data=update_data
        )
        self.assertEqual(response.status_code, 200, response.content)

        response = self.client.get(path=f"{self.url}?name={new_name}")
        response_json = response.json()
        self.assertEqual(response_json["count"], 1)
        client = response_json["results"][0]
        self.assertEqual(client["name"], new_name)

        #-_-# Portfolios #-_-#
        portfolio = Portfolio.objects.first()
        portfolios = [portfolio.id,]
        update_data = {"portfolios": portfolios}
        response = self.client.patch(
            path=f"{self.url}{client_id}/", format="json", data=update_data
        )
        self.assertEqual(response.status_code, 200, response.content)

        response = self.client.get(path=f"{self.url}?portfolios={portfolio.id}")
        response_json = response.json()
        self.assertEqual(response_json["count"], 1)
        client = response_json["results"][0]
        self.assertEqual(client["portfolios"], portfolios)
        self.assertEqual(client["portfolios_object"][0]["user_code"], portfolio.user_code)

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

    def test__assign_invalid_telephone(self):
        response = self.client.post(path=self.url, format="json", data=CREATE_DATA)
        self.assertEqual(response.status_code, 201, response.content)
        response_json = response.json()
        client_id = response_json["id"]

        update_data = {"telephone": "-1234567890"}
        response = self.client.patch(
            path=f"{self.url}{client_id}/", format="json", data=update_data
        )
        self.assertEqual(response.status_code, 400, response.content)

        update_data = {"telephone": "1234567890123456"}
        response = self.client.patch(
            path=f"{self.url}{client_id}/", format="json", data=update_data
        )
        self.assertEqual(response.status_code, 400, response.content)

    def test__assign_invalid_email(self):
        response = self.client.post(path=self.url, format="json", data=CREATE_DATA)
        self.assertEqual(response.status_code, 201, response.content)
        response_json = response.json()
        client_id = response_json["id"]

        update_data = {"email": "email@outlook"}
        response = self.client.patch(
            path=f"{self.url}{client_id}/", format="json", data=update_data
        )
        self.assertEqual(response.status_code, 400, response.content)

        update_data = {"email": "emailoutlook.com"}
        response = self.client.patch(
            path=f"{self.url}{client_id}/", format="json", data=update_data
        )
        self.assertEqual(response.status_code, 400, response.content)
