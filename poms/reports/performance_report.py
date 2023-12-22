import datetime
import json
import logging
import time
import traceback
from datetime import timedelta

from django.forms import model_to_dict

from poms.accounts.models import Account, AccountType
from poms.common.models import ProxyUser, ProxyRequest
from poms.common.utils import get_list_of_business_days_between_two_dates, \
    get_last_business_day_in_month, is_business_day, get_last_business_day, get_closest_bday_of_yesterday, \
    get_last_business_day_of_previous_year, get_last_business_day_of_previous_month, get_last_business_day_in_previous_quarter
from poms.currencies.models import Currency, CurrencyHistory
from poms.instruments.models import Instrument, InstrumentType, PriceHistory
from poms.portfolios.models import Portfolio, PortfolioRegisterRecord, PortfolioRegister
from poms.reports.common import Report
from poms.reports.models import BalanceReportCustomField
from poms.reports.sql_builders.balance import BalanceReportBuilderSql
from poms.strategies.models import Strategy1, Strategy2, Strategy3
from poms.transactions.models import Transaction, TransactionClass
from poms.users.models import EcosystemDefault

_l = logging.getLogger('poms.reports')


class PerformanceReportBuilder:

    def __init__(self, instance=None):

        _l.info('PerformanceReportBuilder init')

        self.instance = instance

        self.ecosystem_defaults = EcosystemDefault.objects.get(master_user=self.instance.master_user)

        _l.info('self.instance master_user %s' % self.instance.master_user)
        _l.info('self.instance period_type %s' % self.instance.period_type)
        _l.info('self.instance begin_date %s' % self.instance.begin_date)
        _l.info('self.instance end_date %s' % self.instance.end_date)

        proxy_user = ProxyUser(self.instance.member, self.instance.master_user)
        proxy_request = ProxyRequest(proxy_user)

        self.context = {
            "request": proxy_request,
            "master_user": self.instance.master_user,
            "member": self.instance.member,
        }

    def get_first_transaction(self):

        try:

            if self.instance.bundle:
                # self.instance.bunch_portfolios = []
                # for item in self.instance.bundle.registers.all():
                #     if item.linked_instrument_id:
                #         self.instance.bunch_portfolios.append(item.linked_instrument_id)

                portfolio_registers = self.instance.bundle.registers.all()

            elif self.instance.registers:
                portfolio_registers = self.instance.registers
            # else:
            #     self.instance.bunch_portfolios = self.instance.registers  # instruments #debug szhitenev fund
            #
            # portfolio_registers = PortfolioRegister.objects.filter(master_user=self.instance.master_user,
            #                                                        linked_instrument__in=self.instance.bunch_portfolios)

            portfolio_registers_map = {}

            portfolios = []

            for portfolio_register in portfolio_registers:
                portfolios.append(portfolio_register.portfolio_id)
                portfolio_registers_map[portfolio_register.portfolio_id] = portfolio_register

            # _l.info('get_first_transaction.portfolios %s ' % portfolios)

            transaction = Transaction.objects.filter(portfolio__in=portfolios,
                                                     transaction_class__in=[TransactionClass.CASH_INFLOW,
                                                                            TransactionClass.CASH_OUTFLOW,
                                                                            TransactionClass.INJECTION,
                                                                            TransactionClass.DISTRIBUTION]).order_by(
                'transaction_date').first()

            return transaction.transaction_date

        except Exception as e:
            _l.error("Could not find first transaction date")
            return None

    def build_report(self):
        st = time.perf_counter()

        self.instance.first_transaction_date = self.get_first_transaction()

        if not self.instance.first_transaction_date:

            self.instance.execution_time = float("{:3.3f}".format(time.perf_counter() - st))
            self.instance.items = []
            self.instance.error_message = "Could not find begin date. Please, check if portfolio has transactions"

            return self.instance

        self.instance.items = []

        self.end_date = self.instance.end_date

        _l.info("typeof end_date %s" % type(self.end_date))

        if not self.instance.end_date:
            self.end_date = get_closest_bday_of_yesterday()

        if not is_business_day(self.instance.end_date):
            self.instance.end_date = get_last_business_day(self.instance.end_date)


        begin_date = None


        if not self.instance.begin_date and self.instance.period_type:
            _l.info("No begin date passed, calculating begin date based on period_type and end_date")
            _l.info('self.instance.period_type %s' % self.instance.period_type)

            if self.instance.period_type == 'inception':

                begin_date = get_last_business_day(self.instance.first_transaction_date - timedelta(days=1))

            elif self.instance.period_type == 'ytd':
                begin_date = get_last_business_day_of_previous_year(self.instance.end_date)

            elif self.instance.period_type == 'qtd':
                begin_date = get_last_business_day_in_previous_quarter(self.instance.end_date)

            elif self.instance.period_type == 'mtd':
                begin_date = get_last_business_day_of_previous_month(self.instance.end_date)

            elif self.instance.period_type == 'daily':
                begin_date = get_last_business_day(self.instance.end_date - timedelta(days=1))


        else:

            begin_date = self.instance.begin_date

            if not begin_date or begin_date <= self.instance.first_transaction_date:
                # if inception date, we take -1 day of inception day
                # 2023-11-20
                # szhitenev
                begin_date = get_last_business_day(self.instance.first_transaction_date - timedelta(days=1))



        self.instance.begin_date = begin_date

        _l.info("typeof end_date %s" % type(self.end_date))
        _l.info("typeof begin_date %s" % type(begin_date))

        if self.end_date < begin_date:
            self.end_date = begin_date

        self.instance.periods = self.get_periods(begin_date, self.end_date, self.instance.segmentation_type)

        cumulative_return = 0

        if self.instance.calculation_type == 'time_weighted':

            for period in self.instance.periods:

                table = self.build_time_weighted(period['date_from'], period['date_to'])

                for key, value in table.items():
                    period['items'].append(table[key])

                period = self.calculate_time_weighted_total_values(period)

                period["cumulative_return"] = (cumulative_return + 1) * (period['total_return'] + 1) - 1

                cumulative_return = period["cumulative_return"]

            self.calculate_time_weighted_grand_total_values()

            for period in self.instance.periods:
                for item in period['items']:

                    for key, value in item['portfolios'].items():

                        result_dicts = []

                        for record in item['portfolios'][key]['records']:
                            record_json = model_to_dict(record)
                            result_dicts.append(record_json)

                        item['portfolios'][key]['records'] = result_dicts

            self.instance.items = []
            self.instance.raw_items = json.loads(
                json.dumps(self.instance.periods, indent=4, sort_keys=True, default=str))

            for period in self.instance.periods:
                item = {}

                item['date_from'] = period['date_from']
                item['date_to'] = period['date_to']

                item['begin_nav'] = period['begin_nav']
                item['end_nav'] = period['end_nav']

                item['cash_flow'] = period['total_cash_flow']
                item['cash_inflow'] = period['total_cash_inflow']
                item['cash_outflow'] = period['total_cash_outflow']
                item['nav'] = period['total_nav']
                item['instrument_return'] = period['total_return']
                if 'cumulative_return' in period:
                    item['cumulative_return'] = period['cumulative_return']

                self.instance.items.append(item)

        if self.instance.calculation_type == 'modified_dietz':
            self.build_modified_dietz(begin_date, self.end_date)

        # _l.info('items total %s' % len(self.instance.items))

        _l.info('build_st done: %s', "{:3.3f}".format(time.perf_counter() - st))

        self.instance.execution_time = float("{:3.3f}".format(time.perf_counter() - st))

        relation_prefetch_st = time.perf_counter()

        # self.add_data_items()

        self.instance.relation_prefetch_time = float("{:3.3f}".format(time.perf_counter() - relation_prefetch_st))

        return self.instance

    def calculate_time_weighted_grand_total_values(self):

        grand_return = 1

        grand_cash_flow = 0
        grand_cash_inflow = 0
        grand_cash_outflow = 0
        grand_nav = 0
        begin_nav = 0
        end_nav = 0

        for period in self.instance.periods:
            grand_return = grand_return * (period['total_return'] + 1)
            grand_cash_flow = grand_cash_flow + period['total_cash_flow']
            grand_cash_inflow = grand_cash_inflow + period['total_cash_inflow']
            grand_cash_outflow = grand_cash_outflow + period['total_cash_outflow']

        grand_return = grand_return - 1

        begin_nav = self.instance.periods[0]['total_nav']
        grand_nav = self.instance.periods[-1]['total_nav']
        end_nav = self.instance.periods[-1]['total_nav']

        self.instance.grand_return = grand_return
        self.instance.grand_cash_flow = grand_cash_flow
        self.instance.grand_cash_inflow = grand_cash_inflow
        self.instance.grand_cash_outflow = grand_cash_outflow
        self.instance.grand_nav = grand_nav
        self.instance.begin_nav = begin_nav
        self.instance.end_nav = end_nav

    def calculate_modified_dietz_grand_total_values(self):

        grand_return = 1

        grand_cash_flow = 0
        grand_cash_inflow = 0
        grand_cash_outflow = 0
        grand_nav = 0
        begin_nav = 0
        end_nav = 0

        # TODO for grand return we need to calculate separate perfomance ignoring months period
        # e.g. instead of 30days windows, we need full amount of days, e.g. 10 years = 3650 days
        # e.g. date_from = inception, date_to = date_to
        for period in self.instance.periods:
            grand_return = grand_return * (period['total_return'] + 1)
            grand_cash_flow = grand_cash_flow + period['total_cash_flow']
            grand_cash_inflow = grand_cash_inflow + period['total_cash_inflow']
            grand_cash_outflow = grand_cash_outflow + period['total_cash_outflow']

        grand_return = grand_return - 1

        begin_nav = self.instance.periods[0]['total_nav']
        grand_nav = self.instance.periods[-1]['total_nav']
        end_nav = self.instance.periods[-1]['total_nav']

        self.instance.grand_return = grand_return
        self.instance.grand_cash_flow = grand_cash_flow
        self.instance.grand_cash_inflow = grand_cash_inflow
        self.instance.grand_cash_outflow = grand_cash_outflow
        self.instance.grand_nav = grand_nav
        self.instance.begin_nav = begin_nav
        self.instance.end_nav = end_nav

    def calculate_time_weighted_total_values(self, period):

        total_nav = 0
        total_cash_flow = 0
        total_cash_inflow = 0
        total_cash_outflow = 0
        total_return = 1

        for item in period['items']:
            total_nav = item['subtotal_nav']
            total_cash_flow = total_cash_flow + item['subtotal_cash_flow']
            total_cash_inflow = total_cash_inflow + item['subtotal_cash_inflow']
            total_cash_outflow = total_cash_outflow + item['subtotal_cash_outflow']

            total_return = total_return * (item['subtotal_return'] + 1)

        total_return = total_return - 1

        period['begin_nav'] = period['items'][0]['subtotal_nav']
        period['end_nav'] = period['items'][-1]['subtotal_nav']

        period['total_cash_flow'] = total_cash_flow
        period['total_cash_inflow'] = total_cash_inflow
        period['total_cash_outflow'] = total_cash_outflow
        period['total_nav'] = total_nav
        period['total_return'] = total_return

        return period

    def calculate_modified_dietz_total_values(self, period):

        total_nav = 0
        total_cash_flow = 0
        total_cash_inflow = 0
        total_cash_outflow = 0
        total_cash_flow_weighted = 0
        total_return = 1

        for item in period['items']:
            total_nav = item['subtotal_nav']
            total_cash_flow = total_cash_flow + item['subtotal_cash_flow']
            total_cash_inflow = total_cash_inflow + item['subtotal_cash_inflow']
            total_cash_outflow = total_cash_outflow + item['subtotal_cash_outflow']
            total_cash_flow_weighted = total_cash_flow_weighted + item['subtotal_cash_flow_weighted']

        period['begin_nav'] = period['items'][0]['subtotal_nav']
        period['end_nav'] = period['items'][-1]['subtotal_nav']

        try:
            total_return = (period['end_nav'] - period['begin_nav'] - total_cash_flow) / (
                    period['begin_nav'] + total_cash_flow_weighted)
        except Exception:
            total_return = 0

        period['total_cash_flow'] = total_cash_flow
        period['total_cash_inflow'] = total_cash_inflow
        period['total_cash_outflow'] = total_cash_outflow
        period['total_cash_flow_weighted'] = total_cash_flow_weighted
        period['total_nav'] = total_nav
        period['total_return'] = total_return

        return period

    def get_dict_of_dates_between_two_dates_with_order(self, date_from, date_to):
        list_result = []
        result = {}

        diff = date_to - date_from

        for i in range(diff.days + 1):
            day = date_from + timedelta(days=i)
            list_result.append(day)

        index = 0
        for item in list_result:
            result[str(item)] = index + 1
            index = index + 1

        return result

    def get_periods(self, date_from, date_to, segmentation_type):

        # _l.info("Getting periods %s from %s to %s" % (self.instance.segmentation_type, date_from, date_to))

        result = []

        dates = get_list_of_business_days_between_two_dates(date_from, date_to)

        # _l.info('dates %s' % dates)

        if segmentation_type == 'days':

            if date_from == date_to and is_business_day(date_from):

                result = self.format_to_days(dates)

            else:

                dates = [get_last_business_day(date_from)]

                result = self.format_to_days(dates)

        if segmentation_type == 'months':
            result = self.format_to_months(dates)

        return result

    def format_to_months(self, dates):

        result = []

        result_obj = {}

        begin_date = dates[0]

        # try:
        #     begin_date = self.get_first_transaction()
        # except Exception as e:
        #     begin_date = dates[0]

        for date in dates:

            date_str = str(date)

            date_pieces = date_str.split('-')

            year = int(date_pieces[0])
            month = int(date_pieces[1])

            year_month = str(year) + '-' + str(month)

            # month_end = datetime.date(year, month, calendar.monthrange(year, month)[1])
            month_end = get_last_business_day_in_month(year, month)

            if month_end >= self.end_date:
                month_end = self.end_date

                if not is_business_day(month_end):
                    month_end = get_last_business_day(month_end)

            month_start = get_last_business_day(
                datetime.date(year, month, 1) - timedelta(days=1))  # 2022-10-01 - 2022-09-30

            # begin_date_year = begin_date.year
            # begin_date_month = begin_date.month

            # previous_end_of_month_of_begin_date = datetime.date(begin_date_year, begin_date_month, 1) - timedelta(
            #     days=1)

            # TODO check?
            # previous_end_of_month_of_begin_date = get_last_business_day_in_month(begin_date_year, begin_date_month) - timedelta(days=1)

            if begin_date > month_start:
                month_start = begin_date

            if year_month not in result_obj:
                result_obj[year_month] = {
                    'date_from': month_start,
                    'date_to': month_end,
                    'items': [],
                    'total_nav': 0,
                    'total_return': 0
                }

        for key, value in result_obj.items():
            result.append(result_obj[key])

        # _l.info("result %s" % result)

        return result

    def format_to_weeks(self, table):

        result = []

        return result

    def format_to_days(self, dates):

        result = []

        for date in dates:
            result_item = {}

            result_item['date_from'] = date - timedelta(days=1)
            result_item['date_to'] = date
            result_item['items'] = []
            result_item['total_nav'] = 0
            result_item['total_return'] = 0

            result.append(result_item)

        return result

    def build_time_weighted(self, date_from, date_to):

        # _l.info("build portfolio records")

        date_from_str = str(date_from)
        date_to_str = str(date_to)

        result = []

        if self.instance.bundle:
            self.instance.bunch_portfolios = []
            for item in self.instance.bundle.registers.all():
                if item.linked_instrument_id:
                    self.instance.bunch_portfolios.append(item.linked_instrument_id)
        else:
            self.instance.bunch_portfolios = self.instance.registers  # instruments #debug szhitenev fund

        portfolio_registers = PortfolioRegister.objects.filter(master_user=self.instance.master_user,
                                                               linked_instrument__in=self.instance.bunch_portfolios)

        portfolio_registers_map = {}

        portfolios = []

        for portfolio_register in portfolio_registers:
            portfolios.append(portfolio_register.portfolio_id)
            portfolio_registers_map[portfolio_register.portfolio_id] = portfolio_register

        # _l.info('build_time_weighted.result portfolios %s ' % portfolios)

        # transactions = Transaction.objects.filter(portfolio__in=portfolios,
        #                                           transaction_date__gte=date_from,
        #                                           transaction_date__lte=date_to,
        #                                           transaction_class__in=[TransactionClass.CASH_INFLOW,
        #                                                                  TransactionClass.CASH_OUTFLOW,
        #                                                                  TransactionClass.INJECTION,
        #                                                                  TransactionClass.DISTRIBUTION]).order_by(
        #     'transaction_date')

        records = PortfolioRegisterRecord.objects.filter(portfolio_register__in=portfolio_registers,
                                                         transaction_date__gte=date_from,
                                                         transaction_date__lte=date_to,
                                                         transaction_class__in=[TransactionClass.CASH_INFLOW,
                                                                                TransactionClass.CASH_OUTFLOW,
                                                                                TransactionClass.INJECTION,
                                                                                TransactionClass.DISTRIBUTION]).order_by(
            'transaction_date')

        # create empty structure start

        table = {}

        if date_from_str not in table:
            table[date_from_str] = {}
            table[date_from_str]['date'] = date_from_str
            table[date_from_str]['portfolios'] = {}
            table[date_from_str]['subtotal_cash_flow'] = 0
            table[date_from_str]['subtotal_cash_inflow'] = 0
            table[date_from_str]['subtotal_cash_outflow'] = 0
            table[date_from_str]['subtotal_nav'] = 0
            table[date_from_str]['subtotal_return'] = 0

            for portfolio_id in portfolios:
                table[date_from_str]['portfolios'][portfolio_id] = {
                    'portfolio_register': portfolio_registers_map[portfolio_id],
                    'portfolio_id': portfolio_id,
                    'transaction_date_str': date_from_str,
                    'transaction_date': date_from,
                    'cash_flow': 0,
                    'cash_inflow': 0,
                    'cash_outflow': 0,
                    'previous_nav': 0,
                    'nav': 0,
                    'instrument_return': 0,
                    'records': []
                }

        for record in records:

            transaction_date_str = str(record.transaction_date)

            if transaction_date_str not in table:
                table[transaction_date_str] = {}
                table[transaction_date_str]['date'] = transaction_date_str
                table[transaction_date_str]['portfolios'] = {}
                table[transaction_date_str]['subtotal_cash_flow'] = 0
                table[transaction_date_str]['subtotal_cash_inflow'] = 0
                table[transaction_date_str]['subtotal_cash_outflow'] = 0
                table[transaction_date_str]['subtotal_nav'] = 0
                table[transaction_date_str]['subtotal_return'] = 0

            if record.portfolio_id not in table[transaction_date_str]['portfolios']:
                table[transaction_date_str]['portfolios'][record.portfolio_id] = {
                    'portfolio_register': record.portfolio_register,
                    'portfolio_id': record.portfolio_id,
                    'transaction_date_str': transaction_date_str,
                    'transaction_date': record.transaction_date,
                    'cash_flow': 0,
                    'cash_inflow': 0,
                    'cash_outflow': 0,
                    'previous_nav': 0,
                    'nav': 0,
                    'instrument_return': 0,
                    'records': []
                }

            if transaction_date_str != date_from_str:  # Always empty records for date_from
                table[transaction_date_str]['portfolios'][record.portfolio_id]['records'].append(record)

        if date_to_str not in table:
            table[date_to_str] = {}
            table[date_to_str]['date'] = date_to_str
            table[date_to_str]['portfolios'] = {}
            table[date_to_str]['subtotal_cash_flow'] = 0
            table[date_to_str]['subtotal_cash_inflow'] = 0
            table[date_to_str]['subtotal_cash_outflow'] = 0
            table[date_to_str]['subtotal_nav'] = 0
            table[date_to_str]['subtotal_return'] = 0

            for portfolio_id in portfolios:
                table[date_to_str]['portfolios'][portfolio_id] = {
                    'portfolio_register': portfolio_registers_map[portfolio_id],
                    'portfolio_id': portfolio_id,
                    'transaction_date_str': date_to_str,
                    'transaction_date': date_to,
                    'cash_flow': 0,
                    'cash_inflow': 0,
                    'cash_outflow': 0,
                    'previous_nav': 0,
                    'nav': 0,
                    'instrument_return': 0,
                    'records': []
                }

        # create empty structure end

        # Fill with Data

        previous_date = None

        for key, value in table.items():

            item_date = table[key]

            _l.info('performance.table.key %s' % key)
            _l.info('performance.table.previous_date %s' % previous_date)

            for _key, _value in item_date['portfolios'].items():

                item = item_date['portfolios'][_key]

                nav = 0

                try:
                    price_history = PriceHistory.objects.get(date=item['transaction_date'],
                                                             instrument=item['portfolio_register'].linked_instrument,
                                                             pricing_policy=item[
                                                                 'portfolio_register'].valuation_pricing_policy)

                    fx_rate = 1

                    if self.instance.report_currency.id == item[
                        'portfolio_register'].linked_instrument.pricing_currency.id:
                        fx_rate = 1
                    else:
                        report_currency_fx_rate = None
                        instrument_pricing_currency_fx_rate = None

                        if self.instance.report_currency.id == self.ecosystem_defaults.currency.id:
                            report_currency_fx_rate = 1
                        else:
                            report_currency_fx_rate = CurrencyHistory.objects.get(date=item['transaction_date'],
                                                                                  currency=self.instance.report_currency,
                                                                                  pricing_policy=item[
                                                                                      'portfolio_register'].valuation_pricing_policy).fx_rate

                        if item[
                            'portfolio_register'].linked_instrument.pricing_currency.id == self.ecosystem_defaults.currency.id:
                            instrument_pricing_currency_fx_rate = 1
                        else:
                            instrument_pricing_currency_fx_rate = CurrencyHistory.objects.get(
                                date=item['transaction_date'],
                                currency=item[
                                    'portfolio_register'].linked_instrument.pricing_currency,
                                pricing_policy=item[
                                    'portfolio_register'].valuation_pricing_policy).fx_rate

                        fx_rate = instrument_pricing_currency_fx_rate / report_currency_fx_rate

                    nav = price_history.nav * fx_rate

                    # report currency / linked_instrument.pricing currency

                except Exception as e:
                    _l.error("Could not calculate nav %s " % e)
                    nav = 0

                previous_nav = 0

                try:
                    if previous_date:
                        previous_nav = previous_date['portfolios'][_key]['nav']
                except Exception as e:
                    previous_nav = 0

                cash_flow = 0
                cash_inflow = 0
                cash_outflow = 0

                for record in item['records']:

                    fx_rate = 1

                    try:

                        if self.instance.report_currency.id == record.valuation_currency.id:
                            fx_rate = 1
                        else:
                            report_currency_fx_rate = None
                            record_valuation_currency_fx_rate = None

                            if self.instance.report_currency.id == self.ecosystem_defaults.currency.id:
                                report_currency_fx_rate = 1
                            else:
                                report_currency_fx_rate = CurrencyHistory.objects.get(date=record.transaction_date,
                                                                                      pricing_policy=record.portfolio_register.valuation_pricing_policy,
                                                                                      currency=self.instance.report_currency).fx_rate

                            if record.valuation_currency.id == self.ecosystem_defaults.currency.id:
                                record_valuation_currency_fx_rate = 1
                            else:
                                record_valuation_currency_fx_rate = CurrencyHistory.objects.get(
                                    date=record.transaction_date,
                                    pricing_policy=record.portfolio_register.valuation_pricing_policy,
                                    currency=record.valuation_currency).fx_rate

                            fx_rate = record_valuation_currency_fx_rate / report_currency_fx_rate

                    except Exception as e:
                        _l.error("Could not calculate fx_rate e %s" % e)
                        _l.error("Could not calculate fx_rate traceback %s" % traceback.format_exc())
                        fx_rate = 1

                    # report / valuation

                    cash_flow = cash_flow + record.cash_amount_valuation_currency * fx_rate

                    if record.transaction_class_id in [TransactionClass.CASH_INFLOW, TransactionClass.INJECTION]:
                        cash_inflow = cash_inflow + record.cash_amount_valuation_currency * fx_rate

                    if record.transaction_class_id in [TransactionClass.CASH_OUTFLOW, TransactionClass.DISTRIBUTION]:
                        cash_outflow = cash_outflow + record.cash_amount_valuation_currency * fx_rate

                instrument_return = 0

                if previous_nav:
                    instrument_return = (nav - cash_flow - previous_nav) / previous_nav
                else:
                    if nav:
                        instrument_return = (nav - cash_flow) / nav
                        # instrument_return = (nav - cash_flow) / cash_flow # 2023-11-08, performance fix
                    else:
                        instrument_return = 0

                item['nav'] = nav

                if item['transaction_date_str'] == date_from_str:
                    item['cash_flow'] = 0
                else:
                    item['cash_flow'] = cash_flow

                if item['transaction_date_str'] == date_from_str:
                    item['cash_inflow'] = 0
                else:
                    item['cash_inflow'] = cash_inflow

                if item['transaction_date_str'] == date_from_str:
                    item['cash_outflow'] = 0
                else:
                    item['cash_outflow'] = cash_outflow

                item['previous_nav'] = previous_nav

                item['instrument_return'] = instrument_return

                if previous_date:
                    item['previous_date'] = json.loads(json.dumps(previous_date, default=str))
                else:
                    item['previous_date'] = None

                previous_date = item_date

        # Calculate nav

        previous_date = None

        for key, value in table.items():

            item_date = table[key]

            for _key, _value in item_date['portfolios'].items():

                item = item_date['portfolios'][_key]

                item_date['subtotal_nav'] = item_date['subtotal_nav'] + item['nav']
                item_date['subtotal_cash_flow'] = item_date['subtotal_cash_flow'] + item['cash_flow']
                item_date['subtotal_cash_inflow'] = item_date['subtotal_cash_inflow'] + item['cash_inflow']
                item_date['subtotal_cash_outflow'] = item_date['subtotal_cash_outflow'] + item['cash_outflow']

                # Return[k,i] * NAV[k,i-1] / Total_NAV[i-1]

                if previous_date and previous_date['subtotal_nav']:
                    item_date['subtotal_return'] = item_date['subtotal_return'] + (
                            item['instrument_return'] * item['previous_nav'] / previous_date['subtotal_nav'])

                previous_date = item_date

        # print('table %s' % table)

        return table

    def get_portfolio_registers(self):

        # if self.instance.bundle:
        #     self.instance.bunch_portfolios = []
        #     for item in self.instance.bundle.registers.all():
        #         if item.linked_instrument_id:
        #             self.instance.bunch_portfolios.append(item.linked_instrument_id)
        # else:
        #     self.instance.bunch_portfolios = self.instance.registers  # instruments #debug szhitenev fund

        if self.instance.bundle:
            # self.instance.bunch_portfolios = []
            # for item in self.instance.bundle.registers.all():
            #     if item.linked_instrument_id:
            #         self.instance.bunch_portfolios.append(item.linked_instrument_id)

            portfolio_registers = self.instance.bundle.registers.all()

        elif self.instance.registers:
            portfolio_registers = self.instance.registers

        # portfolio_registers = PortfolioRegister.objects.filter(master_user=self.instance.master_user,
        #                                                        linked_instrument__in=self.instance.bunch_portfolios)

        portfolio_registers_map = {}

        portfolios = []

        for portfolio_register in portfolio_registers:
            portfolios.append(portfolio_register.portfolio_id)
            portfolio_registers_map[portfolio_register.portfolio_id] = portfolio_register

        return portfolio_registers

    def get_portfolios(self, portfolio_registers):

        portfolios = []

        for portfolio_register in portfolio_registers:
            portfolios.append(portfolio_register.portfolio)

        return portfolios

    def get_modified_dietz_nav_for_record(self, register_record):

        try:
            price_history = PriceHistory.objects.get(date=register_record.transaction_date,
                                                     instrument=register_record.portfolio_register.linked_instrument,
                                                     pricing_policy=register_record.portfolio_register.valuation_pricing_policy)

            fx_rate = 1

            try:

                if self.instance.report_currency.id == register_record.portfolio_register.linked_instrument.pricing_currency.id:
                    fx_rate = 1
                else:
                    report_currency_fx_rate = None
                    instrument_pricing_currency_fx_rate = None

                    if self.instance.report_currency.id == self.ecosystem_defaults.currency.id:
                        report_currency_fx_rate = 1
                    else:
                        report_currency_fx_rate = CurrencyHistory.objects.get(date=register_record,
                                                                              currency=self.instance.report_currency,
                                                                              pricing_policy=register_record.portfolio_register.valuation_pricing_policy).fx_rate

                    if register_record.portfolio_register.linked_instrument.pricing_currency.id == self.ecosystem_defaults.currency.id:
                        instrument_pricing_currency_fx_rate = 1
                    else:
                        instrument_pricing_currency_fx_rate = CurrencyHistory.objects.get(
                            date=register_record.transaction_date,
                            currency=register_record.portfolio_register.linked_instrument.pricing_currency,
                            pricing_policy=register_record.portfolio_register.valuation_pricing_policy).fx_rate

                    fx_rate = instrument_pricing_currency_fx_rate / report_currency_fx_rate

            except Exception as e:
                _l.error('fx_rate e %s' % e)
                fx_rate = 1

            nav = price_history.nav * fx_rate

        except Exception as e:
            nav = 0

        return nav

    def get_nav_by_date(self, portfolios, date, pricing_policy):

        total_nav = 0

        balance_report = Report(master_user=self.instance.master_user)
        balance_report.master_user = self.instance.master_user
        balance_report.member = self.instance.member
        balance_report.report_date = date
        balance_report.pricing_policy = pricing_policy
        balance_report.portfolios = portfolios
        balance_report.report_currency = self.instance.report_currency

        builder = BalanceReportBuilderSql(instance=balance_report)
        balance_report = builder.build_balance_sync()

        nav = 0

        _l.info(f'get_nav_by_date.balance_report. date: {date}, len:{len(balance_report.items)}')

        for it in balance_report.items:
            if it["market_value"]:
                nav = nav + it["market_value"]

        return nav

    def get_record_fx_rate(self, record):

        fx_rate = 1

        try:

            if self.instance.report_currency.id == record.valuation_currency.id:
                fx_rate = 1
            else:
                report_currency_fx_rate = None
                record_valuation_currency_fx_rate = None

                if self.instance.report_currency.id == self.ecosystem_defaults.currency.id:
                    report_currency_fx_rate = 1
                else:
                    report_currency_fx_rate = CurrencyHistory.objects.get(date=record.transaction_date,
                                                                          pricing_policy=record.portfolio_register.valuation_pricing_policy,
                                                                          currency=self.instance.report_currency).fx_rate

                if record.valuation_currency.id == self.ecosystem_defaults.currency.id:
                    record_valuation_currency_fx_rate = 1
                else:
                    record_valuation_currency_fx_rate = CurrencyHistory.objects.get(
                        pricing_policy=record.portfolio_register.valuation_pricing_policy,
                        date=record.transaction_date, currency=record.valuation_currency).fx_rate

                fx_rate = record_valuation_currency_fx_rate / report_currency_fx_rate

        except Exception as e:
            _l.error('fx_rate e %s' % e)
            fx_rate = 1  # TODO check if this is correct

        return fx_rate

    def build_modified_dietz(self, date_from, date_to):

        _l.info('performance_report.build_modified_dietz')

        portfolio_registers = self.get_portfolio_registers()
        portfolios = self.get_portfolios(portfolio_registers)

        dates_map = self.get_dict_of_dates_between_two_dates_with_order(date_from, date_to)

        grand_return = 0

        # TODO may cause errors if portfolios has different pricing policies
        # Consider to discuss with ogreshnev what to do
        # 2023-11-14 szhitenev
        pricing_policy = portfolio_registers[0].valuation_pricing_policy

        begin_nav = self.get_nav_by_date(portfolios, date_from, pricing_policy)
        end_nav = self.get_nav_by_date(portfolios, date_to, pricing_policy)

        self.instance.execution_log = {
            "items": []
        }

        grand_cash_flow = 0
        grand_cash_inflow = 0
        grand_cash_outflow = 0
        # should be begin nav instead of 0
        grand_cash_flow_weighted = begin_nav

        grand_return = 0

        if date_to > date_from:

            for portfolio in portfolios:

                if date_from == portfolio.first_transaction_date() or date_from < portfolio.first_transaction_date():

                    # performance report could not be less then first transaction date
                    date_from = portfolio.first_transaction_date()

                    portfolio_records = PortfolioRegisterRecord.objects.filter(portfolio_register__portfolio=portfolio,
                                                                               transaction_date__gte=date_from,
                                                                               transaction_date__lte=date_to,
                                                                               transaction_class__in=[
                                                                                   TransactionClass.CASH_INFLOW,
                                                                                   TransactionClass.CASH_OUTFLOW,
                                                                                   TransactionClass.INJECTION,
                                                                                   TransactionClass.DISTRIBUTION]).order_by(
                        'transaction_date')

                else:

                    # transaction_date__gt !!!
                    # for case when it is not first transaction date, we need only greater_then

                    portfolio_records = PortfolioRegisterRecord.objects.filter(portfolio_register__portfolio=portfolio,
                                                                               transaction_date__gt=date_from,
                                                                               transaction_date__lte=date_to,
                                                                               transaction_class__in=[
                                                                                   TransactionClass.CASH_INFLOW,
                                                                                   TransactionClass.CASH_OUTFLOW,
                                                                                   TransactionClass.INJECTION,
                                                                                   TransactionClass.DISTRIBUTION]).order_by(
                        'transaction_date')


                for record in portfolio_records:
                    date_n = dates_map[str(record.transaction_date)]
                    date_to_n = dates_map[str(date_to)]
                    date_from_n = dates_map[str(date_from)]

                    # 2022-03-31
                    # 2022-04-01

                    # date_n = 2022-04-01
                    # date_to_n = 2022-04-29
                    # date_from_n = 2022-03-31

                    #   (30 - 2) / (30 - 1) = 28 / 29 = 0

                    # 319 - 13 / 319 - 1

                    time_weight = (date_to_n - date_n) / (date_to_n - date_from_n)

                    fx_rate = self.get_record_fx_rate(record)

                    record_cash_flow = record.cash_amount_valuation_currency * fx_rate

                    if record.transaction_class_id in [TransactionClass.CASH_INFLOW, TransactionClass.INJECTION]:
                        grand_cash_inflow = grand_cash_inflow + record_cash_flow

                    if record.transaction_class_id in [TransactionClass.CASH_OUTFLOW, TransactionClass.DISTRIBUTION]:
                        grand_cash_outflow = grand_cash_outflow + record_cash_flow

                    grand_cash_flow = grand_cash_flow + record_cash_flow
                    grand_cash_flow_weighted = grand_cash_flow_weighted + (record_cash_flow * time_weight)

                    self.instance.execution_log['items'].append({
                        "record": record.id,
                        "date_n": date_n,
                        "date_from_n": date_from_n,
                        "date_to_n": date_to_n,
                        "time_weight": time_weight,
                        "fx_rate": fx_rate,
                        "record_cash_flow": record_cash_flow,
                        "grand_cash_inflow": grand_cash_inflow,
                        "grand_cash_outflow": grand_cash_outflow,
                        "grand_cash_flow": grand_cash_flow,
                        "grand_cash_flow_weighted": grand_cash_flow_weighted
                    })

            try:
                grand_return = (end_nav - begin_nav - grand_cash_flow) / (
                    grand_cash_flow_weighted)
            except Exception as e:
                _l.error("Could not calculate modified dietz return error %s" % e)
                _l.error("Could not calculate modified dietz return traceback %s" % traceback.format_exc())
                grand_return = 0

        self.instance.grand_return = grand_return
        self.instance.grand_cash_flow = grand_cash_flow
        self.instance.grand_cash_flow_weighted = grand_cash_flow_weighted
        self.instance.grand_cash_inflow = grand_cash_inflow
        self.instance.grand_cash_outflow = grand_cash_outflow
        self.instance.grand_nav = end_nav
        self.instance.begin_nav = begin_nav
        self.instance.end_nav = end_nav


