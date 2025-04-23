from poms.common.common_base_test import BaseTestCase
from poms.instruments.models import Instrument, InstrumentType


class InstrumentViewSetTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.realm_code = "realm00000"
        self.space_code = "space00000"
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/instruments/instrument-for-select/"
        self.instrument = Instrument.objects.first()  # Apple

    def test__check_api_url(self):
        response = self.client.get(path=self.url)
        self.assertEqual(response.status_code, 200, response.content)

    def test__filter_and_response(self):
        response = self.client.get(path=f"{self.url}?user_code=Apple")
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        self.assertEqual(len(response_json["results"]), 1)
        user_code = response_json["results"][0]["instrument_type"]
        expected = response_json["results"][0]["instrument_type_object"]["user_code"]
        self.assertEqual(user_code, expected)

    def test__filter_by_query(self):
        response = self.client.get(path=f"{self.url}?query=App")
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        self.assertEqual(len(response_json["results"]), 1)
        user_code = response_json["results"][0]["instrument_type"]
        expected = response_json["results"][0]["instrument_type_object"]["user_code"]
        self.assertEqual(user_code, expected)

    def test__filter_by_empty_query(self):
        response = self.client.get(path=f"{self.url}?query=")
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        self.assertEqual(len(response_json["results"]), 3)

    @BaseTestCase.cases(
        ("stock", "stock"),
        ("bond", "bond"),
    )
    def test__filter_by_instrument_type(self, code):
        i_type = InstrumentType.objects.filter(user_code__endswith=code).first()
        self.instrument.instrument_type = i_type
        self.instrument.save()

        response = self.client.get(path=f"{self.url}?query=&instrument_type={code}")

        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        self.assertEqual(len(response_json["results"]), 2)
