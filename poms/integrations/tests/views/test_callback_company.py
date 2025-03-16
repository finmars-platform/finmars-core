from poms.common.common_base_test import BaseTestCase
from poms.integrations.tests.common_callback_test import CallbackSetTestMixin
from poms.integrations.database_client import get_backend_callback_urls

from poms.counterparties.models import Counterparty


class CallbackCompanyViewSetTest(CallbackSetTestMixin, BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.group = self.db_data.create_counterparty_group()
        self.task = self.create_task(
            name="Import Company From Finmars Database",
            func="import_company_finmars_database",
        )

        BACKEND_CALLBACK_URLS = get_backend_callback_urls()

        self.url = BACKEND_CALLBACK_URLS["company"]

    def test__company_created(self):
        name = self.random_string()
        short_name = self.random_string()
        post_data = {
            "request_id": self.task.id,
            "task_id": None,
            "data": {
                "id": self.random_int(),
                "name": name,
                "short_name": short_name,
                "user_code": name,
                "public_name": name,
                "notes": name,
            },
        }
        response = self.client.post(path=self.url, format="json", data=post_data)
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()
        self.assertEqual(response_json["status"], "ok", response_json)
        self.assertNotIn("message", response_json)

        self.assertIsNotNone(company := Counterparty.objects.filter(name=name).first())

        self.assertEqual(company.name, name)
        self.assertEqual(company.short_name, short_name)
