from datetime import date

from poms.common.common_base_test import BIG, BaseTestCase
from poms.configuration.utils import get_default_configuration_code
from poms.instruments.models import PricingPolicy
from poms.portfolios.models import PortfolioRegister
from poms.portfolios.tasks import calculate_simple_balance_report
from poms.reports.common import Report


class CalculateSimpleBalanceReportTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.portfolio = self.db_data.portfolios[BIG]
        self.instrument = self.db_data.instruments["Apple"]
        self.pricing_policy = PricingPolicy.objects.create(
            master_user=self.master_user,
            user_code=self.random_string(),
            configuration_code=get_default_configuration_code(),
            default_instrument_pricing_scheme=None,
            default_currency_pricing_scheme=None,
        )

    def test__report_portfolio_register_with_instrument(self):
        pr_data = {
            "master_user": self.master_user,
            "portfolio": self.portfolio,
            "linked_instrument": self.instrument,
            "valuation_pricing_policy": self.pricing_policy,
            "valuation_currency": self.db_data.usd,
        }
        portfolio_register = PortfolioRegister.objects.create(**pr_data)

        report = calculate_simple_balance_report(
            report_date=date.today(),
            portfolio_register=portfolio_register,
            member=self.member,
        )

        self.assertIsInstance(report, Report)

    def test__report_portfolio_register_no_instrument(self):
        pr_data = {
            "master_user": self.master_user,
            "portfolio": self.portfolio,
            "linked_instrument": None,
            "valuation_pricing_policy": self.pricing_policy,
            "valuation_currency": self.db_data.usd,
        }
        portfolio_register = PortfolioRegister.objects.create(**pr_data)

        with self.assertRaises(RuntimeError):
            _ = calculate_simple_balance_report(
                report_date=date.today(),
                portfolio_register=portfolio_register,
                member=self.member,
            )
