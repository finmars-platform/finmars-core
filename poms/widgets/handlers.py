import datetime
import math
import statistics

import numpy

from dateutil.relativedelta import relativedelta

from poms.common.utils import get_first_transaction, get_list_of_months_between_two_dates
from poms.currencies.models import Currency
from poms.instruments.models import PriceHistory
from poms.portfolios.models import Portfolio, PortfolioBundle
from poms.reports.voila_constructrices.performance import PerformanceReportBuilder
from poms.users.models import EcosystemDefault
from poms.reports.builders.performance_item import PerformanceReport
from poms.widgets.models import BalanceReportHistory, PLReportHistory

import logging

_l = logging.getLogger('poms.widgets')


class StatsHandler():

    def __init__(self, master_user, member, date=None, currency_id=None, portfolio_id=None, benchmark=None):

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
        self.benchmark = benchmark

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

    def get_annualized_return(self):

        first_transaction = get_first_transaction(portfolio_id=self.portfolio.id)
        now = datetime.datetime.now()

        _l.info('get_annualized_return.first_transaction.accounting_date %s' % first_transaction.accounting_date)

        years_from_first_transaction = relativedelta(now, first_transaction.accounting_date).years

        if years_from_first_transaction == 0:
            years_from_first_transaction = 1

        _l.info('get_annualized_return.years_from_first_transaction %s' % years_from_first_transaction)

        cumulative_return = self.get_cumulative_return()

        annualized_return = cumulative_return ** (1 / years_from_first_transaction)

        return annualized_return

    def get_portfolio_volatility(self):

        performance_monthly_returns_list = []

        for period in self.performance_report.periods:
            performance_monthly_returns_list.append(period['total_return'])

        portfolio_volatility = 0

        if len(performance_monthly_returns_list) > 2:
            portfolio_volatility = statistics.stdev(performance_monthly_returns_list)

        return portfolio_volatility

    def get_annualized_portfolio_volatility(self):

        portfolio_volatility = self.get_portfolio_volatility()

        annualized_portfolio_volatility = 0
        if portfolio_volatility:
            annualized_portfolio_volatility = portfolio_volatility * math.sqrt(12)

        return annualized_portfolio_volatility

    def get_sharpe_ratio(self):

        cumulative_return = self.get_cumulative_return()
        annualized_portfolio_volatility = self.get_annualized_portfolio_volatility()

        sharpe_ratio = 0

        if annualized_portfolio_volatility:
            sharpe_ratio = cumulative_return / annualized_portfolio_volatility

        return sharpe_ratio

    def generate_performance_report(self, date_from, date_to):

        instance = PerformanceReport(
            master_user=self.master_user,
            member=self.member,
            report_currency=self.currency,
            begin_date=date_from,
            end_date=date_to,
            calculation_type='time_weighted',
            segmentation_type='months',
            bundle=self.bundle,
            save_report=True
        )

        builder = PerformanceReportBuilder(instance=instance)
        instance = builder.build_report()

        return instance

    def get_date_or_yesterday(self, date):

        now = datetime.datetime.now().date()

        if date == now:
            d = now - datetime.timedelta(days=1) # set yesterday
        elif date > now - datetime.timedelta(days=1):
            d = now - datetime.timedelta(days=1) # set yesterday
        else:
            d = date

        return d



    def get_max_annualized_drawdown(self):

        first_transaction = get_first_transaction(portfolio_id=self.portfolio.id)

        grand_date_from = first_transaction.accounting_date

        grand_date_to = self.get_date_or_yesterday(self.date)

        months = get_list_of_months_between_two_dates(grand_date_from, grand_date_to)

        if grand_date_from.day != 1:
            months.insert(0, grand_date_from)

        grand_lowest = 0

        results = []

        for month in months:

            date_from = month
            date_to = date_from + datetime.timedelta(days=365)

            date_to = self.get_date_or_yesterday(date_to)

            performance_report = self.generate_performance_report(date_from, date_to)

            lowest = 0

            for period in performance_report.periods:

                if period['cumulative_return'] < lowest:
                    lowest = period['cumulative_return']

            results.append({
                'month': month,
                'lowest': lowest
            })

        for result in results:

            lowest = result['lowest']

            if grand_lowest < lowest:
                grand_lowest = lowest

        # got 120 monthes [...]
        # for each month
        # generate performance report from month start + 12 months
        # took cumulative_return from every period
        # look for  values and find -10 -50 -100 - took -100
        # and find minimum
        # 1 month result = 1 minimum
        # in end of algo we got 120 minimum
        # find mininum from all these 120 values

        # calculate performance reports since inception
        # get totals
        # from january to december
        # from february to january
        # from march to february
        # ...
        # from december to january
        # stop on date now

        max_annualized_drawdown = grand_lowest

        return max_annualized_drawdown

    def get_benchmark_returns(self, date_from, date_to):

        results = []

        months = get_list_of_months_between_two_dates(date_from, date_to)

        if date_from.day != 1:
            months.insert(0, date_from)

        print('months %s' % months)

        prices = PriceHistory.objects.filter(instrument__user_code=self.benchmark, date__in=months)

        for i in range(1, len(prices)):
            results.append((prices[i].principal_price - prices[i - 1].principal_price) / prices[i - 1].principal_price)

        return results

    def get_betta(self):

        portfolio_returns = []
        benchmarks_returns = []

        first_transaction = get_first_transaction(portfolio_id=self.portfolio.id)

        date_from = first_transaction.accounting_date

        date_to = self.get_date_or_yesterday(self.date)

        # from inception
        # end of month
        # (p1 - p0) / p0 = result %

        for period in self.performance_report.periods:
            portfolio_returns.append(period['total_return'])

        benchmarks_returns = self.get_benchmark_returns(date_from, date_to)

        # cov(portfoio, bench) / var(bench)
        # MINDBLOWING WITH SP500

        _l.info('self.performance_report.periods %s' % self.performance_report.periods)

        try:
            betta = numpy.cov(portfolio_returns, benchmarks_returns) / statistics.variance(benchmarks_returns)
        except Exception as e:
            _l.error('portfolio_returns len %s' % len(portfolio_returns))
            _l.error('benchmarks_returns len %s' % len(benchmarks_returns))
            _l.error('StatsHandler.get betta error %s' % e)
            betta = 0

        return betta

    # TODO get_alpha
    def get_alpha(self):

        alpha = 0

        return alpha

    # TODO get_correlation
    def get_correlation(self):

        correlation = 0

        return correlation
