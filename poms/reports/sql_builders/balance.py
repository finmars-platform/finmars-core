import logging
import time

from django.db import connection

from poms.accounts.models import Account
from poms.currencies.models import Currency
from poms.instruments.models import Instrument
from poms.portfolios.models import Portfolio
from poms.reports.builders.balance_item import Report
from poms.reports.builders.base_builder import BaseReportBuilder
from poms.reports.models import BalanceReportCustomField
from poms.users.models import EcosystemDefault

_l = logging.getLogger('poms.reports')

def dictfetchall(cursor):
    "Return all rows from a cursor as a dict"
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]

class ReportBuilderSql:

    def __init__(self, instance=None):

        _l.debug('ReportBuilderSql init')

        self.instance = instance

        self.ecosystem_defaults = EcosystemDefault.objects.get(master_user=self.instance.master_user)

        _l.info('self.instance master_user %s' % self.instance.master_user)
        _l.info('self.instance report_date %s' % self.instance.report_date)



    def build_balance(self):
        st = time.perf_counter()

        self.instance.items = []

        self.build_positions()
        self.build_cash()

        _l.info('items total %s' % len(self.instance.items))

        _l.debug('build_st done: %s', "{:3.3f}".format(time.perf_counter() - st))

        self.add_data_items()

        return self.instance

    def get_position_consolidation_for_select(self):

        result = []

        if self.instance.portfolio_mode == Report.MODE_INDEPENDENT:
            result.append("portfolio_id")

        if self.instance.account_mode == Report.MODE_INDEPENDENT:
            result.append("account_position_id")

        if self.instance.strategy1_mode == Report.MODE_INDEPENDENT:
            result.append("strategy1_position_id")

        if self.instance.strategy2_mode == Report.MODE_INDEPENDENT:
            result.append("strategy2_position_id")

        if self.instance.strategy3_mode == Report.MODE_INDEPENDENT:
            result.append("strategy3_position_id")

        resultString = ''

        if len(result):
            resultString = ", ".join(result) + ', '

        return resultString

    def build_positions(self):

        _l.info("build positions")

        with connection.cursor() as cursor:

            consolidated_select_columns = self.get_position_consolidation_for_select()

            query = """
                CREATE or REPLACE VIEW balance_position_consolidation_matrix AS
                SELECT
                  portfolio_id,
                  account_position_id,
                  strategy1_position_id,
                  strategy2_position_id,
                  strategy3_position_id,
                  instrument_id,
                  SUM(position_size_with_sign) as position_size
                FROM transactions_transaction WHERE transaction_date <= %s AND master_user_id = %s
                GROUP BY
                  portfolio_id,
                  account_position_id,
                  strategy1_position_id,
                  strategy2_position_id,
                  strategy3_position_id,
                  instrument_id;
            """

            cursor.execute(query, [self.instance.report_date, self.instance.master_user.id])

            _l.info("create or replace balance_position_consolidation_matrix")

            query = """
                SELECT 
                    t.*, 
                    
                    i.name,
                    i.short_name,
                    i.user_code,
                    i.pricing_currency_id,
                    
                    (t.position_size * iph.principal_price * i.price_multiplier * cch.fx_rate + (t.position_size * iph.accrued_price * cch.fx_rate * 1 * i.accrued_multiplier)) as market_value
                FROM 
                    (SELECT
                      """ + consolidated_select_columns + """
                      instrument_id,
                      SUM(position_size) as position_size
                    FROM balance_position_consolidation_matrix
                    GROUP BY
                      """ + consolidated_select_columns + """
                      instrument_id) as t
                LEFT JOIN instruments_instrument as i
                ON t.instrument_id = i.id
                LEFT JOIN instruments_pricehistory as iph
                ON t.instrument_id = iph.instrument_id
                LEFT JOIN currencies_currencyhistory as cch
                ON i.pricing_currency_id = cch.currency_id
                WHERE cch.date = %s AND iph.date = %s AND cch.pricing_policy_id = %s;
            """

            cursor.execute(query, [self.instance.report_date, self.instance.report_date, self.instance.pricing_policy.id])

            _l.info("fetch position data")

            result = dictfetchall(cursor)

            ITEM_INSTRUMENT = 1

            for item in result:
                item['item_type'] = ITEM_INSTRUMENT
                item['item_type_code'] = "INSTR"
                item['item_type_name'] = "Instrument"

                if "portfolio_id" not in item:
                    item['portfolio_id'] = self.ecosystem_defaults.portfolio_id

                if "account_position__id" not in item:
                    item['account_position_id'] = self.ecosystem_defaults.account_id

                if "strategy1_position_id" not in item:
                    item['strategy1_position_id'] = self.ecosystem_defaults.strategy1_id

                if "strategy2_position_id" not in item:
                    item['strategy2_position_id'] = self.ecosystem_defaults.strategy2_id

                if "strategy3_position_id" not in item:
                    item['strategy3_position_id'] = self.ecosystem_defaults.strategy3_id

            _l.info('build position result %s ' % len(result))

            self.instance.items = self.instance.items + result

    def get_cash_consolidation_for_select(self):

        result = []

        if self.instance.portfolio_mode == Report.MODE_INDEPENDENT:
            result.append("portfolio_id")

        if self.instance.account_mode == Report.MODE_INDEPENDENT:
            result.append("account_cash_id")

        if self.instance.strategy1_mode == Report.MODE_INDEPENDENT:
            result.append("strategy1_cash_id")

        if self.instance.strategy2_mode == Report.MODE_INDEPENDENT:
            result.append("strategy2_cash_id")

        if self.instance.strategy3_mode == Report.MODE_INDEPENDENT:
            result.append("strategy3_cash_id")

        resultString = ''

        if len(result):
            resultString = ", ".join(result) + ', '

        return resultString

    def build_cash(self):

        _l.info("build cash")

        with connection.cursor() as cursor:

            consolidated_select_columns = self.get_cash_consolidation_for_select()

            query = """
                CREATE or REPLACE VIEW balance_cash_consolidation_matrix AS
                SELECT
                  portfolio_id,
                  account_cash_id,
                  strategy1_cash_id,
                  strategy2_cash_id,
                  strategy3_cash_id,
                  settlement_currency_id,
                  SUM(cash_consideration) as position_size
                FROM transactions_transaction
                WHERE transaction_date <= %s AND master_user_id = %s
                GROUP BY
                  portfolio_id,
                  account_cash_id,
                  strategy1_cash_id,
                  strategy2_cash_id,
                  strategy3_cash_id,
                  settlement_currency_id;
            """

            cursor.execute(query, [self.instance.report_date, self.instance.master_user.id])

            query = """
                SELECT 
                    t.*, 
                    c.name,
                    c.short_name,
                    c.user_code,
                    
                    (t.position_size * cch.fx_rate) as market_value
                FROM 
                    (SELECT
                      """ + consolidated_select_columns + """
                      settlement_currency_id,
                      SUM(position_size) as position_size
                    FROM balance_cash_consolidation_matrix
                    GROUP BY
                      """ + consolidated_select_columns + """
                      settlement_currency_id) AS t
                LEFT JOIN currencies_currency as c
                ON t.settlement_currency_id = c.id
                LEFT JOIN currencies_currencyhistory as cch
                ON t.settlement_currency_id = cch.currency_id
                WHERE cch.date = %s AND cch.pricing_policy_id = %s;
            """

            cursor.execute(query, [self.instance.report_date, self.instance.pricing_policy.id])

            result = dictfetchall(cursor)

            ITEM_CURRENCY = 2

            for item in result:
                item["item_type"] = ITEM_CURRENCY
                item["item_type_code"] = "CCY"
                item["item_type_name"] = "Currency"

                item["currency_id"] = item["settlement_currency_id"]

                if "portfolio_id" not in item:
                    item["portfolio_id"] = self.ecosystem_defaults.portfolio_id

                if "account_cash_id" not in item:
                    item["account_cash_id"] = self.ecosystem_defaults.account_id

                if "strategy1_cash_id" not in item:
                    item["strategy1_cash_id"] = self.ecosystem_defaults.strategy1_id

                if "strategy2_cash_id" not in item:
                    item["strategy2_cash_id"] = self.ecosystem_defaults.strategy2_id

                if "strategy3_cash_id" not in item:
                    item["strategy3_cash_id"] = self.ecosystem_defaults.strategy3_id

            _l.info('build cash result %s ' % len(result))

            self.instance.items = self.instance.items + result

    def add_data_items_instruments(self, ids):

        self.instance.item_instruments = Instrument.objects.select_related(
            'instrument_type',
            'instrument_type__instrument_class',
            'pricing_currency',
            'accrued_currency',
            'payment_size_detail',
            'daily_pricing_model',
            'price_download_scheme',
            'price_download_scheme__provider',
        ).prefetch_related(
            'attributes',
            'attributes__attribute_type',
        ).filter(master_user=self.instance.master_user) \
            .filter(id__in=ids)

    def add_data_items_portfolios(self, ids):

        self.instance.item_portfolios = Portfolio.objects.prefetch_related(
            'attributes'
        ).defer('object_permissions', 'responsibles', 'counterparties', 'transaction_types', 'accounts', 'tags') \
            .filter(master_user=self.instance.master_user)\
            .filter(
            id__in=ids)

    def add_data_items_accounts(self, ids):

        self.instance.item_accounts = Account.objects.select_related('type').prefetch_related(
            'attributes',
        ).defer('object_permissions').filter(master_user=self.instance.master_user).filter(id__in=ids)

    def add_data_items_currencies(self, ids):

        self.instance.item_currencies = Currency.objects.prefetch_related(
            'attributes',
        ).filter(master_user=self.instance.master_user).filter(id__in=ids)

    def add_data_items(self):

        instance_relations_st = time.perf_counter()

        _l.debug('_refresh_with_perms_optimized instance relations done: %s',
                 "{:3.3f}".format(time.perf_counter() - instance_relations_st))

        permissions_st = time.perf_counter()

        _l.debug('_refresh_with_perms_optimized permissions done: %s', "{:3.3f}".format(time.perf_counter() - permissions_st))

        item_relations_st = time.perf_counter()

        instrument_ids = []
        portfolio_ids = []
        account_ids = []
        currencies_ids = []

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

        self.add_data_items_instruments(instrument_ids)
        self.add_data_items_portfolios(portfolio_ids)
        self.add_data_items_accounts(account_ids)
        self.add_data_items_currencies(currencies_ids)

        self.instance.custom_fields = BalanceReportCustomField.objects.filter(master_user=self.instance.master_user)

        _l.debug('_refresh_with_perms_optimized item relations done: %s', "{:3.3f}".format(time.perf_counter() - item_relations_st))
