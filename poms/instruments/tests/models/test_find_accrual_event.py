from datetime import date

from poms.common.common_base_test import BaseTestCase
from poms.common.factories import AccrualEventFactory
from poms.instruments.models import Instrument

YEAR = BaseTestCase.today().year

AMOUNT = 5


class NearestFutureAccrualTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.instrument = Instrument.objects.first()
        self.instrument.maturity_date = date(year=YEAR + 10, month=12, day=31)
        self.instrument.save()

    def create_accruals(self, amount: int) -> None:
        for year in range(YEAR, YEAR + amount):
            AccrualEventFactory(
                instrument=self.instrument,
                end_date=date(year=year, month=1, day=1),
                periodicity_n=360,
            )

    @BaseTestCase.cases(
        ("0", date(year=YEAR + 0, month=2, day=1)),
        ("1", date(year=YEAR + 1, month=2, day=1)),
        ("2", date(year=YEAR + 2, month=2, day=1)),
        ("3", date(year=YEAR + 3, month=2, day=1)),
    )
    def test__inside_list(self, price_date: date):
        self.create_accruals(AMOUNT)
        accrual = self.instrument.find_accrual_event(price_date)
        self.assertIsNotNone(accrual)
        self.assertEqual(
            accrual.end_date, date(year=price_date.year + 1, month=1, day=1)
        )

    @BaseTestCase.cases(
        ("0", date(year=YEAR - 1, month=12, day=31)),
        ("1", date(year=YEAR - 1, month=11, day=30)),
    )
    def test__earlier_than_first_within_90_days(self, price_date):
        self.create_accruals(AMOUNT)
        accrual = self.instrument.find_accrual_event(price_date)
        self.assertIsNotNone(accrual)

    @BaseTestCase.cases(
        ("0", date(year=YEAR - 2, month=1, day=1)),
        ("1", date(year=YEAR - 2, month=11, day=30)),
    )
    def test__earlier_than_first_one_year(self, price_date):
        self.create_accruals(AMOUNT)
        accrual = self.instrument.find_accrual_event(price_date)
        self.assertIsNone(accrual)

    @BaseTestCase.cases(
        ("0", date(year=YEAR + 7, month=2, day=1)),
        ("1", date(year=YEAR + AMOUNT - 1, month=1, day=2)),
    )
    def test__later_than_last_accrual(self, price_date):
        self.create_accruals(AMOUNT)
        accrual = self.instrument.find_accrual_event(price_date)
        self.assertIsNone(accrual)

    @BaseTestCase.cases(
        ("0", date(year=YEAR + 0, month=1, day=1)),
        ("1", date(year=YEAR + 1, month=1, day=1)),
        ("2", date(year=YEAR + 2, month=1, day=1)),
        ("3", date(year=YEAR + 3, month=1, day=1)),
    )
    def test__exact_date(self, price_date: date):
        self.create_accruals(AMOUNT)
        accrual = self.instrument.find_accrual_event(price_date)
        self.assertIsNotNone(accrual)
        self.assertEqual(accrual.end_date, price_date)
