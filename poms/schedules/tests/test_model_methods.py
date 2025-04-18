from django.utils import timezone
from poms.common.common_base_test import BaseTestCase


class ScheduleMethodsTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.schedule = self.create_schedule()

    def test__schedule_save_yes(self):
        current_time = timezone.now()

        next_run_at = self.schedule.schedule(save=True)

        self.assertTrue(next_run_at >= current_time)

    def test__schedule_save_no(self):
        current_time = timezone.now()

        next_run_at = self.schedule.schedule()

        self.assertTrue(next_run_at >= current_time)
