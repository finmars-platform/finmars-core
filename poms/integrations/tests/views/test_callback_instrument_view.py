from datetime import date

from poms.common.common_base_test import BaseTestCase
from poms.common.common_callback_test import CallbackSetTestMixin
from poms.common.database_client import BACKEND_CALLBACK_URLS

from poms.instruments.models import Instrument  # , InstrumentType, InstrumentClass


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
    def test__instrument_no_currency_created(self, instrument_type: str):
        user_code = self.random_string(10)
        post_data = {
            "request_id": self.task.id,
            "data": {
                "instruments": [
                    {
                        "instrument_type": {
                            "user_code": instrument_type,
                        },
                        "user_code": user_code,
                        "short_name": "test_short_name",
                        "name": "test_name",
                        "pricing_currency": {
                            "code": "USD",
                        },
                        "maturity_price": 100.0,
                        "maturity": date.today(),
                        "country": {
                            "code": "USA",
                        },
                        # "pricing_condition": 1,
                        # "payment_size_detail": 1,
                        # "daily_pricing_model": 6,
                        # "attributes": [],
                        # "accrual_calculation_schedules": [],
                    },
                ],
                "currencies": [
                ],
            },
        }

        response = self.client.post(path=self.url, format="json", data=post_data)
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()
        self.assertEqual(response_json["status"], "ok", response_json)
        self.assertNotIn("message", response_json)

        self.assertIsNotNone(Instrument.objects.filter(user_code=user_code).first())

    @BaseTestCase.cases(
        ("bond", "bond"),
        ("stock", "stock"),
    )
    def test__instrument_with_currency_created(self, instrument_type: str):
        user_code = self.random_string(10)
        post_data = {
            "request_id": self.task.id,
            "data": {
                "instruments": [
                    {
                        "instrument_type": {
                            "user_code": instrument_type,
                        },
                        "user_code": user_code,
                        "short_name": "test_short_name",
                        "name": "test_name",
                        "pricing_currency": {
                            "code": "RUB",
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
                        "code": "RUB",
                        "short_name": "RUB",
                        "name": "Russian Ruble",
                    }
                ],
            },
        }

        response = self.client.post(path=self.url, format="json", data=post_data)
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()
        self.assertEqual(response_json["status"], "ok", response_json)
        self.assertNotIn("message", response_json)

        self.assertIsNotNone(Instrument.objects.filter(user_code=user_code).first())
