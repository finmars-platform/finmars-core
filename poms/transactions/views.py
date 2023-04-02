from __future__ import unicode_literals

import logging
import time

import django_filters
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import Prefetch, Q
from django.utils.translation import gettext_lazy
from django_filters.rest_framework import FilterSet
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.settings import api_settings

from poms.accounts.models import Account, AccountType
from poms.common.filters import CharFilter, ModelExtWithPermissionMultipleChoiceFilter, ModelExtMultipleChoiceFilter, \
    NoOpFilter, AttributeFilter, GroupsAttributeFilter, EntitySpecificFilter, ComplexTransactionStatusFilter
from poms.common.pagination import CustomPaginationMixin
from poms.common.views import AbstractClassModelViewSet, AbstractAsyncViewSet
from poms.counterparties.models import Responsible, Counterparty, ResponsibleGroup, CounterpartyGroup
from poms.currencies.models import Currency
from poms.instruments.models import Instrument, InstrumentType, PricingPolicy
from poms.obj_attrs.utils import get_attributes_prefetch
from poms.obj_attrs.views import GenericAttributeTypeViewSet, \
    GenericClassifierViewSet
from poms.obj_perms.filters import ObjectPermissionMemberFilter, ObjectPermissionGroupFilter, \
    ObjectPermissionPermissionFilter
from poms.obj_perms.permissions import PomsConfigurationPermission
from poms.obj_perms.utils import get_permissions_prefetch_lookups
from poms.obj_perms.views import AbstractWithObjectPermissionViewSet, AbstractEvGroupWithObjectPermissionViewSet
from poms.portfolios.models import Portfolio
from poms.strategies.models import Strategy1, Strategy2, Strategy3, Strategy1Subgroup, Strategy1Group, \
    Strategy2Subgroup, Strategy2Group, Strategy3Subgroup, Strategy3Group
from poms.transactions.filters import TransactionObjectPermissionMemberFilter, TransactionObjectPermissionGroupFilter, \
    TransactionObjectPermissionPermissionFilter, ComplexTransactionSpecificFilter
from poms.transactions.handlers import TransactionTypeProcess
from poms.transactions.models import TransactionClass, Transaction, TransactionType, TransactionTypeGroup, \
    ComplexTransaction, EventClass, NotificationClass
from poms.transactions.serializers import TransactionClassSerializer, TransactionSerializer, TransactionTypeSerializer, \
    TransactionTypeProcessSerializer, TransactionTypeGroupSerializer, ComplexTransactionSerializer, \
    EventClassSerializer, NotificationClassSerializer, TransactionTypeLightSerializer, \
    ComplexTransactionLightSerializer, ComplexTransactionSimpleSerializer, \
    RecalculatePermissionTransactionSerializer, RecalculatePermissionComplexTransactionSerializer, \
    TransactionTypeLightSerializerWithInputs, TransactionTypeEvSerializer, ComplexTransactionEvSerializer, \
    TransactionEvSerializer, TransactionTypeRecalculateSerializer, RecalculateUserFieldsSerializer, \
    ComplexTransactionViewOnlySerializer, ComplexTransactionViewOnly
from poms.transactions.tasks import recalculate_permissions_transaction, recalculate_permissions_complex_transaction, \
    recalculate_user_fields
from poms.users.filters import OwnerByMasterUserFilter

_l = logging.getLogger('poms.transactions')


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
    member = ObjectPermissionMemberFilter(object_permission_model=TransactionTypeGroup)
    member_group = ObjectPermissionGroupFilter(object_permission_model=TransactionTypeGroup)
    permission = ObjectPermissionPermissionFilter(object_permission_model=TransactionTypeGroup)

    class Meta:
        model = TransactionTypeGroup
        fields = []


class TransactionTypeGroupViewSet(AbstractWithObjectPermissionViewSet):
    queryset = TransactionTypeGroup.objects.prefetch_related(
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
    member = ObjectPermissionMemberFilter(object_permission_model=TransactionType)
    member_group = ObjectPermissionGroupFilter(object_permission_model=TransactionType)
    permission = ObjectPermissionPermissionFilter(object_permission_model=TransactionType)

    class Meta:
        model = TransactionType
        fields = []


class TransactionTypeAttributeTypeViewSet(GenericAttributeTypeViewSet):
    target_model = TransactionType
    target_model_serializer = TransactionTypeSerializer

    permission_classes = GenericAttributeTypeViewSet.permission_classes + [
        PomsConfigurationPermission
    ]


class TransactionTypeEvFilterSet(FilterSet):
    id = NoOpFilter()
    user_code = CharFilter()
    name = CharFilter()
    short_name = CharFilter()
    public_name = CharFilter()
    group = ModelExtWithPermissionMultipleChoiceFilter(model=TransactionTypeGroup)
    is_valid_for_all_portfolios = django_filters.BooleanFilter()
    is_valid_for_all_instruments = django_filters.BooleanFilter()
    member = ObjectPermissionMemberFilter(object_permission_model=TransactionType)
    member_group = ObjectPermissionGroupFilter(object_permission_model=TransactionType)
    permission = ObjectPermissionPermissionFilter(object_permission_model=TransactionType)

    class Meta:
        model = TransactionType
        fields = []


class TransactionTypeEvViewSet(AbstractWithObjectPermissionViewSet):
    queryset = TransactionType.objects \
        .select_related('group') \
        .prefetch_related(
        'portfolios',
        'instrument_types',
        # get_attributes_prefetch(),
        'attributes',
        'attributes__classifier',
        *get_permissions_prefetch_lookups(
            (None, TransactionType),
            ('group', TransactionTypeGroup),
        )
    )
    serializer_class = TransactionTypeEvSerializer
    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter,
        GroupsAttributeFilter,
        EntitySpecificFilter
    ]
    filter_class = TransactionTypeEvFilterSet
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


