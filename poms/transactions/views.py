from __future__ import unicode_literals

import django_filters
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import Prefetch, Q
from django.utils.translation import ugettext_lazy
from django_filters.rest_framework import FilterSet
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.settings import api_settings

from poms.accounts.models import Account, AccountType
from poms.audit import history
from poms.common.filters import CharFilter, ModelExtWithPermissionMultipleChoiceFilter, ModelExtMultipleChoiceFilter, \
    NoOpFilter, AttributeFilter, GroupsAttributeFilter
from poms.common.pagination import CustomPaginationMixin
from poms.common.views import AbstractClassModelViewSet, AbstractModelViewSet, AbstractAsyncViewSet
from poms.counterparties.models import Responsible, Counterparty, ResponsibleGroup, CounterpartyGroup
from poms.currencies.models import Currency
from poms.instruments.models import Instrument, InstrumentType, PricingPolicy, Periodicity, AccrualCalculationModel
from poms.integrations.tasks import complex_transaction_csv_file_import_validate
from poms.obj_attrs.utils import get_attributes_prefetch
from poms.obj_attrs.views import GenericAttributeTypeViewSet, \
    GenericClassifierViewSet
from poms.obj_perms.filters import ObjectPermissionMemberFilter, ObjectPermissionGroupFilter, \
    ObjectPermissionPermissionFilter
from poms.obj_perms.utils import get_permissions_prefetch_lookups
from poms.obj_perms.views import AbstractWithObjectPermissionViewSet, AbstractEvGroupWithObjectPermissionViewSet
from poms.portfolios.models import Portfolio
from poms.strategies.models import Strategy1, Strategy2, Strategy3, Strategy1Subgroup, Strategy1Group, \
    Strategy2Subgroup, Strategy2Group, Strategy3Subgroup, Strategy3Group
from poms.tags.filters import TagFilter
from poms.tags.utils import get_tag_prefetch
from poms.transactions.filters import TransactionObjectPermissionFilter, ComplexTransactionPermissionFilter, \
    TransactionObjectPermissionMemberFilter, TransactionObjectPermissionGroupFilter, \
    TransactionObjectPermissionPermissionFilter
from poms.transactions.handlers import TransactionTypeProcess
from poms.transactions.models import TransactionClass, Transaction, TransactionType, TransactionTypeGroup, \
    ComplexTransaction, EventClass, NotificationClass, TransactionTypeInput, TransactionTypeAction
from poms.transactions.permissions import TransactionObjectPermission, ComplexTransactionPermission
from poms.transactions.serializers import TransactionClassSerializer, TransactionSerializer, TransactionTypeSerializer, \
    TransactionTypeProcessSerializer, TransactionTypeGroupSerializer, ComplexTransactionSerializer, \
    EventClassSerializer, NotificationClassSerializer, TransactionTypeLightSerializer, \
    ComplexTransactionLightSerializer, ComplexTransactionSimpleSerializer, \
    RecalculatePermissionTransactionSerializer, RecalculatePermissionComplexTransactionSerializer
from poms.transactions.tasks import recalculate_permissions_transaction, recalculate_permissions_complex_transaction
from poms.users.filters import OwnerByMasterUserFilter


class EventClassViewSet(AbstractClassModelViewSet):
    queryset = EventClass.objects
    serializer_class = EventClassSerializer


class NotificationClassViewSet(AbstractClassModelViewSet):
    queryset = NotificationClass.objects
    serializer_class = NotificationClassSerializer


class TransactionClassViewSet(AbstractClassModelViewSet):
    queryset = TransactionClass.objects
    serializer_class = TransactionClassSerializer


class TransactionTypeGroupFilterSet(FilterSet):
    id = NoOpFilter()
    is_deleted = django_filters.BooleanFilter()
    user_code = CharFilter()
    name = CharFilter()
    short_name = CharFilter()
    public_name = CharFilter()
    tag = TagFilter(model=Account)
    member = ObjectPermissionMemberFilter(object_permission_model=TransactionTypeGroup)
    member_group = ObjectPermissionGroupFilter(object_permission_model=TransactionTypeGroup)
    permission = ObjectPermissionPermissionFilter(object_permission_model=TransactionTypeGroup)

    class Meta:
        model = TransactionTypeGroup
        fields = []


class TransactionTypeGroupViewSet(AbstractWithObjectPermissionViewSet):
    queryset = TransactionTypeGroup.objects.prefetch_related(
        get_tag_prefetch(),
        *get_permissions_prefetch_lookups(
            (None, TransactionTypeGroup),
        )
    )
    serializer_class = TransactionTypeGroupSerializer
    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    filter_class = TransactionTypeGroupFilterSet
    ordering_fields = [
        'user_code', 'name', 'short_name', 'public_name',
    ]

    def perform_destroy(self, instance):
        super(TransactionTypeGroupViewSet, self).perform_destroy(instance)

        items_qs = TransactionType.objects.filter(master_user=instance.master_user, group=instance)
        default_group = TransactionTypeGroup.objects.get(master_user=instance.master_user, user_code='-')

        items_qs.update(group=default_group)


class TransactionTypeGroupEvGroupViewSet(AbstractEvGroupWithObjectPermissionViewSet, CustomPaginationMixin):
    queryset = TransactionTypeGroup.objects.prefetch_related(
        get_tag_prefetch(),
        *get_permissions_prefetch_lookups(
            (None, TransactionTypeGroup),
        )
    )

    serializer_class = TransactionTypeGroupSerializer
    pagination_class = api_settings.DEFAULT_PAGINATION_CLASS
    filter_class = TransactionTypeGroupFilterSet

    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter
    ]


class ModelExtWithAllWithPermissionMultipleChoiceFilter(ModelExtWithPermissionMultipleChoiceFilter):
    all_field_name = None

    def __init__(self, *args, **kwargs):
        self.all_field_name = kwargs.pop('all_field_name')
        super(ModelExtWithAllWithPermissionMultipleChoiceFilter, self).__init__(*args, **kwargs)

    def filter(self, qs, value):
        if not value:
            return qs

        if self.is_noop(qs, value):
            return qs

        q = Q()
        for v in set(value):
            predicate = self.get_filter_predicate(v)
            q |= Q(**predicate)

        qs = self.get_method(qs)(q | Q(**{self.all_field_name: True}))

        return qs.distinct() if self.distinct else qs


class ModelExtWithAllWithMultipleChoiceFilter(ModelExtMultipleChoiceFilter):
    all_field_name = None

    def __init__(self, *args, **kwargs):
        self.all_field_name = kwargs.pop('all_field_name')
        super(ModelExtWithAllWithMultipleChoiceFilter, self).__init__(*args, **kwargs)

    def filter(self, qs, value):


        if not value:
            return qs

        if self.is_noop(qs, value):
            return qs

        q = Q()
        for v in set(value):
            predicate = self.get_filter_predicate(v)

            print('predicate %s' % predicate)

            q |= Q(**predicate)

        qs = self.get_method(qs)(q | Q(**{self.all_field_name: True}))

        return qs.distinct() if self.distinct else qs


