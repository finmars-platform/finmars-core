from datetime import date

from poms.common.common_base_test import BaseTestCase
from poms.instruments.models import Instrument

YEAR = date.today().year


class PriceDateIsValidTestCase(BaseTestCase):
    def setUp(self):
        self.init_test_case()
        self.instrument = Instrument.objects.last()
        self.instrument.maturity_date = date(YEAR, 12, 31)
        self.instrument.save()

    def test_valid_date_before_maturity(self):
        test_date = date(YEAR, 10, 1)
        self.assertTrue(self.instrument._price_date_is_valid(test_date))

    def test_invalid_date_on_maturity(self):
        test_date = date(YEAR, 12, 31)
        self.assertFalse(self.instrument._price_date_is_valid(test_date))

    def test_invalid_date_after_maturity(self):
        test_date = date(YEAR + 1, 1, 1)
        self.assertFalse(self.instrument._price_date_is_valid(test_date))

    def test_edge_case_maturity_date_none(self):
        self.instrument.maturity_date = None
        test_date = date(YEAR, 10, 1)
        self.assertTrue(self.instrument._price_date_is_valid(test_date))

    def test_error_case_invalid_input_type(self):
        invalid_input = f"{YEAR}-10-01"  # A string instead of a date object
        with self.assertRaises(ValueError) as context:
            self.instrument._price_date_is_valid(invalid_input)
        self.assertEqual(
            str(context.exception),
            "price_date_is_valid: day must be of type date, not <class 'str'>",
        )
