from datetime import date

from poms.common.common_base_test import BaseTestCase
from poms.common.factories import AccrualCalculationScheduleFactory
from poms.instruments.finmars_quantlib import calculate_accrual_schedule_ratio
from poms.instruments.models import Instrument, Periodicity, AccrualCalculationModel


class CalculateAccrualScheduleRatioTests(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()

    @BaseTestCase.cases(
        ("01", date(2025, 1, 31), 0.1),
        ("02", date(2025, 2, 27), 0.175),
        ("03", date(2025, 3, 31), 0.258),
        ("04", date(2025, 4, 30), 0.35),
        ("05", date(2025, 5, 31), 0.43),
        ("06", date(2025, 6, 30), 0.511),
        ("07", date(2025, 7, 30), 0.594),
        ("08", date(2025, 8, 31), 0.683),
        ("09", date(2025, 9, 30), 0.767),
        ("10", date(2025, 10, 30), 0.855),
        ("11", date(2025, 11, 30), 0.936),
        ("12", date(2025, 12, 23), 1.01),
    )
    def test_accrued_ratio_annually(self, price_date, expected):
        self.accrual_schedule = AccrualCalculationScheduleFactory(
            instrument=Instrument.objects.last(),
            accrual_start_date="2023-01-01",
            accrual_size="0.05",  # 5% coupon rate
            accrual_calculation_model_id=AccrualCalculationModel.DAY_COUNT_ACT_360,  # Actual/360
            periodicity_id=Periodicity.ANNUALLY,
        )
        self.maturity_date = date(2030, 12, 30)

        ratio = calculate_accrual_schedule_ratio(self.accrual_schedule, self.maturity_date, price_date=price_date)
        self.assertAlmostEqual(ratio, expected, places=2, msg="ratio should be equal with 2 decimals")

    @BaseTestCase.cases(
        ("01", date(2025, 1, 31), 0.1),
        ("02", date(2025, 2, 27), 0.175),
        ("03", date(2025, 3, 31), 0.258),
        ("04", date(2025, 4, 30), 0.35),
        ("05", date(2025, 5, 31), 0.43),
        ("06", date(2025, 6, 30), 0.005),
        ("07", date(2025, 7, 30), 0.088),
        ("08", date(2025, 8, 31), 0.175),
        ("09", date(2025, 9, 30), 0.258),
        ("10", date(2025, 10, 30), 0.35),
        ("11", date(2025, 11, 30), 0.43),
        ("12", date(2025, 12, 23), 0.505),
    )
    def test_accrued_ratio_semiannually(self, price_date, expected):
        self.accrual_schedule = AccrualCalculationScheduleFactory(
            instrument=Instrument.objects.last(),
            accrual_start_date="2023-01-01",
            accrual_size="0.05",  # 5% coupon rate
            accrual_calculation_model_id=AccrualCalculationModel.DAY_COUNT_ACT_360,  # Actual/360
            periodicity_id=Periodicity.SEMI_ANNUALLY,
        )
        self.maturity_date = date(2030, 12, 30)

        ratio = calculate_accrual_schedule_ratio(self.accrual_schedule, self.maturity_date, price_date=price_date)
        self.assertAlmostEqual(ratio, expected, places=2, msg="ratio should be equal with 2 decimals")
