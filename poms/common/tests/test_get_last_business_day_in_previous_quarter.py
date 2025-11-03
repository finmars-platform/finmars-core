import datetime

from django.test import SimpleTestCase

from poms.common.utils import get_last_business_day_in_previous_quarter


class TestGetLastBusinessDayInPreviousQuarter(SimpleTestCase):
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
