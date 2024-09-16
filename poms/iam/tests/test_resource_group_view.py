from poms.common.common_base_test import BaseTestCase
from poms.iam.models import ResourceGroup


class ResourceGroupViewTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/iam/resource-group/"

    def test__check_url(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200, response.content)
