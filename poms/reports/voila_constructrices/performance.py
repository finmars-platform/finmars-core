import datetime
import json
import logging
import time
from datetime import timedelta
import calendar

from django.db import connection
from django.forms import model_to_dict
from django.views.generic.dates import timezone_today
from rest_framework.exceptions import APIException

from poms.accounts.models import Account
from poms.common.utils import get_list_of_dates_between_two_dates, get_list_of_business_days_between_two_dates, \
    last_business_day_in_month
from poms.currencies.models import Currency, CurrencyHistory
from poms.instruments.models import Instrument, InstrumentType, LongUnderlyingExposure, ShortUnderlyingExposure, \
    ExposureCalculationModel, PriceHistory
from poms.portfolios.models import Portfolio, PortfolioRegisterRecord, PortfolioRegister
from poms.reports.builders.balance_item import Report
from poms.reports.builders.base_builder import BaseReportBuilder
from poms.reports.models import BalanceReportCustomField
from poms.reports.sql_builders.helpers import get_transaction_filter_sql_string, get_report_fx_rate, \
    get_fx_trades_and_fx_variations_transaction_filter_sql_string, get_where_expression_for_position_consolidation, \
    get_position_consolidation_for_select, get_pl_left_join_consolidation, dictfetchall, \
    get_cash_consolidation_for_select, get_cash_as_position_consolidation_for_select
from poms.reports.sql_builders.pl import PLReportBuilderSql
from poms.strategies.models import Strategy1, Strategy2, Strategy3
from poms.users.models import EcosystemDefault
from django.conf import settings
from poms.transactions.models import Transaction, TransactionClass

_l = logging.getLogger('poms.reports')


