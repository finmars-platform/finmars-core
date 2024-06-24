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

    def test__retrieve(self):
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
        self.assertIn("instruments", response_json)
        self.assertIn("created", response_json)
        self.assertIn("modified", response_json)

    def test__retrieve_with_instruments(self):
        file = FinmarsFile.objects.create(
            name="name.pdf",
            path="/root/etc/system/",
            size=self.random_int(1, 1000),
        )
        instrument = Instrument.objects.last()
        instrument.files.add(file)

        response = self.client.get(path=f"{self.url}{file.id}/")
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        self.assertIn("instruments", response_json)
        self.assertEqual(len(response_json["instruments"]), 1)
        instrument_data = response_json["instruments"][0]
        self.assertEqual(instrument_data["id"], instrument.id)
        self.assertEqual(instrument_data["user_code"], instrument.user_code)

    def test__list(self):
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

    @BaseTestCase.cases(
        ("name_1", "name_1", 1),
        ("name_all", "name", 3),
        ("exten", "2.pdf", 1),
        ("path_1", "/root", 3),
        ("path_2", "etc", 3),
        ("path_3", "/system/", 3),
    )
    def test__list_with_filters(
        self,
        value,
        count,
    ):
        amount = 3
        for i in range(1, amount + 1):
            FinmarsFile.objects.create(
                name=f"name_{i}.pdf",
                path="/root/etc/system/",
                size=self.random_int(10, 1000),
            )

        response = self.client.get(path=f"{self.url}?query={value}")
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        self.assertEqual(response_json["count"], count)
        self.assertEqual(len(response_json["results"]), count)

    def test__create(self):
        file_data = dict(
            name=f"{self.random_string(12)}.pdf",
            path=f"/{self.random_string()}/{self.random_string(5)}/",
            size=self.random_int(10, 1000000000),
        )
        response = self.client.post(path=self.url, data=file_data, format="json")
        self.assertEqual(response.status_code, 201, response.content)

        response_json = response.json()

        self.assertEqual(response_json["name"], file_data["name"])
        self.assertEqual(response_json["extension"], "pdf")
        self.assertEqual(response_json["path"], file_data["path"])
        self.assertEqual(response_json["size"], file_data["size"])
        self.assertIn("id", response_json)
        self.assertIn("instruments", response_json)
        self.assertIn("created", response_json)
        self.assertIn("modified", response_json)

    def test__put(self):
        file_data = dict(
            name=f"{self.random_string(12)}.pdf",
            path=f"/{self.random_string()}/{self.random_string(5)}/",
            size=self.random_int(10, 1000000000),
        )
        response = self.client.post(path=self.url, data=file_data, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        response_json = response.json()
        file_id = response_json["id"]
        self.assertEqual(response_json["path"], file_data["path"])

        file_data["path"] = "/root/"
        response = self.client.put(
            path=f"{self.url}{file_id}/", data=file_data, format="json"
        )
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()
        self.assertEqual(response_json["path"], file_data["path"])