# DEPRECATED
class TransactionTypeLightViewSet(AbstractWithObjectPermissionViewSet):
    queryset = TransactionType.objects.select_related('group').prefetch_related(
        'portfolios',
        'instrument_types',
        get_attributes_prefetch(),
        *get_permissions_prefetch_lookups(
            (None, TransactionType),
            ('group', TransactionTypeGroup),
        )
    )
    serializer_class = TransactionTypeLightSerializer
    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter
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


# DEPRECATED
class TransactionTypeLightWithInputsViewSet(AbstractWithObjectPermissionViewSet):
    queryset = TransactionType.objects.select_related('group').prefetch_related(
        'portfolios',
        'instrument_types',
        'inputs',
        'context_parameters',
        get_attributes_prefetch(),
        *get_permissions_prefetch_lookups(
            (None, TransactionType),
            ('group', TransactionTypeGroup),
        )
    )
    serializer_class = TransactionTypeLightSerializerWithInputs
    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter,
        GroupsAttributeFilter,
        EntitySpecificFilter
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
        AttributeFilter,
        EntitySpecificFilter
    ]


class TransactionTypeViewSet(AbstractWithObjectPermissionViewSet):
    queryset = TransactionType.objects
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

    @action(detail=False, methods=['get'], url_path='light', serializer_class=TransactionTypeLightSerializer)
    def list_light(self, request, *args, **kwargs):

        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginator.post_paginate_queryset(queryset, request)
        serializer = self.get_serializer(page, many=True)

        result = self.get_paginated_response(serializer.data)

        return result

    @action(detail=False, methods=['get'], url_path='light-with-inputs',
            serializer_class=TransactionTypeLightSerializerWithInputs)
    def list_light_with_inputs(self, request, *args, **kwargs):

        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginator.post_paginate_queryset(queryset, request)
        serializer = self.get_serializer(page, many=True)

        result = self.get_paginated_response(serializer.data)

        return result

    def get_context_for_book(self, request):

        master_user = request.user.master_user
        context_values = {}

        instrument_id = request.query_params.get('context_instrument', None)
        pricing_currency_id = request.query_params.get('context_pricing_currency', None)
        accrued_currency_id = request.query_params.get('context_accrued_currency', None)
        portfolio_id = request.query_params.get('context_portfolio', None)
        account_id = request.query_params.get('context_account', None)
        strategy1_id = request.query_params.get('context_strategy1', None)
        strategy2_id = request.query_params.get('context_strategy2', None)
        strategy3_id = request.query_params.get('context_strategy3', None)

        currency_id = request.query_params.get('context_currency', None)
        pricing_policy_id = request.query_params.get('context_pricing_policy', None)
        allocation_balance_id = request.query_params.get('context_allocation_balance', None)
        allocation_pl_id = request.query_params.get('context_allocation_pl', None)

        context_instrument = None
        context_pricing_currency = None
        context_accrued_currency = None
        context_portfolio = None
        context_account = None
        context_strategy1 = None
        context_strategy2 = None
        context_strategy3 = None

        context_currency = None
        context_pricing_policy = None
        context_allocation_balance = None
        context_allocation_pl = None

        context_position_size = request.query_params.get('context_position_size', None)

        if context_position_size:
            try:
                context_position_size = float(context_position_size)
            except Exception as e:
                context_position_size = None

        context_effective_date = request.query_params.get('context_effective_date', None)
        context_notification_date = request.query_params.get('context_notification_date', None)
        context_final_date = request.query_params.get('context_final_date', None)
        context_maturity_date = request.query_params.get('context_maturity_date', None)

        context_report_date = request.query_params.get('context_report_date', None)
        context_report_start_date = request.query_params.get('context_report_start_date', None)

        if pricing_policy_id:
            try:
                context_pricing_policy = PricingPolicy.objects.get(master_user=master_user, id=pricing_policy_id)
            except PricingPolicy.DoesNotExist:
                context_pricing_policy = None

        if currency_id:
            try:
                context_currency = Currency.objects.get(master_user=master_user, id=currency_id)
            except Currency.DoesNotExist:
                context_currency = None

        if allocation_balance_id:
            try:
                context_allocation_balance = Instrument.objects.get(master_user=master_user, id=allocation_balance_id)
            except Instrument.DoesNotExist:
                context_allocation_balance = None

        if allocation_pl_id:
            try:
                context_allocation_pl = Instrument.objects.get(master_user=master_user, id=allocation_pl_id)
            except Instrument.DoesNotExist:
                context_allocation_pl = None

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
            'context_instrument': context_instrument,
            'context_pricing_currency': context_pricing_currency,
            'context_accrued_currency': context_accrued_currency,
            'context_portfolio': context_portfolio,
            'context_account': context_account,
            'context_strategy1': context_strategy1,
            'context_strategy2': context_strategy2,
            'context_strategy3': context_strategy3,
            'context_position_size': context_position_size,
            'context_effective_date': context_effective_date,
            # 'notification_date': context_notification_date, # not in context variables
            # 'final_date': context_final_date,
            # 'maturity_date': context_maturity_date,

            'context_currency': context_currency,
            'context_report_date': context_report_date,
            'context_report_start_date': context_report_start_date,
            'context_pricing_policy': context_pricing_policy,
            'context_allocation_balance': context_allocation_balance,
            'context_allocation_pl': context_allocation_pl
        })

        context_values['context_parameter'] = request.query_params.get('context_parameter', None)

        context_parameter_exist = True
        increment = 1
        while context_parameter_exist:

            try:
                parameter = request.query_params.get('context_parameter' + str(increment), None)

                if parameter:
                    context_values['context_parameter' + str(increment)] = parameter
                    increment = increment + 1
                else:
                    context_parameter_exist = False
            except Exception as e:
                context_parameter_exist = False

        return context_values

    @action(detail=True, methods=['get', 'put'], url_path='book', serializer_class=TransactionTypeProcessSerializer)
    def book(self, request, pk=None):

        # Some Inputs can choose from which context variable it will take value
        context_values = self.get_context_for_book(request)
        # But by default Context Variables overwrites default value
        # default_values = self.get_context_for_book(request)

        # print("default_values %s" % default_values)
        print("context_values %s" % context_values)
        print("pk %s" % pk)

        transaction_type = TransactionType.objects.get(pk=pk)

        if request.method == 'GET':

            instance = TransactionTypeProcess(process_mode='book', transaction_type=transaction_type,
                                              context=self.get_serializer_context(), context_values=context_values,
                                              member=request.user.member)

            instance.complex_transaction.id = 0

            serializer = self.get_serializer(instance=instance)
            return Response(serializer.data)
        else:

            complex_transaction_status = request.data['complex_transaction_status']

            uniqueness_reaction = request.data.get('uniqueness_reaction', None)

            instance = TransactionTypeProcess(process_mode=request.data['process_mode'],
                                              transaction_type=transaction_type,
                                              context=self.get_serializer_context(), context_values=context_values,
                                              complex_transaction_status=complex_transaction_status,
                                              uniqueness_reaction=uniqueness_reaction, member=request.user.member)

            try:

                serializer = self.get_serializer(instance=instance, data=request.data)
                serializer.is_valid(raise_exception=True)
                serializer.save()

                return Response(serializer.data)
            finally:
                if instance.has_errors:
                    transaction.set_rollback(True)

    @action(detail=True, methods=['get', 'put'], url_path='book-pending',
            serializer_class=TransactionTypeProcessSerializer)
    def book_pending(self, request, pk=None):

        complex_transaction_status = ComplexTransaction.PENDING

        transaction_type = TransactionType.objects.get(pk=pk)

        instance = TransactionTypeProcess(process_mode='book', transaction_type=transaction_type,
                                          context=self.get_serializer_context(),
                                          complex_transaction_status=complex_transaction_status,
                                          member=request.user.member)

        if request.method == 'GET':
            serializer = self.get_serializer(instance=instance)
            return Response(serializer.data)
        else:
            try:
                serializer = self.get_serializer(instance=instance, data=request.data)
                serializer.is_valid(raise_exception=True)
                serializer.save()
                return Response(serializer.data)
            finally:
                if instance.has_errors:
                    transaction.set_rollback(True)

    @action(detail=True, methods=['get', 'put'], url_path='recalculate',
            serializer_class=TransactionTypeRecalculateSerializer, permission_classes=[IsAuthenticated])
    def recalculate(self, request, pk=None):

        st = time.perf_counter()

        complex_transaction_status = ComplexTransaction.PRODUCTION

        transaction_type = TransactionType.objects.get(pk=pk)

        context_values = self.get_context_for_book(request)
        # But by default Context Variables overwrites default value
        # default_values = self.get_context_for_book(request)

        uniqueness_reaction = request.data.get('uniqueness_reaction', None)

        process_st = time.perf_counter()

        instance = TransactionTypeProcess(process_mode=request.data['process_mode'], transaction_type=transaction_type,
                                          context=self.get_serializer_context(), context_values=context_values,
                                          complex_transaction_status=complex_transaction_status,
                                          uniqueness_reaction=uniqueness_reaction, member=request.user.member)

        _l.debug('rebook TransactionTypeProcess done: %s', "{:3.3f}".format(time.perf_counter() - process_st))

        serializer = self.get_serializer(instance=instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='recalculate-user-fields',
            serializer_class=RecalculateUserFieldsSerializer)
    def recalculate_user_fields(self, request, pk):

        context = {'request': request}

        print('request.data %s' % request.data)

        serializer = RecalculateUserFieldsSerializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        task_id = instance.task_id

        # signer = TimestampSigner()

        print('instance %s' % instance)

        if task_id:

            # TODO import-like status check chain someday
            # TODO Right now is not important because status showed at Active Processes page
            return Response(serializer.data, status=status.HTTP_200_OK)

        else:

            instance.transaction_type_type_id = pk

            res = recalculate_user_fields.apply_async(kwargs={'instance': instance})

            # instance.task_id = signer.sign('%s' % res.id)
            instance.task_id = res.id
            instance.task_status = res.status

            print('instance.task_id %s' % instance.task_id)

            serializer = RecalculateUserFieldsSerializer(instance=instance, many=False)
            return Response(serializer.data, status=status.HTTP_200_OK)


