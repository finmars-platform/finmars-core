from datetime import date

from poms.common.common_base_test import BaseTestCase
from poms.common.factories import AccrualFactory, AccrualCalculationModelFactory
from poms.instruments.models import (
    AccrualCalculationModel,
    Accrual,
    Instrument,
)



class NearestFutureAccrualTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.instrument = Instrument.objects.first()
        self.start_year = self.today().year

    def create_accruals(self, amount: int) -> None:
        for year in range(self.start_year, self.start_year + amount):
            AccrualFactory(instrument=self.instrument, date=date(year=year, month=1, day=1))

    def test__in_list(self):
        self.create_accruals(5)
