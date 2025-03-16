from datetime import date

from poms.celery_tasks.models import CeleryTask
from poms.common.common_base_test import BaseTestCase
from poms.csv_import.handlers import PERIODICITY_MAP
from poms.currencies.models import Currency
from poms.instruments.models import AccrualEvent, AccrualCalculationSchedule, Instrument
from poms.integrations.database_client import get_backend_callback_urls
from poms.integrations.tests.common_callback_test import CallbackSetTestMixin


class CallbackInstrumentViewSetTest(CallbackSetTestMixin, BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.task = self.create_task(
            name="Import Instrument From Finmars Database",
            func="import_instrument_finmars_database",
        )
        backend_callback_urls = get_backend_callback_urls()
        self.url = backend_callback_urls["instrument"]
        self.identifier = {
            "cbond_id": f"{self.random_int(_max=1000)}",
            "isin": self.random_string(12),
            "state_reg_number": self.random_string(15),
            "bbgid": self.random_string(),
            "isin_code_144a": "",
            "isin_code_3": "",
            "database_id": self.random_int(_max=1000),
        }

    def validate_result_instrument(self, instrument_code):
        instrument = Instrument.objects.filter(user_code=instrument_code).first()
        self.assertIsNotNone(instrument)
        self.assertIsNotNone(instrument.country)
        self.assertEqual(instrument.country.alpha_3, "USA")

        self.assertEqual(instrument.identifier.keys(), self.identifier.keys())
        return instrument

    def test__stock_with_currency_created(self):
        instrument_code = self.random_string()
        currency_code = self.random_choice(["USD", "EUR"])
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
                        "identifier": self.identifier,
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

        self.validate_result_instrument(instrument_code)
        self.assertIsNotNone(Currency.objects.filter(user_code=currency_code).first())

        self.task.refresh_from_db()

        self.assertEqual(self.task.status, CeleryTask.STATUS_DONE)

    def test__bond_with_factor_and_accrual_schedules_created(self):
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
                        "identifier": self.identifier,
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
                                "accrual_size": 0.1,
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
                            {
                                "id": 64,
                                "accrual_start_date": "2018-01-31",
                                "first_payment_date": "2018-02-27",
                                "accrual_size": 0.2,
                                "periodicity_n": 2,
                                "accrual_calculation_model": 3,
                                "accrual_calculation_model_object": {
                                    "id": 3,
                                    "name": "Actual/Actual (ISDA)",
                                    "short_name": None,
                                    "user_code": "Actual/Actual (ISDA)",
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
                        "accrual_events": [],
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
        self.assertEqual(len(instrument.accrual_calculation_schedules.all()), 2)

        accruals = AccrualCalculationSchedule.objects.filter(instrument=instrument).order_by("accrual_start_date")
        accrual_1 = accruals[0]
        self.assertIsNotNone(accrual_1)
        self.assertEqual(
            accrual_1.accrual_calculation_model.user_code,
            "DAY_COUNT_30_360_GERMAN",  # code 21
        )
        self.assertEqual(accrual_1.periodicity_id, PERIODICITY_MAP[2])

        accrual_2 = accruals[1]
        self.assertIsNotNone(accrual_2)
        self.assertEqual(
            accrual_2.accrual_calculation_model.user_code,
            "DAY_COUNT_ACT_ACT_ISDA",  # code 3
        )
        self.assertEqual(accrual_2.periodicity_id, PERIODICITY_MAP[2])

    def test__instrument_with_periodicity_created(self):
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
                        "identifier": self.identifier,
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
                                "periodicity_n": 0,  # should be set as ANNUALLY
                                "accrual_calculation_model": 21,
                                "accrual_calculation_model_object": {
                                    "id": 21,
                                    "name": "30/360 German",
                                    "short_name": None,
                                    "user_code": "30/360 German",
                                    "public_name": None,
                                    "notes": None,
                                },
                                "periodicity": None,  # should be set as ANNUALLY
                                "periodicity_object": {},
                                "notes": "",
                            },
                        ],
                        "accrual_events": [],
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

        accrual = AccrualCalculationSchedule.objects.filter(instrument=instrument).first()
        self.assertIsNotNone(accrual)
        self.assertEqual(
            accrual.accrual_calculation_model.user_code,
            "DAY_COUNT_30_360_GERMAN",  # code 21
        )
        self.assertEqual(accrual.periodicity_id, PERIODICITY_MAP[1])

    def test__instrument_with_accrual_events_created(self):
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
                        "identifier": self.identifier,
                        "factor_schedules": [],
                        "accrual_calculation_schedules": [],
                        "accrual_events": [
                            {
                                "accrual_calculation_model": 100,
                                "accrual_calculation_model_object": {
                                    "id": 100,
                                    "name": "Simple",
                                    "notes": None,
                                    "public_name": None,
                                    "short_name": None,
                                    "user_code": "Simple",
                                },
                                "accrual_size": 0.523087370779387,
                                "end_date": "2025-01-01",
                                "notes": "cQoXedKAFbWwtOmBPSkV",
                                "payment_date": "2025-01-03",
                                "periodicity_n": 248,
                                "start_date": "2024-04-28",
                                "user_code": "VANGUARD:2025-01-01",
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

        self.assertEqual(len(instrument.accrual_events.all()), 1)
        accrual_event = AccrualEvent.objects.filter(instrument=instrument).first()
        self.assertIsNotNone(accrual_event)

        event_data: dict = post_data["data"]["instruments"][0]["accrual_events"][0]
        self.assertEqual(accrual_event.user_code, event_data["user_code"])
        self.assertEqual(accrual_event.periodicity_n, event_data["periodicity_n"])
        self.assertEqual(accrual_event.accrual_calculation_model_id, event_data["accrual_calculation_model"])
        self.assertEqual(accrual_event.accrual_size, event_data["accrual_size"])
        self.assertEqual(str(accrual_event.start_date), event_data["start_date"])
        self.assertEqual(str(accrual_event.end_date), event_data["end_date"])
        self.assertEqual(str(accrual_event.payment_date), event_data["payment_date"])
        self.assertEqual(accrual_event.notes, event_data["notes"])
