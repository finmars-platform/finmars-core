from poms.common.common_base_test import BaseTestCase
from poms.common.common_callback_test import CallbackSetTestMixin
from poms.common.database_client import BACKEND_CALLBACK_URLS

# from poms.counterparties.models import Currency


class CallbackCurrencyViewSetTest(CallbackSetTestMixin, BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.task = self.create_task(
            name="Import Currency From Finmars Database",
            func="import_currency_finmars_database",
        )
        self.url = BACKEND_CALLBACK_URLS["currency"]

    def test__company_created(self):
        post_data = {
            "request_id": self.task.id,
            "data": {
                "user_code": "test_user_code",
                "code": "test_code",
                "name": "test_name",
            },
        }
        response = self.client.post(path=self.url, format="json", data=post_data)
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()
        print("currency_created", response_json)

        # self.assertEqual(response_json["status"], "ok")
        # self.assertNotIn("message", response_json)
