from datetime import date
from unittest.mock import patch

from poms.common.common_base_test import BaseTestCase
from poms.common.factories import AccrualEventFactory, AccrualCalculationScheduleFactory
from poms.instruments.models import (
    AccrualEvent,
    AccrualCalculationSchedule,
    Instrument,
)

YEAR = date.today().year


class GetAccruedPriceMethodTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.instrument = Instrument.objects.last()

    def test_init(self):
        self.accrual_event = AccrualEventFactory(instrument=self.instrument)
        self.accrual_schedule = AccrualCalculationScheduleFactory(
            instrument=self.instrument
        )
        self.assertEqual(AccrualEvent.objects.count(), 1)
        self.assertEqual(AccrualCalculationSchedule.objects.count(), 1)

    def test_get_accrued_price_accrual_event(self):
        self.accrual_event = AccrualEventFactory(
            instrument=self.instrument,
            start_date=date(YEAR, 5, 10),
            end_date=date(YEAR, 7, 10),
            accrual_size=100,
        )

        price_date = date(YEAR, 6, 15)
        with patch(
            "poms.instruments.models.calculate_accrual_event_factor",
            return_value=0.5,
        ):
            price = self.instrument.get_accrued_price(price_date)
            self.assertEqual(price, 50.0)

    def test_get_accrued_price_accrual_schedule(self):
        self.accrual_schedule = AccrualCalculationScheduleFactory(
            instrument=self.instrument,
            accrual_start_date=f"{YEAR}-01-01",
            first_payment_date=f"{YEAR}-07-01",
            accrual_size=100,
        )
        price_date = date(YEAR, 6, 15)

        with patch(
            "poms.instruments.models.calculate_accrual_schedule_factor",
            return_value=0.5,
        ):
            price = self.instrument.get_accrued_price(price_date)
            self.assertEqual(price, 50.0)

    def test_get_accrued_price_invalid_date(self):
        self.instrument.maturity_date = date(YEAR, 1, 1)
        price_date = date(YEAR, 1, 2)

        price = self.instrument.get_accrued_price(price_date)

        self.assertEqual(price, 0)

    def test_get_accrued_price_no_any_accrual(self):
        price_date = date(YEAR, 6, 15)

        price = self.instrument.get_accrued_price(price_date)

        self.assertEqual(price, 0)
