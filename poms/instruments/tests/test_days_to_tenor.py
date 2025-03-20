import unittest

import QuantLib as ql

from poms.instruments.finmars_quantlib import FixedRateBond


class TestDaysToQuantlibPeriod(unittest.TestCase):

    def test_default_30e360_annual(self):
        """Test 360 days with default 30E/360 returns Annual."""
        result = FixedRateBond.convert_days_to_tenor(360)
        self.assertEqual(result, ql.Period(1, ql.Years))

    def test_30e360_semiannual(self):
        """Test 180 days with 30E/360 returns Semiannual."""
        result = FixedRateBond.convert_days_to_tenor(180, ql.Thirty360(ql.Thirty360.European))
        self.assertEqual(result, ql.Period(6, ql.Months))

    def test_30e360_quarterly(self):
        """Test 90 days with 30E/360 returns Quarterly."""
        result = FixedRateBond.convert_days_to_tenor(90, ql.Thirty360(ql.Thirty360.European))
        self.assertEqual(result, ql.Period(3, ql.Months))

    def test_30e360_bimonthly(self):
        """Test 60 days with 30E/360 returns Bimonthly."""
        result = FixedRateBond.convert_days_to_tenor(60, ql.Thirty360(ql.Thirty360.European))
        self.assertEqual(result, ql.Period(2, ql.Months))

    def test_30e360_monthly(self):
        """Test 30 days with 30E/360 returns Monthly."""
        result = FixedRateBond.convert_days_to_tenor(30, ql.Thirty360(ql.Thirty360.European))
        self.assertEqual(result, ql.Period(1, ql.Months))

    def test_30e360_biweekly(self):
        """Test 14 days with 30E/360 returns Biweekly."""
        result = FixedRateBond.convert_days_to_tenor(14, ql.Thirty360(ql.Thirty360.European))
        self.assertEqual(result, ql.Period(ql.Biweekly))

    def test_30e360_every_fourth_week(self):
        """Test 28 days with 30E/360 returns EveryFourthWeek."""
        result = FixedRateBond.convert_days_to_tenor(28, ql.Thirty360(ql.Thirty360.European))
        self.assertEqual(result, ql.Period(ql.EveryFourthWeek))

    def test_actual365_annual(self):
        """Test 365 days with Actual/365 returns Annual."""
        result = FixedRateBond.convert_days_to_tenor(365, ql.Actual365Fixed())
        self.assertEqual(result, ql.Period(1, ql.Years))

    def test_actual365_semiannual(self):
        """Test 182 days with Actual/365 returns Semiannual."""
        result = FixedRateBond.convert_days_to_tenor(182, ql.Actual365Fixed())
        self.assertEqual(result, ql.Period(6, ql.Months))

    def test_actual365_biweekly(self):
        """Test 14 days with Actual/365 returns Biweekly."""
        result = FixedRateBond.convert_days_to_tenor(14, ql.Actual365Fixed())
        self.assertEqual(result, ql.Period(ql.Biweekly))

    def test_actual365_every_fourth_week(self):
        """Test 28 days with Actual/365 returns EveryFourthWeek."""
        result = FixedRateBond.convert_days_to_tenor(28, ql.Actual365Fixed())
        self.assertEqual(result, ql.Period(ql.EveryFourthWeek))

    def test_172_days_30e360(self):
        """Test 172 days with 30E/360 (from user example) returns Semiannual."""
        result = FixedRateBond.convert_days_to_tenor(172, ql.Thirty360(ql.Thirty360.European))
        self.assertEqual(result, ql.Period(6, ql.Months))

    def test_negative_days(self):
        """Test negative days raises ValueError."""
        with self.assertRaises(ValueError):
            FixedRateBond.convert_days_to_tenor(-1)

    def test_zero_days(self):
        """Test zero days raises ValueError."""
        with self.assertRaises(ValueError):
            FixedRateBond.convert_days_to_tenor(0)

    def test_intermediate_days(self):
        """Test an intermediate value (e.g., 20 days) with 30E/360 returns closest period."""
        result = FixedRateBond.convert_days_to_tenor(20, ql.Thirty360(ql.Thirty360.European))
        self.assertEqual(result, ql.Period(ql.Biweekly))  # 20 is closer to 14 than to 28
