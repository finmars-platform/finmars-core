import datetime

from django.test import SimpleTestCase

from poms.common.utils import get_last_business_day_of_previous_year


class TestGetLastBusinessDayOfPreviousYear(SimpleTestCase):
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
