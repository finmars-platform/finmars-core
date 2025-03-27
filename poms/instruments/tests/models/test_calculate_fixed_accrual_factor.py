from datetime import date

from poms.common.common_base_test import BaseTestCase
from poms.common.factories import AccrualCalculationScheduleFactory
from poms.instruments.finmars_quantlib import calculate_fixed_accrual_factor
from poms.instruments.models import Instrument


class CalculateFixedAccrualFactorTests(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.accrual_schedule = AccrualCalculationScheduleFactory(
            instrument=Instrument.objects.last(),
            accrual_start_date="2023-01-01",
            accrual_size="0.05",  # 5% coupon rate
            accrual_calculation_model_id=4,  # Actual/360
            periodicity_id=11,  # ANNUALLY = 11
        )
        self.maturity_date = date(2030, 12, 30)

    @BaseTestCase.cases(
        ("01", date(2025, 1, 31), 0.005),
        ("02", date(2025, 2, 27), 0.009),
        ("03", date(2025, 3, 31), 0.013),
        ("04", date(2025, 4, 30), 0.018),
        ("05", date(2025, 5, 31), 0.022),
        ("06", date(2025, 6, 30), 0.026),
        ("07", date(2025, 7, 30), 0.03),
        ("08", date(2025, 8, 31), 0.034),
        ("09", date(2025, 9, 30), 0.038),
        ("10", date(2025, 10, 30), 0.043),
        ("11", date(2025, 11, 30), 0.047),
        ("12", date(2025, 12, 23), 0.051),
    )
    def test_accrued_amount_between_issue_and_maturity(self, price_date, expected):
        # Calculate accrued amount for a date between issue date and maturity date

        factor = calculate_fixed_accrual_factor(self.accrual_schedule, self.maturity_date, price_date=price_date)

        self.assertEqual(round(factor, 3), expected)
