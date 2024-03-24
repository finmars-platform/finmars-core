from django.conf import settings
from poms.currencies.constants import DASH
from poms.common.common_base_test import BaseTestCase
from poms.portfolios.models import Portfolio

class PortfolioDeleteViewSetTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.realm_code = 'realm00000'
        self.space_code = 'space00000'
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/portfolios/portfolio"

    def test_detail_delete_main_portfolios(self):
        for portfolio in Portfolio.objects.filter(user_code__in=DASH):
            response = self.client.delete(path=f"{self.url}/{portfolio.id}/")
            self.assertEqual(response.status_code, 409)
            
    def test_detail_delete_custom_portfolios(self):
        portfolio = Portfolio.objects.last()
        portfolio = Portfolio.objects.create(
            user_code="test",
            name="test",
            owner=portfolio.owner,
            master_user=portfolio.master_user,
        )

        self.assertNotIn(portfolio.user_code, DASH)

        response = self.client.delete(path=f"{self.url}/{portfolio.id}/")
        self.assertEqual(response.status_code, 204)