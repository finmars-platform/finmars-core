import logging
import time
from collections import defaultdict

from django.db import transaction
from django.db.models import Q

from poms.common.utils import force_qs_evaluation
from poms.obj_attrs.models import GenericAttributeType
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
        _l.debug('build transaction')

        with transaction.atomic():
            try:
                # if settings.DEBUG:
                #     _l.debug('> _make_transactions')
                #     self._make_transactions(10000)
                #     _l.debug('< _make_transactions')

                self._load()
                # self._set_trns_refs(self._transactions)
                self._items = [TransactionReportItem(self.instance, trn=t) for t in self._transactions]
                self.instance.items = self._items
                self._refresh_from_db()
                # self._set_items_refs(self._items)
                # self._update_instance()
                self.instance.close()

                # if settings.DEBUG:
                #     _l.debug('> pickle')
                #     import pickle
                #     data = pickle.dumps(self.instance, protocol=pickle.HIGHEST_PROTOCOL)
                #     _l.debug('< pickle: %s', len(data))
                #     _l.debug('> pickle.zlib')
                #     import zlib
                #     data1 = zlib.compress(data)
                #     _l.debug('< pickle.zlib: %s', len(data1))
                #
                #     _l.debug('> json')
                #     from poms.reports.serializers import TransactionReportSerializer
                #     from rest_framework.renderers import JSONRenderer
                #     s = TransactionReportSerializer(instance=self.instance, context={
                #         'master_user': self.instance.master_user,
                #         'member': self.instance.member,
                #     })
                #     data_dict = s.data
                #     r = JSONRenderer()
                #     data = r.render(data_dict)
                #     _l.debug('< json: %s', len(data))
                #     _l.debug('> json.zlib')
                #     import zlib
                #     data1 = zlib.compress(data)
                #     _l.debug('< json.zlib: %s', len(data1))
            finally:
                transaction.set_rollback(True)

        _l.debug('done: %s', (time.perf_counter() - st))

        self.instance.custom_fields = TransactionReportCustomField.objects.filter(master_user=self.instance.master_user)

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

    def _trn_qs(self):
        # from poms.obj_attrs.utils import get_attributes_prefetch
        #
        # qs = Transaction.objects.prefetch_related(
        #     'complex_transaction',
        #     'transaction_class',
        #     'instrument',
        #     'transaction_currency',
        #     'settlement_currency',
        #     'portfolio',
        #     'account_position',
        #     'account_cash',
        #     'account_interim',
        #     'strategy1_position',
        #     'strategy1_cash',
        #     'strategy2_position',
        #     'strategy2_cash',
        #     'strategy3_position',
        #     'strategy3_cash',
        #     'responsible',
        #     'counterparty',
        #     'linked_instrument',
        #     'allocation_balance',
        #     'allocation_pl',
        #     get_attributes_prefetch(),
        #     get_attributes_prefetch('complex_transaction__attributes'),
        #     get_attributes_prefetch('instrument__attributes'),
        #     get_attributes_prefetch('transaction_currency__attributes'),
        #     get_attributes_prefetch('settlement_currency__attributes'),
        #     get_attributes_prefetch('portfolio__attributes'),
        #     get_attributes_prefetch('account_position__attributes'),
        #     get_attributes_prefetch('account_cash__attributes'),
        #     get_attributes_prefetch('account_interim__attributes'),
        #     get_attributes_prefetch('responsible__attributes'),
        #     get_attributes_prefetch('counterparty__attributes'),
        #     get_attributes_prefetch('linked_instrument__attributes'),
        #     get_attributes_prefetch('allocation_balance__attributes'),
        #     get_attributes_prefetch('allocation_pl__attributes'),
        # )
        #
        # a_filters = [
        #     Q(complex_transaction__isnull=True) | Q(complex_transaction__status=ComplexTransaction.PRODUCTION,
        #                                             complex_transaction__is_deleted=False)
        # ]
        # kw_filters = {
        #     'master_user': self.instance.master_user,
        #     'is_deleted': False,
        # }

        qs = super(TransactionReportBuilder, self)._trn_qs()

        # _l.debug('< base _trn_qs: %s', len(list(qs)))

        _l.debug('self.instance.begin_date %s', str(self.instance.begin_date))
        _l.debug('self.instance.end_date: %s', str(self.instance.end_date))

        filters = Q()

        filter_obj = {}

        if self.instance.begin_date:
            # filters &= Q(complex_transaction__date__gte=self.instance.begin_date)

            filter_obj['complex_transaction__' + self.instance.date_field + '__gte'] = self.instance.begin_date



            # qs = qs.filter(complex_transaction__date__gte=self.instance.begin_date)
            qs = qs.filter(**filter_obj)

        # _l.debug('< base begin date filter: %s', len(list(qs)))

        force_qs_evaluation(qs)

        if self.instance.end_date:
            # filters &= Q(complex_transaction__date__lte=self.instance.end_date)

            filter_obj['complex_transaction__' + self.instance.date_field + '__lte'] = self.instance.end_date

            print('filter_obj %s ' % filter_obj)

            # qs = qs.filter(complex_transaction__date__lte=self.instance.end_date)
            qs = qs.filter(**filter_obj)

            # qs = qs.filter(filters)

        # _l.debug('< base end date filter: %s', len(list(qs)))

        _l.debug('< filters %s', filters)

        # if self.instance.begin_date:
        #     # a_filters.append(Q(complex_transaction__date__gte=self.instance.begin_date))
        #     kw_filters['complex_transaction__date__gte'] = self.instance.begin_date
        #
        # if self.instance.end_date:
        #     # a_filters.append(Q(complex_transaction__date__lte=self.instance.end_date))
        #     kw_filters['complex_transaction__date__lte'] = self.instance.end_date

        # if self.instance.portfolios:
        #     kw_filters['portfolio__in'] = self.instance.portfolios
        #
        # if self.instance.accounts:
        #     kw_filters['account_position__in'] = self.instance.accounts
        #     kw_filters['account_cash__in'] = self.instance.accounts
        #     kw_filters['account_interim__in'] = self.instance.accounts
        #
        # if self.instance.accounts_position:
        #     kw_filters['account_position__in'] = self.instance.accounts_position
        #
        # if self.instance.accounts_cash:
        #     kw_filters['account_cash__in'] = self.instance.accounts_cash
        #
        # if self.instance.strategies1:
        #     kw_filters['strategy1_position__in'] = self.instance.strategies1
        #     kw_filters['strategy1_cash__in'] = self.instance.strategies1
        #
        # if self.instance.strategies2:
        #     kw_filters['strategy2_position__in'] = self.instance.strategies2
        #     kw_filters['strategy2_cash__in'] = self.instance.strategies2
        #
        # if self.instance.strategies3:
        #     kw_filters['strategy3_position__in'] = self.instance.strategies3
        #     kw_filters['strategy3_cash__in'] = self.instance.strategies3
        #
        # qs = qs.filter(*a_filters, **kw_filters)

        # qs = qs.filter(filters)

        # _l.debug('< base after_filters: %s', len(list(qs)))

        qs = qs.order_by('complex_transaction__date', 'complex_transaction__code', 'transaction_code')

        # from poms.transactions.filters import TransactionObjectPermissionFilter
        # qs = TransactionObjectPermissionFilter.filter_qs(qs, self.instance.master_user, self.instance.member)

        return qs

    def _load(self):
        _l.debug('> _load')

        qs = self._trn_qs()

        qs = self._trn_qs_permission_filter(qs)

        self._transactions = list(qs)

        _l.debug('< _load: %s', len(self._transactions))

    def _refresh_from_db(self):
        _l.info('> _refresh_from_db')

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

        _l.info('< _refresh_from_db')
