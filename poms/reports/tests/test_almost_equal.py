from django.test import TestCase

from poms.reports.backend_reports_utils import (
    almost_equal_floats,
    BackendReportHelperService,
)


class TestAlmostEqualFloats(TestCase):
    def test_equal_values(self):
        self.assertTrue(almost_equal_floats(1.2345, 1.2345))
        self.assertTrue(almost_equal_floats(0.0, 0.0))
        self.assertTrue(almost_equal_floats(-5.6789, -5.6789))

    def test_equal_up_to_n_decimals(self):
        self.assertTrue(
            almost_equal_floats(1.234567, 1.234599)
        )  # Equal up to 4 decimals
        self.assertFalse(
            almost_equal_floats(1.234567, 1.235599)
        )  # Different at 3rd decimal

    def test_not_equal(self):
        self.assertFalse(almost_equal_floats(1.23, 1.24))
        self.assertFalse(almost_equal_floats(-0.0001, 0.0001))

    def test_negative_numbers(self):
        self.assertTrue(almost_equal_floats(-1.2345, -1.23451))
        self.assertTrue(almost_equal_floats(-1.2342, -1.2346, round_digits=3))

    def test_large_numbers(self):
        self.assertTrue(almost_equal_floats(123456.1234, 123456.1234))
        self.assertTrue(
            almost_equal_floats(123456.12343, 123456.12346)
        )  # Equal up to 4 decimals
        self.assertFalse(almost_equal_floats(123456.1234, 123456.1235))

    def test_small_numbers(self):
        # Equal (diff < epsilon=0.0001)
        self.assertTrue(almost_equal_floats(0.00001, 0.00002, round_digits=4))

        # Not equal (diff = epsilon)
        self.assertFalse(almost_equal_floats(0.0001, 0.0002, round_digits=4))

    def test_edge_cases(self):
        self.assertFalse(
            almost_equal_floats(float("nan"), float("nan"))
        )  # NaN is not equal to itself
        self.assertTrue(
            almost_equal_floats(1.000049, 1.000051, round_digits=4)
        )  # Very close

    def test_custom_round_digits(self):
        self.assertTrue(
            almost_equal_floats(1.234567, 1.234568, round_digits=5)
        )  # Equal up to 5 decimals
        self.assertFalse(
            almost_equal_floats(1.234567, 1.234577, round_digits=5)
        )  # Different at 5th decimal


class TestFilterValueFromTable(TestCase):
    def setUp(self):
        super().setUp()
        self.service = BackendReportHelperService()

    def test_equal_values(self):
        result = self.service.filter_value_from_table(5.43217, 5.43210, "equal")
        self.assertTrue(result)

    def test_not_equal_values(self):
        result = self.service.filter_value_from_table(5.4321, 5.4321, "not_equal")
        self.assertFalse(result)

    def test_equal_small_numbers(self):
        result = self.service.filter_value_from_table(0.00001, 0.00002, "equal")
        self.assertTrue(result)

    def test_not_equal_small_numbers(self):
        result = self.service.filter_value_from_table(0.00001, 0.00002, "not_equal")
        self.assertFalse(result)
