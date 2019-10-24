import copy
import logging

import time

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import FieldDoesNotExist
from django.db.models import Q, prefetch_related_objects, Prefetch
from django.utils.functional import cached_property

from poms.accounts.models import Account, AccountType
from poms.counterparties.models import Responsible, ResponsibleGroup, Counterparty, CounterpartyGroup
from poms.currencies.models import Currency
from poms.instruments.models import Instrument, InstrumentType, AccrualCalculationSchedule, InstrumentFactorSchedule
from poms.obj_attrs.models import GenericAttributeType
from poms.obj_attrs.utils import get_attributes_prefetch, get_attributes_prefetch_simple
from poms.obj_perms.models import GenericObjectPermission
from poms.obj_perms.utils import get_permissions_prefetch_lookups
from poms.portfolios.models import Portfolio
from poms.reports.models import BalanceReportCustomField
from poms.strategies.models import Strategy1, Strategy1Subgroup, Strategy1Group, Strategy2, Strategy2Subgroup, \
    Strategy2Group, Strategy3, Strategy3Subgroup, Strategy3Group
from poms.tags.utils import get_tag_prefetch
from poms.transactions.models import ComplexTransaction, TransactionClass, TransactionType, TransactionTypeGroup

from poms.accounts.models import Account
from poms.accounts.models import AccountType
from poms.counterparties.models import Responsible, ResponsibleGroup, Counterparty, CounterpartyGroup
from poms.instruments.models import Instrument, InstrumentType
from poms.obj_perms.utils import get_permissions_prefetch_lookups
from poms.obj_attrs.utils import get_attributes_prefetch
from poms.portfolios.models import Portfolio
from poms.strategies.models import Strategy1, Strategy1Subgroup, Strategy1Group, Strategy2, Strategy2Subgroup, \
    Strategy2Group, Strategy3, Strategy3Subgroup, Strategy3Group
from poms.transactions.models import Transaction, ComplexTransaction, TransactionType

from poms.common.utils import force_qs_evaluation

from django.db.models import F

_l = logging.getLogger('poms.reports')


