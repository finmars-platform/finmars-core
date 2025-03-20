import unittest
from datetime import date

import QuantLib as ql

from poms.instruments.finmars_quantlib import FixedRateBond

ISSUE_DATE = date(day=1, month=1, year=2020)
MATURITY_DATE = date(day=31, month=12, year=2030)
RATE = 0.03  # 3% annual coupon


class TestBond(unittest.TestCase):
    """Unit tests for the Bond class."""

    def setUp(self):
        """Set up a Bond instance for all tests."""
        self.bond = FixedRateBond(
            issue_date=ISSUE_DATE,
            maturity_date=MATURITY_DATE,
            coupon_rate=RATE,
            days_between_coupons=360,
            day_count=ql.Thirty360(ql.Thirty360.European),  # 30E/360
        )

    def test_accrued_amount_one_third_period(self):
        """Test accrued amount one-third through a coupon period (60/180 days)."""
        eval_date = date(2025, 3, 1)  # 60 days from Jan 1 under 30E/360
        accrued = self.bond.accrued_amount(eval_date)
        # Semiannual coupon = 1000 * 0.03 * 0.5 = 15
        # 60/180 = 0.3333 of period, so 15 * 0.3333 = 5.0
        expected = 5.0
        self.assertAlmostEqual(accrued, expected, places=2, msg="Accrued should be 5.0 at one-third")

    def test_accrued_amount_mid_period(self):
        """Test accrued amount halfway through a coupon period (90/180 days)."""
        eval_date = date(2025, 4, 1)  # 90 days from Jan 1
        accrued = self.bond.accrued_amount(eval_date)
        # 90/180 = 0.5 of period, so 15 * 0.5 = 7.5
        expected = 7.5
        self.assertAlmostEqual(accrued, expected, places=1, msg="Accrued should be 7.5 at mid-period")

    def test_accrued_amount_specific_date(self):
        """Test accrued amount on May 1, 2025 (120/180 days)."""
        eval_date = date(2025, 5, 1)  # 120 days from Jan 1
        accrued = self.bond.accrued_amount(eval_date)
        # 120/180 = 0.6667 of period, so 15 * 0.6667 = 10.0
        expected = 10.0
        self.assertAlmostEqual(accrued, expected, places=2, msg="Accrued should be 10 on May 1")

    def test_accrued_amount_end_of_period(self):
        """Test accrued amount at the end of a coupon period (full coupon)."""
        eval_date = date(2025, 6, 30)  # End of first coupon period
        accrued = self.bond.accrued_amount(eval_date)
        # Full semiannual coupon = 15
        expected = 15.0
        self.assertAlmostEqual(accrued, expected, places=2, msg="Accrued should be 15 at period end")

    def test_accrued_amount_start_of_second_period(self):
        """Test accrued amount at the start of the second coupon period (should be 0)."""
        eval_date = date(2025, 7, 1)  # Start of second coupon period
        accrued = self.bond.accrued_amount(eval_date)
        self.assertAlmostEqual(accrued, 0.0, places=2, msg="Accrued should be 0 at second period start")

    def test_accrued_amount_mid_second_period(self):
        """Test accrued amount halfway through the second coupon period (90/180 days)."""
        eval_date = date(2025, 10, 1)  # 90 days from Jul 1
        accrued = self.bond.accrued_amount(eval_date)
        # 90/180 = 0.5 of period, so 15 * 0.5 = 7.5
        expected = 7.5
        self.assertAlmostEqual(accrued, expected, places=2, msg="Accrued should be 7.5 in second period mid")

    def test_accrued_amount_before_issue(self):
        """Test accrued amount before issue date (should be 0)."""
        eval_date = date(2019, 12, 31)  # Day before issue
        accrued = self.bond.accrued_amount(eval_date)
        self.assertAlmostEqual(accrued, 0.0, places=2, msg="Accrued should be 0 before issue")

    def test_accrued_amount_start_of_period(self):
        """Test accrued amount at the start of a coupon period (should be 0)."""
        eval_date = date(2025, 1, 1)  # Start of first coupon period
        accrued = self.bond.accrued_amount(eval_date)
        self.assertAlmostEqual(accrued, 0.0, places=2, msg="Accrued should be 0 at period start")

    def test_accrued_amount_maturity_date(self):
        """Test accrued amount on maturity date (end of final period)."""
        eval_date = date(2031, 1, 1)  # Maturity date, end of last period
        accrued = self.bond.accrued_amount(eval_date)
        # Last period: Jul 1, 2029 to Jan 1, 2030 = 180 days, full coupon = 15
        expected = 0.0
        self.assertAlmostEqual(accrued, expected, places=2, msg="Accrued should be 15 on maturity")
