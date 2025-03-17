from celery.schedules import schedule
from django.conf import settings
from poms.schedules.models import Schedule
from poms.common.common_base_test import BaseTestCase

EXPECTED_RESPONSE = {
    "count": 1,
    "next": None,
    "previous": None,
    "results": [
        {
            "id": 1,
            "name": "ZRLGJNTAGQ",
            "user_code": "UIFPGILCMT:prrnjirvwb",
            "notes": None,
            "is_enabled": True,
            "cron_expr": "* * * * *",
            "procedures": [],
            "last_run_at": "2025-03-17T09:21:27+0000",
            "next_run_at": "2025-03-17T09:22:00+0000",
            "error_handler": "break",
            "data": None,
            "configuration_code": "UIFPGILCMT",
            "meta": {
                "content_type": "schedules.schedule",
                "app_label": "schedules",
                "model_name": "schedule",
                "space_code": "space00000",
                "realm_code": "realm00000",
            },
        }
    ],
}


class ScheduleViewSetTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/schedules/schedule/"

    def test__api_url(self):
        response = self.client.get(path=self.url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()

        self.assertIn("count", response_json)
        self.assertIn("next", response_json)
        self.assertIn("previous", response_json)
        self.assertIn("results", response_json)
        self.assertEqual(response_json["count"], 0)
        self.assertEqual(len(response_json["results"]), 0)

    @BaseTestCase.cases(
        ("1", "0 0 * * *"),
        ("2", "0 12 * * MON"),
        ("3", "0 0,12 * * *"),
        ("4", "0 */2 * * *"),
        ("5", "0 0 1 * *"),
        ("6", "0 0 * * 0"),
        ("7", "0 0 1,15 * *"),
        ("8", "*/15 * * * *"),
        ("9", "0 1-5 * * *"),
        ("0", "0 0 * * MON-FRI"),
    )
    def test__list(self, cron_str):
        self.schedule = self.create_schedule(cron_expr=cron_str)
        response = self.client.get(path=self.url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()

        self.assertEqual(response_json["count"], 1)
        self.assertEqual(len(response_json["results"]), 1)
        expected_keys = EXPECTED_RESPONSE["results"][0].keys()
        schedule_data = response_json["results"][0]
        actual_keys = schedule_data.keys()
        self.assertEqual(actual_keys, expected_keys)
        self.assertEqual(schedule_data["cron_expr"], cron_str)



    # def test__run_schedule(self):
    #     run_schedule_url = f"{self.url}{self.schedule.pk}run-schedule/"
    #     response = self.client.post(path=run_schedule_url, format="json", data={})
    #     self.assertEqual(response.status_code, 200, response.content)