class BaseReportBuilder:
    def __init__(self, instance, queryset=None):
        self.instance = instance
        self._queryset = queryset

    @cached_property
    def _trn_cls_sell(self):
        return TransactionClass.objects.get(pk=TransactionClass.SELL)

    @cached_property
    def _trn_cls_buy(self):
        return TransactionClass.objects.get(pk=TransactionClass.BUY)

    @cached_property
    def _trn_cls_fx_trade(self):
        return TransactionClass.objects.get(pk=TransactionClass.FX_TRADE)

    @cached_property
    def _trn_clsinstr_pl(self):
        return TransactionClass.objects.get(pk=TransactionClass.INSTRUMENT_PL)

    @cached_property
    def _trn_cls_trn_pl(self):
        return TransactionClass.objects.get(pk=TransactionClass.TRANSACTION_PL)

    @cached_property
    def _trn_cls_transfer(self):
        return TransactionClass.objects.get(pk=TransactionClass.TRANSFER)

    @cached_property
    def _trn_cls_fx_transfer(self):
        return TransactionClass.objects.get(pk=TransactionClass.FX_TRANSFER)

    @cached_property
    def _trn_cls_cash_in(self):
        return TransactionClass.objects.get(pk=TransactionClass.CASH_INFLOW)

    @cached_property
    def _trn_cls_cash_out(self):
        return TransactionClass.objects.get(pk=TransactionClass.CASH_OUTFLOW)

    def _trn_qs_prefetch_old(self, qs):
        return qs.prefetch_related(
            'complex_transaction',
            'complex_transaction__transaction_type',
            'transaction_class',
            'instrument__instrument_type',
            'instrument__instrument_type__instrument_class',
            'instrument__pricing_currency',
            'instrument__accrued_currency',
            'instrument__accrual_calculation_schedules',
            'instrument__accrual_calculation_schedules__accrual_calculation_model',
            'instrument__accrual_calculation_schedules__periodicity',
            'instrument__factor_schedules',
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
            'linked_instrument__instrument_type',
            'linked_instrument__instrument_type__instrument_class',
            'linked_instrument__pricing_currency',
            'linked_instrument__accrued_currency',
            'linked_instrument__accrual_calculation_schedules',
            'linked_instrument__accrual_calculation_schedules__accrual_calculation_model',
            'linked_instrument__accrual_calculation_schedules__periodicity',
            'linked_instrument__factor_schedules',
            'allocation_balance',
            'allocation_balance__instrument_type',
            'allocation_balance__instrument_type__instrument_class',
            'allocation_balance__pricing_currency',
            'allocation_balance__accrued_currency',
            'allocation_balance__accrual_calculation_schedules',
            'allocation_balance__accrual_calculation_schedules__accrual_calculation_model',
            'allocation_balance__accrual_calculation_schedules__periodicity',
            'allocation_balance__factor_schedules',
            'allocation_pl',
            'allocation_pl__instrument_type',
            'allocation_pl__instrument_type__instrument_class',
            'allocation_pl__pricing_currency',
            'allocation_pl__accrued_currency',
            'allocation_pl__accrual_calculation_schedules',
            'allocation_pl__accrual_calculation_schedules__accrual_calculation_model',
            'allocation_pl__accrual_calculation_schedules__periodicity',
            'allocation_pl__factor_schedules',
            get_attributes_prefetch(),
            get_attributes_prefetch('complex_transaction__attributes'),
            get_attributes_prefetch('instrument__attributes'),
            get_attributes_prefetch('transaction_currency__attributes'),
            get_attributes_prefetch('settlement_currency__attributes'),
            get_attributes_prefetch('portfolio__attributes'),
            get_attributes_prefetch('account_position__attributes'),
            get_attributes_prefetch('account_cash__attributes'),
            get_attributes_prefetch('account_interim__attributes'),
            get_attributes_prefetch('responsible__attributes'),
            get_attributes_prefetch('counterparty__attributes'),
            get_attributes_prefetch('linked_instrument__attributes'),
            get_attributes_prefetch('allocation_balance__attributes'),
            get_attributes_prefetch('allocation_pl__attributes'),
            *get_permissions_prefetch_lookups(
                ('complex_transaction__transaction_type', TransactionType),
                ('instrument', Instrument),
                ('instrument__instrument_type', InstrumentType),
                ('portfolio', Portfolio),
                ('account_cash', Account),
                ('account_cash__type', AccountType),
                ('account_position', Account),
                ('account_position__type', AccountType),
                ('account_interim', Account),
                ('account_interim__type', AccountType),
                ('strategy1_position', Strategy1),
                ('strategy1_position__subgroup', Strategy1Subgroup),
                ('strategy1_position__subgroup__group', Strategy1Group),
                ('strategy1_cash', Strategy1),
                ('strategy1_cash__subgroup', Strategy1Subgroup),
                ('strategy1_cash__subgroup__group', Strategy1Group),
                ('strategy2_position', Strategy2),
                ('strategy2_position__subgroup', Strategy2Subgroup),
                ('strategy2_position__subgroup__group', Strategy2Group),
                ('strategy2_cash', Strategy2),
                ('strategy2_cash__subgroup', Strategy2Subgroup),
                ('strategy2_cash__subgroup__group', Strategy2Group),
                ('strategy3_position', Strategy3),
                ('strategy3_position__subgroup', Strategy3Subgroup),
                ('strategy3_position__subgroup__group', Strategy3Group),
                ('strategy3_cash', Strategy3),
                ('strategy3_cash__subgroup', Strategy3Subgroup),
                ('strategy3_cash__subgroup__group', Strategy3Group),
                ('responsible', Responsible),
                ('responsible__group', ResponsibleGroup),
                ('counterparty', Counterparty),
                ('counterparty__group', CounterpartyGroup),
                ('linked_instrument', Instrument),
                ('linked_instrument__instrument_type', InstrumentType),
                ('allocation_balance', Instrument),
                ('allocation_balance__instrument_type', InstrumentType),
                ('allocation_pl', Instrument),
                ('allocation_pl__instrument_type', InstrumentType),
            )
        )

    def _trn_qs_permission_filter(self, qs):

        if self.instance.member is None:
            return qs

        if self.instance.member.is_superuser:
            return qs

        ctype = ContentType.objects.get_for_model(Transaction)
        codename = 'view_transaction'

        # _l.debug('Before permission filter len %s' % len(qs))

        ids = GenericObjectPermission.objects.filter(
            content_type=ctype, permission__content_type=ctype, permission__codename=codename,
            group__in=self.instance.member.groups.all()
        ).values_list('object_id', flat=True)

        qs = qs.filter(pk__in=ids)

        # _l.debug('After permission filter len %s' % len(qs))

        return qs

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
            'linked_instrument__instrument_type',
            'allocation_balance',
            'allocation_pl',
        )

        # _l.debug('_trn_qs_prefetch  done: %s', (time.perf_counter() - _qs_st))

        return qs

    def _trn_qs_filter(self, qs):
        return qs

    def _trn_qs_old(self):

        _trn_qs_st = time.perf_counter()

        # qs = self._queryset if self._queryset is not None else Transaction.objects
        # qs = qs.filter(
        #     master_user=self.instance.master_user,
        #     is_deleted=False,
        # ).filter(
        #     Q(master_user=self.instance.master_user, is_deleted=False),
        #     Q(complex_transaction__isnull=True) | Q(complex_transaction__status=ComplexTransaction.PRODUCTION,
        #                                             complex_transaction__is_deleted=False)
        # )

        qs = self._queryset if self._queryset is not None else Transaction.objects

        base_qs_st = time.perf_counter()

        qs = qs.filter(
            master_user=self.instance.master_user,
            is_deleted=False,
        )

        force_qs_evaluation(qs)

        # _l.debug("_get_only_transactions base len %s" % len(qs))

        _l.debug('_get_only_transactions base_qs_st done: %s', (time.perf_counter() - base_qs_st))

        # prefetch_qs_st = time.perf_counter()
        #
        # qs = self._trn_qs_prefetch(qs)
        #
        # force_qs_evaluation(qs)
        #
        # _l.debug('_get_only_transactions prefetch_qs_st done: %s', (time.perf_counter() - prefetch_qs_st))

        production_only_qs_st = time.perf_counter()

        qs = qs.filter(complex_transaction__status=ComplexTransaction.PRODUCTION)

        force_qs_evaluation(qs)

        _l.debug('_get_only_transactions production_only_qs_st done: %s', (time.perf_counter() - production_only_qs_st))

        # _l.debug("_get_only_transactions after production filter len %s" % len(qs))

        relation_filter_qs_st = time.perf_counter()

        if self.instance.portfolios:
            qs = qs.filter(portfolio__in=self.instance.portfolios)
            force_qs_evaluation(qs)

        if self.instance.accounts:
            qs = qs.filter(account_position__in=self.instance.accounts,
                           account_cash__in=self.instance.accounts,
                           account_interim__in=self.instance.accounts)
            force_qs_evaluation(qs)

        if self.instance.accounts_position:
            qs = qs.filter(account_position__in=self.instance.accounts_position)
            force_qs_evaluation(qs)

        if self.instance.accounts_cash:
            qs = qs.filter(account_cash__in=self.instance.accounts_cash)
            force_qs_evaluation(qs)

        if self.instance.strategies1:
            qs = qs.filter(strategy1_position__in=self.instance.strategies1,
                           strategy1_cash__in=self.instance.strategies1)
            force_qs_evaluation(qs)

        if self.instance.strategies2:
            qs = qs.filter(strategy2_position__in=self.instance.strategies2,
                           strategy2_cash__in=self.instance.strategies2)
            force_qs_evaluation(qs)

        if self.instance.strategies3:
            qs = qs.filter(strategy3_position__in=self.instance.strategies3,
                           strategy3_cash__in=self.instance.strategies3)
            force_qs_evaluation(qs)

        _l.debug('_get_only_transactions relation_filter_qs_st done: %s', (time.perf_counter() - relation_filter_qs_st))

        permission_filter_qs_st = time.perf_counter()

        if self.instance.member is not None:
            from poms.transactions.filters import TransactionObjectPermissionFilter
            qs = TransactionObjectPermissionFilter.filter_qs(qs, self.instance.master_user, self.instance.member)

        _l.debug('_get_only_transactions permission_filter_qs_st done: %s',
                 (time.perf_counter() - permission_filter_qs_st))

        specific_filter_qs_st = time.perf_counter()

        qs = self._trn_qs_filter(qs)

        # result = list(qs)
        result = qs

        _l.debug('_get_only_transactions specific_filter_qs_st done: %s', (time.perf_counter() - specific_filter_qs_st))

        _l.debug('_get_only_transactions _trn_qs_st done: %s', (time.perf_counter() - _trn_qs_st))

        # _l.debug("_get_only_transactions end len %s" % len(qs))

        return result

    def _trn_qs(self):

        _trn_qs_st = time.perf_counter()

        qs = self._queryset if self._queryset is not None else Transaction.objects

        qs = self._trn_qs_prefetch(qs)

        # qs = self._prefetch_instruments_data(qs)

        # complex_qs = ComplexTransaction.objects.filter(status=ComplexTransaction.PRODUCTION,
        #                                                master_user=self.instance.master_user, is_deleted=False)

        # qs = qs.filter(complex_transaction__in=complex_qs)

        qs = qs.filter(master_user=self.instance.master_user, is_canceled=False)

        # TODO USED AS BACKEND FILTERS FOR REPORTS
        # TODO MAYBE WILL BE USED IN FUTURE

        if self.instance.portfolios:
            qs = qs.filter(portfolio__in=self.instance.portfolios)

        if self.instance.accounts:
            qs = qs.filter(account_position__in=self.instance.accounts,
                           account_cash__in=self.instance.accounts,
                           account_interim__in=self.instance.accounts)

        if self.instance.accounts_position:
            qs = qs.filter(account_position__in=self.instance.accounts_position)

        if self.instance.accounts_cash:
            qs = qs.filter(account_cash__in=self.instance.accounts_cash)

        if self.instance.strategies1:
            qs = qs.filter(strategy1_position__in=self.instance.strategies1,
                           strategy1_cash__in=self.instance.strategies1)

        if self.instance.strategies2:
            qs = qs.filter(strategy2_position__in=self.instance.strategies2,
                           strategy2_cash__in=self.instance.strategies2)

        if self.instance.strategies3:
            qs = qs.filter(strategy3_position__in=self.instance.strategies3,
                           strategy3_cash__in=self.instance.strategies3)

        qs = self._trn_qs_filter(qs)

        result = qs

        # _l.debug('_trn_qs_optimized  done: %s', (time.perf_counter() - _trn_qs_st))

        return result

    def _clone(self, obj):
        ret = copy.copy(obj)
        ret._is_cloned = True
        return ret

    def _refresh_attrs(self, items, attrs, queryset, objects=None):
        # _l.debug('refresh: %s -> %s', attrs, queryset.model)

        # return self._refresh_attrs_simple(items=items, attrs=attrs, objects=objects)

        pks = set()
        if objects is not None:
            for obj in objects:
                if obj:
                    pks.add(obj.id)
        else:
            if not items or not attrs:
                return []

            for item in items:
                for attr in attrs:
                    obj = getattr(item, attr, None)
                    if obj:
                        pks.add(obj.id)

        # query_st = time.perf_counter()

        objs = queryset.in_bulk(pks)

        # _l.debug('_refresh_attrs len %s' % len(list(objs)))
        #
        # _l.debug('_refresh_attrs query done: %s', (time.perf_counter() - query_st))

        # _l.debug('objs: %s', objs.keys())

        if objects is not None:
            objects.clear()
            objects.extend(objs.values())
        else:
            for item in items:
                for attr in attrs:
                    obj = getattr(item, attr, None)
                    if obj:
                        setattr(item, attr, objs[obj.id])

        return list(objs.values())

    def _refresh_attrs_simple(self, items, attrs, objects=None):
        # _l.debug('refresh: %s', attrs)

        if not items or not attrs:
            return []

        objs = {}
        if objects is not None:
            for obj in objects:
                if obj:
                    objs[obj.id] = obj
        else:
            for item in items:
                for attr in attrs:
                    obj = getattr(item, attr, None)
                    if obj:
                        objs[obj.id] = obj

        # _l.debug('objs: %s', objs.keys())

        return list(objs.values())

    def _refresh_custom_fields(self, master_user, items, attrs, objects=None):
        return self._refresh_attrs(
            items=items,
            attrs=attrs,
            objects=objects,
            queryset=BalanceReportCustomField.objects.filter(
                master_user=master_user,
            )
        )

    def _refresh_complex_transactions(self, master_user, items, attrs, objects=None):
        return self._refresh_attrs(
            items=items,
            attrs=attrs,
            objects=objects,
            queryset=ComplexTransaction.objects.filter(
                transaction_type__master_user=master_user
            ).prefetch_related(
                'transaction_type',
                'transaction_type__group',
                get_attributes_prefetch(),
                *get_permissions_prefetch_lookups(
                    ('transaction_type', TransactionType),
                    ('transaction_type__group', TransactionTypeGroup),
                )
            )
        )

    def _refresh_transaction_classes(self, master_user, items, attrs, objects=None):
        return self._refresh_attrs(
            items=items,
            attrs=attrs,
            objects=objects,
            queryset=TransactionClass.objects.all()
        )

    def _refresh_instruments(self, master_user, items, attrs, objects=None):

        # return Instrument.objects.filter(
        #     master_user=master_user
        # ).prefetch_related(
        #     'master_user',
        #     'instrument_type',
        #     'instrument_type__instrument_class',
        #     'pricing_currency',
        #     'accrued_currency',
        #     'payment_size_detail',
        #     'daily_pricing_model',
        #     'price_download_scheme',
        #     'price_download_scheme__provider',
        #     get_attributes_prefetch(),
        #     get_tag_prefetch(),
        #     *get_permissions_prefetch_lookups(
        #         (None, Instrument),
        #         ('instrument_type', InstrumentType),
        #     )
        # )
        #
        return self._refresh_attrs(
            items=items,
            attrs=attrs,
            objects=objects,
            queryset=Instrument.objects.filter(
                master_user=master_user
            ).prefetch_related(
                # 'master_user',
                'instrument_type',
                'instrument_type__instrument_class',
                'pricing_currency',
                'accrued_currency',
                'payment_size_detail',
                'daily_pricing_model',
                'price_download_scheme',
                'price_download_scheme__provider',
                get_attributes_prefetch(),
                # get_tag_prefetch(),
                *get_permissions_prefetch_lookups(
                    (None, Instrument),
                    ('instrument_type', InstrumentType),
                )
            )
        )

    def _refresh_currencies(self, master_user, items, attrs, objects=None):
        return self._refresh_attrs(
            items=items,
            attrs=attrs,
            objects=objects,
            queryset=Currency.objects.filter(
                master_user=master_user,
            ).prefetch_related(
                get_attributes_prefetch(),
            )
        )

    def _refresh_portfolios(self, master_user, items, attrs, objects=None):

        return self._refresh_attrs(
            items=items,
            attrs=attrs,
            objects=objects,
            queryset=Portfolio.objects.filter(
                master_user=master_user,
            ).prefetch_related(
                get_attributes_prefetch(),
                *get_permissions_prefetch_lookups(
                    (None, Portfolio),
                )
            )
        )

    def _refresh_accounts(self, master_user, items, attrs, objects=None):
        return self._refresh_attrs(
            items=items,
            attrs=attrs,
            objects=objects,
            queryset=Account.objects.filter(
                master_user=master_user,
            ).prefetch_related(
                'type',
                get_attributes_prefetch(),
                *get_permissions_prefetch_lookups(
                    (None, Account),
                    ('type', AccountType),
                )
            ).defer('object_permissions')
        )

    def _refresh_strategies1(self, master_user, items, attrs, objects=None):
        return self._refresh_attrs(
            items=items,
            attrs=attrs,
            objects=objects,
            queryset=Strategy1.objects.filter(
                master_user=master_user,
            ).prefetch_related(
                'subgroup',
                'subgroup__group',
                *get_permissions_prefetch_lookups(
                    (None, Strategy1),
                    # ('subgroup', Strategy1Subgroup),
                    # ('subgroup__group', Strategy1Group),
                )
            )
        )

    def _refresh_strategies2(self, master_user, items, attrs, objects=None):
        return self._refresh_attrs(
            items=items,
            attrs=attrs,
            objects=objects,
            queryset=Strategy2.objects.filter(
                master_user=master_user,
            ).prefetch_related(
                'subgroup',
                'subgroup__group',
                *get_permissions_prefetch_lookups(
                    (None, Strategy2),
                    # ('subgroup', Strategy2Subgroup),
                    # ('subgroup__group', Strategy2Group),
                )
            )
        )

    def _refresh_strategies3(self, master_user, items, attrs, objects=None):
        return self._refresh_attrs(
            items=items,
            attrs=attrs,
            objects=objects,
            queryset=Strategy3.objects.filter(
                master_user=master_user,
            ).prefetch_related(
                'subgroup',
                'subgroup__group',
                *get_permissions_prefetch_lookups(
                    (None, Strategy3),
                    # ('subgroup', Strategy3Subgroup),
                    # ('subgroup__group', Strategy3Group),
                )
            )
        )

    def _refresh_responsibles(self, master_user, items, attrs, objects=None):
        return self._refresh_attrs(
            items=items,
            attrs=attrs,
            objects=objects,
            queryset=Responsible.objects.filter(
                master_user=master_user,
            ).prefetch_related(
                'group',
                get_attributes_prefetch(),
                *get_permissions_prefetch_lookups(
                    (None, Responsible),
                    # ('group', ResponsibleGroup),
                )
            )
        )

    def _refresh_counterparties(self, master_user, items, attrs, objects=None):
        return self._refresh_attrs(
            items=items,
            attrs=attrs,
            objects=objects,
            queryset=Counterparty.objects.filter(
                master_user=master_user,
            ).prefetch_related(
                'group',
                get_attributes_prefetch(),
                *get_permissions_prefetch_lookups(
                    (None, Counterparty),
                    # ('group', CounterpartyGroup),
                )
            )
        )

    def _refresh_currency_fx_rates(self, master_user, items, attrs, objects=None):
        return self._refresh_attrs_simple(items=items, attrs=attrs, objects=objects)

    def _refresh_item_instrument_pricings(self, master_user, items, attrs, objects=None):
        return self._refresh_attrs_simple(items=items, attrs=attrs, objects=objects)

    def _refresh_item_instrument_accruals(self, master_user, items, attrs, objects=None):
        return self._refresh_attrs_simple(items=items, attrs=attrs, objects=objects)

    # SZ LOGIC BELOW

    def _get_relation_permissions(self, groups, app_label, model):

        content_type = ContentType.objects.get(app_label=app_label, model=model)

        codename = 'view_' + model

        return GenericObjectPermission.objects.filter(group__in=groups, content_type=content_type,
                                                      permission__codename=codename)

    def _get_relations_ids_from_items(self, items, attrs):

        result = set()

        for item in items:
            for attr in attrs:
                obj = getattr(item, attr, None)
                if obj:
                    result.add(obj.id)

        return result

    def _get_attribute_types(self, master_user):

        return list(GenericAttributeType.objects.prefetch_related('classifiers').defer('object_permissions').filter(
            master_user=master_user))

    def _set_attribute_types_in_relations(self, items, attribute_types):

        for item in items:

            if item.attributes:

                for attribute in item.attributes.all():

                    for attribute_type in attribute_types:

                        if attribute_type.id == attribute.attribute_type_id:
                            setattr(attribute, 'attribute_type', attribute_type)

        return items

    def _get_accounts_by_ids(self, ids):

        return Account.objects.select_related('type').prefetch_related(
            # get_attributes_prefetch_simple(),
            'attributes',
            *get_permissions_prefetch_lookups(
                ('type', AccountType),
            )
        ).defer('object_permissions').filter(id__in=ids)

    def _get_currencies_by_ids(self, ids):

        return Currency.objects.prefetch_related(
            get_attributes_prefetch_simple()
        ).filter(id__in=ids)

    def _get_portfolios_by_ids(self, ids):

        return Portfolio.objects.prefetch_related(
            # get_attributes_prefetch_simple()
            'attributes'
        ).defer('object_permissions', 'responsibles', 'counterparties', 'transaction_types', 'accounts', 'tags').filter(
            id__in=ids)

    def _get_instruments_by_ids(self, ids):

        return Instrument.objects.select_related(
            'instrument_type',
            'instrument_type__instrument_class',
            'pricing_currency',
            'accrued_currency',
            'payment_size_detail',
            'daily_pricing_model',
            'price_download_scheme',
            'price_download_scheme__provider',
        ).prefetch_related(
            # get_attributes_prefetch_simple(),
            'attributes',
            *get_permissions_prefetch_lookups(
                ('instrument_type', InstrumentType),
            )
        ).filter(id__in=ids)

    def _get_instrument_types_by_ids(self, ids):
        return InstrumentType.objects.defer('object_permissions').filter(
            id__in=ids)

    def _get_account_types_by_ids(self, ids):
        return AccountType.objects.defer('object_permissions').filter(
            id__in=ids)

    def _get_strategies1_by_ids(self, ids):
        return Strategy1.objects.select_related(
            'subgroup',
            'subgroup__group').defer('object_permissions').filter(
            id__in=ids)

    def _get_strategies2_by_ids(self, ids):
        return Strategy2.objects.select_related(
            'subgroup',
            'subgroup__group').defer('object_permissions').filter(
            id__in=ids)

    def _get_strategies3_by_ids(self, ids):
        return Strategy3.objects.select_related(
            'subgroup',
            'subgroup__group').defer('object_permissions').filter(
            id__in=ids)
