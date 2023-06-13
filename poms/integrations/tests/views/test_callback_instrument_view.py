from datetime import date

from poms.common.common_base_test import BaseTestCase
from poms.common.common_callback_test import CallbackSetTestMixin
from poms.common.database_client import BACKEND_CALLBACK_URLS

from poms.instruments.models import Instrument
from poms.currencies.models import Currency


class CallbackInstrumentViewSetTest(CallbackSetTestMixin, BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.task = self.create_task(
            name="Import Instrument From Finmars Database",
            func="import_instrument_finmars_database",
        )
        self.url = BACKEND_CALLBACK_URLS["instrument"]

    @BaseTestCase.cases(
        ("bond", "bond"),
        ("stock", "stock"),
    )
    def test__instrument_with_currency_created(self, instrument_type: str):
        instrument_code = self.random_string(10)
        currency_code = self.random_string(3)
        post_data = {
            "request_id": self.task.id,
            "data": {
                "instruments": [
                    {
                        "instrument_type": {
                            "user_code": instrument_type,
                        },
                        "user_code": instrument_code,
                        "short_name": "test_short_name",
                        "name": "test_name",
                        "pricing_currency": {
                            "code": currency_code,
                        },
                        "maturity_price": 100.0,
                        "maturity": date.today(),
                        "country": {
                            "code": "USA",
                        },
                    },
                ],
                "currencies": [
                    {
                        "user_code": currency_code,
                        "short_name": f"short_{currency_code}",
                        "name": f"name_{currency_code}",
                        "public_name":  f"public_{currency_code}"
                    }
                ],
            },
        }

        response = self.client.post(path=self.url, format="json", data=post_data)
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()
        self.assertEqual(response_json["status"], "ok", response_json)
        self.assertNotIn("message", response_json)

        self.assertIsNotNone(Instrument.objects.filter(user_code=instrument_code).first())
        self.assertIsNotNone(Currency.objects.filter(user_code=currency_code).first())
