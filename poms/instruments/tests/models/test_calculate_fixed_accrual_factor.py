from datetime import date
from unittest import TestCase
from unittest.mock import Mock

import QuantLib as ql

from poms.instruments.finmars_quantlib import calculate_fixed_accrual_factor


class CalculateFixedAccrualFactorTests(TestCase):

    # Calculate accrued amount for a date between issue date and maturity date
    def test_accrued_amount_between_issue_and_maturity(self):
        accrual_schedule = Mock()
        accrual_schedule.accrual_start_date = "2023-01-01"
        accrual_schedule.accrual_size = "0.05"  # 5% coupon rate
        accrual_schedule.accrual_calculation_model.get_quantlib_day_count.return_value = ql.Actual360()
        accrual_schedule.accrual_calculation_model_id = 1
        accrual_schedule.periodicity = Mock()
        accrual_schedule.periodicity.get_quantlib_periodicity.return_value = ql.Period(ql.Annual)
        accrual_schedule.periodicity.id = 1

        maturity_date = date(2030, 12, 30)
        price_date = date(2023, 7, 1)  # Halfway through the bond's life

        for day in [
            date(2025, 1, 31),
            date(2025, 2, 27),
            date(2025, 3, 31),
            date(2025, 4, 30),
            date(2025, 5, 31),
            date(2025, 6, 30),
        ]:
            factor = calculate_fixed_accrual_factor(accrual_schedule, maturity_date, price_date=day)

            print(day, factor)

            # self.assertLess(result, float(accrual_schedule.accrual_size))
