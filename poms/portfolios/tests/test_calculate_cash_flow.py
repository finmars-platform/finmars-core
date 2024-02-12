from poms.common.common_base_test import BIG, BaseTestCase
from poms.configuration.utils import get_default_configuration_code
from poms.instruments.models import PricingPolicy
from poms.portfolios.models import PortfolioRegister
from poms.portfolios.tasks import calculate_cash_flow


class CalculateCashFlowTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.portfolio = self.db_data.portfolios[BIG]
        self.instrument = self.db_data.instruments["Apple"]
        self.pricing_policy = PricingPolicy.objects.create(
            master_user=self.master_user,
            owner=self.member,
            user_code=self.random_string(),
            configuration_code=get_default_configuration_code(),
            default_instrument_pricing_scheme=None,
            default_currency_pricing_scheme=None,
        )
        self.portfolio_register = PortfolioRegister.objects.create(
            master_user=self.master_user,
            owner=self.member,
            portfolio=self.portfolio,
            linked_instrument=self.instrument,
            valuation_pricing_policy=self.pricing_policy,
            valuation_currency=self.db_data.usd,
        )

    def test__fx_ok(self):

        calculate_cash_flow(
            master_user=self.master_user,
            date=self.today(),
            pricing_policy=self.pricing_policy,
            portfolio_register=self.portfolio_register,
        )
