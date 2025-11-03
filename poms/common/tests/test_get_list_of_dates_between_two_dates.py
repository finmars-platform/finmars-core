import datetime

from django.test import SimpleTestCase

from poms.common.utils import get_list_of_dates_between_two_dates


class TestGetListOfDatesBetweenTwoDates(SimpleTestCase):
    def test_same_day(self):
        today = datetime.date.today()
        self.assertEqual(len(get_list_of_dates_between_two_dates(today, today)), 1)

    def test_two_days(self):
        today = datetime.date.today()
        tomorrow = today + datetime.timedelta(days=1)
        self.assertEqual(len(get_list_of_dates_between_two_dates(today, tomorrow)), 2)
