from datetime import date

from poms.common.common_base_test import BaseTestCase

from poms.common.formula_accruals import calculate_accrual_event_factor
from poms.instruments.models import AccrualCalculationModel

from poms.instruments.tests.common_test_data import ACCRUAL_MODELS_IDS


class CalculateAccrualEventFactorTests(BaseTestCase):
    def setUp(self):
        self.init_test_case()


    def create_accrual_event(self, ):
        pass

    # def test_calculate_accrual_event_factor_act_360(self):
    #     # Act
    #     accrual_factor = calculate_accrual_event_factor(self.accrual_event, date(2024, 1, 1))
    #
    #     # Assert
    #     # self.assertAlmostEqual(accrual_factor, 364/360, places=5) # id: act_360_full_year
    #
    # def test_calculate_accrual_event_factor_act_365(self):
    #     # Arrange
    #     self.accrual_event.accrual_calcualation_model.id = AccrualCalculationModel.DAY_COUNT_ACT_365L  # Using a supported day count
    #     self.accrual_event.date = date(2024, 6, 30)
    #
    #     # Act
    #     accrual_factor = calculate_accrual_event_factor(self.accrual_event, date(2024, 1, 1))
    #
    #     # Assert
    #     # self.assertAlmostEqual(accrual_factor, 181/365, places=5) # id: act_365_half_year
    #
    #
    # # Add more test methods for other scenarios and edge cases...
