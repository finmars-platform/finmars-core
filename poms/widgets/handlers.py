import datetime
import logging
import math
import statistics
import traceback

import numpy
from dateutil.relativedelta import relativedelta
from django.db.models import Q

from poms.common.utils import get_first_transaction, get_last_bdays_of_months_between_two_dates, get_last_business_day, \
    str_to_date
from poms.currencies.models import Currency
from poms.instruments.models import PriceHistory
from poms.portfolios.models import Portfolio, PortfolioBundle
from poms.reports.common import PerformanceReport
from poms.reports.performance_report import PerformanceReportBuilder
from poms.users.models import EcosystemDefault
from poms.widgets.models import BalanceReportHistory, PLReportHistory

_l = logging.getLogger('poms.widgets')


class StatsHandler():

    def __init__(self, master_user, member, date=None, currency_id=None, portfolio_id=None, benchmark=None):

        self.master_user = master_user
        self.member = member

        _l.info('StatsHandler requested date %s ' % date)

        self.date = self.get_date_or_yesterday(datetime.datetime.strptime(date, "%Y-%m-%d").date())

        _l.info('StatsHandler date or yesterday %s ' % self.date)

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
            self.balance_history = None
            _l.error("Balance history is not calcualated for %s of %s" % (date, self.portfolio))

        try:
            self.pl_history = PLReportHistory.objects.get(date=date, portfolio=self.portfolio)
        except Exception as e:
            self.pl_history = None
            _l.error("PL history is not calcualated for %s of %s" % (date, self.portfolio))

        self.performance_report = self.get_performance_report()

    def get_performance_report(self):

        first_transaction = get_first_transaction(self.portfolio)

        instance = PerformanceReport(
            master_user=self.master_user,
            member=self.member,
            report_currency=self.currency,
            begin_date=first_transaction.accounting_date,
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
        if self.balance_history:
            return self.balance_history.nav
        return 0

    def get_pl_total(self):
        if self.pl_history:
            return self.pl_history.total
        return 0

    def get_cumulative_return(self):
        return self.performance_report.grand_return

    def get_annualized_return(self):

        first_transaction = get_first_transaction(self.portfolio)
        now = datetime.date.today()

        _l.info('get_annualized_return.first_transaction.accounting_date %s' % first_transaction.accounting_date)

        _delta = now - first_transaction.accounting_date
        days_from_first_transaction = _delta.days

        if days_from_first_transaction == 0:
            return 0

        _l.info('get_annualized_return.years_from_first_transaction %s' % days_from_first_transaction)

        cumulative_return = self.get_cumulative_return()

        # sign = 1
        #
        # if cumulative_return < 0:
        #     sign = - 1
        #
        # annualized_return = (abs(cumulative_return) ** (1 / (days_from_first_transaction / 365))) * sign


        annualized_return = (1 + cumulative_return) ** (365 / days_from_first_transaction) -1

        return annualized_return

    def get_portfolio_volatility(self):

        performance_monthly_returns_list = []


        # YTD, date

        # 2022-12-30, 2023-11-16
        # get_months_between_two_dates(ytd_date, date)

        # performance [2022-12-30, 2023-01-31] - grand_return
        # performance [2023-01-31, 2023-02-28] - grand_return
        # performance [2023-02-28, 2023-03-31] - grand_return
        # ...



        # for month in [date_from, date_to]:
        #     performance_report = self.generate_performance_report(inception, month.date_to)
        #     performance_monthly_returns_list.append(performance_report.grand_return)


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
            # annualized_portfolio_volatility = portfolio_volatility * math.sqrt(11) # TODO possible 11? statistical n-1

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
            d = now - datetime.timedelta(days=1)  # set yesterday
        elif date > now - datetime.timedelta(days=1):
            d = now - datetime.timedelta(days=1)  # set yesterday
        else:
            d = date

        return d

    def get_max_annualized_drawdown(self):

        first_transaction = get_first_transaction(self.portfolio)

        grand_date_from = first_transaction.accounting_date

        grand_date_to = self.get_date_or_yesterday(self.date)

        end_of_months = get_last_bdays_of_months_between_two_dates(grand_date_from, grand_date_to)

        grand_lowest = 0

        results = []

        for month in end_of_months:

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

        _l.info('get_max_annualized_drawdown.results %s' % results)

        grand_lowest_month = None

        for result in results:

            lowest = result['lowest']

            if lowest < grand_lowest:
                grand_lowest = lowest
                grand_lowest_month = result['month']

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

        return max_annualized_drawdown, grand_lowest_month

    def get_benchmark_returns(self, date_from, date_to):

        results = []

        end_of_months = get_last_bdays_of_months_between_two_dates(date_from, date_to)

        _l.info('get_benchmark_returns.date_from %s' % date_from)
        _l.info('get_benchmark_returns.date_to %s' % date_to)
        _l.info('get_benchmark_returns.end_of_months %s' % end_of_months)

        _l.info('get_benchmark_returns.end_of_months before len %s' % len(end_of_months))

        q = Q()

        previos_bday_of_date_from = get_last_business_day(end_of_months[0] - + datetime.timedelta(days=1))

        end_of_months.insert(0, previos_bday_of_date_from)  # get previous day of start end of month
        _l.info('previos_bday_of_date_from %s' % previos_bday_of_date_from)

        _l.info('get_benchmark_returns.end_of_months after len %s' % len(end_of_months))

        end_of_months[-1] = get_last_business_day(self.get_date_or_yesterday(end_of_months[-1]))

        _l.info('get_benchmark_returns.end_of_months %s' % end_of_months)

        for date in end_of_months:
            query = Q(**{'date': date})

            q = q | query

        q = q & Q(**{'instrument__user_code': self.benchmark, 'pricing_policy': self.ecosystem_default.pricing_policy})

        prices = PriceHistory.objects.filter(q)

        if len(end_of_months) != len(prices):
            _l.error("Not enough Prices for benchmark_returns")
        else:
            # for i in range(1, len(end_of_months) + 1):
            _l.info('get_benchmark_returns.end_of_months end_of_months len %s' % len(end_of_months))
            _l.info('get_benchmark_returns.end_of_months prices len %s' % len(prices))
            i = 1
            while i < len(end_of_months):
                results.append(
                    (prices[i].principal_price - prices[i - 1].principal_price) / prices[i - 1].principal_price)
                i = i + 1

        return results

    def get_betta(self):

        portfolio_returns = []
        benchmarks_returns = []

        first_transaction = get_first_transaction(self.portfolio)

        date_from = first_transaction.accounting_date

        date_to = self.date

        # from inception
        # end of month
        # (p1 - p0) / p0 = result %

        # portfolio_months = []

        for period in self.performance_report.periods:

            _l.info('period %s' % period)
            _l.info('period.date_to %s' % period['date_to'])
            _l.info('period.total_return %s' % period['total_return'])

            if str(period['date_to']) >= str(date_from):  # TODO some mystery

                portfolio_returns.append(period['total_return'])
                # portfolio_months.append(period['date_to'])

        benchmarks_returns = self.get_benchmark_returns(date_from, date_to)

        # _l.info('portfolio_months %s' % portfolio_months)

        # cov(portfoio, bench) / var(bench)
        # MINDBLOWING WITH SP500

        # _l.info('self.performance_report.periods %s' % self.performance_report.periods)

        try:
            betta = numpy.cov(portfolio_returns, benchmarks_returns)[0][1] / statistics.variance(benchmarks_returns)
        except Exception as e:
            _l.error('portfolio_returns len %s' % len(portfolio_returns))
            _l.error('benchmarks_returns len %s' % len(benchmarks_returns))
            _l.error('StatsHandler.get betta error %s' % e)
            betta = 0

        return betta

    def get_alpha(self):

        alpha = 0
        # alpha = Retrurn_portfolio - Betta * Return_benchmark
        benchmarks_returns = []
        first_transaction = get_first_transaction(self.portfolio)

        date_from = first_transaction.accounting_date

        date_to = self.date

        cumulative_return = self.get_cumulative_return()
        # benchmarks_returns = self.get_benchmark_returns(date_from, date_to)

        betta = self.get_betta()

        try:

            inception_date_price = PriceHistory.objects.get(date=date_from,
                                                            instrument__user_code=self.benchmark,
                                                            pricing_policy=self.ecosystem_default.pricing_policy).principal_price
            report_date_price = PriceHistory.objects.get(date=date_to,
                                                         instrument__user_code=self.benchmark,
                                                         pricing_policy=self.ecosystem_default.pricing_policy).principal_price

            benchmarks_returns = (report_date_price - inception_date_price) / inception_date_price

            alpha = cumulative_return - betta * benchmarks_returns
        except Exception as e:
            _l.error('get_alpha error %s ' % e)
            _l.error('get_alpha error  betta %s ' % betta)
            _l.error('get_alpha error  benchmarks_returns %s ' % benchmarks_returns)
            _l.error('get_alpha error  cumulative_return %s ' % cumulative_return)
            _l.error('get_alpha traceback %s ' % traceback.format_exc())
            alpha = 0

        return alpha

    def get_correlation(self):

        portfolio_returns = []
        benchmarks_returns = []

        first_transaction = get_first_transaction(self.portfolio)

        date_from = first_transaction.accounting_date

        date_to = self.date

        # from inception
        # end of month
        # (p1 - p0) / p0 = result %

        for period in self.performance_report.periods:
            if str_to_date(period['date_to']) >= date_from:  # TODO some mystery
                portfolio_returns.append(period['total_return'])

        benchmarks_returns = self.get_benchmark_returns(date_from, date_to)

        correlation = 0

        try:
            correlation = numpy.corrcoef(portfolio_returns, benchmarks_returns)[0, 1]
        except Exception as e:
            _l.error('portfolio_returns len %s' % len(portfolio_returns))
            _l.error('benchmarks_returns len %s' % len(benchmarks_returns))
            _l.error('StatsHandler.get betta error %s' % e)
            correlation = 0

        return correlation
