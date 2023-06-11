from poms.common.common_base_test import BaseTestCase
from poms.common.common_callback_test import CallbackSetTestMixin
from poms.common.database_client import BACKEND_CALLBACK_URLS

# from poms.counterparties.models import Counterparty


class CallbackCompanyViewSetTest(CallbackSetTestMixin, BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.task = self.create_task(
            name="Import Company From Finmars Database",
            func="import_company_finmars_database",
        )
        self.url = BACKEND_CALLBACK_URLS["company"]

    def test__company_created(self):
        post_data = {
            "request_id": self.task.id,
            "data": {
                "items": [
                    {
                        "code": "test_user_code",
                        "name": "test_name",
                        "shortName": "test_short_name",
                    },
                ],
            },
        }
        response = self.client.post(path=self.url, format="json", data=post_data)
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()
        print("company_created", response_json)
        self.assertEqual(response_json["status"], "ok", response_json)
        self.assertNotIn("message", response_json)

        #TODO Check Counterparty table
