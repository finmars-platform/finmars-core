from django.conf import settings
from poms.schedules.models import Schedule
from poms.common.common_base_test import BaseTestCase


class ScheduleViewSetTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()

        self.realm_code = 'realm00000'
        self.space_code = 'space00000'
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/schedules/schedule/"
        self.schedule = self.create_schedule()


    def test__run_schedule(self):
        run_schedule_url = f"{self.url}{self.schedule.pk}/run-schedule/"        
        response = self.client.post(path=run_schedule_url, format="json", data={})
        self.assertEqual(response.status_code, 200, response.content)