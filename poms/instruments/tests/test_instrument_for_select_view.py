from django.conf import settings

from poms.common.common_base_test import BaseTestCase
from poms.instruments.models import Instrument


class InstrumentViewSetTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = f"/{settings.BASE_API_URL}/api/v1/instruments/instrument-for-select/"
        self.pricing_policy = None
        self.instrument = Instrument.objects.first()

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
