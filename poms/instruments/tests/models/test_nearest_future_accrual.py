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

    def test__in_list(self):
        pass
