import datetime
import json
import logging
import time
from datetime import timedelta
import calendar

from django.db import connection
from django.views.generic.dates import timezone_today
from rest_framework.exceptions import APIException

from poms.accounts.models import Account
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
        _l.info('self.instance report_date %s' % self.instance.report_date)

    def build_report(self):
        st = time.perf_counter()

        self.instance.items = []

        if self.instance.calculation_type == 'time_weighted':
            self.build_time_weighted()

        if self.instance.calculation_type == 'money_weighted':
            self.build_money_weighted()

        _l.info('items total %s' % len(self.instance.items))

        _l.info('build_st done: %s', "{:3.3f}".format(time.perf_counter() - st))

        self.add_data_items()

        return self.instance

    def format_to_months(self, table):

        result = []

        result_obj = {}

        for key, value in table.items():

            date_pieces = key.split('-')

            year = int(date_pieces[0])
            month = int(date_pieces[1])

            year_month = str(year) + '-' + str(month)

            if year_month not in result_obj:
                result_obj[year_month] = {
                    'date_from': datetime.date(year, month, 1),
                    'date_to': calendar.monthrange(year, month)[1],
                    'items': [],
                    'grand_nav': 0,
                    'grand_return': 0
                }

            result_obj[year_month]['items'].append(table[key])


        for key, value in result_obj.items():

            grand_nav = 0
            grand_return = 1

            for item in result_obj[key]['items']:

                grand_nav = item['total_nav']

                grand_return = grand_return * ( item['total_return'] + 1)

            grand_return = grand_return - 1

            result_obj[key]['grand_nav'] = grand_nav
            result_obj[key]['grand_return'] = grand_return

            result.append(result_obj[key])

        return result

    def format_to_weeks(self, table):

        result = []

        return result

    def format_to_days(self, table):

        result = []

        for key, value in table.items():

            result_item = {}

            result_item['date_from'] = key
            result_item['date_to'] = key
            result_item['items'] = [table[key]]
            result_item['grand_nav'] = table[key]['total_nav']
            result_item['grand_return'] = table[key]['total_return']

            result.append(result_item)

        return result

    def build_time_weighted(self):

        _l.info("build portfolio records")

        result = []

        self.instance.bunch_portfolios = self.instance.registers  # instruments #debug szhitenev fund

        portfolio_registers = PortfolioRegister.objects.filter(master_user=self.instance.master_user,
                                                               linked_instrument__in=self.instance.bunch_portfolios)

        portfolio_registers_map = {}

        portfolios = []

        for portfolio_register in portfolio_registers:
            portfolios.append(portfolio_register.portfolio_id)
            portfolio_registers_map[portfolio_register.portfolio_id] = portfolio_register

        end_date = self.instance.end_date

        if self.instance.end_date > timezone_today():
            end_date = timezone_today() - timedelta(days=1)
            # end_date = timezone_today() + timedelta(days=30)

        _l.info('end_date %s' % end_date)

        begin_date_str = str(self.instance.begin_date)
        end_date_str = str(end_date)


        transactions = Transaction.objects.filter(portfolio__in=portfolios,
                                                  accounting_date__lte=end_date,
                                                  accounting_date__gte=self.instance.begin_date,
                                                  transaction_class__in=[TransactionClass.CASH_INFLOW,
                                                                         TransactionClass.CASH_OUTFLOW,
                                                                         TransactionClass.INJECTION,
                                                                         TransactionClass.DISTRIBUTION]).order_by(
            'accounting_date')

        table = {}

        for trn in transactions:

            accounting_date_str = str(trn.accounting_date)

            if accounting_date_str not in table:
                table[accounting_date_str] = {}
                table[accounting_date_str]['portfolios'] = {}
                table[accounting_date_str]['total_nav'] = 0
                table[accounting_date_str]['total_return'] = 0

            if trn.portfolio_id not in table[accounting_date_str]['portfolios']:
                table[accounting_date_str]['portfolios'][trn.portfolio_id] = {
                    'portfolio_register': portfolio_registers_map[trn.portfolio_id],
                    'portfolio_id': trn.portfolio_id,
                    'accounting_date_str': accounting_date_str,
                    'accounting_date': trn.accounting_date,
                    'cash_in_out': 0,
                    'previous_nav': 0,
                    'nav': 0,
                    'instrument_return': 0,
                    'transactions': []
                }

            table[accounting_date_str]['portfolios'][trn.portfolio_id]['transactions'].append(trn)

        previous_date = None

        if begin_date_str not in table:
            table[begin_date_str] = {}
            table[begin_date_str]['portfolios'] = {}
            table[begin_date_str]['total_nav'] = 0
            table[begin_date_str]['total_return'] = 0

            for portfolio_id in portfolios:
                table[begin_date_str]['portfolios'][portfolio_id] = {
                    'portfolio_register': portfolio_registers_map[portfolio_id],
                    'portfolio_id': portfolio_id,
                    'accounting_date_str': begin_date_str,
                    'accounting_date': self.instance.begin_date,
                    'cash_in_out': 0,
                    'previous_nav': 0,
                    'nav': 0,
                    'instrument_return': 0,
                    'transactions': []
                }


        if end_date_str not in table:
            table[end_date_str] = {}
            table[end_date_str]['portfolios'] = {}
            table[end_date_str]['total_nav'] = 0
            table[end_date_str]['total_return'] = 0

            for portfolio_id in portfolios:
                table[end_date_str]['portfolios'][portfolio_id] = {
                    'portfolio_register': portfolio_registers_map[portfolio_id],
                    'portfolio_id': portfolio_id,
                    'accounting_date_str': end_date_str,
                    'accounting_date': end_date,
                    'cash_in_out': 0,
                    'previous_nav': 0,
                    'nav': 0,
                    'instrument_return': 0,
                    'transactions': []
                }

        for key, value in table.items():

            item_date = table[key]

            for _key, _value in item_date['portfolios'].items():

                item = item_date['portfolios'][_key]

                nav = 0

                try:
                    price_history = PriceHistory.objects.get(date=item['accounting_date'],
                                                             instrument=item['portfolio_register'].linked_instrument,
                                                             pricing_policy=item[
                                                                 'portfolio_register'].valuation_pricing_policy)

                    nav = price_history.nav
                except Exception as e:
                    nav = 0

                previous_nav = 0
                previous_nav_date = None
                if previous_date:
                    previous_nav = previous_date['portfolios'][_key]['nav']
                    previous_nav_date = previous_date['portfolios'][_key]['accounting_date']



                cash_in_out = 0

                for trn in item['transactions']:

                    fx_rate = 0

                    if trn.transaction_currency_id == item['portfolio_register'].valuation_currency_id:
                        fx_rate = 1
                    else:
                        try:

                            valuation_ccy_fx_rate = CurrencyHistory.objects.get(currency_id=item['portfolio_register'].valuation_currency_id,
                                                                                date=trn.transaction_date).fx_rate
                            cash_ccy_fx_rate = CurrencyHistory.objects.get(currency_id=trn.settlement_currency_id,
                                                                           date=trn.transaction_date).fx_rate

                            fx_rate = valuation_ccy_fx_rate / cash_ccy_fx_rate

                        except Exception:
                            fx_rate = 0

                    cash_in_out = cash_in_out + trn.cash_consideration * fx_rate

                instrument_return = 0

                if previous_nav:
                    instrument_return = (nav - cash_in_out - previous_nav) / previous_nav
                else:
                    instrument_return = 0

                item['nav'] = nav
                item['cash_in_out'] = cash_in_out
                item['previous_nav'] = previous_nav
                item['previous_nav_date'] = previous_nav_date
                item['instrument_return'] = instrument_return

            # Calculate nav
            for _key, _value in item_date['portfolios'].items():

                item = item_date['portfolios'][_key]

                item_date['total_nav'] = item_date['total_nav'] + item['nav']

                # Return[k,i] * NAV[k,i-1] / Total_NAV[i-1]

                if previous_date and previous_date['total_nav']:
                    item_date['total_return'] = item_date['total_return'] + (
                                item['instrument_return'] * item['previous_nav'] / previous_date['total_nav'])

            previous_date = item_date

        print('table %s' % table)

        result_table = []

        _l.info('self.instance.segmentation_type %s' % self.instance.segmentation_type)

        if self.instance.segmentation_type == 'days':
            result_table = self.format_to_days(table)

        if self.instance.segmentation_type == 'weeks':
            result_table = self.format_to_weeks(table)

        if self.instance.segmentation_type == 'months':
            result_table = self.format_to_months(table)


        self.instance.items = []
        self.instance.raw_items = json.loads(json.dumps(result_table, indent=4, sort_keys=True, default=str))

    def build_money_weighted(self):

        _l.info("build portfolio records")

        result = []

        self.instance.bunch_portfolios = [44]  # instruments #debug szhitenev fund

        portfolio_registers = PortfolioRegister.objects.filter(master_user=self.instance.master_user,
                                                               linked_instrument__in=self.instance.bunch_portfolios)

        portfolio_registers_map = {}

        portfolios = []

        for portfolio_register in portfolio_registers:
            portfolios.append(portfolio_register.portfolio_id)
            portfolio_registers_map[portfolio_register.portfolio_id] = portfolio_register

        transactions = Transaction.objects.filter(portfolio__in=portfolios,
                                                  transaction_class__in=[TransactionClass.CASH_INFLOW,
                                                                         TransactionClass.CASH_OUTFLOW,
                                                                         TransactionClass.INJECTION,
                                                                         TransactionClass.DISTRIBUTION]).order_by(
            'accounting_date')

        table = {}

        for trn in transactions:

            accounting_date_str = str(trn.accounting_date)

            if accounting_date_str not in table:
                table[accounting_date_str] = {}
                table[accounting_date_str]['portfolios'] = {}
                table[accounting_date_str]['total_nav'] = 0
                table[accounting_date_str]['total_return'] = 0

            if trn.portfolio_id not in table[accounting_date_str]['portfolios']:
                table[accounting_date_str]['portfolios'][trn.portfolio_id] = {
                    'portfolio_register': portfolio_registers_map[trn.portfolio_id],
                    'portfolio_id': trn.portfolio_id,
                    'accounting_date_str': accounting_date_str,
                    'accounting_date': trn.accounting_date,
                    'cash_in_out': 0,
                    'previous_nav': 0,
                    'nav': 0,
                    'instrument_return': 0,
                    'transactions': []
                }

            table[accounting_date_str]['portfolios'][trn.portfolio_id]['transactions'].append(trn)

        previous_date = None

        for key, value in table.items():

            item_date = table[key]

            for _key, _value in item_date['portfolios'].items():

                item = item_date['portfolios'][_key]

                price_history = PriceHistory.objects.get(date=item['accounting_date'],
                                                         instrument=item['portfolio_register'].linked_instrument,
                                                         pricing_policy=item[
                                                             'portfolio_register'].valuation_pricing_policy)

                previous_nav = 0
                previous_nav_date = None
                if previous_date:
                    previous_nav = previous_date['portfolios'][_key]['nav']
                    previous_nav_date = previous_date['portfolios'][_key]['accounting_date']

                nav = price_history.nav

                cash_in_out = 0

                for trn in item['transactions']:
                    cash_in_out = cash_in_out + trn.cash_consideration  # TODO add fx conversion?

                instrument_return = 0

                if previous_nav:
                    instrument_return = (nav - cash_in_out - previous_nav) / previous_nav
                else:
                    instrument_return = 0

                item['nav'] = nav
                item['cash_in_out'] = cash_in_out
                item['previous_nav'] = previous_nav
                item['previous_nav_date'] = previous_nav_date
                item['instrument_return'] = instrument_return

            # Calculate nav
            for _key, _value in item_date['portfolios'].items():

                item = item_date['portfolios'][_key]

                item_date['total_nav'] = item_date['total_nav'] + item['nav']

                # Return[k,i] * NAV[k,i-1] / Total_NAV[i-1]

                if previous_date:
                    item_date['total_return'] = item_date['total_return'] + (
                                item['instrument_return'] * item['previous_nav'] / previous_date['total_nav'])

            previous_date = item_date

        print('table %s' % table)

        self.instance.items = []
        self.instance.raw_items = json.loads(json.dumps(table, indent=4, sort_keys=True, default=str))

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
        ).defer('object_permissions', 'responsibles', 'counterparties', 'transaction_types', 'accounts', 'tags') \
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
