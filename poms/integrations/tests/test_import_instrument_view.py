from django.conf import settings

from poms.common.common_base_test import BaseTestCase


class ImportInstrumentDatabaseViewSetTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = (
            f"/{settings.BASE_API_URL}/api/v1"
            f"/import/finmars-database/instrument/"
        )

    def test_400(self):
        response = self.client.post(path=self.url, format="json", data={})
        self.assertEqual(response.status_code, 400, response.content)
