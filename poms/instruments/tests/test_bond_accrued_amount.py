from datetime import date
from unittest import TestCase

import QuantLib as ql

from poms.instruments.finmars_quantlib import Actual365A, Actual365L, FixedRateBond

ISSUE_DATE = date(day=1, month=1, year=2020)
MATURITY_DATE = date(day=31, month=12, year=2030)
RATE = 0.03  # 3% annual coupon
FACE_AMOUNT = 1000


class TestBond(TestCase):
    """Unit tests for the Bond class."""

    def setUp(self):
        """Set up a Bond instance for all tests."""
        self.bond = FixedRateBond(
            issue_date=ISSUE_DATE,
            maturity_date=MATURITY_DATE,
            coupon_rate=RATE,
            days_between_coupons=360,
            day_count=ql.Thirty360(ql.Thirty360.European),  # 30E/360
            face_amount=FACE_AMOUNT,
        )

    # def test_null(self):
    #     year_days = 360
    #     periods = (
    #         (ql.Period(1, ql.Years), year_days),  # 360 or 365 days
    #         (ql.Period(6, ql.Months), year_days / 2),  # 180 or 182.5 days
    #         (ql.Period(3, ql.Months), year_days / 4),  # 90 or 91.25 days
    #         (ql.Period(2, ql.Months), year_days / 6),  # 60 or 60.833 days
    #         (ql.Period(1, ql.Months), year_days / 12),  # 30 or 30.417 days
    #         (ql.Period(ql.EveryFourthWeek), 28),  # 28 days (4 weeks)
    #         (ql.Period(ql.Biweekly), 14),  # 14 days (2 weeks)
    #     )
    #
    #     for p, d in periods:
    #         p.frequency()
    #
    # def test_cash_flows(self):
    #     for coupon in self.bond.cash_flows():
    #         ql_date = coupon.date()
    #         day = date(ql_date.year(), ql_date.month(), ql_date.dayOfMonth())
    #         print(day, coupon.amount())

    def test_prices(self):
        start_date = ql.Date(1, 1, 2025)
        end_date = ql.Date(30, 12, 2025)
        coupon_days = self.bond.day_count.dayCount(start_date, end_date)

        print(f"face amount = {FACE_AMOUNT}")
        print(f"coupon rate = {RATE}")
        print("day count = 30E/360\n")
        print("   date     method  manual   diff")

        for i, eval_date in enumerate([
            date(2025, 1, 31),
            date(2025, 2, 27),
            date(2025, 3, 31),
            date(2025, 4, 30),
            date(2025, 5, 31),
            date(2025, 6, 30),
            date(2025, 7, 31),
            date(2025, 8, 31),
            date(2025, 9, 30),
            date(2025, 10, 31),
            date(2025, 11, 30),
            date(2025, 12, 28),
        ], start=1):
            # print("NPV=", self.bond.ql_bond.NPV())
            # print("cleanPrice=", self.bond.ql_bond.cleanPrice())
            # print("dirtyPrice=", self.bond.ql_bond.dirtyPrice())
            accrued_ratio = round(self.bond.accrued_amount(eval_date) / 100, 4)
            amount_1 = round(self.bond.face_amount * accrued_ratio, 2)

            price_date = ql.Date(eval_date.day, eval_date.month, eval_date.year)
            days_to_price = self.bond.day_count.dayCount(start_date, price_date)
            accrual_factor = round(RATE * (days_to_price / coupon_days), 4)
            amount_2 = round(self.bond.face_amount * accrual_factor, 2)

            diff = round(amount_2 - amount_1, 2)
            percent = int(round((diff / (RATE * FACE_AMOUNT)) * 100, 0))
            print(f"{str(eval_date)}  {amount_1:5.2f}   {amount_2:5.2f}    {percent}%")

    # def test_accrued_amount_one_third_period(self):
    #     """Test accrued amount one-third through a coupon period (60/180 days)."""
    #       # 60 days from Jan 1 under 30E/360
    #     accrued = self.bond.accrued_amount(eval_date)
    #     print(f"dirty_price={self.bond.ql_bond.dirty_price()}")
    #     print(
    #         f"yield={self.bond.ql_bond.bondYield(self.bond.day_count, self.bond.compounding, self.bond.compounding_frequency)}"
    #     )
    #
    #     # Semiannual coupon = 1000 * 0.03 * 0.5 = 15
    #     # 60/180 = 0.3333 of period, so 15 * 0.3333 = 5.0
    #     expected = 5.0
    #     self.assertAlmostEqual(accrued, expected, places=2, msg="Accrued should be 5.0 at one-third")

    # def test_accrued_amount_mid_period(self):
    #     """Test accrued amount halfway through a coupon period (90/180 days)."""
    #     eval_date = date(2025, 4, 1)  # 90 days from Jan 1
    #     accrued = self.bond.accrued_amount(eval_date)
    #     # 90/180 = 0.5 of period, so 15 * 0.5 = 7.5
    #     expected = 7.5
    #     self.assertAlmostEqual(accrued, expected, places=1, msg="Accrued should be 7.5 at mid-period")
    #
    # def test_accrued_amount_specific_date(self):
    #     """Test accrued amount on May 1, 2025 (120/180 days)."""
    #     eval_date = date(2025, 5, 1)  # 120 days from Jan 1
    #     accrued = self.bond.accrued_amount(eval_date)
    #     # 120/180 = 0.6667 of period, so 15 * 0.6667 = 10.0
    #     expected = 10.0
    #     self.assertAlmostEqual(accrued, expected, places=2, msg="Accrued should be 10 on May 1")
    #
    # def test_accrued_amount_end_of_period(self):
    #     """Test accrued amount at the end of a coupon period (full coupon)."""
    #     eval_date = date(2025, 6, 30)  # End of first coupon period
    #     accrued = self.bond.accrued_amount(eval_date)
    #     # Full semiannual coupon = 15
    #     expected = 15.0
    #     self.assertAlmostEqual(accrued, expected, places=2, msg="Accrued should be 15 at period end")
    #
    # def test_accrued_amount_start_of_second_period(self):
    #     """Test accrued amount at the start of the second coupon period (should be 0)."""
    #     eval_date = date(2025, 7, 1)  # Start of second coupon period
    #     accrued = self.bond.accrued_amount(eval_date)
    #     self.assertAlmostEqual(accrued, 0.0, places=2, msg="Accrued should be 0 at second period start")
    #
    # def test_accrued_amount_mid_second_period(self):
    #     """Test accrued amount halfway through the second coupon period (90/180 days)."""
    #     eval_date = date(2025, 10, 1)  # 90 days from Jul 1
    #     accrued = self.bond.accrued_amount(eval_date)
    #     # 90/180 = 0.5 of period, so 15 * 0.5 = 7.5
    #     expected = 7.5
    #     self.assertAlmostEqual(accrued, expected, places=2, msg="Accrued should be 7.5 in second period mid")
    #
    # def test_accrued_amount_before_issue(self):
    #     """Test accrued amount before issue date (should be 0)."""
    #     eval_date = date(2019, 12, 31)  # Day before issue
    #     accrued = self.bond.accrued_amount(eval_date)
    #     self.assertAlmostEqual(accrued, 0.0, places=2, msg="Accrued should be 0 before issue")
    #
    # def test_accrued_amount_start_of_period(self):
    #     """Test accrued amount at the start of a coupon period (should be 0)."""
    #     eval_date = date(2025, 1, 1)  # Start of first coupon period
    #     accrued = self.bond.accrued_amount(eval_date)
    #     self.assertAlmostEqual(accrued, 0.0, places=2, msg="Accrued should be 0 at period start")
    #
    # def test_accrued_amount_maturity_date(self):
    #     """Test accrued amount on maturity date (end of final period)."""
    #     eval_date = date(2031, 1, 1)  # Maturity date, end of last period
    #     accrued = self.bond.accrued_amount(eval_date)
    #     # Last period: Jul 1, 2029 to Jan 1, 2030 = 180 days, full coupon = 15
    #     expected = 0.0
    #     self.assertAlmostEqual(accrued, expected, places=2, msg="Accrued should be 15 on maturity")
    #