class TransactionTypeFilterSet(FilterSet):
    id = NoOpFilter()
    user_code = CharFilter()
    name = CharFilter()
    short_name = CharFilter()
    public_name = CharFilter()
    group = ModelExtWithPermissionMultipleChoiceFilter(model=TransactionTypeGroup)
    # portfolio = ModelExtWithPermissionMultipleChoiceFilter(model=Portfolio, name='portfolios')
    portfolios = ModelExtWithAllWithMultipleChoiceFilter(model=Portfolio,
                                                                  all_field_name='is_valid_for_all_portfolios')
    # instrument_type = ModelExtWithPermissionMultipleChoiceFilter(model=InstrumentType, name='instrument_types')
    instrument_types = ModelExtWithAllWithMultipleChoiceFilter(model=InstrumentType,
                                                                        all_field_name='is_valid_for_all_instruments')
    is_valid_for_all_portfolios = django_filters.BooleanFilter()
    is_valid_for_all_instruments = django_filters.BooleanFilter()
    tag = TagFilter(model=TransactionType)
    member = ObjectPermissionMemberFilter(object_permission_model=TransactionType)
    member_group = ObjectPermissionGroupFilter(object_permission_model=TransactionType)
    permission = ObjectPermissionPermissionFilter(object_permission_model=TransactionType)

    class Meta:
        model = TransactionType
        fields = []


class TransactionTypeAttributeTypeViewSet(GenericAttributeTypeViewSet):
    target_model = TransactionType
    target_model_serializer = TransactionTypeSerializer


class TransactionTypeLightViewSet(AbstractWithObjectPermissionViewSet):
    queryset = TransactionType.objects.select_related('group').prefetch_related(
        'portfolios',
        'instrument_types',
        get_attributes_prefetch(),
        get_tag_prefetch(),
        *get_permissions_prefetch_lookups(
            (None, TransactionType),
            ('group', TransactionTypeGroup),
        )
    )
    serializer_class = TransactionTypeLightSerializer
    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter,
        GroupsAttributeFilter,
    ]
    filter_class = TransactionTypeFilterSet
    ordering_fields = [
        'user_code',
        'name',
        'short_name',
        'public_name',
        'group',
        'group__user_code',
        'group__name',
        'group__short_name',
        'group__public_name',
    ]


class TransactionTypeLightEvGroupViewSet(AbstractEvGroupWithObjectPermissionViewSet, CustomPaginationMixin):
    queryset = TransactionType.objects.select_related(
        'group'
    ).prefetch_related(
        'portfolios',
        get_tag_prefetch(),
        Prefetch(
            'instrument_types',
            queryset=InstrumentType.objects.select_related('instrument_class')
        ),
        *get_permissions_prefetch_lookups(
            (None, TransactionType),
            ('group', TransactionTypeGroup),
            ('portfolios', Portfolio),
            ('instrument_types', InstrumentType),
        )
    )
    serializer_class = TransactionTypeLightSerializer
    pagination_class = api_settings.DEFAULT_PAGINATION_CLASS
    # filter_class = TransactionTypeFilterSet

    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter
    ]


