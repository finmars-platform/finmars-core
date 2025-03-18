from poms.common.common_base_test import BaseTestCase
from poms.common.factories import AccrualEventFactory, AccrualCalculationScheduleFactory
from poms.instruments.models import (
    AccrualEvent,
    AccrualCalculationSchedule,
    Instrument,
)

class GetAccrualSizePriceMethodTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.instrument = Instrument.objects.first()
        self.accrual_event = AccrualEventFactory(instrument=self.instrument)
        self.accrual_schedule = AccrualCalculationScheduleFactory(instrument=self.instrument)

    def test_init(self):
        self.assertEqual(AccrualEvent.objects.count(), 1)
        self.assertEqual(AccrualCalculationSchedule.objects.count(), 1)
