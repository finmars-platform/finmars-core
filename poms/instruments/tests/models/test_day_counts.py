from QuantLib import Date

from poms.common.common_base_test import BaseTestCase
from poms.instruments.finmars_quantlib import Actual365A, Actual365L


class Actual365ATest(BaseTestCase):
    def test_name(self):
        self.assertEqual(Actual365A().name(), "Actual/365A")

    @BaseTestCase.cases(
        ("366", Date(1, 1, 2000), Date(1, 1, 2001), 366),
        ("29", Date(1, 2, 2000), Date(1, 3, 2000), 29),
        ("365", Date(1, 1, 2025), Date(1, 1, 2026), 365),
        ("28", Date(1, 2, 2025), Date(1, 3, 2025), 28),
    )
    def test_day_count(self, d1, d2, days):
        self.assertEqual(Actual365A().dayCount(d1, d2), days)

    @BaseTestCase.cases(
        ("1", Date(1, 1, 2000), 365),
        ("2", Date(11, 11, 2001), 365),
        ("3", Date(1, 3, 2000), 366),
        ("4", Date(11, 11, 2024), 366),
        ("5", Date(3, 3, 2024), 366),
        ("6", Date(7, 7, 2025), 365),
    )
    def test_days_in_year(self, d, days):
        self.assertEqual(Actual365A().days_in_year(d), days)


class Actual365LTest(BaseTestCase):
    def test_name(self):
        self.assertEqual(Actual365L().name(), "Actual/365L")

    @BaseTestCase.cases(
        ("366", Date(1, 1, 2000), Date(1, 1, 2001), 366),
        ("29", Date(1, 2, 2000), Date(1, 3, 2000), 29),
        ("365", Date(1, 1, 2025), Date(1, 1, 2026), 365),
        ("28", Date(1, 2, 2025), Date(1, 3, 2025), 28),
    )
    def test_day_count(self, d1, d2, days):
        self.assertEqual(Actual365L().dayCount(d1, d2), days)

    @BaseTestCase.cases(
        ("1", Date(1, 1, 2000), 366),
        ("2", Date(11, 11, 2001), 365),
        ("3", Date(1, 3, 2000), 366),
        ("4", Date(11, 11, 2024), 366),
        ("5", Date(3, 3, 2020), 366),
        ("6", Date(7, 7, 2025), 365),
    )
    def test_days_in_year(self, d, days):
        self.assertEqual(Actual365L().days_in_year(d), days)