class TransactionTypeViewSet(AbstractWithObjectPermissionViewSet):
    queryset = TransactionType.objects.select_related(
        'group'
    ).prefetch_related(
        'portfolios',
        get_tag_prefetch(),
        get_attributes_prefetch(),
        Prefetch(
            'instrument_types',
            queryset=InstrumentType.objects.select_related('instrument_class')
        ),
        Prefetch(
            'inputs',
            queryset=TransactionTypeInput.objects.select_related(
                'content_type',
                'account',
                'account__type',
                'instrument_type',
                'instrument_type__instrument_class',
                'instrument',
                'instrument__instrument_type',
                'instrument__instrument_type__instrument_class',
                'currency',
                'counterparty',
                'counterparty__group',
                'responsible',
                'responsible__group',
                'portfolio',
                'strategy1',
                'strategy1__subgroup',
                'strategy1__subgroup__group',
                'strategy2',
                'strategy2__subgroup',
                'strategy2__subgroup__group',
                'strategy3',
                'strategy3__subgroup',
                'strategy3__subgroup__group',
                'daily_pricing_model',
                'payment_size_detail',
                'price_download_scheme',
                'pricing_policy',
                'periodicity',
                'accrual_calculation_model'
            ).prefetch_related(
                *get_permissions_prefetch_lookups(
                    ('account', Account),
                    ('account__type', AccountType),
                    ('instrument_type', InstrumentType),
                    ('instrument', Instrument),
                    ('instrument__instrument_type', InstrumentType),
                    ('counterparty', Counterparty),
                    ('counterparty__group', CounterpartyGroup),
                    ('responsible', Responsible),
                    ('responsible__group', ResponsibleGroup),
                    ('portfolio', Portfolio),
                    ('strategy1', Strategy1),
                    ('strategy1__subgroup', Strategy1Subgroup),
                    ('strategy1__subgroup__group', Strategy1Group),
                    ('strategy2', Strategy2),
                    ('strategy2__subgroup', Strategy2Subgroup),
                    ('strategy2__subgroup__group', Strategy2Group),
                    ('strategy3', Strategy3),
                    ('strategy3__subgroup', Strategy3Subgroup),
                    ('strategy3__subgroup__group', Strategy3Group),
                )
            )
        ),
        Prefetch(
            'actions',
            queryset=TransactionTypeAction.objects.select_related(
                'transactiontypeactioninstrument',
                'transactiontypeactioninstrument__instrument_type',
                'transactiontypeactioninstrument__instrument_type_input',
                'transactiontypeactioninstrument__instrument_type__instrument_class',
                'transactiontypeactioninstrument__pricing_currency',
                'transactiontypeactioninstrument__pricing_currency_input',
                'transactiontypeactioninstrument__accrued_currency',
                'transactiontypeactioninstrument__accrued_currency_input',
                'transactiontypeactioninstrument__daily_pricing_model',
                'transactiontypeactioninstrument__daily_pricing_model_input',
                'transactiontypeactioninstrument__payment_size_detail',
                'transactiontypeactioninstrument__payment_size_detail_input',
                'transactiontypeactioninstrument__price_download_scheme',
                'transactiontypeactioninstrument__price_download_scheme_input',

                'transactiontypeactiontransaction',
                'transactiontypeactiontransaction__transaction_class',
                'transactiontypeactiontransaction__portfolio',
                'transactiontypeactiontransaction__portfolio_input',
                'transactiontypeactiontransaction__instrument',
                'transactiontypeactiontransaction__instrument_input',
                'transactiontypeactiontransaction__instrument_phantom',
                'transactiontypeactiontransaction__instrument__instrument_type',
                'transactiontypeactiontransaction__instrument__instrument_type__instrument_class',
                'transactiontypeactiontransaction__transaction_currency',
                'transactiontypeactiontransaction__transaction_currency_input',
                'transactiontypeactiontransaction__settlement_currency',
                'transactiontypeactiontransaction__settlement_currency_input',
                'transactiontypeactiontransaction__account_position',
                'transactiontypeactiontransaction__account_position_input',
                'transactiontypeactiontransaction__account_position__type',
                'transactiontypeactiontransaction__account_cash',
                'transactiontypeactiontransaction__account_cash_input',
                'transactiontypeactiontransaction__account_cash__type',
                'transactiontypeactiontransaction__account_interim',
                'transactiontypeactiontransaction__account_interim_input',
                'transactiontypeactiontransaction__account_interim__type',
                'transactiontypeactiontransaction__strategy1_position',
                'transactiontypeactiontransaction__strategy1_position_input',
                'transactiontypeactiontransaction__strategy1_position__subgroup',
                'transactiontypeactiontransaction__strategy1_position__subgroup__group',
                'transactiontypeactiontransaction__strategy1_cash',
                'transactiontypeactiontransaction__strategy1_cash_input',
                'transactiontypeactiontransaction__strategy1_cash__subgroup',
                'transactiontypeactiontransaction__strategy1_cash__subgroup__group',
                'transactiontypeactiontransaction__strategy2_position',
                'transactiontypeactiontransaction__strategy2_position_input',
                'transactiontypeactiontransaction__strategy2_position__subgroup',
                'transactiontypeactiontransaction__strategy2_position__subgroup__group',
                'transactiontypeactiontransaction__strategy2_cash',
                'transactiontypeactiontransaction__strategy2_cash_input',
                'transactiontypeactiontransaction__strategy2_cash__subgroup',
                'transactiontypeactiontransaction__strategy2_cash__subgroup__group',
                'transactiontypeactiontransaction__strategy3_position',
                'transactiontypeactiontransaction__strategy3_position_input',
                'transactiontypeactiontransaction__strategy3_position__subgroup',
                'transactiontypeactiontransaction__strategy3_position__subgroup__group',
                'transactiontypeactiontransaction__strategy3_cash',
                'transactiontypeactiontransaction__strategy3_cash_input',
                'transactiontypeactiontransaction__strategy3_cash__subgroup',
                'transactiontypeactiontransaction__strategy3_cash__subgroup__group',
                'transactiontypeactiontransaction__responsible',
                'transactiontypeactiontransaction__responsible_input',
                'transactiontypeactiontransaction__responsible__group',
                'transactiontypeactiontransaction__counterparty',
                'transactiontypeactiontransaction__counterparty_input',
                'transactiontypeactiontransaction__counterparty__group',
                'transactiontypeactiontransaction__linked_instrument',
                'transactiontypeactiontransaction__linked_instrument_input',
                'transactiontypeactiontransaction__linked_instrument_phantom',
                'transactiontypeactiontransaction__linked_instrument__instrument_type',
                'transactiontypeactiontransaction__linked_instrument__instrument_type__instrument_class',
                'transactiontypeactiontransaction__allocation_balance',
                'transactiontypeactiontransaction__allocation_balance_input',
                'transactiontypeactiontransaction__allocation_balance_phantom',
                'transactiontypeactiontransaction__allocation_balance__instrument_type',
                'transactiontypeactiontransaction__allocation_balance__instrument_type__instrument_class',
                'transactiontypeactiontransaction__allocation_pl',
                'transactiontypeactiontransaction__allocation_pl_input',
                'transactiontypeactiontransaction__allocation_pl_phantom',
                'transactiontypeactiontransaction__allocation_pl__instrument_type',
                'transactiontypeactiontransaction__allocation_pl__instrument_type__instrument_class',

                # 'transactiontypeactioninstrumentfactorschedule__instrument',
                # 'transactiontypeactioninstrumentfactorschedule__instrument_input',
                # 'transactiontypeactioninstrumentfactorschedule__instrument_phantom',
                #
                # 'transactiontypeactioninstrumentmanualpricingformula__instrument',
                # 'transactiontypeactioninstrumentmanualpricingformula__instrument_input',
                # 'transactiontypeactioninstrumentmanualpricingformula__instrument_phantom',
                # 'transactiontypeactioninstrumentmanualpricingformula__pricing_policy',
                # 'transactiontypeactioninstrumentmanualpricingformula__pricing_policy_input',

                # 'transactiontypeactioninstrumentaccrualcalculationschedules__instrument',
                # 'transactiontypeactioninstrumentaccrualcalculationschedules__instrument_input',
                # 'transactiontypeactioninstrumentaccrualcalculationschedules__instrument_phantom',
                # 'transactiontypeactioninstrumentaccrualcalculationschedules__periodicity',
                # 'transactiontypeactioninstrumentaccrualcalculationschedules__periodicity_input',
                # 'transactiontypeactioninstrumentaccrualcalculationschedules__accrual_calculation_model',
                # 'transactiontypeactioninstrumentaccrualcalculationschedules__accrual_calculation_model_input',

            ).prefetch_related(
                # *get_permissions_prefetch_lookups(
                #     ('transactiontypeactioninstrument__instrument_type', InstrumentType),
                #
                #     ('transactiontypeactiontransaction__portfolio', Portfolio),
                #     ('transactiontypeactiontransaction__instrument', Instrument),
                #     ('transactiontypeactiontransaction__instrument__instrument_type', InstrumentType),
                #     ('transactiontypeactiontransaction__account_position', Account),
                #     ('transactiontypeactiontransaction__account_position__type', AccountType),
                #     ('transactiontypeactiontransaction__account_cash', Account),
                #     ('transactiontypeactiontransaction__account_cash__type', AccountType),
                #     ('transactiontypeactiontransaction__account_interim', Account),
                #     ('transactiontypeactiontransaction__account_interim__type', AccountType),
                #     ('transactiontypeactiontransaction__strategy1_position', Strategy1),
                #     ('transactiontypeactiontransaction__strategy1_position__subgroup', Strategy1Subgroup),
                #     ('transactiontypeactiontransaction__strategy1_position__subgroup__group', Strategy1Group),
                #     ('transactiontypeactiontransaction__strategy1_cash', Strategy1),
                #     ('transactiontypeactiontransaction__strategy1_cash__subgroup', Strategy1Subgroup),
                #     ('transactiontypeactiontransaction__strategy1_cash__subgroup__group', Strategy1Group),
                #     ('transactiontypeactiontransaction__strategy2_position', Strategy2),
                #     ('transactiontypeactiontransaction__strategy2_position__subgroup', Strategy2Subgroup),
                #     ('transactiontypeactiontransaction__strategy2_position__subgroup__group', Strategy2Group),
                #     ('transactiontypeactiontransaction__strategy2_cash', Strategy2),
                #     ('transactiontypeactiontransaction__strategy2_cash__subgroup', Strategy2Subgroup),
                #     ('transactiontypeactiontransaction__strategy2_cash__subgroup__group', Strategy2Group),
                #     ('transactiontypeactiontransaction__strategy3_position', Strategy3),
                #     ('transactiontypeactiontransaction__strategy3_position__subgroup', Strategy3Subgroup),
                #     ('transactiontypeactiontransaction__strategy3_position__subgroup__group', Strategy3Group),
                #     ('transactiontypeactiontransaction__strategy3_cash', Strategy3),
                #     ('transactiontypeactiontransaction__strategy3_cash__subgroup', Strategy3Subgroup),
                #     ('transactiontypeactiontransaction__strategy3_cash__subgroup__group', Strategy3Group),
                #     ('transactiontypeactiontransaction__counterparty', Counterparty),
                #     ('transactiontypeactiontransaction__counterparty__group', CounterpartyGroup),
                #     ('transactiontypeactiontransaction__responsible__group', ResponsibleGroup),
                #     ('transactiontypeactiontransaction__responsible', Responsible),
                #     ('transactiontypeactiontransaction__linked_instrument', Instrument),
                #     ('transactiontypeactiontransaction__linked_instrument__instrument_type', InstrumentType),
                #     ('transactiontypeactiontransaction__allocation_balance', Instrument),
                #     ('transactiontypeactiontransaction__allocation_balance__instrument_type', InstrumentType),
                #     ('transactiontypeactiontransaction__allocation_pl', Instrument),
                #     ('transactiontypeactiontransaction__allocation_pl__instrument_type', InstrumentType),
                #
                #     # ('transactiontypeactioninstrumentfactorschedule__instrument', Instrument),
                #     # ('transactiontypeactioninstrumentfactorschedule__instrument__instrument_type', InstrumentType),
                #     #
                #     # ('transactiontypeactioninstrumentmanualpricingformula__instrument', Instrument),
                #     # (
                #     #     'transactiontypeactioninstrumentmanualpricingformula__instrument__instrument_type',
                #     #     InstrumentType),
                #     # ('transactiontypeactioninstrumentmanualpricingformula__pricing_policy', PricingPolicy),
                #
                #     # ('transactiontypeactioninstrumentaccrualcalculationschedules__instrument', Instrument),
                #     # ('transactiontypeactioninstrumentaccrualcalculationschedules__instrument__instrument_type',
                #     #  InstrumentType),
                #
                #     # ('transactiontypeactioninstrumentaccrualcalculationschedules__periodicity', Periodicity),
                #     # ('transactiontypeactioninstrumentaccrualcalculationschedules__accrual_calculation_model',
                #     #  AccrualCalculationModel),
                #
                # )
            )
        ),
        # *get_permissions_prefetch_lookups(
        #     (None, TransactionType),
        #     ('group', TransactionTypeGroup),
        #     ('portfolios', Portfolio),
        #     ('instrument_types', InstrumentType),
        # )
    )
    # prefetch_permissions_for = (
    #     ('group', TransactionTypeGroup),
    #     ('portfolios', Portfolio),
    #     ('instrument_types', InstrumentType),
    # )
    serializer_class = TransactionTypeSerializer
    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter,
        GroupsAttributeFilter,
    ]
    filter_class = TransactionTypeFilterSet
    ordering_fields = [
        'user_code',
        'name',
        'short_name',
        'public_name',
        'group',
        'group__user_code',
        'group__name',
        'group__short_name',
        'group__public_name',
    ]

    def get_context_for_book(self, request):

        master_user = request.user.master_user
        context_values = {}

        instrument_id = request.query_params.get('instrument', None)
        pricing_currency_id = request.query_params.get('pricing_currency', None)
        accrued_currency_id = request.query_params.get('accrued_currency', None)
        portfolio_id = request.query_params.get('portfolio', None)
        account_id = request.query_params.get('account', None)
        strategy1_id = request.query_params.get('strategy1', None)
        strategy2_id = request.query_params.get('strategy2', None)
        strategy3_id = request.query_params.get('strategy3', None)

        context_instrument = None
        context_pricing_currency = None
        context_accrued_currency = None
        context_portfolio = None
        context_account = None
        context_strategy1 = None
        context_strategy2 = None
        context_strategy3 = None

        context_position = request.query_params.get('position', None)
        context_effective_date = request.query_params.get('effective_date', None)
        context_notification_date = request.query_params.get('notification_date', None)
        context_final_date = request.query_params.get('final_date', None)
        context_maturity_date = request.query_params.get('maturity_date', None)

        print('strategy1_id %s' % strategy1_id)

        if instrument_id:
            try:
                context_instrument = Instrument.objects.get(master_user=master_user, id=instrument_id)
            except Instrument.DoesNotExist:
                context_instrument = None

        if portfolio_id:
            try:
                context_portfolio = Portfolio.objects.get(master_user=master_user, id=portfolio_id)
            except Portfolio.DoesNotExist:
                context_portfolio = None

        if account_id:
            try:
                context_account = Account.objects.get(master_user=master_user, id=account_id)
            except Account.DoesNotExist:
                context_account = None

        if strategy1_id:
            try:
                context_strategy1 = Strategy1.objects.get(master_user=master_user, id=strategy1_id)
            except Strategy1.DoesNotExist:
                context_strategy1 = None

        if strategy2_id:
            try:
                context_strategy2 = Strategy2.objects.get(master_user=master_user, id=strategy2_id)
            except Strategy2.DoesNotExist:
                context_strategy2 = None

        if strategy3_id:
            try:
                context_strategy3 = Strategy3.objects.get(master_user=master_user, id=strategy3_id)
            except Strategy3.DoesNotExist:
                context_strategy3 = None

        if pricing_currency_id:
            try:
                context_pricing_currency = Currency.objects.get(master_user=master_user, id=pricing_currency_id)
            except Currency.DoesNotExist:
                context_pricing_currency = None

        if accrued_currency_id:
            try:
                context_accrued_currency = Currency.objects.get(master_user=master_user, id=pricing_currency_id)
            except Currency.DoesNotExist:
                context_accrued_currency = None

        context_values.update({
            'instrument': context_instrument,
            'pricing_currency': context_pricing_currency,
            'accrued_currency': context_accrued_currency,
            'portfolio': context_portfolio,
            'account': context_account,
            'strategy1': context_strategy1,
            'strategy2': context_strategy2,
            'strategy3': context_strategy3,
            'position': context_position,
            'effective_date': context_effective_date,
            # 'notification_date': context_notification_date, # not in context variables
            # 'final_date': context_final_date,
            # 'maturity_date': context_maturity_date
        })

        return context_values

    @action(detail=True, methods=['get', 'put'], url_path='book', serializer_class=TransactionTypeProcessSerializer)
    def book(self, request, pk=None):

        complex_transaction_status = ComplexTransaction.PRODUCTION

        # Some Inputs can choose from which context variable it will take value
        context_values = self.get_context_for_book(request)
        # But by default Context Variables overwrites default value
        default_values = self.get_context_for_book(request)

        print("context_values %s" % context_values)

        transaction_type = TransactionType.objects.get(pk=pk)

        instance = TransactionTypeProcess(process_mode='book', transaction_type=transaction_type,
                                          context=self.get_serializer_context(), context_values=context_values,
                                          default_values=default_values,
                                          complex_transaction_status=complex_transaction_status)

        if request.method == 'GET':
            serializer = self.get_serializer(instance=instance)
            return Response(serializer.data)
        else:
            try:
                history.set_flag_addition()

                serializer = self.get_serializer(instance=instance, data=request.data)
                serializer.is_valid(raise_exception=True)
                serializer.save()

                history.set_actor_content_object(instance.complex_transaction)

                return Response(serializer.data)
            finally:
                if instance.has_errors:
                    transaction.set_rollback(True)

    @action(detail=True, methods=['get', 'put'], url_path='book-pending', serializer_class=TransactionTypeProcessSerializer)
    def book_pending(self, request, pk=None):

        complex_transaction_status = ComplexTransaction.PENDING

        transaction_type = TransactionType.objects.get(pk=pk)

        instance = TransactionTypeProcess(process_mode='book', transaction_type=transaction_type,
                                          context=self.get_serializer_context(),
                                          complex_transaction_status=complex_transaction_status)

        if request.method == 'GET':
            serializer = self.get_serializer(instance=instance)
            return Response(serializer.data)
        else:
            try:
                history.set_flag_addition()

                serializer = self.get_serializer(instance=instance, data=request.data)
                serializer.is_valid(raise_exception=True)
                serializer.save()

                history.set_actor_content_object(instance.complex_transaction)

                return Response(serializer.data)
            finally:
                if instance.has_errors:
                    transaction.set_rollback(True)