def add_data_items_instruments(self, ids):
    self.instance.item_instruments = Instrument.objects.prefetch_related(
        'attributes',
        'attributes__attribute_type',
        'attributes__classifier',
    ).filter(master_user=self.instance.master_user) \
        .filter(id__in=ids)


def add_data_items_instrument_types(self, instruments):
    ids = []

    for instrument in instruments:
        ids.append(instrument.instrument_type_id)

    self.instance.item_instrument_types = InstrumentType.objects.prefetch_related(
        'attributes',
        'attributes__attribute_type',
        'attributes__classifier',
    ).filter(master_user=self.instance.master_user) \
        .filter(id__in=ids)


def add_data_items_portfolios(self, ids):
    self.instance.item_portfolios = Portfolio.objects.prefetch_related(
        'attributes'
    ).defer('responsibles', 'counterparties', 'transaction_types', 'accounts') \
        .filter(master_user=self.instance.master_user) \
        .filter(
        id__in=ids)


def add_data_items_accounts(self, ids):
    self.instance.item_accounts = Account.objects.prefetch_related(
        'attributes',
        'attributes__attribute_type',
        'attributes__classifier',
    ).filter(master_user=self.instance.master_user).filter(id__in=ids)


def add_data_items_account_types(self, accounts):
    ids = []

    for account in accounts:
        ids.append(account.type_id)

    self.instance.item_account_types = AccountType.objects.prefetch_related(
        'attributes',
        'attributes__attribute_type',
        'attributes__classifier',
    ).filter(master_user=self.instance.master_user) \
        .filter(id__in=ids)


