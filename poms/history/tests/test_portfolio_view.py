from unittest import mock
from django.conf import settings
from django.contrib.contenttypes.models import ContentType

from poms.common.common_base_test import BaseTestCase
from poms.history.tests.factories import HistoricalRecordFactory


class HistoryRecordViewSetTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = (
            f"/{self.realm_code}/{self.space_code}/api/v1/history/historical-record"
        )

    def _create_history_record(self):
        content_type = ContentType.objects.using(settings.DB_DEFAULT).first()
        return HistoricalRecordFactory(content_type=content_type)

    def test_retrieve(self):
        history_record = self._create_history_record()

        response = self.client.get(f"{self.url}/{history_record.id}/")
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        self.assertEqual(response_json["id"], history_record.id)
        self.assertIn("action", response_json)
        self.assertIn("content_type", response_json)
        self.assertIn("context_url", response_json)
        self.assertIn("created_at", response_json)
        self.assertIn("diff", response_json)
        self.assertIn("member", response_json)
        self.assertIn("member_object", response_json)
        self.assertIn("notes", response_json)
        self.assertIn("user_code", response_json)

    def test_export(self):
        with mock.patch("poms_app.celery_app.send_task") as send_task:
            response = self.client.post(
                f"{self.url}/export/", data={"date_to": "2020-01-01"}
            )

            self.assertEqual(response.status_code, 200, response.content)

            response_json = response.json()
            task_id = response_json["task_id"]

            send_task.assert_called_once_with(
                "history.export_journal_to_storage",
                kwargs={
                    "task_id": task_id,
                    "context": {
                        "realm_code": self.realm_code,
                        "space_code": self.space_code,
                    },
                },
                queue="backend-background-queue",
            )