class TransactionTypeEvGroupViewSet(AbstractEvGroupWithObjectPermissionViewSet, CustomPaginationMixin):
    queryset = TransactionType.objects.select_related(
        'group'
    ).prefetch_related(
        'portfolios',
        get_tag_prefetch(),
        Prefetch(
            'instrument_types',
            queryset=InstrumentType.objects.select_related('instrument_class')
        ),
        *get_permissions_prefetch_lookups(
            (None, TransactionType),
            ('group', TransactionTypeGroup),
            ('portfolios', Portfolio),
            ('instrument_types', InstrumentType),
        )
    )
    serializer_class = TransactionTypeSerializer
    pagination_class = api_settings.DEFAULT_PAGINATION_CLASS
    # filter_class = TransactionTypeFilterSet

    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter
    ]


class TransactionAttributeTypeViewSet(GenericAttributeTypeViewSet):
    target_model = Transaction
    target_model_serializer = TransactionSerializer


class TransactionClassifierViewSet(GenericClassifierViewSet):
    target_model = Transaction


class TransactionFilterSet(FilterSet):
    id = NoOpFilter()

    complex_transaction__code = django_filters.RangeFilter()
    complex_transaction__date = django_filters.DateFromToRangeFilter()
    complex_transaction__transaction_type = django_filters.Filter(field_name='complex_transaction__transaction_type')

    complex_transaction = ModelExtMultipleChoiceFilter(model=ComplexTransaction, field_name='id',
                                                       master_user_path='transaction_type__master_user')

    transaction_class = django_filters.ModelMultipleChoiceFilter(queryset=TransactionClass.objects)
    transaction_code = django_filters.RangeFilter()
    portfolio = ModelExtWithPermissionMultipleChoiceFilter(model=Portfolio)
    instrument = ModelExtWithPermissionMultipleChoiceFilter(model=Instrument)
    transaction_currency = ModelExtMultipleChoiceFilter(model=Currency)
    position_size_with_sign = django_filters.RangeFilter()
    settlement_currency = ModelExtMultipleChoiceFilter(model=Currency)
    cash_consideration = django_filters.RangeFilter()
    principal_with_sign = django_filters.RangeFilter()
    carry_with_sign = django_filters.RangeFilter()
    overheads_with_sign = django_filters.RangeFilter()
    transaction_date = django_filters.DateFromToRangeFilter()
    accounting_date = django_filters.DateFromToRangeFilter()
    cash_date = django_filters.DateFromToRangeFilter()
    account_position = ModelExtWithPermissionMultipleChoiceFilter(model=Account)
    account_cash = ModelExtWithPermissionMultipleChoiceFilter(model=Account)
    account_interim = ModelExtWithPermissionMultipleChoiceFilter(model=Account)
    strategy1_position = ModelExtWithPermissionMultipleChoiceFilter(model=Strategy1)
    strategy1_cash = ModelExtWithPermissionMultipleChoiceFilter(model=Strategy1)
    strategy2_position = ModelExtWithPermissionMultipleChoiceFilter(model=Strategy2)
    strategy2_cash = ModelExtWithPermissionMultipleChoiceFilter(model=Strategy2)
    strategy3_position = ModelExtWithPermissionMultipleChoiceFilter(model=Strategy3)
    strategy3_cash = ModelExtWithPermissionMultipleChoiceFilter(model=Strategy3)
    reference_fx_rate = django_filters.RangeFilter()
    is_locked = django_filters.BooleanFilter()
    is_deleted = django_filters.BooleanFilter()
    factor = django_filters.RangeFilter()
    trade_price = django_filters.RangeFilter()
    principal_amount = django_filters.RangeFilter()
    carry_amount = django_filters.RangeFilter()
    overheads = django_filters.RangeFilter()
    responsible = ModelExtWithPermissionMultipleChoiceFilter(model=Responsible)
    counterparty = ModelExtWithPermissionMultipleChoiceFilter(model=Counterparty)
    linked_instrument = ModelExtWithPermissionMultipleChoiceFilter(model=Instrument)
    allocation_balance = ModelExtWithPermissionMultipleChoiceFilter(model=Instrument)
    allocation_pl = ModelExtWithPermissionMultipleChoiceFilter(model=Instrument)

    account_member = TransactionObjectPermissionMemberFilter(object_permission_model=Account)
    account_member_group = TransactionObjectPermissionGroupFilter(object_permission_model=Account)
    account_permission = TransactionObjectPermissionPermissionFilter(object_permission_model=Account)
    portfolio_member = TransactionObjectPermissionMemberFilter(object_permission_model=Portfolio)
    portfolio_member_group = TransactionObjectPermissionGroupFilter(object_permission_model=Portfolio)
    portfolio_permission = TransactionObjectPermissionPermissionFilter(object_permission_model=Portfolio)

    class Meta:
        model = Transaction
        fields = []


