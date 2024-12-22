from django.conf import settings

from poms.common.common_base_test import BIG, BaseTestCase, SMALL
from poms.portfolios.models import PortfolioReconcileGroup
from poms.configuration.utils import get_default_configuration_code

class PortfolioReconcileGroupViewTest(BaseTestCase):
    databases = "__all__"
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/portfolios/portfolio-reconcile-group/"
        self.portfolio_1 = self.db_data.portfolios[BIG]
        self.portfolio_2 = self.db_data.portfolios[SMALL]

    def test_check_url(self):
        response = self.client.get(path=self.url)
        self.assertEqual(response.status_code, 200, response.content)

    def test_simple_create(self):
        user_code = get_default_configuration_code()
        name = self.random_string()
        precision = self.random_integer(1, 100)
        create_data = {
            "name": name,
            "user_code": user_code,
            "portfolios": [self.portfolio_1.id, self.portfolio_2.id],
            "precision": precision,
        }
        response = self.client.post(self.url, data=create_data, format="json")
        self.assertEqual(response.status_code, 201, response.content)

        group_data = response.json()
        self.assertEqual(group_data["name"], name)
        self.assertEqual(group_data["precision"], precision)
        self.assertEqual(group_data["User_code"], user_code)

    def test_update_create(self):
        user_code = get_default_configuration_code()
        name = self.random_string()
        precision = self.random_integer(1, 100)
        create_data = {
            "name": name,
            "user_code": user_code,
            "portfolios": [self.portfolio_1.id, self.portfolio_2.id],
            "precision": precision,
        }
        response = self.client.post(self.url, data=create_data, format="json")
        self.assertEqual(response.status_code, 201, response.content)

        print(response.json())
