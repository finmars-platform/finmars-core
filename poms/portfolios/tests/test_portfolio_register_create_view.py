from django.conf import settings

from poms.common.common_base_test import BIG, BaseTestCase
from poms.configuration.utils import get_default_configuration_code
from poms.instruments.models import PricingPolicy
from poms.portfolios.models import PortfolioRegister

PORTFOLIO_API = f"/{settings.BASE_API_URL}/api/v1/portfolios/portfolio-register"


class PortfolioRegisterCreateTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = f"{PORTFOLIO_API}/"
        self.portfolio = self.db_data.portfolios[BIG]
        self.instrument = self.db_data.instruments["Apple"]
        self.pricing_policy = PricingPolicy.objects.create(
            master_user=self.master_user,
            owner=self.finmars_bot,
            user_code=self.random_string(),
            configuration_code=get_default_configuration_code(),
            default_instrument_pricing_scheme=None,
            default_currency_pricing_scheme=None,
        )
        self.pr_data = {
            "portfolio": self.portfolio.id,
            "linked_instrument": self.instrument.id,
            "valuation_currency": self.db_data.usd.id,
            "valuation_pricing_policy": self.pricing_policy.id,
            "name": "name",
            "short_name": "short_name",
            "user_code": "user_code",
            "public_name": "public_name",
        }

    def test_no_create_with_invalid_new_instrument(self):
        new_instrument = self.db_data.instruments["Tesla B."]
        new_pr_data = {
            **self.pr_data,
            "new_linked_instrument": {
                "name": new_instrument.name,
                "short_name": new_instrument.short_name,
                "user_code": new_instrument.user_code,
                "public_name": new_instrument.public_name,
                "instrument_type": self.random_int(),
            },
        }

        response = self.client.post(self.url, data=new_pr_data, format="json")
        self.assertEqual(response.status_code, 200, response.content)