def get_transaction_queryset(select_related=True, complex_transaction_transactions=False):
    qs = Transaction.objects

    fields1 = (
        'master_user',
        'complex_transaction',
        'complex_transaction__transaction_type',
        'complex_transaction__transaction_type__group',
        'transaction_class',
        'instrument',
        'instrument__instrument_type',
        'instrument__instrument_type__instrument_class',
        'transaction_currency',
        'settlement_currency',
        'portfolio',
        'account_cash',
        'account_cash__type',
        'account_position',
        'account_position__type',
        'account_interim',
        'account_interim__type',
        'strategy1_position',
        'strategy1_position__subgroup',
        'strategy1_position__subgroup__group',
        'strategy1_cash',
        'strategy1_cash__subgroup',
        'strategy1_cash__subgroup__group',
        'strategy2_position',
        'strategy2_position__subgroup',
        'strategy2_position__subgroup__group',
        'strategy2_cash',
        'strategy2_cash__subgroup',
        'strategy2_cash__subgroup__group',
        'strategy3_position',
        'strategy3_position__subgroup',
        'strategy3_position__subgroup__group',
        'strategy3_cash',
        'strategy3_cash__subgroup',
        'strategy3_cash__subgroup__group',
        'responsible',
        'responsible__group',
        'counterparty',
        'counterparty__group',
        'linked_instrument',
        'linked_instrument__instrument_type',
        'linked_instrument__instrument_type__instrument_class',
        'allocation_balance',
        'allocation_balance__instrument_type',
        'allocation_balance__instrument_type__instrument_class',
        'allocation_pl',
        'allocation_pl__instrument_type',
        'allocation_pl__instrument_type__instrument_class',
    )
    if select_related:
        qs = qs.select_related(*fields1)
    else:
        qs = qs.prefetch_related(*fields1)

    qs = qs.prefetch_related(
        get_attributes_prefetch(),
        *get_permissions_prefetch_lookups(
            ('complex_transaction__transaction_type', TransactionType),
            ('complex_transaction__transaction_type__group', TransactionTypeGroup),
            ('portfolio', Portfolio),
            ('instrument', Instrument),
            ('instrument__instrument_type', InstrumentType),
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

    if complex_transaction_transactions:
        qs = qs.prefetch_related(
            Prefetch(
                'complex_transaction__transactions',
                queryset=get_transaction_queryset(select_related=select_related).order_by(
                    'complex_transaction_order', 'transaction_date'
                )
            )
        )

    return qs


def get_complex_transaction_queryset(select_related=True, transactions=False):
    fields1 = (
        'transaction_type',
        'transaction_type__group',
    )
    qs = ComplexTransaction.objects

    if select_related:
        qs = qs.select_related(*fields1)
    else:
        qs = qs.prefetch_related(*fields1)

    qs = qs.prefetch_related(
        get_attributes_prefetch(),
        *get_permissions_prefetch_lookups(
            ('transaction_type', TransactionType),
            ('transaction_type__group', TransactionTypeGroup),
        )
    )

    if transactions:
        qs = qs.prefetch_related(
            Prefetch(
                'transactions',
                queryset=get_transaction_queryset(select_related=select_related).order_by(
                    'transaction_date', 'complex_transaction_order',
                )
            )
        )

    return qs


class TransactionViewSet(AbstractModelViewSet):
    queryset = get_transaction_queryset(select_related=False, complex_transaction_transactions=True)
    # queryset = Transaction.objects.select_related(
    #     'master_user',
    #     'complex_transaction',
    #     'complex_transaction__transaction_type',
    #     'complex_transaction__transaction_type__group',
    #     'transaction_class',
    #     'instrument',
    #     'instrument__instrument_type',
    #     'instrument__instrument_type__instrument_class',
    #     'transaction_currency',
    #     'settlement_currency',
    #     'portfolio',
    #     'account_cash',
    #     'account_cash__type',
    #     'account_position',
    #     'account_position__type',
    #     'account_interim',
    #     'account_interim__type',
    #     'strategy1_position',
    #     'strategy1_position__subgroup',
    #     'strategy1_position__subgroup__group',
    #     'strategy1_cash',
    #     'strategy1_cash__subgroup',
    #     'strategy1_cash__subgroup__group',
    #     'strategy2_position',
    #     'strategy2_position__subgroup',
    #     'strategy2_position__subgroup__group',
    #     'strategy2_cash',
    #     'strategy2_cash__subgroup',
    #     'strategy2_cash__subgroup__group',
    #     'strategy3_position',
    #     'strategy3_position__subgroup',
    #     'strategy3_position__subgroup__group',
    #     'strategy3_cash',
    #     'strategy3_cash__subgroup',
    #     'strategy3_cash__subgroup__group',
    #     'responsible',
    #     'responsible__group',
    #     'counterparty',
    #     'counterparty__group',
    #     'linked_instrument',
    #     'linked_instrument__instrument_type',
    #     'linked_instrument__instrument_type__instrument_class',
    #     'allocation_balance',
    #     'allocation_balance__instrument_type',
    #     'allocation_balance__instrument_type__instrument_class',
    #     'allocation_pl',
    #     'allocation_pl__instrument_type',
    #     'allocation_pl__instrument_type__instrument_class',
    # ).prefetch_related(
    #     get_attributes_prefetch(),
    #     *get_permissions_prefetch_lookups(
    #         ('portfolio', Portfolio),
    #         ('instrument', Instrument),
    #         ('instrument__instrument_type', InstrumentType),
    #         ('account_cash', Account),
    #         ('account_cash__type', AccountType),
    #         ('account_position', Account),
    #         ('account_position__type', AccountType),
    #         ('account_interim', Account),
    #         ('account_interim__type', AccountType),
    #         ('strategy1_position', Strategy1),
    #         ('strategy1_position__subgroup', Strategy1Subgroup),
    #         ('strategy1_position__subgroup__group', Strategy1Group),
    #         ('strategy1_cash', Strategy1),
    #         ('strategy1_cash__subgroup', Strategy1Subgroup),
    #         ('strategy1_cash__subgroup__group', Strategy1Group),
    #         ('strategy2_position', Strategy2),
    #         ('strategy2_position__subgroup', Strategy2Subgroup),
    #         ('strategy2_position__subgroup__group', Strategy2Group),
    #         ('strategy2_cash', Strategy2),
    #         ('strategy2_cash__subgroup', Strategy2Subgroup),
    #         ('strategy2_cash__subgroup__group', Strategy2Group),
    #         ('strategy3_position', Strategy3),
    #         ('strategy3_position__subgroup', Strategy3Subgroup),
    #         ('strategy3_position__subgroup__group', Strategy3Group),
    #         ('strategy3_cash', Strategy3),
    #         ('strategy3_cash__subgroup', Strategy3Subgroup),
    #         ('strategy3_cash__subgroup__group', Strategy3Group),
    #         ('responsible', Responsible),
    #         ('responsible__group', ResponsibleGroup),
    #         ('counterparty', Counterparty),
    #         ('counterparty__group', CounterpartyGroup),
    #         ('linked_instrument', Instrument),
    #         ('linked_instrument__instrument_type', InstrumentType),
    #         ('allocation_balance', Instrument),
    #         ('allocation_balance__instrument_type', InstrumentType),
    #         ('allocation_pl', Instrument),
    #         ('allocation_pl__instrument_type', InstrumentType),
    #     )
    # )
    serializer_class = TransactionSerializer
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        TransactionObjectPermissionFilter,
        AttributeFilter,
        GroupsAttributeFilter,
    ]
    permission_classes = AbstractModelViewSet.permission_classes + [
        TransactionObjectPermission,
    ]
    # filter_class = TransactionFilterSet
    ordering_fields = [
        'complex_transaction',
        'complex_transaction__code',
        'complex_transaction__date',
        'complex_transaction_order',
        'transaction_code',
        'portfolio',
        'portfolio__user_code',
        'portfolio__name',
        'portfolio__short_name',
        'portfolio__public_name',
        'instrument',
        'instrument__user_code',
        'instrument__name',
        'instrument__short_name',
        'instrument__public_name',
        'transaction_currency',
        'transaction_currency__user_code',
        'transaction_currency__name',
        'transaction_currency__short_name',
        'transaction_currency__public_name',
        'position_size_with_sign',
        'settlement_currency',
        'settlement_currency__user_code',
        'settlement_currency__name',
        'settlement_currency__short_name',
        'settlement_currency__public_name',
        'cash_consideration',
        'principal_with_sign',
        'carry_with_sign',
        'overheads_with_sign',
        'transaction_date',
        'accounting_date',
        'cash_date',
        'account_cash',
        'account_cash__user_code',
        'account_cash__name',
        'account_cash__short_name',
        'account_cash__public_name',
        'account_cash',
        'account_cash__user_code',
        'account_position__name',
        'account_position__short_name',
        'account_position__public_name',
        'account_interim',
        'account_interim__user_code',
        'account_interim__name',
        'account_interim__short_name',
        'account_interim__public_name',
        'strategy1_position',
        'strategy1_position__user_code',
        'strategy1_position__name',
        'strategy1_position__short_name',
        'strategy1_position__public_name',
        'strategy1_cash',
        'strategy1_cash__user_code',
        'strategy1_cash__name',
        'strategy1_cash__short_name',
        'strategy1_cash__public_name',
        'strategy2_position',
        'strategy2_position__user_code',
        'strategy2_position__name',
        'strategy2_position__short_name',
        'strategy2_position__public_name',
        'strategy2_cash',
        'strategy2_cash__user_code',
        'strategy2_cash__name',
        'strategy2_cash__short_name',
        'strategy2_cash__public_name',
        'strategy3_position',
        'strategy3_position__user_code',
        'strategy3_position__name',
        'strategy3_position__short_name',
        'strategy3_position__public_name',
        'strategy3_cash',
        'strategy3_cash__user_code',
        'strategy3_cash__name',
        'strategy3_cash__short_name',
        'strategy3_cash__public_name',
        'reference_fx_rate',
        'is_locked',
        'is_deleted',
        'factor',
        'trade_price',
        'principal_amount',
        'carry_amount',
        'overheads',
        'responsible',
        'responsible__user_code',
        'responsible__name',
        'responsible__short_name',
        'responsible__public_name',
        'counterparty',
        'counterparty__user_code',
        'counterparty__name',
        'counterparty__short_name',
        'counterparty__public_name',
        'linked_instrument',
        'linked_instrument__user_code',
        'linked_instrument__name',
        'linked_instrument__short_name',
        'linked_instrument__public_name',
        'allocation_balance',
        'allocation_balance__user_code',
        'allocation_balance__name',
        'allocation_balance__short_name',
        'allocation_balance__public_name',
        'allocation_pl',
        'allocation_pl__user_code',
        'allocation_pl__name',
        'allocation_pl__short_name',
        'allocation_pl__public_name',
    ]

    def perform_update(self, serializer):
        super(TransactionViewSet, self).perform_update(serializer)
        serializer.instance.calc_cash_by_formulas()

    def perform_destroy(self, instance):
        super(TransactionViewSet, self).perform_destroy(instance)
        instance.calc_cash_by_formulas()


class TransactionEvGroupViewSet(AbstractEvGroupWithObjectPermissionViewSet, CustomPaginationMixin):
    queryset = get_transaction_queryset(select_related=False, complex_transaction_transactions=True)
    serializer_class = TransactionSerializer
    pagination_class = api_settings.DEFAULT_PAGINATION_CLASS
    # filter_class = TransactionFilterSet

    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter
    ]


