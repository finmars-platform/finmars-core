import datetime

from django.test import SimpleTestCase

from poms.common.utils import get_last_business_day_of_previous_month


class TestGetLastBusinessDayOfPreviousMonth(SimpleTestCase):
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
