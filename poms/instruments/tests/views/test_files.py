from poms.common.common_base_test import BaseTestCase
from poms.instruments.models import Instrument, FinmarsFile


class FinmarsFileViewSetTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.realm_code = "realm00000"
        self.space_code = "space00000"
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/instruments/files/"
        self.instrument = Instrument.objects.first()

    def test__api_url(self):
        response = self.client.get(path=self.url)
        response_json = response.json()

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(len(response_json["results"]), 0)
        self.assertEqual(response_json["count"], 0)
        self.assertIn("next", response_json)
        self.assertIn("previous", response_json)
        self.assertIn("meta", response_json)

    def test_retrieve(self):
        file = FinmarsFile.objects.create(
            name="name.pdf",
            path="/root/etc/system/",
            size=1111111111,
        )
        response = self.client.get(path=f"{self.url}{file.id}/")
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        self.assertEqual(response_json["id"], file.id)
        self.assertEqual(response_json["name"], "name.pdf")
        self.assertEqual(response_json["extension"], "pdf")
        self.assertEqual(response_json["path"], "/root/etc/system/")
        self.assertEqual(response_json["size"], 1111111111)
        self.assertIn("created", response_json)
        self.assertIn("modified", response_json)

    def test_list(self):
        amount = 10
        for i in range(1, amount + 1):
            FinmarsFile.objects.create(
                name=f"name_{i}.pdf",
                path="/root/etc/system/",
                size=self.random_int(100, 1000000),
            )

        response = self.client.get(path=self.url)
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        self.assertEqual(response_json["count"], amount)
        self.assertEqual(len(response_json["results"]), amount)
