from django.conf import settings

from poms.common.common_base_test import BaseTestCase
from poms.reports.tests.common_test_data import REQUEST_PAYLOAD

DATE_FORMAT = settings.API_DATE_FORMAT


class ReportsViewItemsSetTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.realm_code = "realm00000"
        self.space_code = "space00000"
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/reports/backend-transaction-report/items/"

    def test__check_api_url(self):
        response = self.client.post(path=self.url, format="json", data={})
        self.assertEqual(response.status_code, 400, response.content)

    def test__check_with_payload(self):
        response = self.client.post(path=self.url, format="json", data=REQUEST_PAYLOAD)
        # TODO prepare payload
        self.assertEqual(response.status_code, 400, response.content)
