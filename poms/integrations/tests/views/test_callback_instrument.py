from datetime import date
from unittest import skip

from poms.celery_tasks.models import CeleryTask
from poms.common.common_base_test import BaseTestCase
from poms.currencies.models import Currency
from poms.csv_import.handlers import PERIODICITY_MAP
from poms.instruments.models import AccrualCalculationSchedule, Instrument
from poms.integrations.database_client import BACKEND_CALLBACK_URLS
from poms.integrations.tests.common_callback_test import CallbackSetTestMixin


class CallbackInstrumentViewSetTest(CallbackSetTestMixin, BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.task = self.create_task(
            name="Import Instrument From Finmars Database",
            func="import_instrument_finmars_database",
        )
        self.url = BACKEND_CALLBACK_URLS["instrument"]

    def validate_result_instrument(self, instrument_code):
        result = Instrument.objects.filter(user_code=instrument_code).first()
        self.assertIsNotNone(result)
        self.assertIsNotNone(result.country)
        self.assertEqual(result.country.alpha_3, "USA")
        return result

    @skip("till fix the full name instrument type")
    def test__stock_instrument_with_currency_created(self):
        instrument_code = self.random_string(10)
        currency_code = self.random_string(3)
        post_data = {
            "request_id": self.task.id,
            "task_id": None,
            "data": {
                "instruments": [
                    {
                        "instrument_type": {
                            "user_code": "stock",
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
                            "alpha_3": "USA",
                        },
                    },
                ],
                "currencies": [
                    {
                        "user_code": currency_code,
                        "short_name": f"short_{currency_code}",
                        "name": f"name_{currency_code}",
                        "public_name": f"public_{currency_code}",
                    }
                ],
            },
        }

        response = self.client.post(path=self.url, format="json", data=post_data)
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()
        self.assertEqual(response_json["status"], "ok", response_json)
        self.assertNotIn("message", response_json)

        instrument = self.validate_result_instrument(instrument_code)
        self.assertIsNotNone(Currency.objects.filter(user_code=currency_code).first())

        self.task.refresh_from_db()

        self.assertEqual(self.task.status, CeleryTask.STATUS_DONE)

    @skip("till fix the full name instrument type")
    def test__instrument_with_factor_and_accrual_schedules_created(self):
        instrument_code = self.random_string(11)
        currency_code = self.random_string(3)
        post_data = {
            "request_id": self.task.id,
            "task_id": None,
            "data": {
                "instruments": [
                    {
                        "instrument_type": {
                            "user_code": "bond",
                        },
                        "user_code": instrument_code,
                        "short_name": "test_short_name",
                        "name": "test_name",
                        "pricing_currency": {
                            "code": currency_code,
                        },
                        "maturity_price": 100.0,
                        "maturity_date": date.today(),
                        "country": {
                            "alpha_3": "USA",
                        },
                        "factor_schedules": [
                            {"effective_date": "2023-08-08", "factor_value": 1.0},
                            {"effective_date": "2024-02-08", "factor_value": 9.0},
                            {"effective_date": "2025-08-08", "factor_value": 8.0},
                        ],
                        "accrual_calculation_schedules": [
                            {
                                "id": 63,
                                "accrual_start_date": "2017-02-08",
                                "first_payment_date": "2017-02-08",
                                "accrual_size": 0.0875,
                                "periodicity_n": 2,
                                "accrual_calculation_model": 21,
                                "accrual_calculation_model_object": {
                                    "id": 21,
                                    "name": "30/360 German",
                                    "short_name": None,
                                    "user_code": "30/360 German",
                                    "public_name": None,
                                    "notes": None,
                                },
                                "periodicity": 12,
                                "periodicity_object": {
                                    "id": 12,
                                    "name": " Annually",
                                    "short_name": None,
                                    "user_code": "ANNUALLY",
                                    "public_name": None,
                                    "notes": None,
                                },
                                "notes": "",
                            },
                        ],
                    },
                ],
                "currencies": [
                    {
                        "user_code": currency_code,
                        "short_name": f"short_{currency_code}",
                        "name": f"name_{currency_code}",
                        "public_name": f"public_{currency_code}",
                    }
                ],
            },
        }

        response = self.client.post(path=self.url, format="json", data=post_data)
        self.assertEqual(response.status_code, 200, response.content)

        instrument = self.validate_result_instrument(instrument_code)
        self.assertEqual(len(instrument.factor_schedules.all()), 3)
        self.assertEqual(len(instrument.accrual_calculation_schedules.all()), 1)

        accrual = AccrualCalculationSchedule.objects.filter(
            instrument=instrument
        ).first()
        self.assertIsNotNone(accrual)
        self.assertEqual(
            accrual.accrual_calculation_model.user_code,
            "DAY_COUNT_30_360_GERMAN",  # code 21
        )
        self.assertEqual(accrual.periodicity_id, PERIODICITY_MAP[2])
