from datetime import date

from poms.common.common_base_test import BaseTestCase
from poms.common.factories import (
    AccrualCalculationModel,
    AccrualCalculationModelFactory,
    AccrualFactory,
)
from poms.common.formula_accruals import calculate_accrual_event_factor
from poms.instruments.models import Accrual


class CalculateAccrualEventFactorTests(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        self.init_test_case()

    def create_accrual_event(self, model_type: int, day: date) -> Accrual:
        return AccrualFactory(
            instrument=self.default_instrument,
            accrual_calculation_model=AccrualCalculationModelFactory(model_type=model_type),
            date=day,
        )

    @BaseTestCase.cases(
        ("DAY_COUNT_ACT_ACT_ICMA", AccrualCalculationModel.DAY_COUNT_ACT_ACT_ICMA),
        ("DAY_COUNT_ACT_ACT_ISDA", AccrualCalculationModel.DAY_COUNT_ACT_ACT_ISDA),
        ("DAY_COUNT_ACT_360", AccrualCalculationModel.DAY_COUNT_ACT_360),
        ("DAY_COUNT_ACT_365L", AccrualCalculationModel.DAY_COUNT_ACT_365L),
        ("DAY_COUNT_30_360_ISDA", AccrualCalculationModel.DAY_COUNT_30_360_ISDA),
        ("DAY_COUNT_30E_PLUS_360", AccrualCalculationModel.DAY_COUNT_30E_PLUS_360),
        ("DAY_COUNT_NL_365", AccrualCalculationModel.DAY_COUNT_NL_365),
        ("DAY_COUNT_30_360_US", AccrualCalculationModel.DAY_COUNT_30_360_US),
        ("DAY_COUNT_BD_252", AccrualCalculationModel.DAY_COUNT_BD_252),
        ("DAY_COUNT_30_360_GERMAN", AccrualCalculationModel.DAY_COUNT_30_360_GERMAN),
        ("DAY_COUNT_ACT_365_FIXED", AccrualCalculationModel.DAY_COUNT_ACT_365_FIXED),
        ("DAY_COUNT_30E_360", AccrualCalculationModel.DAY_COUNT_30E_360),
        ("DAY_COUNT_ACT_365A", AccrualCalculationModel.DAY_COUNT_ACT_365A),
        ("DAY_COUNT_ACT_366", AccrualCalculationModel.DAY_COUNT_ACT_366),
        ("DAY_COUNT_ACT_364", AccrualCalculationModel.DAY_COUNT_ACT_364),
        # CURRENTLY UNUSED BY CBOND
        ("DAY_COUNT_ACT_365", AccrualCalculationModel.DAY_COUNT_ACT_365),
        ("DAY_COUNT_30_360_ISMA", AccrualCalculationModel.DAY_COUNT_30_360_ISMA),
        ("DAY_COUNT_ACT_ACT_AFB", AccrualCalculationModel.DAY_COUNT_ACT_ACT_AFB),
        ("DAY_COUNT_30_365", AccrualCalculationModel.DAY_COUNT_30_365),
        ("DAY_COUNT_SIMPLE", AccrualCalculationModel.DAY_COUNT_SIMPLE),
    )
    def test_create_all_models_and_counter(self, model_type: int):
        accrual_event = self.create_accrual_event(model_type, self.random_future_date())
        self.assertIsNotNone(accrual_event)

        day_counter = accrual_event.accrual_calculation_model.get_quantlib_day_count(
            accrual_event.accrual_calculation_model.id
        )
        self.assertIsNotNone(day_counter)

        self.assertTrue(hasattr(day_counter, "dayCount"))
        self.assertTrue(hasattr(day_counter, "yearFraction"))

    @BaseTestCase.cases(
        ("DAY_COUNT_ACT_ACT_ICMA", AccrualCalculationModel.DAY_COUNT_ACT_ACT_ICMA),
        ("DAY_COUNT_ACT_ACT_ISDA", AccrualCalculationModel.DAY_COUNT_ACT_ACT_ISDA),
        ("DAY_COUNT_ACT_360", AccrualCalculationModel.DAY_COUNT_ACT_360),
        ("DAY_COUNT_ACT_365L", AccrualCalculationModel.DAY_COUNT_ACT_365L),
        ("DAY_COUNT_30_360_ISDA", AccrualCalculationModel.DAY_COUNT_30_360_ISDA),
        ("DAY_COUNT_30E_PLUS_360", AccrualCalculationModel.DAY_COUNT_30E_PLUS_360),
        ("DAY_COUNT_NL_365", AccrualCalculationModel.DAY_COUNT_NL_365),
        ("DAY_COUNT_30_360_US", AccrualCalculationModel.DAY_COUNT_30_360_US),
        ("DAY_COUNT_BD_252", AccrualCalculationModel.DAY_COUNT_BD_252),
        ("DAY_COUNT_30_360_GERMAN", AccrualCalculationModel.DAY_COUNT_30_360_GERMAN),
        ("DAY_COUNT_ACT_365_FIXED", AccrualCalculationModel.DAY_COUNT_ACT_365_FIXED),
        ("DAY_COUNT_30E_360", AccrualCalculationModel.DAY_COUNT_30E_360),
        ("DAY_COUNT_ACT_365A", AccrualCalculationModel.DAY_COUNT_ACT_365A),
        ("DAY_COUNT_ACT_366", AccrualCalculationModel.DAY_COUNT_ACT_366),
        ("DAY_COUNT_ACT_364", AccrualCalculationModel.DAY_COUNT_ACT_364),
        # CURRENTLY UNUSED BY CBOND
        ("DAY_COUNT_ACT_365", AccrualCalculationModel.DAY_COUNT_ACT_365),
        ("DAY_COUNT_30_360_ISMA", AccrualCalculationModel.DAY_COUNT_30_360_ISMA),
        ("DAY_COUNT_ACT_ACT_AFB", AccrualCalculationModel.DAY_COUNT_ACT_ACT_AFB),
        ("DAY_COUNT_30_365", AccrualCalculationModel.DAY_COUNT_30_365),
        ("DAY_COUNT_SIMPLE", AccrualCalculationModel.DAY_COUNT_SIMPLE),
    )
    def test_calculate_accrual_event_factor_act_360(self, model_type):
        accrual_event = self.create_accrual_event(model_type, date(2026, 1, 1))
        accrual_factor = calculate_accrual_event_factor(accrual_event, date(2025, 6, 1))

        print(f"June 1st {accrual_factor=}")

    @BaseTestCase.cases(
        ("DAY_COUNT_ACT_ACT_ICMA", AccrualCalculationModel.DAY_COUNT_ACT_ACT_ICMA),
        ("DAY_COUNT_ACT_ACT_ISDA", AccrualCalculationModel.DAY_COUNT_ACT_ACT_ISDA),
        ("DAY_COUNT_ACT_360", AccrualCalculationModel.DAY_COUNT_ACT_360),
        ("DAY_COUNT_ACT_365L", AccrualCalculationModel.DAY_COUNT_ACT_365L),
        ("DAY_COUNT_30_360_ISDA", AccrualCalculationModel.DAY_COUNT_30_360_ISDA),
        ("DAY_COUNT_30E_PLUS_360", AccrualCalculationModel.DAY_COUNT_30E_PLUS_360),
        ("DAY_COUNT_NL_365", AccrualCalculationModel.DAY_COUNT_NL_365),
        ("DAY_COUNT_30_360_US", AccrualCalculationModel.DAY_COUNT_30_360_US),
        ("DAY_COUNT_BD_252", AccrualCalculationModel.DAY_COUNT_BD_252),
        ("DAY_COUNT_30_360_GERMAN", AccrualCalculationModel.DAY_COUNT_30_360_GERMAN),
        ("DAY_COUNT_ACT_365_FIXED", AccrualCalculationModel.DAY_COUNT_ACT_365_FIXED),
        ("DAY_COUNT_30E_360", AccrualCalculationModel.DAY_COUNT_30E_360),
        ("DAY_COUNT_ACT_365A", AccrualCalculationModel.DAY_COUNT_ACT_365A),
        ("DAY_COUNT_ACT_366", AccrualCalculationModel.DAY_COUNT_ACT_366),
        ("DAY_COUNT_ACT_364", AccrualCalculationModel.DAY_COUNT_ACT_364),
        # CURRENTLY UNUSED BY CBOND
        ("DAY_COUNT_ACT_365", AccrualCalculationModel.DAY_COUNT_ACT_365),
        ("DAY_COUNT_30_360_ISMA", AccrualCalculationModel.DAY_COUNT_30_360_ISMA),
        ("DAY_COUNT_ACT_ACT_AFB", AccrualCalculationModel.DAY_COUNT_ACT_ACT_AFB),
        ("DAY_COUNT_30_365", AccrualCalculationModel.DAY_COUNT_30_365),
        ("DAY_COUNT_SIMPLE", AccrualCalculationModel.DAY_COUNT_SIMPLE),
    )
    def test_calculate_accrual_event_factor_act_360(self, model_type):
        accrual_event = self.create_accrual_event(model_type, date(2026, 1, 1))
        accrual_factor = calculate_accrual_event_factor(accrual_event, date(2025, 12, 31))

        print(f"December 31st {accrual_factor=}")
