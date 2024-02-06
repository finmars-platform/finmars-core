from poms.common.common_base_test import BaseTestCase
from poms.instruments.models import Instrument, PriceHistory
from poms.instruments.fields import AUTO_CALCULATE


class PriceHistoryModeltTest(BaseTestCase):
    databases = "__all__"
    maxDiff = None

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.instrument = Instrument.objects.first()
        self.pricing_history = self.create_pricing_history()
        self.err_msg = self.random_string()

    def create_pricing_history(self) -> PriceHistory:
        return PriceHistory.objects.create(
            instrument=self.instrument,
            principal_price=self.random_int(),
            accrued_price=self.random_int(),
            long_delta=self.random_int(),
            short_delta=self.random_int(),
        )

    def prepare_test(self):
        self.pricing_history.error_message = self.err_msg
        self.pricing_history.save()

        self.pricing_history.refresh_from_db()
        self.assertIn(self.err_msg, self.pricing_history.error_message)

    @BaseTestCase.cases(
        ("none", None),
        ("auto_calculate", AUTO_CALCULATE)
    )
    def test__reset_error_message_when_calculate_accrued_price(self, signal):
        self.prepare_test()

        self.pricing_history.accrued_price = signal
        self.pricing_history.save()

        self.assertFalse(self.err_msg in self.pricing_history.error_message)

    @BaseTestCase.cases(
        ("none", None),
        ("auto_calculate", AUTO_CALCULATE)
    )
    def test__reset_error_message_when_calculate_factor(self, signal):
        self.prepare_test()

        self.pricing_history.factor = signal
        self.pricing_history.save()

        self.assertFalse(self.err_msg in self.pricing_history.error_message)
