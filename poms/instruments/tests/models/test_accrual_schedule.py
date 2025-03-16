from datetime import date

from poms.common.common_base_test import BaseTestCase
from poms.instruments.models import (
    DATE_FORMAT,
    AccrualCalculationSchedule,
    Instrument,
)
from poms.common.factories import ACCRUAL_MODELS_IDS


class AccrualCalculationScheduleModelTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.instrument = Instrument.objects.first()
        self.accrual_model_id = self.random_choice(ACCRUAL_MODELS_IDS)

    @BaseTestCase.cases(
        ("1", date.today(), date.today()),
        ("2", date.today().strftime(DATE_FORMAT), date.today().strftime(DATE_FORMAT)),
        ("3", date.today().strftime(DATE_FORMAT), date.today()),
        ("4", date.today(), date.today().strftime(DATE_FORMAT)),
    )
    def test_create_date_or_str(self, accrual_start_date, first_payment_date):
        AccrualCalculationSchedule.objects.create(
            instrument=self.instrument,
            accrual_calculation_model_id=self.accrual_model_id,
            accrual_start_date=accrual_start_date,
            first_payment_date=first_payment_date,
        )

    @BaseTestCase.cases(
        ("int", 172651),
        ("str", "18736"),
    )
    def test_error_invalid_start_date(self, accrual_start_date):
        with self.assertRaises(Exception):
            AccrualCalculationSchedule.objects.create(
                instrument=self.instrument,
                accrual_calculation_model_id=self.accrual_model_id,
                accrual_start_date=accrual_start_date,
                first_payment_date=self.random_future_date(),
            )

    @BaseTestCase.cases(
        ("int", 827634),
        ("str", "827634"),
    )
    def test_error_invalid_first_payment_date(self, first_payment_date):
        with self.assertRaises(Exception):
            AccrualCalculationSchedule.objects.create(
                instrument=self.instrument,
                accrual_calculation_model_id=self.accrual_model_id,
                accrual_start_date=self.random_future_date(),
                first_payment_date=first_payment_date,
            )

    @BaseTestCase.cases(
        ("date", date.today()),
        ("str", date.today().strftime(DATE_FORMAT)),
    )
    def test_duplicated_start_date(self, accrual_start_date):
        old_accrual = AccrualCalculationSchedule.objects.create(
            instrument=self.instrument,
            accrual_calculation_model_id=self.accrual_model_id,
            accrual_start_date=accrual_start_date,
            first_payment_date=self.random_future_date(),
        )

        new_accrual = AccrualCalculationSchedule.objects.create(
            instrument=self.instrument,
            accrual_calculation_model_id=self.accrual_model_id,
            accrual_start_date=accrual_start_date,
            first_payment_date=self.random_future_date(),
            notes=self.random_string(),
        )

        self.assertEqual(old_accrual.id, new_accrual.id)
        self.assertNotEqual(old_accrual.notes, new_accrual.notes)
        self.assertNotEqual(old_accrual.first_payment_date, new_accrual.first_payment_date)

    @BaseTestCase.cases(
        ("date", date.today()),
        ("str", date.today().strftime(DATE_FORMAT)),
    )
    def test__try_to_save_duplicated_start_date(self, accrual_start_date):
        old_accrual = AccrualCalculationSchedule.objects.create(
            instrument=self.instrument,
            accrual_start_date=accrual_start_date,
            accrual_calculation_model_id=self.accrual_model_id,
            first_payment_date=self.yesterday(),
        )

        new_first_date = self.random_future_date()
        new_accrual = AccrualCalculationSchedule(
            instrument=self.instrument,
            accrual_start_date=accrual_start_date,
            accrual_calculation_model_id=self.accrual_model_id,
            first_payment_date=new_first_date,
        )
        new_accrual.save()

        old_accrual.refresh_from_db()

        self.assertEqual(old_accrual.first_payment_date, new_first_date.strftime(DATE_FORMAT))
