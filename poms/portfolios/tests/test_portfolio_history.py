from poms.common.common_base_test import BaseTestCase
from poms.portfolios.models import Portfolio

from django.conf import settings

class PortfolioViewSetTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.realm_code = 'realm00000'
        self.space_code = 'space00000'
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/portfolios/portfolio-history/calculate/"
        self.portfolio = Portfolio.objects.last()
        self.portfolio_id = self.portfolio.id
        self.user_code = self.random_string()
        self.portfolio.user_code = self.user_code
        self.portfolio.save()
        self.db_data.create_portfolio_register(
            self.portfolio,
            self.db_data.default_instrument,
            self.user_code,
        )
        self.req_data = {
            "portfolio": str(self.portfolio_id),
            "date": self.today().strftime(settings.API_DATE_FORMAT),
            "calculation_period_date_from": self.yesterday().strftime(settings.API_DATE_FORMAT),
        }

    @BaseTestCase.cases(
        ("multipart", "multipart"),
        ("json", "json"),
    )
    def test_post(self, format):
        response = self.client.post(self.url, data=self.req_data, format=format)
        self.assertEqual(response.status_code, 200, response.content)
