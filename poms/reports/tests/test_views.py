from django.conf import settings

from poms.common.common_base_test import BaseTestCase
from poms.reports.tests.test_data import ITEMS_PAYLOAD, GROUPS_PAYLOAD

DATE_FORMAT = settings.API_DATE_FORMAT
API_URL = f"/{settings.BASE_API_URL}/api/v1/reports/backend-transaction-report"


class BackendBalanceReportItemsViewSetTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = f"{API_URL}/items/"

    def test__check_api_url(self):
        response = self.client.post(path=self.url, format="json", data={})
        self.assertEqual(response.status_code, 400, response.content)

    def test__check_with_payload(self):
        response = self.client.post(path=self.url, format="json", data=ITEMS_PAYLOAD)
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()
        print(response_json)


class BackendBalanceReportGroupsTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = f"{API_URL}/groups/"

    def test__check_api_url(self):
        response = self.client.post(path=self.url, format="json", data={})
        self.assertEqual(response.status_code, 400, response.content)

    def test__check_with_payload(self):
        response = self.client.post(path=self.url, format="json", data=GROUPS_PAYLOAD)
        self.assertEqual(response.status_code, 400, response.content)

        response_json = response.json()
        print(response_json)
