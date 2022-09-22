import datetime
import math
import statistics

from poms.currencies.models import Currency
from poms.portfolios.models import Portfolio, PortfolioBundle
from poms.reports.voila_constructrices.performance import PerformanceReportBuilder
from poms.users.models import EcosystemDefault
from poms.reports.builders.performance_item import PerformanceReport
from poms.widgets.models import BalanceReportHistory, PLReportHistory


class StatsHandler():

    def __init__(self, master_user, member, date=None, currency_id=None, portfolio_id=None):

        self.master_user = master_user
        self.member = member

        if not date:

            yesterday = datetime.datetime.now() - datetime.timedelta(days=1)

            self.date_str = yesterday.strftime("%Y-%m-%d")

        else:
            self.date_str = date

        self.date = datetime.datetime.strptime(self.date_str, "%Y-%m-%d").date()

        self.ecosystem_default = EcosystemDefault.objects.get(master_user=master_user)

        if not currency_id:
            self.currency = self.ecosystem_default.currency
        else:
            self.currency = Currency.objects.get(id=currency_id)

        self.portfolio = Portfolio.objects.get(id=portfolio_id)

        self.bundle = PortfolioBundle.objects.get(user_code=self.portfolio.user_code)  # may cause un error

        try:
            self.balance_history = BalanceReportHistory.objects.get(date=date, portfolio=self.portfolio)
        except Exception as e:
            raise Exception("Balance History is not collected")

        try:
            self.pl_history = PLReportHistory.objects.get(date=date, portfolio=self.portfolio)
        except Exception as e:
            raise Exception("PL History is not collected")

        self.performance_report = self.get_performance_report()

    def get_performance_report(self):

        instance = PerformanceReport(
            master_user=self.master_user,
            member=self.member,
            report_currency=self.currency,
            end_date=self.date,
            calculation_type='time_weighted',
            segmentation_type='months',
            bundle=self.bundle,
            save_report=True
        )

        builder = PerformanceReportBuilder(instance=instance)
        instance = builder.build_report()

        return instance

    def get_balance_nav(self):
        return self.balance_history.nav

    def get_pl_total(self):
        return self.pl_history.total

    def get_cumulative_return(self):
        return self.performance_report.grand_return

    # TODO do get_annualized_return
    def get_annualized_return(self):

        years_from_first_transaction = 1  # count years from first transaction date

        cumulative_return = self.get_cumulative_return()

        annualized_return = cumulative_return ** (1 / years_from_first_transaction)

        return annualized_return

    # TODO do get_portfolio_volatility
    def get_portfolio_volatility(self):

        performance_monthly_returns_list = []

        portfolio_volatility = 0

        if len(performance_monthly_returns_list) > 2:
            portfolio_volatility = statistics.stdev(performance_monthly_returns_list)

        return portfolio_volatility

    # TODO get_annualized_portfolio_volatility
    def get_annualized_portfolio_volatility(self):

        portfolio_volatility = self.get_portfolio_volatility()

        annualized_portfolio_volatility = 0
        if portfolio_volatility:
            annualized_portfolio_volatility = portfolio_volatility * math.sqrt(12)

        return annualized_portfolio_volatility

    # TODO get_sharpe_ratio
    def get_sharpe_ratio(self):

        cumulative_return = self.get_cumulative_return()
        annualized_portfolio_volatility = self.get_annualized_portfolio_volatility()

        sharpe_ratio = 0

        if annualized_portfolio_volatility:
            sharpe_ratio = cumulative_return / annualized_portfolio_volatility

        return sharpe_ratio

    # TODO get_max_annualized_drawdown
    def get_max_annualized_drawdown(self):

        # calculate performance reports since inception
        # get totals
        # from january to december
        # from february to january
        # from march to february
        # ...
        # from december to january
        # stop on date now

        max_annualized_drawdown = 0

        return max_annualized_drawdown

    # TODO get_betta
    def get_betta(self):

        betta = 0  # MINDBLOWING WITH SP500

        return betta

    # TODO get_alpha
    def get_alpha(self):

        alpha = 0

        return alpha

    # TODO get_correlation
    def get_correlation(self):

        correlation = 0

        return correlation
