from django.conf import settings

from poms.common.common_base_test import BaseTestCase
from poms.ui.models import MemberLayout


class MemberLayoutViewSetTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = f"/{settings.BASE_API_URL}/api/v1/ui/member-layout/"

    def test__list(self):
        response = self.client.get(path=self.url)
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        print(response_json)
