from datetime import date

from poms.common.common_base_test import BaseTestCase
from poms.common.factories import AccrualFactory
from poms.instruments.models import Instrument

YEAR = BaseTestCase.today().year

AMOUNT = 5

class NearestFutureAccrualTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.instrument = Instrument.objects.first()

    def create_accruals(self, amount: int) -> None:
        for year in range(YEAR, YEAR + amount):
            AccrualFactory(instrument=self.instrument, date=date(year=year, month=1, day=1))

    @BaseTestCase.cases(
        ("0", date(year=YEAR+0, month=2, day=1)),
        ("1", date(year=YEAR+1, month=2, day=1)),
        ("2", date(year=YEAR+2, month=2, day=1)),
        ("3", date(year=YEAR+3, month=2, day=1)),
    )
    def test__inside_list(self, target_date):
        self.create_accruals(AMOUNT)
        accrual = self.instrument.find_nearest_future_accrual(target_date)
        self.assertIsNotNone(accrual)


    @BaseTestCase.cases(
        ("0", date(year=YEAR-1, month=1, day=1)),
        ("1", date(year=YEAR-1, month=12, day=31)),
        ("2", date(year=YEAR+7, month=2, day=1)),
        ("3", date(year=YEAR+AMOUNT-1, month=1, day=2)),
    )
    def test__outside_list(self, target_date):
        self.create_accruals(AMOUNT)
        accrual = self.instrument.find_nearest_future_accrual(target_date)
        self.assertIsNone(accrual)
