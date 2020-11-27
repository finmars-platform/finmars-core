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
from poms.reports.sql_builders.helpers import dictfetchall
from poms.transactions.models import ComplexTransaction
from poms.users.models import EcosystemDefault

_l = logging.getLogger('poms.reports')


class TransactionReportBuilderSql:

    def __init__(self, instance=None):

        _l.debug('ReportBuilderSql init')

        self.instance = instance

        self.ecosystem_defaults = EcosystemDefault.objects.get(master_user=self.instance.master_user)

        _l.debug('self.instance master_user %s' % self.instance.master_user)
        _l.debug('self.instance begin_date %s' % self.instance.begin_date)
        _l.debug('self.instance end_date %s' % self.instance.end_date)

    def build_transaction(self):
        st = time.perf_counter()

        self.instance.items = []

        self.build_items()

        _l.debug('items total %s' % len(self.instance.items))

        _l.debug('build_st done: %s', "{:3.3f}".format(time.perf_counter() - st))

        self.add_data_items()

        return self.instance

    def build_items(self):

        _l.debug("build items")

        with connection.cursor() as cursor:

            query = """
                SELECT
                  -- transaction fields
                  t.*,
                  -- complex transaction fields
                  tc.status as complex_transaction_status,
                  tc.code as complex_transaction_code,
                  tc.text as complex_transaction_text,
                  tc.date as complex_transaction_date,
                  -- complex transaction user fields
                  tc.user_text_1 as complex_transaction_user_text_1,
                  tc.user_text_2 as complex_transaction_user_text_2,
                  tc.user_text_3 as complex_transaction_user_text_3,
                  tc.user_text_4 as complex_transaction_user_text_4,
                  tc.user_text_5 as complex_transaction_user_text_5,
                  tc.user_text_6 as complex_transaction_user_text_6,
                  tc.user_text_7 as complex_transaction_user_text_7,
                  tc.user_text_8 as complex_transaction_user_text_8,
                  tc.user_text_9 as complex_transaction_user_text_9,
                  tc.user_text_10 as complex_transaction_user_text_10,
                  tc.user_text_11 as complex_transaction_user_text_11,
                  tc.user_text_12 as complex_transaction_user_text_12,
                  tc.user_text_13 as complex_transaction_user_text_13,
                  tc.user_text_14 as complex_transaction_user_text_14,
                  tc.user_text_15 as complex_transaction_user_text_15,
                  tc.user_text_16 as complex_transaction_user_text_16,
                  tc.user_text_17 as complex_transaction_user_text_17,
                  tc.user_text_18 as complex_transaction_user_text_18,
                  tc.user_text_19 as complex_transaction_user_text_19,
                  tc.user_text_20 as complex_transaction_user_text_20,
                  
                  tc.user_number_1 as complex_transaction_user_number_1,
                  tc.user_number_2 as complex_transaction_user_number_2,
                  tc.user_number_3 as complex_transaction_user_number_3,
                  tc.user_number_4 as complex_transaction_user_number_4,
                  tc.user_number_5 as complex_transaction_user_number_5,
                  tc.user_number_6 as complex_transaction_user_number_6,
                  tc.user_number_7 as complex_transaction_user_number_7,
                  tc.user_number_8 as complex_transaction_user_number_8,
                  tc.user_number_9 as complex_transaction_user_number_9,
                  tc.user_number_10 as complex_transaction_user_number_10,
                  tc.user_number_11 as complex_transaction_user_number_11,
                  tc.user_number_12 as complex_transaction_user_number_12,
                  tc.user_number_13 as complex_transaction_user_number_13,
                  tc.user_number_14 as complex_transaction_user_number_14,
                  tc.user_number_15 as complex_transaction_user_number_15,
                  tc.user_number_16 as complex_transaction_user_number_16,
                  tc.user_number_17 as complex_transaction_user_number_17,
                  tc.user_number_18 as complex_transaction_user_number_18,
                  tc.user_number_19 as complex_transaction_user_number_19,
                  tc.user_number_20 as complex_transaction_user_number_20,
                  
                  tc.user_date_1 as complex_transaction_user_date_1,
                  tc.user_date_2 as complex_transaction_user_date_2,
                  tc.user_date_3 as complex_transaction_user_date_3,
                  tc.user_date_4 as complex_transaction_user_date_4,
                  tc.user_date_5 as complex_transaction_user_date_5,
                  
                  -- complex transaction transaction type fields
                  tt.id as transaction_type_id,
                  tt.user_code as transaction_type_user_code,
                  tt.name as transaction_type_name,
                  tt.short_name as transaction_type_short_name,
                  -- complex transaction transaction type group fields
                  tt2.name as transaction_type_group_name
                FROM transactions_transaction as t
                LEFT JOIN transactions_complextransaction tc on t.complex_transaction_id = tc.id
                LEFT JOIN transactions_transactiontype tt on tc.transaction_type_id = tt.id
                LEFT JOIN transactions_transactiontypegroup tt2 on tt.group_id = tt2.id
                WHERE t.transaction_date >= %s AND t.transaction_date <= %s AND t.master_user_id = %s
                
            """

            cursor.execute(query, [self.instance.begin_date, self.instance.end_date, self.instance.master_user.id])

            result = dictfetchall(cursor)

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
            'attributes__classifier',
        ).filter(master_user=self.instance.master_user) \
            .filter(id__in=ids)

    def add_data_items_portfolios(self, ids):

        self.instance.item_portfolios = Portfolio.objects.prefetch_related(
            'attributes',
            'attributes__attribute_type',
                 'attributes__classifier',
        ).defer('object_permissions', 'responsibles', 'counterparties', 'transaction_types', 'accounts', 'tags') \
            .filter(master_user=self.instance.master_user)\
            .filter(
            id__in=ids)

    def add_data_items_accounts(self, ids):

        self.instance.item_accounts = Account.objects.select_related('type').prefetch_related(
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

    def add_data_items_complex_transactions(self, ids):

        self.instance.item_complex_transactions = ComplexTransaction.objects.prefetch_related(
            'transaction_type',
            'transaction_type__group',
            'attributes',
            'attributes__attribute_type',
            'attributes__classifier'
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

        complex_transactions_ids = []

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

            # if item['complex_transaction_id'] not in complex_transactions_ids:
            #     complex_transactions_ids.append(item['complex_transaction_id'])


        self.add_data_items_instruments(instrument_ids)
        self.add_data_items_portfolios(portfolio_ids)
        self.add_data_items_accounts(account_ids)
        self.add_data_items_currencies(currencies_ids)
        # self.add_data_items_complex_transactions(complex_transactions_ids)  # too slow

        self.instance.custom_fields = BalanceReportCustomField.objects.filter(master_user=self.instance.master_user)

        _l.debug('_refresh_with_perms_optimized item relations done: %s', "{:3.3f}".format(time.perf_counter() - item_relations_st))