def add_data_items_currencies(self, ids):
    self.instance.item_currencies = Currency.objects.prefetch_related(
        'attributes',
        'attributes__attribute_type',
        'attributes__classifier',
    ).filter(master_user=self.instance.master_user).filter(id__in=ids)


def add_data_items_strategies1(self, ids):
    self.instance.item_strategies1 = Strategy1.objects.prefetch_related(
        'attributes',
        'attributes__attribute_type',
        'attributes__classifier',
    ).filter(master_user=self.instance.master_user).filter(id__in=ids)


def add_data_items_strategies2(self, ids):
    self.instance.item_strategies2 = Strategy2.objects.prefetch_related(
        'attributes',
        'attributes__attribute_type',
        'attributes__classifier',
    ).filter(master_user=self.instance.master_user).filter(id__in=ids)


def add_data_items_strategies3(self, ids):
    self.instance.item_strategies3 = Strategy3.objects.prefetch_related(
        'attributes',
        'attributes__attribute_type',
        'attributes__classifier',
    ).filter(master_user=self.instance.master_user).filter(id__in=ids)


def add_data_items(self):
    instance_relations_st = time.perf_counter()

    _l.debug('_refresh_with_perms_optimized instance relations done: %s',
             "{:3.3f}".format(time.perf_counter() - instance_relations_st))

    permissions_st = time.perf_counter()

    _l.debug('_refresh_with_perms_optimized permissions done: %s',
             "{:3.3f}".format(time.perf_counter() - permissions_st))

    item_relations_st = time.perf_counter()

    instrument_ids = []
    portfolio_ids = []
    account_ids = []
    currencies_ids = []
    strategies1_ids = []
    strategies2_ids = []
    strategies3_ids = []

    for item in self.instance.items:

        if 'portfolio_id' in item and item['portfolio_id'] != '-':
            portfolio_ids.append(item['portfolio_id'])

        if 'instrument_id' in item:
            instrument_ids.append(item['instrument_id'])

        if 'account_position_id' in item and item['account_position_id'] != '-':
            account_ids.append(item['account_position_id'])
        if 'account_cash_id' in item and item['account_cash_id'] != '-':
            account_ids.append(item['account_cash_id'])

        if 'currency_id' in item:
            currencies_ids.append(item['currency_id'])
        if 'pricing_currency_id' in item:
            currencies_ids.append(item['pricing_currency_id'])
        if 'exposure_currency_id' in item:
            currencies_ids.append(item['exposure_currency_id'])

        if 'strategy1_position_id' in item:
            strategies1_ids.append(item['strategy1_position_id'])

        if 'strategy2_position_id' in item:
            strategies2_ids.append(item['strategy2_position_id'])

        if 'strategy3_position_id' in item:
            strategies3_ids.append(item['strategy3_position_id'])

        if 'strategy1_cash_id' in item:
            strategies1_ids.append(item['strategy1_cash_id'])

        if 'strategy2_cash_id' in item:
            strategies2_ids.append(item['strategy2_cash_id'])

        if 'strategy3_cash_id' in item:
            strategies3_ids.append(item['strategy3_cash_id'])

    instrument_ids = list(set(instrument_ids))
    portfolio_ids = list(set(portfolio_ids))
    account_ids = list(set(account_ids))
    currencies_ids = list(set(currencies_ids))
    strategies1_ids = list(set(strategies1_ids))
    strategies2_ids = list(set(strategies2_ids))
    strategies3_ids = list(set(strategies3_ids))

    self.add_data_items_instruments(instrument_ids)
    self.add_data_items_portfolios(portfolio_ids)
    self.add_data_items_accounts(account_ids)
    self.add_data_items_currencies(currencies_ids)
    self.add_data_items_strategies1(strategies1_ids)
    self.add_data_items_strategies2(strategies2_ids)
    self.add_data_items_strategies3(strategies3_ids)

    # _l.info('add_data_items_strategies1 %s ' % self.instance.item_strategies1)

    self.add_data_items_instrument_types(self.instance.item_instruments)
    self.add_data_items_account_types(self.instance.item_accounts)

    self.instance.custom_fields = BalanceReportCustomField.objects.filter(master_user=self.instance.master_user)

    _l.info('_refresh_with_perms_optimized item relations done: %s',
            "{:3.3f}".format(time.perf_counter() - item_relations_st))

    # _l.info('add_data_items_strategies1 %s ' % self.instance.item_strategies1)
