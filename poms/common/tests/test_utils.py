from django.test import SimpleTestCase
import datetime

from poms.common.utils import (
    get_last_business_day_of_previous_year,
    get_last_business_day_of_previous_month,
    get_last_business_day_in_previous_quarter,
)


class TestBusinessDayFunctions(SimpleTestCase):
    def test_last_business_day_of_previous_year(self):
        test_cases = [
            (datetime.date(2022, 4, 15), datetime.date(2021, 12, 31)),
            (datetime.date(2024, 7, 30), datetime.date(2023, 12, 29)),
            (datetime.date(2023, 12, 31), datetime.date(2022, 12, 30)),
        ]
        for date, expected_day in test_cases:
            with self.subTest(date=date):
                last_business_day = get_last_business_day_of_previous_year(date)
                self.assertEqual(last_business_day, expected_day)

    def test_last_business_day_of_previous_month(self):
        test_cases = [
            (datetime.date(2023, 6, 15), datetime.date(2023, 5, 31)),
            (datetime.date(2023, 10, 1), datetime.date(2023, 9, 29)),
            (datetime.date(2024, 1, 2), datetime.date(2023, 12, 29)),
        ]
        for date, expected_day in test_cases:
            with self.subTest(date=date):
                last_business_day = get_last_business_day_of_previous_month(date)
                self.assertEqual(last_business_day, expected_day)

    def test_last_business_day_in_previous_quarter(self):
        test_cases = [
            (datetime.date(2023, 4, 15), datetime.date(2023, 3, 31)),
            (datetime.date(2023, 11, 1), datetime.date(2023, 9, 29)),
            (datetime.date(2024, 7, 2), datetime.date(2024, 6, 28)),
        ]
        for date, expected_day in test_cases:
            with self.subTest(date=date):
                last_business_day = get_last_business_day_in_previous_quarter(date)
                self.assertEqual(last_business_day, expected_day)
