from unittest import mock

from django.conf import settings

from poms.celery_tasks.models import CeleryTask
from poms.common.common_base_test import BaseTestCase
from poms.common.database_client import BACKEND_CALLBACK_URLS
from poms.users.fields import Member, MasterUser

# from poms.counterparties.models import Counterparty


class CallbackCompanyViewSetTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = BACKEND_CALLBACK_URLS["company"]
        master_user = MasterUser.objects.get(base_api_url=settings.BASE_API_URL)
        member = Member.objects.get(master_user=master_user)
        self.remote_task_id = self.random_int()
        self.task = CeleryTask.objects.create(
            master_user=master_user,
            member=member,
            verbose_name="Import Company From Finmars Database",
            function_name="import_company_finmars_database",
            type="import",
            result_object={"task_id": self.remote_task_id},
            status=CeleryTask.STATUS_PENDING,
        )

    def test__no_request_id(self):
        post_data = {"data": {"items": []}}
        response = self.client.post(path=self.url, format="json", data=post_data)
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()
        self.assertEqual(response_json["status"], "error")
        self.assertIn("message", response_json)

    def test__invalid_request_id(self):
        post_data = {"request_id": self.random_int(), "data": {"items": []}}
        response = self.client.post(path=self.url, format="json", data=post_data)
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()
        self.assertEqual(response_json["status"], "error")
        self.assertIn("message", response_json)

    def test__no_data(self):
        post_data = {
            "request_id": self.random_int(),
        }
        response = self.client.post(path=self.url, format="json", data=post_data)
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()
        self.assertEqual(response_json["status"], "error")
        self.assertIn("message", response_json)

    def test__no_items(self):
        post_data = {
            "request_id": self.random_int(),
            "data": {},
        }
        response = self.client.post(path=self.url, format="json", data=post_data)
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()
        self.assertEqual(response_json["status"], "error")
        self.assertIn("message", response_json)

    def test__empty_items(self):
        post_data = {"request_id": self.task.id, "data": {"items": []}}
        response = self.client.post(path=self.url, format="json", data=post_data)
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()
        self.assertEqual(response_json["status"], "ok")
        self.assertNotIn("message", response_json)
