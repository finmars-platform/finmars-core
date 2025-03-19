from datetime import date

from poms.common.common_base_test import BaseTestCase
from poms.common.factories import AccrualEventFactory, AccrualCalculationScheduleFactory
from poms.instruments.models import Instrument

YEAR = date.today().year


class GetAccrualSizeMethodTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.instrument = Instrument.objects.last()

    def test_get_accrued_price_accrual_event(self):
        self.accrual_event = AccrualEventFactory(
            instrument=self.instrument,
            start_date=date(YEAR, 5, 10),
            end_date=date(YEAR, 7, 10),
            accrual_size=111,
        )
        price_date = date(YEAR, 6, 15)

        size = self.instrument.get_accrual_size(price_date)

        self.assertEqual(size, 111)

    def test_get_accrued_price_accrual_schedule(self):
        self.accrual_schedule = AccrualCalculationScheduleFactory(
            instrument=self.instrument,
            accrual_start_date = f"{YEAR}-01-01",
            first_payment_date = f"{YEAR}-07-01",
            accrual_size = 222,
        )
        price_date = date(YEAR, 6, 15)

        size = self.instrument.get_accrual_size(price_date)

        self.assertEqual(size, 222)

    def test_get_accrued_price_invalid_date(self):
        self.instrument.maturity_date = date(YEAR, 1, 1)
        price_date = date(YEAR, 1, 2)

        size = self.instrument.get_accrual_size(price_date)

        self.assertEqual(size, 0)

    def test_get_accrued_price_no_any_accrual(self):
        price_date = date(YEAR, 6, 15)

        size = self.instrument.get_accrual_size(price_date)

        self.assertEqual(size, 0)