class TransactionTypeEvGroupViewSet(AbstractEvGroupWithObjectPermissionViewSet, CustomPaginationMixin):
    queryset = TransactionType.objects.select_related(
        'group'
    ).prefetch_related(
        'portfolios',
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


class TransactionViewSet(AbstractWithObjectPermissionViewSet):
    queryset = get_transaction_queryset(select_related=False, complex_transaction_transactions=True)
    # queryset = get_transaction_queryset(select_related=False, complex_transaction_transactions=False)
    serializer_class = TransactionSerializer
    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        # TransactionObjectPermissionFilter,
        AttributeFilter,
        GroupsAttributeFilter,
    ]
    permission_classes = AbstractWithObjectPermissionViewSet.permission_classes + [
        # TransactionObjectPermission,
    ]
    filter_class = TransactionFilterSet
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
        # Deprecated 2023-03-10
        # serializer.instance.calc_cash_by_formulas()

    def perform_destroy(self, instance):
        super(TransactionViewSet, self).perform_destroy(instance)
        # Deprecated 2023-03-10
        # instance.calc_cash_by_formulas()

    @action(detail=False, methods=['get'], url_path='attributes')
    def list_attributes(self, request, *args, **kwargs):
        items = [
            {
                "key": "notes",
                "name": "Notes",
                "value_type": 10
            },
            {
                "key": "transaction_code",
                "name": "Transaction Code",
                "value_type": 20
            },
            {
                "key": "transaction_class",
                "name": "Transaction class",
                "value_content_type": "transactions.transactionclass",
                "value_entity": "transaction_class",
                "code": "user_code",
                "value_type": "field"
            },
            {
                "key": "portfolio",
                "name": "Portfolio",
                "value_content_type": "portfolios.portfolio",
                "value_entity": "portfolio",
                "code": "user_code",
                "value_type": "field"
            },
            {
                "key": "transaction_currency",
                "name": "Transaction currency",
                "value_type": "field"
            },
            {
                "key": "instrument",
                "name": "Instrument",
                "value_content_type": "instruments.instrument",
                "value_entity": "instrument",
                "code": "user_code",
                "value_type": "field"
            },
            {
                "key": "position_size_with_sign",
                "name": "Position Size with sign",
                "value_type": 20
            },
            {
                "key": "settlement_currency",
                "name": "Settlement currency",
                "value_type": "field"
            },
            {
                "key": "cash_consideration",
                "name": "Cash consideration",
                "value_type": 20
            },
            {
                "key": "principal_with_sign",
                "name": "Principal with sign",
                "value_type": 20
            },
            {
                "key": "carry_with_sign",
                "name": "Carry with sign",
                "value_type": 20
            },
            {
                "key": "overheads_with_sign",
                "name": "Overheads with sign",
                "value_type": 20
            },
            {
                "key": "accounting_date",
                "name": "Accounting date",
                "value_type": 40
            },
            {
                "key": "cash_date",
                "name": "Cash date",
                "value_type": 40
            },
            {
                "key": "account_cash",
                "name": "Account cash",
                "value_type": 'field'
            },
            {
                "key": "account_position",
                "name": "Account position",
                "value_type": 'field'
            },
            {
                "key": "account_interim",
                "name": "Account interim",
                "value_type": 'field'
            },
            {
                "key": "strategy1_position",
                "name": "Strategy1 position",
                "value_type": 'field'
            },
            {
                "key": "strategy1_cash",
                "name": "Strategy1 cash",
                "value_type": 'field'
            },
            {
                "key": "strategy2_position",
                "name": "Strategy2 position",
                "value_type": 'field'
            },
            {
                "key": "strategy2_cash",
                "name": "Strategy2 cash",
                "value_type": 'field'
            },
            {
                "key": "strategy3_position",
                "name": "Strategy3 position",
                "value_type": 'field'
            },
            {
                "key": "strategy3_cash",
                "name": "Strategy3 cash",
                "value_type": 'field'
            },
            {
                "key": "reference_fx_rate",
                "name": "Reference fx rate",
                "value_type": 20
            },
            {
                "key": "is_locked",
                "name": "Is locked",
                "value_type": 50
            },
            {
                "key": "is_canceled",
                "name": "Is canceled",
                "value_type": 50
            },
            {
                "key": "factor",
                "name": "Factor",
                "value_type": 20
            },
            {
                "key": "principal_amount",
                "name": "Principal amount",
                "value_type": 20
            },
            {
                "key": "carry_amount",
                "name": "Carry amount",
                "value_type": 20
            },
            {
                "key": "overheads",
                "name": "overheads",
                "value_type": 20
            },
            {
                "key": "responsible",
                "name": "Responsible",
                "value_content_type": "counterparties.responsible",
                "value_entity": "responsible",
                "code": "user_code",
                "value_type": 'field'
            },
            {
                "key": "counterparty",
                "name": "Counterparty",
                "value_content_type": "counterparties.counterparty",
                "value_entity": "counterparty",
                "code": "user_code",
                "value_type": 'field'
            },
            {
                "key": "trade_price",
                "name": "Trade price",
                "value_type": 20
            },
            {
                "key": "object_permissions_user",
                "name": "Users permissions",
                "value_type": "mc_field"
            },
            {
                "key": "object_permissions_group",
                "name": "Groups permissions",
                "value_type": "mc_field"
            },
            {
                "key": "allocation_balance",
                "name": "Allocation Balance",
                "value_content_type": "instruments.instrument",
                "value_entity": "instrument",
                "code": "user_code",
                "value_type": 'field'
            },
            {
                "key": "allocation_pl",
                "name": "Allocation P&L",
                "value_content_type": "instruments.instrument",
                "value_entity": "instrument",
                "code": "user_code",
                "value_type": 'field'
            },
            {
                "key": "linked_instrument",
                "name": "Linked instrument",
                "value_content_type": "instruments.instrument",
                "value_entity": "instrument",
                "code": "user_code",
                "value_type": 'field'
            }
        ]

        result = {
            "count": len(items),
            "next": None,
            "previous": None,
            "results": items
        }

        return Response(result)