class ComplexTransactionAttributeTypeViewSet(GenericAttributeTypeViewSet):
    target_model = ComplexTransaction
    target_model_serializer = ComplexTransactionSerializer


class ComplexTransactionFilterSet(FilterSet):
    id = NoOpFilter()
    code = django_filters.RangeFilter()
    date = django_filters.DateFromToRangeFilter()
    is_deleted = django_filters.BooleanFilter()
    transaction_type = ModelExtWithPermissionMultipleChoiceFilter(model=TransactionType)

    class Meta:
        model = ComplexTransaction
        fields = []


# class ComplexTransactionViewSet(AbstractModelViewSet):
class ComplexTransactionViewSet(AbstractWithObjectPermissionViewSet):
    queryset = get_complex_transaction_queryset(select_related=False, transactions=True)
    serializer_class = ComplexTransactionSerializer

    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        # ComplexTransactionPermissionFilter,
        OwnerByMasterUserFilter,
        AttributeFilter,
        GroupsAttributeFilter,
    ]
    # filter_class = ComplexTransactionFilterSet
    ordering_fields = [
        'date',
        'code',
        'is_deleted',
    ]

    # def perform_update(self, serializer):
    #     if serializer.is_locked:
    #         raise PermissionDenied()
    #     return super(ComplexTransactionViewSet, self).perform_update(serializer)

    def perform_destroy(self, instance):

        Transaction.objects.filter(
            complex_transaction=instance
        ).delete()

        ComplexTransaction.objects.get(id=instance.id).delete()

    @action(detail=True, methods=['get', 'put'], url_path='rebook', serializer_class=TransactionTypeProcessSerializer)
    def rebook(self, request, pk=None):
        complex_transaction = self.get_object()

        # if request.method != 'GET':
        #     complex_transaction.status = ComplexTransaction.PRODUCTION

        print('detail_route: /rebook: process rebook')

        instance = TransactionTypeProcess(transaction_type=complex_transaction.transaction_type,
                                          process_mode='rebook',
                                          complex_transaction=complex_transaction,
                                          context=self.get_serializer_context())
        if request.method == 'GET':
            serializer = self.get_serializer(instance=instance)
            return Response(serializer.data)
        else:
            try:
                history.set_flag_change()

                if request.data['complex_transaction']:
                    request.data['complex_transaction']['status'] = ComplexTransaction.PRODUCTION

                serializer = self.get_serializer(instance=instance, data=request.data)
                serializer.is_valid(raise_exception=True)
                serializer.save()

                history.set_actor_content_object(complex_transaction)

                return Response(serializer.data)
            finally:
                if instance.has_errors:
                    transaction.set_rollback(True)

    @action(detail=True, methods=['get', 'put'], url_path='rebook-pending', serializer_class=TransactionTypeProcessSerializer)
    def rebook_pending(self, request, pk=None):

        complex_transaction = self.get_object()

        complex_transaction.status = ComplexTransaction.PENDING

        instance = TransactionTypeProcess(transaction_type=complex_transaction.transaction_type,
                                          process_mode='rebook',
                                          complex_transaction=complex_transaction,
                                          context=self.get_serializer_context())
        if request.method == 'GET':
            serializer = self.get_serializer(instance=instance)
            return Response(serializer.data)
        else:
            try:
                history.set_flag_change()

                serializer = self.get_serializer(instance=instance, data=request.data)
                serializer.is_valid(raise_exception=True)
                serializer.save()

                history.set_actor_content_object(complex_transaction)

                return Response(serializer.data)
            finally:
                if instance.has_errors:
                    transaction.set_rollback(True)

    @action(detail=True, methods=['put'], url_path='update-properties', serializer_class=ComplexTransactionSimpleSerializer)
    def update_properties(self, request, pk=None):
        complex_transaction = self.get_object()

        # if request.method != 'GET':
        #     complex_transaction.status = ComplexTransaction.PRODUCTION

        # print('request.data %s' % request.data)
        print('detail_route: /update_properties: process update_properties')

        serializer = self.get_serializer(instance=complex_transaction, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        history.set_actor_content_object(complex_transaction)

        return Response(serializer.data)

    @action(detail=False, methods=['put', 'patch'], url_path='bulk-update-properties', serializer_class=ComplexTransactionSimpleSerializer)
    def bulk_update_properties(self, request):
        data = request.data
        if not isinstance(data, list):
            raise ValidationError(ugettext_lazy('Required list'))

        partial = request.method.lower() == 'patch'
        # queryset = self.filter_queryset(self.get_queryset())
        queryset = self.get_queryset()

        has_error = False
        serializers = []
        for adata in data:
            pk = adata['id']
            try:
                instance = queryset.get(pk=pk)
            except ObjectDoesNotExist:
                has_error = True
                serializers.append(None)
            else:
                try:
                    self.check_object_permissions(request, instance)
                except PermissionDenied:
                    raise

                serializer = self.get_serializer(instance=instance, data=adata, partial=partial)
                if not serializer.is_valid(raise_exception=False):
                    has_error = True
                serializers.append(serializer)

        if has_error:
            errors = []
            for serializer in serializers:
                if serializer:
                    errors.append(serializer.errors)
                else:
                    errors.append({
                        api_settings.NON_FIELD_ERRORS_KEY: ugettext_lazy('Not Found')
                    })
            raise ValidationError(errors)
        else:
            instances = []
            for serializer in serializers:
                self.perform_update(serializer)
                instances.append(serializer.instance)

            ret_serializer = self.get_serializer(
                instance=queryset.filter(pk__in=(i.id for i in instances)), many=True)
            return Response(list(ret_serializer.data), status=status.HTTP_200_OK)



class ComplexTransactionEvGroupViewSet(AbstractEvGroupWithObjectPermissionViewSet, CustomPaginationMixin):
    queryset = get_complex_transaction_queryset(select_related=False, transactions=True)
    serializer_class = ComplexTransactionSerializer
    pagination_class = api_settings.DEFAULT_PAGINATION_CLASS
    # filter_class = ComplexTransactionFilterSet

    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        # ComplexTransactionPermissionFilter,
        OwnerByMasterUserFilter,
        AttributeFilter
    ]


