from unittest import mock

from poms.common.common_base_test import BaseTestCase
from poms.schedules.models import Schedule

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

    def prepare_data(self, cron_expr: str = None) -> dict:
        return dict(
            cron_expr=cron_expr or "* * * * *",
            user_code=self.random_string(),
            short_name=self.random_string(),
            name=self.random_string(),
            configuration_code=self.random_string(),
        )

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
    def test__list(self, cron_expr):
        self.create_schedule(cron_expr=cron_expr)
        response = self.client.get(path=self.url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()

        self.assertEqual(response_json["count"], 1)
        self.assertEqual(len(response_json["results"]), 1)
        expected_keys = EXPECTED_RESPONSE["results"][0].keys()
        schedule_data = response_json["results"][0]
        actual_keys = schedule_data.keys()
        self.assertEqual(actual_keys, expected_keys)
        self.assertEqual(schedule_data["cron_expr"], cron_expr)

    @BaseTestCase.cases(
        ("2", "0 12 * * MON"),
        ("3", "0 0,12 * * *"),
        ("4", "0 */2 * * *"),
        ("5", "0 0 1 * *"),
    )
    def test__retrieve(self, cron_expr):
        test_schedule = self.create_schedule(cron_expr=cron_expr)
        response = self.client.get(path=f"{self.url}{test_schedule.id}/")
        self.assertEqual(response.status_code, 200)
        schedule_data = response.json()

        self.assertEqual(schedule_data["cron_expr"], test_schedule.cron_expr)

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
    def test_create(self, cron_expr):
        post_data = self.prepare_data(cron_expr)

        response = self.client.post(path=self.url, data=post_data, format="json")
        self.assertEqual(response.status_code, 201)
        schedule_data = response.json()

        self.assertEqual(schedule_data["cron_expr"], cron_expr)

        test_schedule = Schedule.objects.get(pk=schedule_data["id"])
        self.assertEqual(test_schedule.cron_expr, cron_expr)

    @BaseTestCase.cases(
        ("2", "1-60 * * * *"),
        ("3", "0 24 * * *"),
        ("4", "0 0 0 * *"),
        ("5", "0 0 * JANU *"),
    )
    def test_invalid_cron_expr(self, cron_expr):
        post_data = self.prepare_data(cron_expr)

        response = self.client.post(path=self.url, data=post_data, format="json")
        self.assertEqual(response.status_code, 400)

    @BaseTestCase.cases(
        ("2", "0 12 * * MON"),
        ("3", "0 0,12 * * *"),
        ("4", "0 */2 * * *"),
        ("5", "0 0 1 * *"),
    )
    def test__update_patch(self, cron_expr):
        test_schedule = self.create_schedule()  # create default schedule

        patch_data = {"cron_expr": cron_expr}
        response = self.client.patch(
            path=f"{self.url}{test_schedule.id}/", data=patch_data, format="json"
        )
        self.assertEqual(response.status_code, 200)
        schedule_data = response.json()

        self.assertEqual(schedule_data["cron_expr"], cron_expr)
        test_schedule.refresh_from_db()
        self.assertEqual(test_schedule.cron_expr, cron_expr)

    def test__delete(self):
        test_schedule = self.create_schedule()
        response = self.client.get(path=f"{self.url}{test_schedule.id}/")
        self.assertEqual(response.status_code, 200)

        response = self.client.delete(path=f"{self.url}{test_schedule.id}/")
        self.assertEqual(response.status_code, 204)

        result = Schedule.objects.filter(pk=test_schedule.id).first()
        self.assertIsNone(result)

    @mock.patch("poms.schedules.views.process.apply_async")
    def test__run_schedule(self, mock_process):
        test_schedule = self.create_schedule()
        run_schedule_url = f"{self.url}{test_schedule.id}/run-schedule/"

        response = self.client.post(path=run_schedule_url)
        self.assertEqual(response.status_code, 200, response.content)

        self.assertEqual(response.json(), {"status": "ok"})
        mock_process.assert_called_once()

    def test__run_schedule_invalid_id(self):
        run_schedule_url = f"{self.url}{self.random_int(10, 100)}/run-schedule/"

        response = self.client.post(path=run_schedule_url)
        self.assertEqual(response.status_code, 404, response.content)
