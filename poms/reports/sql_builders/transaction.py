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


class TransactionReportBuilderSql:

    def __init__(self, instance=None):

        _l.debug('ReportBuilderSql init')

        self.instance = instance

        self.ecosystem_defaults = EcosystemDefault.objects.get(master_user=self.instance.master_user)

        _l.info('self.instance master_user %s' % self.instance.master_user)
        _l.info('self.instance begin_date %s' % self.instance.begin_date)
        _l.info('self.instance end_date %s' % self.instance.end_date)

    def build_transaction(self):
        st = time.perf_counter()

        self.instance.items = []

        self.build_items()

        _l.info('items total %s' % len(self.instance.items))

        _l.info('build_st done: %s', "{:3.3f}".format(time.perf_counter() - st))

        self.add_data_items()

        return self.instance

    def build_items(self):

        _l.info("build items")

        with connection.cursor() as cursor:

            query = """
                SELECT
                  * 
                FROM transactions_transaction
                WHERE transaction_date >= %s AND transaction_date <= %s AND master_user_id = %s
            """

            cursor.execute(query, [self.instance.begin_date,  self.instance.end_date, self.instance.master_user.id])

            result = dictfetchall(cursor)

            _l.info('build cash result %s ' % len(result))

            self.instance.items = result

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
            'attributes__attribute_type'
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

            portfolio_ids.append(item['portfolio_id'])

            instrument_ids.append(item['instrument_id'])
            instrument_ids.append(item['allocation_balance_id'])
            instrument_ids.append(item['allocation_pl_id'])
            instrument_ids.append(item['linked_instrument_id'])

            account_ids.append(item['account_position_id'])
            account_ids.append(item['account_cash_id'])

            currencies_ids.append(item['settlement_currency_id'])
            currencies_ids.append(item['transaction_currency_id'])


        self.add_data_items_instruments(instrument_ids)
        self.add_data_items_portfolios(portfolio_ids)
        self.add_data_items_accounts(account_ids)
        self.add_data_items_currencies(currencies_ids)

        self.instance.custom_fields = BalanceReportCustomField.objects.filter(master_user=self.instance.master_user)

        _l.debug('_refresh_with_perms_optimized item relations done: %s', "{:3.3f}".format(time.perf_counter() - item_relations_st))