class ComplexTransactionLightViewSet(AbstractWithObjectPermissionViewSet):
    queryset = qs = ComplexTransaction.objects.select_related(
        'transaction_type',
        'transaction_type__group',
    ).prefetch_related(
        get_attributes_prefetch(),
        *get_permissions_prefetch_lookups(
            ('transaction_type', TransactionType),
            ('transaction_type__group', TransactionTypeGroup),
        )
    )

    serializer_class = ComplexTransactionLightSerializer

    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        # ComplexTransactionPermissionFilter,
        OwnerByMasterUserFilter,
        AttributeFilter,
        GroupsAttributeFilter,
    ]
    # filter_class = ComplexTransactionFilterSet
    ordering_fields = [
        'date',
        'code',
        'is_deleted',
    ]


class ComplexTransactionLightEvGroupViewSet(AbstractEvGroupWithObjectPermissionViewSet, CustomPaginationMixin):
    queryset = get_complex_transaction_queryset(select_related=False, transactions=True)
    serializer_class = ComplexTransactionLightSerializer
    pagination_class = api_settings.DEFAULT_PAGINATION_CLASS
    # filter_class = ComplexTransactionFilterSet

    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        # ComplexTransactionPermissionFilter,
        OwnerByMasterUserFilter,
        AttributeFilter
    ]


class RecalculatePermissionTransactionViewSet(AbstractAsyncViewSet):
    serializer_class = RecalculatePermissionTransactionSerializer
    celery_task = recalculate_permissions_transaction


class RecalculatePermissionComplexTransactionViewSet(AbstractAsyncViewSet):
    serializer_class = RecalculatePermissionComplexTransactionSerializer
    celery_task = recalculate_permissions_complex_transaction