# class TestBondAccruedAmount(TestCase):
#     def setUp(self):
#         self.bond_30E360 = FixedRateBond(
#             issue_date=ISSUE_DATE,
#             maturity_date=MATURITY_DATE,
#             coupon_rate=RATE,
#             days_between_coupons=180,
#             day_count=ql.Thirty360(ql.Thirty360.European),
#         )
#         self.bond_act365 = FixedRateBond(
#             issue_date=ISSUE_DATE,
#             maturity_date=MATURITY_DATE,
#             coupon_rate=RATE,
#             days_between_coupons=180,
#             day_count=ql.Actual365Fixed(),
#         )
#         self.bond_act360 = FixedRateBond(
#             issue_date=ISSUE_DATE,
#             maturity_date=MATURITY_DATE,
#             coupon_rate=RATE,
#             days_between_coupons=180,
#             day_count=ql.Actual360(),
#         )
#         self.bond_act365a = FixedRateBond(
#             issue_date=ISSUE_DATE,
#             maturity_date=MATURITY_DATE,
#             coupon_rate=RATE,
#             days_between_coupons=180,
#             day_count=Actual365A(),
#         )
#         self.bond_act365l = FixedRateBond(
#             issue_date=ISSUE_DATE,
#             maturity_date=MATURITY_DATE,
#             coupon_rate=RATE,
#             days_between_coupons=180,
#             day_count=Actual365L(),
#         )
#
#     def _test_accrued_amount(self, bond, eval_date, expected, places=2, msg=None):
#         accrued = bond.accrued_amount(eval_date)
#         self.assertAlmostEqual(accrued, expected, places=places, msg=msg)
#
#     def test_accrued_amount_one_third_period(self):
#         eval_date = date(2025, 3, 1)
#         self._test_accrued_amount(
#             self.bond_30E360, eval_date, 5.0, msg="30E/360: Accrued should be 5.0 at one-third"
#         )
#         self._test_accrued_amount(
#             self.bond_act365, eval_date, 4.93, msg="Act/365: Accrued should be 4.93 at one-third"
#         )
#         self._test_accrued_amount(
#             self.bond_act360, eval_date, 5.06, msg="Act/360: Accrued should be 5.06 at one-third"
#         )
#         self._test_accrued_amount(
#             self.bond_act365a, eval_date, 4.93, msg="Act/365A: Accrued should be 4.93 at one-third"
#         )
#         self._test_accrued_amount(
#             self.bond_act365l, eval_date, 4.93, msg="Act/365L: Accrued should be 4.93 at one-third"
#         )
#
#     def test_accrued_amount_mid_period(self):
#         eval_date = date(2025, 4, 1)
#         self._test_accrued_amount(
#             self.bond_30E360, eval_date, 7.5, msg="30E/360: Accrued should be 7.5 at mid-period"
#         )
#         self._test_accrued_amount(
#             self.bond_act365, eval_date, 7.397, msg="Act/365: Accrued should be 7.397 at mid-period"
#         )
#         self._test_accrued_amount(
#             self.bond_act360, eval_date, 7.59, msg="Act/360: Accrued should be 7.59 at mid-period"
#         )
#         self._test_accrued_amount(
#             self.bond_act365a, eval_date, 7.397, msg="Act/365A: Accrued should be 7.397 at mid-period"
#         )
#         self._test_accrued_amount(
#             self.bond_act365l, eval_date, 7.397, msg="Act/365L: Accrued should be 7.397 at mid-period"
#         )
#
#     def test_accrued_amount_specific_date(self):
#         eval_date = date(2025, 5, 1)
#         self._test_accrued_amount(self.bond_30E360, eval_date, 10.0, msg="30E/360: Accrued should be 10.0 on May 1")
#         self._test_accrued_amount(self.bond_act365, eval_date, 9.86, msg="Act/365: Accrued should be 9.86 on May 1")
#         self._test_accrued_amount(
#             self.bond_act360, eval_date, 10.12, msg="Act/360: Accrued should be 10.12 on May 1"
#         )
#         self._test_accrued_amount(
#             self.bond_act365a, eval_date, 9.86, msg="Act/365A: Accrued should be 9.86 on May 1"
#         )
#         self._test_accrued_amount(
#             self.bond_act365l, eval_date, 9.86, msg="Act/365L: Accrued should be 9.86 on May 1"
#         )
#
#     def test_accrued_amount_end_of_period(self):
#         eval_date = date(2025, 6, 30)
#         self._test_accrued_amount(
#             self.bond_30E360, eval_date, 15.0, msg="30E/360: Accrued should be 15.0 at period end"
#         )
#         self._test_accrued_amount(
#             self.bond_act365, eval_date, 14.79, msg="Act/365: Accrued should be 14.79 at period end"
#         )
#         self._test_accrued_amount(
#             self.bond_act360, eval_date, 15.18, msg="Act/360: Accrued should be 15.18 at period end"
#         )
#         self._test_accrued_amount(
#             self.bond_act365a, eval_date, 14.79, msg="Act/365A: Accrued should be 14.79 at period end"
#         )
#         self._test_accrued_amount(
#             self.bond_act365l, eval_date, 14.79, msg="Act/365L: Accrued should be 14.79 at period end"
#         )
#
#     def test_accrued_amount_start_of_second_period(self):
#         eval_date = date(2025, 7, 1)
#         self._test_accrued_amount(
#             self.bond_30E360, eval_date, 0.0, msg="30E/360: Accrued should be 0.0 at second period start"
#         )
#         self._test_accrued_amount(
#             self.bond_act365, eval_date, 0.0, msg="Act/365: Accrued should be 0.0 at second period start"
#         )
#         self._test_accrued_amount(
#             self.bond_act360, eval_date, 0.0, msg="Act/360: Accrued should be 0.0 at second period start"
#         )
#         self._test_accrued_amount(
#             self.bond_act365a, eval_date, 0.0, msg="Act/365A: Accrued should be 0.0 at second period start"
#         )
#         self._test_accrued_amount(
#             self.bond_act365l, eval_date, 0.0, msg="Act/365L: Accrued should be 0.0 at second period start"
#         )
#
#     def test_accrued_amount_before_issue(self):
#         eval_date = date(2019, 12, 31)
#         self._test_accrued_amount(self.bond_30E360, eval_date, 0.0, msg="30E/360: Accrued should be 0 before issue")
#         self._test_accrued_amount(self.bond_act365, eval_date, 0.0, msg="Act/365: Accrued should be 0 before issue")
#         self._test_accrued_amount(self.bond_act360, eval_date, 0.0, msg="Act/360: Accrued should be 0 before issue")
#         self._test_accrued_amount(
#             self.bond_act365a, eval_date, 0.0, msg="Act/365A: Accrued should be 0 before issue"
#         )
#         self._test_accrued_amount(
#             self.bond_act365l, eval_date, 0.0, msg="Act/365L: Accrued should be 0 before issue"
#         )
#
#     def test_accrued_amount_start_of_period(self):
#         eval_date = date(2025, 1, 1)
#         self._test_accrued_amount(
#             self.bond_30E360, eval_date, 0.0, msg="30E/360: Accrued should be 0 at period start"
#         )
#         self._test_accrued_amount(
#             self.bond_act365, eval_date, 0.0, msg="Act/365: Accrued should be 0 at period start"
#         )
#         self._test_accrued_amount(
#             self.bond_act360, eval_date, 0.0, msg="Act/360: Accrued should be 0 at period start"
#         )
#         self._test_accrued_amount(
#             self.bond_act365a, eval_date, 0.0, msg="Act/365A: Accrued should be 0 at period start"
#         )
#         self._test_accrued_amount(
#             self.bond_act365l, eval_date, 0.0, msg="Act/365L: Accrued should be 0 at period start"
#         )
#
#     def test_accrued_amount_maturity_date(self):
#         eval_date = MATURITY_DATE
#         self._test_accrued_amount(self.bond_30E360, eval_date, 0.0, msg="30E/360: Accrued should be 0 on maturity")
#         self._test_accrued_amount(self.bond_act365, eval_date, 0.0, msg="Act/365: Accrued should be 0 on maturity")
#         self._test_accrued_amount(self.bond_act360, eval_date, 0.0, msg="Act/360: Accrued should be 0 on maturity")
#         self._test_accrued_amount(
#             self.bond_act365a, eval_date, 0.0, msg="Act/365A: Accrued should be 0 on maturity"
#         )
#         self._test_accrued_amount(
#             self.bond_act365l, eval_date, 0.0, msg="Act/365L: Accrued should be 0 on maturity"
#         )
