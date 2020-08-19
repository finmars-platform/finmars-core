import logging
import time
from collections import defaultdict

from django.db import transaction
from django.db.models import Q

from poms.common.utils import force_qs_evaluation
from poms.obj_attrs.models import GenericAttributeType
from poms.obj_attrs.utils import get_attributes_prefetch
from poms.reports.builders.base_builder import BaseReportBuilder
from poms.reports.builders.transaction_item import TransactionReportItem
from poms.reports.models import BalanceReportCustomField, TransactionReportCustomField
from poms.transactions.models import Transaction, ComplexTransaction

_l = logging.getLogger('poms.reports')


class TransactionReportBuilder(BaseReportBuilder):
    def __init__(self, instance):
        super(TransactionReportBuilder, self).__init__(instance)

        self._transactions = []
        self._items = []

        self._similar_cache = defaultdict(dict)

        # self._complex_transactions = {}
        # self._transaction_types = {}
        # self._transaction_classes = {}
        # self._instruments = {}
        # self._currencies = {}
        # self._portfolios ={}
        # self._accounts = {}
        # self._strategies1 = {}
        # self._strategies2 = {}
        # self._strategies3 = {}
        # self._responsibles = {}
        # self._counterparties = {}
        # self._attribute_types = {}

    def build(self):
        st = time.perf_counter()
        _l.info('build transaction')

        with transaction.atomic():
            try:
                # if settings.DEBUG:
                #     _l.info('> _make_transactions')
                #     self._make_transactions(10000)
                #     _l.info('< _make_transactions')

                load_st = time.perf_counter()

                self._load()

                _l.info('build load_st done: %s', "{:3.3f}".format(time.perf_counter() - load_st))

                # self._set_trns_refs(self._transactions)

                to_transaction_report_item_st = time.perf_counter()

                self._items = [TransactionReportItem(self.instance, trn=t) for t in self._transactions]
                self.instance.items = self._items
                _l.info('build to_transaction_report_item done: %s', "{:3.3f}".format(time.perf_counter() - to_transaction_report_item_st))

                _refresh_from_db_st = time.perf_counter()

                self._refresh_from_db()

                _l.info('build refresh_from_db done: %s', "{:3.3f}".format(time.perf_counter() - _refresh_from_db_st))

                # self._set_items_refs(self._items)
                # self._update_instance()

                close_st = time.perf_counter()

                self.instance.close()

                _l.info('build close_st done: %s', "{:3.3f}".format(time.perf_counter() - close_st))

            finally:
                transaction.set_rollback(True)


        custom_fields_st = time.perf_counter()

        self.instance.custom_fields = TransactionReportCustomField.objects.filter(master_user=self.instance.master_user)

        _l.info('build custom_fields_st done: %s', "{:3.3f}".format(time.perf_counter() - custom_fields_st))

        _l.info('build done: %s', "{:3.3f}".format(time.perf_counter() - st))

        return self.instance

    def _get_ref(self, clazz, pk, obj=None):
        tc = self._similar_cache[clazz]
        try:
            return tc[pk]
        except KeyError:
            if obj is not None:
                tc[pk] = obj
                return obj
        return None

    def _set_ref(self, obj, attr, attr_id=None, clazz=None):
        if attr_id is None:
            attr_id = '%s_id' % attr
        pk = getattr(obj, attr_id, None)
        if pk is None:
            return
        if clazz is None:
            obj = getattr(obj, attr, None)
            if obj is None:
                return
            clazz = type(obj)
        tc = self._similar_cache[clazz]
        if pk in tc:
            val = tc[pk]
            setattr(obj, attr, val)
        else:
            val = getattr(obj, attr)
            tc[pk] = val
        return val

    def _set_attrs(self, obj):
        if obj:
            for a in obj.attributes.all():
                self._set_ref(a, 'attribute_type', clazz=GenericAttributeType)

    def _trn_qs_prefetch(self, qs):

        _qs_st = time.perf_counter()

        qs = qs.select_related(

            'complex_transaction',
            'complex_transaction__transaction_type',
            'transaction_class',

            'instrument',
            'instrument__instrument_type',
            'instrument__instrument_type__instrument_class',
            'instrument__pricing_currency',
            'instrument__accrued_currency',

            'allocation_balance',
            'allocation_pl',
            'linked_instrument',
            'linked_instrument__instrument_type',

            'transaction_currency',
            'settlement_currency',

            'portfolio',

            'account_position',
            'account_cash',
            'account_interim',

            'strategy1_position',
            'strategy1_cash',
            'strategy2_position',
            'strategy2_cash',
            'strategy3_position',
            'strategy3_cash',

            'responsible',
            'counterparty',

        )

        # _l.info('_trn_qs_prefetch  done: %s', (time.perf_counter() - _qs_st))

        return qs

    def _trn_qs_filter(self, qs):

        filters = Q()

        if self.instance.portfolios:
            filters &= Q(portfolio__in=self.instance.portfolios)

        if self.instance.accounts:
            filters &= Q(account_position__in=self.instance.accounts) | Q(account_cash__in=self.instance.accounts) | Q(
                account_interim__in=self.instance.accounts)

        if self.instance.strategies1:
            filters &= Q(strategy1_position__in=self.instance.strategies1) | Q(
                strategy1_cash__in=self.instance.strategies1)

        if self.instance.strategies2:
            filters &= Q(strategy2_position__in=self.instance.strategies2) | Q(
                strategy2_cash__in=self.instance.strategies2)

        if self.instance.strategies3:
            filters &= Q(strategy3_position__in=self.instance.strategies3) | Q(
                strategy3_cash__in=self.instance.strategies3)

        qs = qs.filter(filters)

        return qs

    def _load(self):
        # _l.info('> _load')

        trn_qs_st = time.perf_counter()

        trn_qs = Transaction.objects

        trn_qs = self._trn_qs_prefetch(trn_qs)

        trn_qs = trn_qs.filter(master_user=self.instance.master_user, is_canceled=False)

        trn_qs = self._trn_qs_permission_filter(trn_qs)
        trn_qs = self._trn_qs_filter(trn_qs)

        _l.info('_load_transactions trn_qs_st done: %s', "{:3.3f}".format(time.perf_counter() - trn_qs_st))

        _l.info('self.instance.begin_date %s', str(self.instance.begin_date))
        _l.info('self.instance.end_date: %s', str(self.instance.end_date))

        filter_obj = {}

        if self.instance.begin_date:

            filter_obj['complex_transaction__' + self.instance.date_field + '__gte'] = self.instance.begin_date

        if self.instance.end_date:

            filter_obj['complex_transaction__' + self.instance.date_field + '__lte'] = self.instance.end_date

        trn_qs = trn_qs.filter(**filter_obj)

        trn_qs = trn_qs.order_by('complex_transaction__date', 'complex_transaction__code', 'transaction_code')

        self._transactions = list(trn_qs)

        _l.info('_load len: %s', len(self._transactions))

    def _refresh_from_db(self):
        # _l.info('> _refresh_from_db')

        self.instance.portfolios = self._refresh_portfolios(
            master_user=self.instance.master_user,
            items=None,
            attrs=None,
            objects=self.instance.portfolios
        )
        self.instance.accounts = self._refresh_accounts(
            master_user=self.instance.master_user,
            items=None,
            attrs=None,
            objects=self.instance.accounts
        )
        self.instance.accounts_position = self._refresh_accounts(
            master_user=self.instance.master_user,
            items=None,
            attrs=None,
            objects=self.instance.accounts_position
        )
        self.instance.accounts_cash = self._refresh_accounts(
            master_user=self.instance.master_user,
            items=None,
            attrs=None,
            objects=self.instance.accounts_cash
        )
        self.instance.strategies1 = self._refresh_strategies1(
            master_user=self.instance.master_user,
            items=None,
            attrs=None,
            objects=self.instance.strategies1
        )
        self.instance.strategies2 = self._refresh_strategies2(
            master_user=self.instance.master_user,
            items=None,
            attrs=None,
            objects=self.instance.strategies2
        )
        self.instance.strategies3 = self._refresh_strategies3(
            master_user=self.instance.master_user,
            items=None,
            attrs=None,
            objects=self.instance.strategies3
        )

        self.instance.item_complex_transactions = self._refresh_complex_transactions(
            master_user=self.instance.master_user,
            items=self.instance.items,
            attrs=['complex_transaction']
        )
        self.instance.item_transaction_classes = self._refresh_transaction_classes(
            master_user=self.instance.master_user,
            items=self.instance.items,
            attrs=['transaction_class']
        )
        self.instance.item_instruments = self._refresh_instruments(
            master_user=self.instance.master_user,
            items=self.instance.items,
            attrs=['instrument', 'linked_instrument', 'allocation_balance', 'allocation_pl']
        )
        self.instance.item_currencies = self._refresh_currencies(
            master_user=self.instance.master_user,
            items=self.instance.items,
            attrs=['transaction_currency', 'settlement_currency']
        )
        self.instance.item_portfolios = self._refresh_portfolios(
            master_user=self.instance.master_user,
            items=self.instance.items,
            attrs=['portfolio']
        )
        self.instance.item_accounts = self._refresh_accounts(
            master_user=self.instance.master_user,
            items=self.instance.items,
            attrs=['account_position', 'account_cash', 'account_interim']
        )
        self.instance.item_strategies1 = self._refresh_strategies1(
            master_user=self.instance.master_user,
            items=self.instance.items,
            attrs=['strategy1_position', 'strategy1_cash']
        )
        self.instance.item_strategies2 = self._refresh_strategies2(
            master_user=self.instance.master_user,
            items=self.instance.items,
            attrs=['strategy2_position', 'strategy2_cash']
        )
        self.instance.item_strategies3 = self._refresh_strategies3(
            master_user=self.instance.master_user,
            items=self.instance.items,
            attrs=['strategy3_position', 'strategy3_cash']
        )
        self.instance.item_counterparties = self._refresh_counterparties(
            master_user=self.instance.master_user,
            items=self.instance.items,
            attrs=['counterparty']
        )
        self.instance.item_responsibles = self._refresh_responsibles(
            master_user=self.instance.master_user,
            items=self.instance.items,
            attrs=['responsible']
        )

        # _l.info('< _refresh_from_db')
