from datetime import date

from poms.common.common_base_test import BaseTestCase
from poms.common.common_callback_test import CallbackSetTestMixin
from poms.common.database_client import BACKEND_CALLBACK_URLS

# from poms.counterparties.models import Instrument


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
        ("bonds", "bonds"),
        ("stocks", "stocks"),
    )
    def test__instrument_created(self, instrument_type: str):
        post_data = {
            "request_id": self.task.id,
            "data": {
                "items": [
                    {
                        "instrument_type": {
                            "user_code": instrument_type,
                        },
                        "user_code": "test_user_code",
                        "short_name": "test_short_name",
                        "name": "test_name",
                        "pricing_currency": {
                            "code": "USD",
                        },
                        "payment_size_detail": None,
                        "maturity_price": 1.0,
                        "maturity": date.today(),
                        "country": {
                            "code": "USA",
                        },
                        # "attributes": [],
                        # "accrual_calculation_schedules": [],
                    },
                ],
            },
        }

        print(f"test master_user={self.user.master_user.id}")
        response = self.client.post(path=self.url, format="json", data=post_data)
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()
        self.assertEqual(response_json["status"], "ok", response_json)
        self.assertNotIn("message", response_json)