class PerformanceReportBuilder:

    def __init__(self, instance=None):

        _l.info('PerformanceReportBuilder init')

        self.instance = instance

        self.ecosystem_defaults = EcosystemDefault.objects.get(master_user=self.instance.master_user)

        _l.info('self.instance master_user %s' % self.instance.master_user)
        _l.info('self.instance begin_date %s' % self.instance.begin_date)
        _l.info('self.instance end_date %s' % self.instance.end_date)

    def get_first_transaction(self):

        try:

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

            _l.info('get_first_transaction.portfolios %s ' % portfolios)

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

        self.instance.items = []

        end_date = self.instance.end_date

        if self.instance.end_date > timezone_today():
            # end_date = timezone_today() - timedelta(days=1)
            end_date = timezone_today()

        self.instance.first_transaction_date = self.get_first_transaction()

        begin_date = self.instance.begin_date

        # if begin_date < first_transaction_date:
        #     begin_date = first_transaction_date

        _l.info('build_report.begin_date %s' % begin_date)
        _l.info('build_report.end_date %s' % end_date)

        if end_date < begin_date:
            end_date = begin_date

        self.instance.periods = self.get_periods(begin_date, end_date, self.instance.segmentation_type)

        cumulative_return = 0
        for period in self.instance.periods:

            if self.instance.calculation_type == 'time_weighted':
                table = self.build_time_weighted(period['date_from'], period['date_to'])

                for key, value in table.items():
                    period['items'].append(table[key])

                period = self.calculate_time_weighted_total_values(period)

            if self.instance.calculation_type == 'money_weighted':
                table = self.build_money_weighted(period['date_from'], period['date_to'])

                for key, value in table.items():
                    period['items'].append(table[key])

                period = self.calculate_money_weighted_total_values(period)

            period["cumulative_return"] = (cumulative_return + 1) * (period['total_return'] + 1) - 1

            cumulative_return = period["cumulative_return"]

        if self.instance.calculation_type == 'time_weighted':
            self.calculate_time_weighted_grand_total_values()

        if self.instance.calculation_type == 'money_weighted':
            self.calculate_money_weighted_grand_total_values()

        for period in self.instance.periods:
            for item in period['items']:

                for key, value in item['portfolios'].items():

                    result_dicts = []

                    for record in item['portfolios'][key]['records']:
                        record_json = model_to_dict(record)
                        result_dicts.append(record_json)

                    item['portfolios'][key]['records'] = result_dicts

        self.instance.items = []
        self.instance.raw_items = json.loads(json.dumps(self.instance.periods, indent=4, sort_keys=True, default=str))

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

        _l.info('items total %s' % len(self.instance.items))

        _l.info('build_st done: %s', "{:3.3f}".format(time.perf_counter() - st))

        self.add_data_items()

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

    def calculate_money_weighted_grand_total_values(self):

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

    def calculate_money_weighted_total_values(self, period):

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

        _l.info("Getting periods %s from %s to %s" % (self.instance.segmentation_type, date_from, date_to))

        result = []

        dates = get_list_of_business_days_between_two_dates(date_from, date_to)

        if segmentation_type == 'days':
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
            month_end = last_business_day_in_month(year, month)

            if month_end > timezone_today():
                month_end = timezone_today() - timedelta(days=1)

            month_start = datetime.date(year, month, 1) - timedelta(days=1)

            begin_date_year = begin_date.year
            begin_date_month = begin_date.month

            # previous_end_of_month_of_begin_date = datetime.date(begin_date_year, begin_date_month, 1) - timedelta(
            #     days=1)

            previous_end_of_month_of_begin_date = last_business_day_in_month(begin_date_year, begin_date_month)

            if month_start < previous_end_of_month_of_begin_date:
                month_start = previous_end_of_month_of_begin_date

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

        _l.info("result %s" % result)

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

        _l.info("build portfolio records")

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

        _l.info('build_time_weighted.result portfolios %s ' % portfolios)

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

        print('table %s' % table)

        return table

    def build_money_weighted(self, date_from, date_to):

        _l.info("build portfolio records")

        date_from_str = str(date_from)
        date_to_str = str(date_to)

        result = []

        dates_map = self.get_dict_of_dates_between_two_dates_with_order(date_from, date_to)

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

        _l.info('build_time_weighted.result portfolios %s ' % portfolios)

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

        # FILL START DATE START
        table[date_from_str] = {}
        table[date_from_str]['date'] = date_from_str
        table[date_from_str]['portfolios'] = {}
        table[date_from_str]['subtotal_cash_flow'] = 0
        table[date_from_str]['subtotal_cash_inflow'] = 0
        table[date_from_str]['subtotal_cash_outflow'] = 0
        table[date_from_str]['subtotal_cash_flow_weighted'] = 0
        table[date_from_str]['subtotal_nav'] = 0

        for portfolio_id in portfolios:

            nav = 0

            try:
                price_history = PriceHistory.objects.get(date=date_from,
                                                         instrument=portfolio_registers_map[
                                                             portfolio_id].linked_instrument,
                                                         pricing_policy=portfolio_registers_map[
                                                             portfolio_id].valuation_pricing_policy)

                fx_rate = 1

                if self.instance.report_currency.id == portfolio_registers_map[
                    portfolio_id].linked_instrument.pricing_currency.id:
                    fx_rate = 1
                else:
                    report_currency_fx_rate = None
                    instrument_pricing_currency_fx_rate = None

                    if self.instance.report_currency.id == self.ecosystem_defaults.currency.id:
                        report_currency_fx_rate = 1
                    else:
                        report_currency_fx_rate = CurrencyHistory.objects.get(date=date_from,
                                                                              currency=self.instance.report_currency,
                                                                              pricing_policy=portfolio_registers_map[
                                                                                  portfolio_id].valuation_pricing_policy).fx_rate
                    if portfolio_registers_map[
                        portfolio_id].linked_instrument.pricing_currency.id == self.ecosystem_defaults.currency.id:
                        instrument_pricing_currency_fx_rate = 1
                    else:
                        instrument_pricing_currency_fx_rate = CurrencyHistory.objects.get(date=date_from,
                                                                                          currency=
                                                                                          portfolio_registers_map[
                                                                                              portfolio_id].linked_instrument.pricing_currency,
                                                                                          pricing_policy=
                                                                                          portfolio_registers_map[
                                                                                              portfolio_id].valuation_pricing_policy).fx_rate

                    fx_rate = instrument_pricing_currency_fx_rate / report_currency_fx_rate

                nav = price_history.nav * fx_rate
            except Exception as e:
                _l.info("Money weighted date_from nav error %s" % e)
                nav = 0

            table[date_from_str]['portfolios'][portfolio_id] = {
                'portfolio_register': portfolio_registers_map[portfolio_id],
                'portfolio_id': portfolio_id,
                'transaction_date_str': date_from_str,
                'transaction_date': date_from,
                'cash_flow': 0,
                'cash_inflow': 0,
                'cash_outflow': 0,
                'cash_flow_weighted': nav * 1,
                'nav': nav,
                'records': []
            }

        # FILL START DATE END

        for record in records:

            transaction_date_str = str(record.transaction_date)

            if transaction_date_str not in table:
                table[transaction_date_str] = {}
                table[transaction_date_str]['date'] = transaction_date_str
                table[transaction_date_str]['portfolios'] = {}
                table[transaction_date_str]['subtotal_cash_flow'] = 0
                table[transaction_date_str]['subtotal_cash_inflow'] = 0
                table[transaction_date_str]['subtotal_cash_outflow'] = 0
                table[transaction_date_str]['subtotal_cash_flow_weighted'] = 0
                table[transaction_date_str]['subtotal_nav'] = 0

            if record.portfolio_id not in table[transaction_date_str]['portfolios']:
                table[transaction_date_str]['portfolios'][record.portfolio_id] = {
                    'portfolio_register': portfolio_registers_map[record.portfolio_id],
                    'portfolio_id': record.portfolio_id,
                    'transaction_date_str': transaction_date_str,
                    'transaction_date': record.transaction_date,
                    'cash_flow': 0,
                    'cash_inflow': 0,
                    'cash_outflow': 0,
                    'nav': 0,
                    'records': []
                }

            table[transaction_date_str]['portfolios'][record.portfolio_id]['records'].append(record)

        # FILL END DATE START

        table[date_to_str] = {}
        table[date_to_str]['date'] = date_to_str
        table[date_to_str]['portfolios'] = {}
        table[date_to_str]['subtotal_cash_flow'] = 0
        table[date_to_str]['subtotal_cash_inflow'] = 0
        table[date_to_str]['subtotal_cash_outflow'] = 0
        table[date_to_str]['subtotal_cash_flow_weighted'] = 0
        table[date_to_str]['subtotal_nav'] = 0

        for portfolio_id in portfolios:

            nav = 0

            try:
                price_history = PriceHistory.objects.get(date=date_to,
                                                         instrument=portfolio_registers_map[
                                                             portfolio_id].linked_instrument,
                                                         pricing_policy=portfolio_registers_map[
                                                             portfolio_id].valuation_pricing_policy)

                _l.info('price_history.nav %s' % price_history.nav)

                fx_rate = 1

                if self.instance.report_currency.id == portfolio_registers_map[
                    portfolio_id].linked_instrument.pricing_currency.id:
                    fx_rate = 1
                else:
                    report_currency_fx_rate = None
                    instrument_pricing_currency_fx_rate = None

                    if self.instance.report_currency.id == self.ecosystem_defaults.currency.id:
                        report_currency_fx_rate = 1

                    else:

                        report_currency_fx_rate = CurrencyHistory.objects.get(date=date_to,
                                                                              pricing_policy=portfolio_registers_map[
                                                                                  portfolio_id].valuation_pricing_policy,
                                                                              currency=self.instance.report_currency).fx_rate

                    if portfolio_registers_map[
                        portfolio_id].linked_instrument.pricing_currency.id == self.ecosystem_defaults.currency.id:
                        instrument_pricing_currency_fx_rate = 1

                    else:
                        instrument_pricing_currency_fx_rate = CurrencyHistory.objects.get(date=date_to,
                                                                                          pricing_policy=
                                                                                          portfolio_registers_map[
                                                                                              portfolio_id].valuation_pricing_policy,
                                                                                          currency=
                                                                                          portfolio_registers_map[
                                                                                              portfolio_id].linked_instrument.pricing_currency).fx_rate

                    fx_rate = instrument_pricing_currency_fx_rate / report_currency_fx_rate

                nav = price_history.nav * fx_rate

            except Exception as e:
                _l.error("end date nav e %s" % e)
                nav = 0

            table[date_to_str]['portfolios'][portfolio_id] = {
                'portfolio_register': portfolio_registers_map[portfolio_id],
                'portfolio_id': portfolio_id,
                'transaction_date_str': date_to_str,
                'transaction_date': date_to,
                'cash_flow': 0,
                'cash_inflow': 0,
                'cash_outflow': 0,
                'cash_flow_weighted': 0,
                'previous_nav': 0,
                'nav': nav,
                'records': []
            }

        # FILL END DATE END

        # print('table %s '  % table)

        # create empty structure end

        # Fill with Data

        for key, value in table.items():

            item_date = table[key]

            if key != date_to_str and key != date_from_str:

                for _key, _value in item_date['portfolios'].items():

                    item = item_date['portfolios'][_key]

                    nav = 0

                    try:
                        price_history = PriceHistory.objects.get(date=item['transaction_date'],
                                                                 instrument=item[
                                                                     'portfolio_register'].linked_instrument,
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
                    except Exception as e:
                        nav = 0

                    cash_flow = 0
                    cash_inflow = 0
                    cash_outflow = 0

                    for record in item['records']:

                        fx_rate = 1

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

                        cash_flow = cash_flow + record.cash_amount_valuation_currency * fx_rate

                        if record.transaction_class_id in [TransactionClass.CASH_INFLOW, TransactionClass.INJECTION]:
                            cash_inflow = cash_inflow + record.cash_amount_valuation_currency * fx_rate

                        if record.transaction_class_id in [TransactionClass.CASH_OUTFLOW, TransactionClass.DISTRIBUTION]:
                            cash_outflow = cash_outflow + record.cash_amount_valuation_currency * fx_rate

                    date_n = dates_map[item['transaction_date_str']]
                    date_to_n = dates_map[str(date_to)]
                    date_from_n = dates_map[str(date_from)]

                    time_weight = (date_to_n - date_n) / (date_to_n - date_from_n)

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

                    item['cash_flow_weighted'] = cash_flow * time_weight
                    item['nav'] = nav

            else:
                print("Skip %s " % key)

        #  Calculate subtotals

        for key, value in table.items():

            item_date = table[key]

            for _key, _value in item_date['portfolios'].items():
                item = item_date['portfolios'][_key]

                item_date['subtotal_nav'] = item_date['subtotal_nav'] + item['nav']

                item_date['subtotal_cash_flow'] = item_date['subtotal_cash_flow'] + item['cash_flow']
                item_date['subtotal_cash_inflow'] = item_date['subtotal_cash_inflow'] + item['cash_inflow']
                item_date['subtotal_cash_outflow'] = item_date['subtotal_cash_outflow'] + item['cash_outflow']

                item_date['subtotal_cash_flow_weighted'] = item_date['subtotal_cash_flow_weighted'] + item[
                    'cash_flow_weighted']

        return table

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
        ).defer('object_permissions', 'responsibles', 'counterparties', 'transaction_types', 'accounts') \
            .filter(master_user=self.instance.master_user) \
            .filter(
            id__in=ids)

    def add_data_items_accounts(self, ids):

        self.instance.item_accounts = Account.objects.prefetch_related(
            'attributes',
            'attributes__attribute_type',
            'attributes__classifier',
        ).defer('object_permissions').filter(master_user=self.instance.master_user).filter(id__in=ids)

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
        ).defer('object_permissions').filter(master_user=self.instance.master_user).filter(id__in=ids)

    def add_data_items_strategies2(self, ids):
        self.instance.item_strategies2 = Strategy2.objects.prefetch_related(
            'attributes',
            'attributes__attribute_type',
            'attributes__classifier',
        ).defer('object_permissions').filter(master_user=self.instance.master_user).filter(id__in=ids)

    def add_data_items_strategies3(self, ids):
        self.instance.item_strategies3 = Strategy3.objects.prefetch_related(
            'attributes',
            'attributes__attribute_type',
            'attributes__classifier',
        ).defer('object_permissions').filter(master_user=self.instance.master_user).filter(id__in=ids)

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

        self.instance.custom_fields = BalanceReportCustomField.objects.filter(master_user=self.instance.master_user)

        _l.info('_refresh_with_perms_optimized item relations done: %s',
                "{:3.3f}".format(time.perf_counter() - item_relations_st))

        # _l.info('add_data_items_strategies1 %s ' % self.instance.item_strategies1)