class TransactionEvViewSet(AbstractWithObjectPermissionViewSet):
    queryset = qs = Transaction.objects.select_related(
        'master_user',
        'complex_transaction',
        'transaction_class',
        'instrument',
        'transaction_currency',
        'settlement_currency',
        'portfolio',
        'account_cash',
        'account_position',
        'account_interim',
        'strategy1_position',
        'strategy1_cash',
        'strategy2_position',
        'strategy2_cash',
        'strategy3_position',
        'strategy3_cash',
        'responsible',
        'counterparty',
        'linked_instrument',
        'allocation_balance',
        'allocation_pl',
    ).prefetch_related(
        *get_permissions_prefetch_lookups(
            (None, Transaction),
            ('complex_transaction', ComplexTransaction),
            ('portfolio', Portfolio),
            ('instrument', Instrument),
            ('account_cash', Account),
            ('account_position', Account),
            ('account_interim', Account),
            ('strategy1_position', Strategy1),
            ('strategy1_cash', Strategy1),
            ('strategy2_position', Strategy2),
            ('strategy2_cash', Strategy2),
            ('strategy3_position', Strategy3),
            ('strategy3_cash', Strategy3),
            ('responsible', Responsible),
            ('counterparty', Counterparty),
            ('linked_instrument', Instrument),
            ('allocation_balance', Instrument),
            ('allocation_pl', Instrument),
        )
    )
    serializer_class = TransactionEvSerializer
    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter,
        GroupsAttributeFilter,
    ]
    permission_classes = AbstractWithObjectPermissionViewSet.permission_classes + [
        # TransactionObjectPermission,
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
        # Deprecated 2023-03-10
        # serializer.instance.calc_cash_by_formulas()

    def perform_destroy(self, instance):
        super(TransactionViewSet, self).perform_destroy(instance)
        # Deprecated 2023-03-10
        # instance.calc_cash_by_formulas()


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

    @action(detail=False, methods=['get'], url_path='light', serializer_class=ComplexTransactionLightSerializer)
    def list_light(self, request, *args, **kwargs):

        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginator.post_paginate_queryset(queryset, request)
        serializer = self.get_serializer(page, many=True)

        result = self.get_paginated_response(serializer.data)

        return result

    @action(detail=False, methods=['get'], url_path='attributes')
    def list_attributes(self, request, *args, **kwargs):

        items = [
            {
                "key": "code",
                "name": "Code",
                "value_type": 20
            },
            {
                "key": "date",
                "name": "Date",
                "value_type": 40
            },
            {
                "key": "status",
                "name": "Status",
                "value_type": "field",
                "value_entity": "complex-transaction-status",
                "code": "user_code",
                "value_content_type": "transactions.complextransactionstatus",
            },
            {
                "key": "is_locked",
                "name": "Is locked",
                "value_type": 50
            },
            {
                "key": "is_canceled",
                "name": "Is canceled",
                "value_type": 50
            },
            {
                "key": "transaction_unique_code",
                "name": "Transaction Unique Code",
                "value_type": 10
            },
            {
                "key": "text",
                "name": "Description",
                "value_type": 10
            },
            {
                "key": "transaction_type",
                "name": "Transaction Type",
                "value_type": "field",
                "value_entity": "transaction-type",
                "code": "user_code",
                "value_content_type": "transactions.transactiontype",
            },

            {
                "key": "user_text_1",
                "name": "User Text 1",
                "value_type": 10
            },
            {
                "key": "user_text_2",
                "name": "User Text 2",
                "value_type": 10
            },

            {
                "key": "user_text_3",
                "name": "User Text 3",
                "value_type": 10
            },

            {
                "key": "user_text_4",
                "name": "User Text 4",
                "value_type": 10
            },

            {
                "key": "user_text_5",
                "name": "User Text 5",
                "value_type": 10
            },

            {
                "key": "user_text_6",
                "name": "User Text 6",
                "value_type": 10
            },

            {
                "key": "user_text_7",
                "name": "User Text 7",
                "value_type": 10
            },

            {
                "key": "user_text_8",
                "name": "User Text 8",
                "value_type": 10
            },

            {
                "key": "user_text_9",
                "name": "User Text 9",
                "value_type": 10
            },

            {
                "key": "user_text_10",
                "name": "User Text 10",
                "value_type": 10
            },

            {
                "key": "user_text_11",
                "name": "User Text 11",
                "value_type": 10
            },
            {
                "key": "user_text_12",
                "name": "User Text 12",
                "value_type": 10
            },

            {
                "key": "user_text_13",
                "name": "User Text 13",
                "value_type": 10
            },

            {
                "key": "user_text_14",
                "name": "User Text 14",
                "value_type": 10
            },

            {
                "key": "user_text_15",
                "name": "User Text 15",
                "value_type": 10
            },

            {
                "key": "user_text_16",
                "name": "User Text 16",
                "value_type": 10
            },

            {
                "key": "user_text_17",
                "name": "User Text 17",
                "value_type": 10
            },

            {
                "key": "user_text_18",
                "name": "User Text 18",
                "value_type": 10
            },

            {
                "key": "user_text_19",
                "name": "User Text 19",
                "value_type": 10
            },

            {
                "key": "user_text_20",
                "name": "User Text 20",
                "value_type": 10
            },

            {
                "key": "user_text_21",
                "name": "User Text 21",
                "value_type": 10
            },
            {
                "key": "user_text_22",
                "name": "User Text 22",
                "value_type": 10
            },

            {
                "key": "user_text_23",
                "name": "User Text 23",
                "value_type": 10
            },

            {
                "key": "user_text_24",
                "name": "User Text 24",
                "value_type": 10
            },

            {
                "key": "user_text_25",
                "name": "User Text 25",
                "value_type": 10
            },

            {
                "key": "user_text_26",
                "name": "User Text 26",
                "value_type": 10
            },

            {
                "key": "user_text_27",
                "name": "User Text 27",
                "value_type": 10
            },

            {
                "key": "user_text_28",
                "name": "User Text 28",
                "value_type": 10
            },

            {
                "key": "user_text_29",
                "name": "User Text 29",
                "value_type": 10
            },

            {
                "key": "user_text_30",
                "name": "User Text 30",
                "value_type": 10
            },

            {
                "key": "user_number_1",
                "name": "User Number 1",
                "value_type": 20
            },
            {
                "key": "user_number_2",
                "name": "User Number 2",
                "value_type": 20
            },

            {
                "key": "user_number_3",
                "name": "User Number 3",
                "value_type": 20
            },

            {
                "key": "user_number_4",
                "name": "User Number 4",
                "value_type": 20
            },

            {
                "key": "user_number_5",
                "name": "User Number 5",
                "value_type": 20
            },

            {
                "key": "user_number_6",
                "name": "User Number 6",
                "value_type": 20
            },

            {
                "key": "user_number_7",
                "name": "User Number 7",
                "value_type": 20
            },

            {
                "key": "user_number_8",
                "name": "User Number 8",
                "value_type": 20
            },

            {
                "key": "user_number_9",
                "name": "User Number 9",
                "value_type": 20
            },

            {
                "key": "user_number_10",
                "name": "User Number 10",
                "value_type": 20
            },
            {
                "key": "user_number_11",
                "name": "User Number 11",
                "value_type": 20
            },
            {
                "key": "user_number_12",
                "name": "User Number 12",
                "value_type": 20
            },

            {
                "key": "user_number_13",
                "name": "User Number 13",
                "value_type": 20
            },

            {
                "key": "user_number_14",
                "name": "User Number 14",
                "value_type": 20
            },

            {
                "key": "user_number_15",
                "name": "User Number 15",
                "value_type": 20
            },

            {
                "key": "user_number_16",
                "name": "User Number 16",
                "value_type": 20
            },

            {
                "key": "user_number_17",
                "name": "User Number 17",
                "value_type": 20
            },

            {
                "key": "user_number_18",
                "name": "User Number 18",
                "value_type": 20
            },

            {
                "key": "user_number_19",
                "name": "User Number 19",
                "value_type": 20
            },

            {
                "key": "user_number_20",
                "name": "User Number 20",
                "value_type": 20
            },

            {
                "key": "user_date_1",
                "name": "User Date 1",
                "value_type": 40
            },
            {
                "key": "user_date_2",
                "name": "User Date 2",
                "value_type": 40
            },
            {
                "key": "user_date_3",
                "name": "User Date 3",
                "value_type": 40
            },
            {
                "key": "user_date_4",
                "name": "User Date 4",
                "value_type": 40
            },
            {
                "key": "user_date_5",
                "name": "User Date 5",
                "value_type": 40
            }
        ]

        result = {
            "count": len(items),
            "next": None,
            "previous": None,
            "results": items
        }

        return Response(result)

    # def perform_update(self, serializer):
    #     if serializer.is_locked:
    #         raise PermissionDenied()
    #     return super(ComplexTransactionViewSet, self).perform_update(serializer)

    @action(detail=True, methods=['get', 'put'], url_path='rebook', serializer_class=TransactionTypeProcessSerializer,
            permission_classes=[IsAuthenticated])
    def rebook(self, request, pk=None):
        complex_transaction = self.get_object()

        if request.method == 'GET':

            instance = TransactionTypeProcess(transaction_type=complex_transaction.transaction_type,
                                              process_mode='rebook',
                                              complex_transaction=complex_transaction,
                                              clear_execution_log=False,
                                              record_execution_log=False,
                                              context=self.get_serializer_context(), member=request.user.member)

            serializer = self.get_serializer(instance=instance)
            return Response(serializer.data)
        else:

            st = time.perf_counter()

            _l.info('complex tt status %s' % request.data['complex_transaction_status'])

            uniqueness_reaction = request.data.get('uniqueness_reaction', None)

            # complex_transaction.execution_log = ''

            instance = TransactionTypeProcess(transaction_type=complex_transaction.transaction_type,
                                              process_mode=request.data['process_mode'],
                                              complex_transaction=complex_transaction,
                                              complex_transaction_status=request.data['complex_transaction_status'],
                                              context=self.get_serializer_context(),
                                              uniqueness_reaction=uniqueness_reaction, member=request.user.member)

            _l.info("==== INIT REBOOK ====")

            try:

                if request.data['complex_transaction']:
                    if not request.data['complex_transaction']['status']:
                        request.data['complex_transaction']['status'] = ComplexTransaction.PRODUCTION

                serializer = self.get_serializer(instance=instance, data=request.data)
                serializer.is_valid(raise_exception=True)
                serializer.save()

                return Response(serializer.data)

            finally:

                _l.debug('rebook done: %s', "{:3.3f}".format(time.perf_counter() - st))

                if instance.has_errors:
                    transaction.set_rollback(True)

    @action(detail=True, methods=['get', 'put'], url_path='recalculate',
            serializer_class=TransactionTypeRecalculateSerializer, permission_classes=[IsAuthenticated])
    def recalculate(self, request, pk=None):

        st = time.perf_counter()

        complex_transaction = self.get_object()

        uniqueness_reaction = request.data.get('uniqueness_reaction', None)

        process_st = time.perf_counter()

        instance = TransactionTypeProcess(transaction_type=complex_transaction.transaction_type,
                                          process_mode=request.data['process_mode'],
                                          complex_transaction=complex_transaction,
                                          context=self.get_serializer_context(),
                                          uniqueness_reaction=uniqueness_reaction, member=request.user.member)

        _l.debug('rebook TransactionTypeProcess done: %s', "{:3.3f}".format(time.perf_counter() - process_st))

        if request.data['complex_transaction']:
            request.data['complex_transaction']['status'] = ComplexTransaction.PRODUCTION

        serialize_st = time.perf_counter()

        serializer = self.get_serializer(instance=instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        _l.debug('rebook serialize done: %s', "{:3.3f}".format(time.perf_counter() - serialize_st))

        return Response(serializer.data)

    @action(detail=True, methods=['get', 'put'], url_path='rebook-pending',
            serializer_class=TransactionTypeProcessSerializer, permission_classes=[IsAuthenticated])
    def rebook_pending(self, request, pk=None):

        complex_transaction = self.get_object()

        complex_transaction.status_id = ComplexTransaction.PENDING

        instance = TransactionTypeProcess(transaction_type=complex_transaction.transaction_type,
                                          process_mode='rebook',
                                          complex_transaction=complex_transaction,
                                          context=self.get_serializer_context(), member=request.user.member)
        if request.method == 'GET':
            serializer = self.get_serializer(instance=instance)
            return Response(serializer.data)
        else:
            try:

                serializer = self.get_serializer(instance=instance, data=request.data)
                serializer.is_valid(raise_exception=True)
                serializer.save()

                return Response(serializer.data)
            finally:
                if instance.has_errors:
                    transaction.set_rollback(True)

    @action(detail=True, methods=['put'], url_path='update-properties',
            serializer_class=ComplexTransactionSimpleSerializer)
    def update_properties(self, request, pk=None):
        complex_transaction = self.get_object()

        # if request.method != 'GET':
        #     complex_transaction.status = ComplexTransaction.PRODUCTION

        # print('request.data %s' % request.data)
        print('detail_route: /update_properties: process update_properties')

        serializer = self.get_serializer(instance=complex_transaction, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)

    @action(detail=False, methods=['put', 'patch'], url_path='bulk-update-properties',
            serializer_class=ComplexTransactionSimpleSerializer)
    def bulk_update_properties(self, request):
        data = request.data
        if not isinstance(data, list):
            raise ValidationError(gettext_lazy('Required list'))

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
                        api_settings.NON_FIELD_ERRORS_KEY: gettext_lazy('Not Found')
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

    @action(detail=True, methods=['get'], url_path='view', serializer_class=ComplexTransactionViewOnlySerializer,
            permission_classes=[IsAuthenticated])
    def view(self, request, pk=None):

        _st = time.perf_counter()

        complex_transaction = ComplexTransaction.objects.get(id=pk)
        transaction_type = TransactionType.objects.get(id=complex_transaction.transaction_type_id)

        instance = ComplexTransactionViewOnly(complex_transaction,
                                              transaction_type=transaction_type
                                              )

        _serialize_st = time.perf_counter()
        serializer = self.get_serializer(instance=instance)
        response = Response(serializer.data)
        result_time = "{:3.3f}".format(time.perf_counter() - _serialize_st)
        _l.debug('ComplexTransactionViewOnly.serialize total %s' % result_time)

        result_time = "{:3.3f}".format(time.perf_counter() - _st)
        _l.debug('ComplexTransactionViewOnly.response total %s' % result_time)

        return response

    @action(detail=False, methods=['get', 'post'], url_path='bulk-restore')
    def bulk_restore(self, request):
        # print('Bulk delelete here')

        if request.method.lower() == 'get':
            return self.list(request)

        data = request.data

        queryset = self.filter_queryset(self.get_queryset())
        # is_fake = bool(request.query_params.get('is_fake'))

        _l.info('bulk_restore %s' % data['ids'])

        complex_transactions = ComplexTransaction.objects.filter(id__in=data['ids'])

        for complex_transaction in complex_transactions:

            if complex_transaction.deleted_transaction_unique_code:

                used = ComplexTransaction.objects.filter(
                    transaction_unique_code=complex_transaction.deleted_transaction_unique_code)

                if len(used):
                    pass  # that means, we could not restore transaction until user fix transaction uniq code issue
                else:
                    complex_transaction.transaction_unique_code = complex_transaction.deleted_transaction_unique_code
                    complex_transaction.deleted_transaction_unique_code = None
                    complex_transaction.is_deleted = False
                    complex_transaction.save()

            else:
                complex_transaction.is_deleted = False
                complex_transaction.save()

            for transaction in complex_transaction.transactions.all():
                transaction.is_deleted = False
                transaction.save()

        return Response({'message': 'ok'})


class ComplexTransactionEvGroupViewSet(AbstractEvGroupWithObjectPermissionViewSet, CustomPaginationMixin):
    queryset = get_complex_transaction_queryset(select_related=False, transactions=True)
    serializer_class = ComplexTransactionSerializer
    pagination_class = api_settings.DEFAULT_PAGINATION_CLASS
    # filter_class = ComplexTransactionFilterSet

    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        # ComplexTransactionPermissionFilter,
        OwnerByMasterUserFilter,
        AttributeFilter,
        ComplexTransactionStatusFilter,
    ]


# DEPRECATED
class ComplexTransactionLightViewSet(AbstractWithObjectPermissionViewSet):
    queryset = qs = ComplexTransaction.objects.select_related(
        'transaction_type',
        'transaction_type__group',
    ).prefetch_related(
        get_attributes_prefetch(),
        *get_permissions_prefetch_lookups(
            (None, ComplexTransaction),
            ('transaction_type', TransactionType),
            ('transaction_type__group', TransactionTypeGroup),
        )
    )

    serializer_class = ComplexTransactionLightSerializer

    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        # ComplexTransactionPermissionFilter,
        ComplexTransactionSpecificFilter,
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


class ComplexTransactionEvViewSet(AbstractWithObjectPermissionViewSet):
    queryset = qs = ComplexTransaction.objects.select_related(
        'transaction_type',
        'transaction_type__group',
    ).prefetch_related(
        get_attributes_prefetch(),
        *get_permissions_prefetch_lookups(
            (None, ComplexTransaction),
            ('transaction_type', TransactionType),
            ('transaction_type__group', TransactionTypeGroup),
        )
    )

    serializer_class = ComplexTransactionEvSerializer

    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        # ComplexTransactionPermissionFilter,
        ComplexTransactionSpecificFilter,
        OwnerByMasterUserFilter,
        AttributeFilter,
        GroupsAttributeFilter,
        ComplexTransactionStatusFilter
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
        ComplexTransactionSpecificFilter,
        OwnerByMasterUserFilter,
        AttributeFilter
    ]


class RecalculatePermissionTransactionViewSet(AbstractAsyncViewSet):
    serializer_class = RecalculatePermissionTransactionSerializer
    celery_task = recalculate_permissions_transaction


class RecalculatePermissionComplexTransactionViewSet(AbstractAsyncViewSet):
    serializer_class = RecalculatePermissionComplexTransactionSerializer
    celery_task = recalculate_permissions_complex_transaction
