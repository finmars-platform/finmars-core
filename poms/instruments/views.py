from __future__ import unicode_literals

import django_filters
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import Prefetch, Q, Case, When, Value, BooleanField
from django.utils import timezone
from rest_framework import serializers
from rest_framework.decorators import list_route, detail_route
from rest_framework.exceptions import MethodNotAllowed, PermissionDenied, ValidationError
from rest_framework.filters import FilterSet
from rest_framework.response import Response
from rest_framework.settings import api_settings

from poms.accounts.models import Account
from poms.accounts.models import AccountType
from poms.audit import history
from poms.common.filters import CharFilter, ModelExtWithPermissionMultipleChoiceFilter, NoOpFilter, \
    ModelExtMultipleChoiceFilter, AttributeFilter, GroupsAttributeFilter
from poms.common.mixins import UpdateModelMixinExt
from poms.common.pagination import CustomPaginationMixin
from poms.common.utils import date_now
from poms.common.views import AbstractClassModelViewSet, AbstractModelViewSet, AbstractReadOnlyModelViewSet
from poms.currencies.models import Currency
from poms.instruments.filters import OwnerByInstrumentFilter, PriceHistoryObjectPermissionFilter, \
    GeneratedEventPermissionFilter
from poms.instruments.handlers import GeneratedEventProcess
from poms.instruments.models import Instrument, PriceHistory, InstrumentClass, DailyPricingModel, \
    AccrualCalculationModel, PaymentSizeDetail, Periodicity, CostMethod, InstrumentType, PricingPolicy, \
    EventScheduleConfig, ManualPricingFormula, \
    AccrualCalculationSchedule, EventSchedule, EventScheduleAction, GeneratedEvent
from poms.instruments.serializers import InstrumentSerializer, PriceHistorySerializer, \
    InstrumentClassSerializer, DailyPricingModelSerializer, AccrualCalculationModelSerializer, \
    PaymentSizeDetailSerializer, PeriodicitySerializer, CostMethodSerializer, InstrumentTypeSerializer, \
    PricingPolicySerializer, EventScheduleConfigSerializer, InstrumentCalculatePricesAccruedPriceSerializer, \
    GeneratedEventSerializer, EventScheduleActionSerializer
from poms.instruments.tasks import calculate_prices_accrued_price, generate_events, process_events, \
    only_generate_events_at_date, generate_events_do_not_inform_apply_default0, \
    generate_events_do_not_inform_apply_default
from poms.integrations.models import PriceDownloadScheme
from poms.obj_attrs.utils import get_attributes_prefetch
from poms.obj_attrs.views import GenericAttributeTypeViewSet, \
    GenericClassifierViewSet
from poms.obj_perms.filters import ObjectPermissionMemberFilter, ObjectPermissionGroupFilter, \
    ObjectPermissionPermissionFilter
from poms.obj_perms.utils import get_permissions_prefetch_lookups
from poms.obj_perms.views import AbstractWithObjectPermissionViewSet, AbstractEvGroupWithObjectPermissionViewSet
from poms.portfolios.models import Portfolio
from poms.strategies.models import Strategy1, Strategy1Subgroup, Strategy1Group, Strategy2, Strategy2Subgroup, \
    Strategy2Group, Strategy3, Strategy3Subgroup, Strategy3Group
from poms.tags.filters import TagFilter
from poms.tags.utils import get_tag_prefetch
from poms.transactions.models import TransactionType, TransactionTypeGroup, NotificationClass
from poms.transactions.serializers import TransactionTypeProcessSerializer
from poms.users.filters import OwnerByMasterUserFilter
from poms.users.permissions import SuperUserOrReadOnly

import datetime


class InstrumentClassViewSet(AbstractClassModelViewSet):
    queryset = InstrumentClass.objects
    serializer_class = InstrumentClassSerializer


class DailyPricingModelViewSet(AbstractClassModelViewSet):
    queryset = DailyPricingModel.objects
    serializer_class = DailyPricingModelSerializer


class AccrualCalculationModelClassViewSet(AbstractClassModelViewSet):
    queryset = AccrualCalculationModel.objects
    serializer_class = AccrualCalculationModelSerializer


class PaymentSizeDetailViewSet(AbstractClassModelViewSet):
    queryset = PaymentSizeDetail.objects
    serializer_class = PaymentSizeDetailSerializer


class PeriodicityViewSet(AbstractClassModelViewSet):
    queryset = Periodicity.objects
    serializer_class = PeriodicitySerializer


class CostMethodViewSet(AbstractClassModelViewSet):
    queryset = CostMethod.objects
    serializer_class = CostMethodSerializer


class PricingPolicyFilterSet(FilterSet):
    id = NoOpFilter()
    user_code = CharFilter()
    name = CharFilter()

    class Meta:
        model = PricingPolicy
        fields = []


class PricingPolicyViewSet(AbstractModelViewSet):
    queryset = PricingPolicy.objects
    serializer_class = PricingPolicySerializer
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter,
        GroupsAttributeFilter,
    ]
    permission_classes = AbstractModelViewSet.permission_classes + [
        SuperUserOrReadOnly,
    ]
    ordering_fields = [
        'user_code', 'name', 'short_name', 'public_name'
    ]
    filter_class = PricingPolicyFilterSet


class PricingPolicyEvGroupViewSet(AbstractEvGroupWithObjectPermissionViewSet, CustomPaginationMixin):
    queryset = PricingPolicy.objects
    serializer_class = PricingPolicySerializer
    pagination_class = api_settings.DEFAULT_PAGINATION_CLASS

    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter,
        GroupsAttributeFilter
    ]


class InstrumentTypeFilterSet(FilterSet):
    id = NoOpFilter()
    is_deleted = django_filters.BooleanFilter()
    user_code = CharFilter()
    name = CharFilter()
    short_name = CharFilter()
    public_name = CharFilter()
    instrument_class = django_filters.ModelMultipleChoiceFilter(queryset=InstrumentClass.objects)
    one_off_event = ModelExtWithPermissionMultipleChoiceFilter(model=TransactionType)
    regular_event = ModelExtWithPermissionMultipleChoiceFilter(model=TransactionType)
    factor_same = ModelExtWithPermissionMultipleChoiceFilter(model=TransactionType)
    factor_up = ModelExtWithPermissionMultipleChoiceFilter(model=TransactionType)
    factor_down = ModelExtWithPermissionMultipleChoiceFilter(model=TransactionType)
    tag = TagFilter(model=InstrumentType)
    member = ObjectPermissionMemberFilter(object_permission_model=InstrumentType)
    member_group = ObjectPermissionGroupFilter(object_permission_model=InstrumentType)
    permission = ObjectPermissionPermissionFilter(object_permission_model=InstrumentType)

    class Meta:
        model = InstrumentType
        fields = []


class InstrumentTypeViewSet(AbstractWithObjectPermissionViewSet):
    queryset = InstrumentType.objects.select_related(
        'master_user',
        'instrument_class',
        'one_off_event',
        'one_off_event__group',
        'regular_event',
        'regular_event__group',
        'factor_same',
        'factor_same__group',
        'factor_up',
        'factor_up__group',
        'factor_down',
        'factor_down__group',
    ).prefetch_related(
        get_tag_prefetch(),
        *get_permissions_prefetch_lookups(
            (None, InstrumentType),
            ('one_off_event', TransactionType),
            ('one_off_event__group', TransactionTypeGroup),
            ('regular_event', TransactionType),
            ('regular_event__group', TransactionTypeGroup),
            ('factor_same', TransactionType),
            ('factor_same__group', TransactionTypeGroup),
            ('factor_up', TransactionType),
            ('factor_up__group', TransactionTypeGroup),
            ('factor_down', TransactionType),
            ('factor_down__group', TransactionTypeGroup),
        )
    )
    serializer_class = InstrumentTypeSerializer
    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter,
        GroupsAttributeFilter,
    ]
    filter_class = InstrumentTypeFilterSet
    ordering_fields = [
        'user_code', 'name', 'short_name', 'public_name',
    ]


class InstrumentTypeEvGroupViewSet(AbstractEvGroupWithObjectPermissionViewSet, CustomPaginationMixin):
    queryset = InstrumentType.objects.select_related(
        'master_user',
        'instrument_class',
        'one_off_event',
        'one_off_event__group',
        'regular_event',
        'regular_event__group',
        'factor_same',
        'factor_same__group',
        'factor_up',
        'factor_up__group',
        'factor_down',
        'factor_down__group',
    ).prefetch_related(
        get_tag_prefetch(),
        *get_permissions_prefetch_lookups(
            (None, InstrumentType),
            ('one_off_event', TransactionType),
            ('one_off_event__group', TransactionTypeGroup),
            ('regular_event', TransactionType),
            ('regular_event__group', TransactionTypeGroup),
            ('factor_same', TransactionType),
            ('factor_same__group', TransactionTypeGroup),
            ('factor_up', TransactionType),
            ('factor_up__group', TransactionTypeGroup),
            ('factor_down', TransactionType),
            ('factor_down__group', TransactionTypeGroup),
        )
    )
    serializer_class = InstrumentTypeSerializer
    pagination_class = api_settings.DEFAULT_PAGINATION_CLASS
    filter_class = InstrumentTypeFilterSet

    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter,
        GroupsAttributeFilter
    ]


class InstrumentAttributeTypeViewSet(GenericAttributeTypeViewSet):
    target_model = Instrument


class InstrumentClassifierViewSet(GenericClassifierViewSet):
    target_model = Instrument


class InstrumentFilterSet(FilterSet):
    id = NoOpFilter()
    is_deleted = django_filters.BooleanFilter()
    user_code = CharFilter()
    name = CharFilter()
    public_name = CharFilter()
    short_name = CharFilter()
    instrument_type = ModelExtWithPermissionMultipleChoiceFilter(model=InstrumentType)
    instrument_type__instrument_class = django_filters.ModelMultipleChoiceFilter(queryset=InstrumentClass.objects)
    pricing_currency = ModelExtMultipleChoiceFilter(model=Currency)
    price_multiplier = django_filters.RangeFilter()
    accrued_currency = ModelExtMultipleChoiceFilter(model=Currency)
    accrued_multiplier = django_filters.RangeFilter()
    payment_size_detail = django_filters.ModelMultipleChoiceFilter(queryset=PaymentSizeDetail.objects)
    default_price = django_filters.RangeFilter()
    default_accrued = django_filters.RangeFilter()
    user_text_1 = CharFilter()
    user_text_2 = CharFilter()
    user_text_3 = CharFilter()
    reference_for_pricing = CharFilter()
    daily_pricing_model = django_filters.ModelMultipleChoiceFilter(queryset=DailyPricingModel.objects)
    price_download_scheme = ModelExtMultipleChoiceFilter(model=PriceDownloadScheme, field_name='scheme_name')
    maturity_date = django_filters.DateFromToRangeFilter()
    tag = TagFilter(model=Instrument)
    member = ObjectPermissionMemberFilter(object_permission_model=Instrument)
    member_group = ObjectPermissionGroupFilter(object_permission_model=Instrument)
    permission = ObjectPermissionPermissionFilter(object_permission_model=Instrument)

    class Meta:
        model = Instrument
        fields = []


class InstrumentViewSet(AbstractWithObjectPermissionViewSet):
    queryset = Instrument.objects.select_related(
        'instrument_type',
        'instrument_type__instrument_class',
        'pricing_currency',
        'accrued_currency',
        'payment_size_detail',
        'daily_pricing_model',
        'price_download_scheme',
        'price_download_scheme__provider',
    ).prefetch_related(
        # Prefetch(
        #     'attributes',
        #     queryset=InstrumentAttribute.objects.select_related('attribute_type', 'classifier')
        # ),
        Prefetch(
            'manual_pricing_formulas',
            queryset=ManualPricingFormula.objects.select_related('pricing_policy')
        ),
        Prefetch(
            'accrual_calculation_schedules',
            queryset=AccrualCalculationSchedule.objects.select_related('accrual_calculation_model', 'periodicity')
        ),
        'factor_schedules',
        Prefetch(
            'event_schedules',
            queryset=EventSchedule.objects.select_related(
                'event_class', 'notification_class', 'periodicity'
            ).prefetch_related(
                Prefetch(
                    'actions',
                    queryset=EventScheduleAction.objects.select_related(
                        'transaction_type',
                        'transaction_type__group'
                    ).prefetch_related(
                        *get_permissions_prefetch_lookups(
                            ('transaction_type', TransactionType),
                            ('transaction_type__group', TransactionTypeGroup)
                        )
                    )
                ),
            )),
        get_attributes_prefetch(),
        get_tag_prefetch(),
        *get_permissions_prefetch_lookups(
            (None, Instrument),
            ('instrument_type', InstrumentType),
            # ('attributes__attribute_type', InstrumentAttributeType),
        )
    )
    serializer_class = InstrumentSerializer
    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter,
        GroupsAttributeFilter,
    ]
    filter_class = InstrumentFilterSet
    ordering_fields = [
        'user_code', 'name', 'short_name', 'public_name', 'reference_for_pricing',
        'instrument_type', 'instrument_type__user_code', 'instrument_type__name', 'instrument_type__short_name',
        'instrument_type__public_name',
        'pricing_currency', 'pricing_currency__user_code', 'pricing_currency__name', 'pricing_currency__short_name',
        'pricing_currency__public_name', 'price_multiplier',
        'accrued_currency', 'accrued_currency__user_code', 'accrued_currency__name', 'accrued_currency__short_name',
        'accrued_currency__public_name', 'accrued_multiplier',
        'default_price', 'default_accrued', 'user_text_1', 'user_text_2', 'user_text_3',
        'reference_for_pricing',
        'maturity_date',
    ]

    @list_route(methods=['post'], url_path='rebuild-events', serializer_class=serializers.Serializer)
    def rebuild_all_events(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        processed = 0
        for instance in queryset:
            try:
                instance.rebuild_event_schedules()
            except ValueError as e:
                pass
            processed += 1
        return Response({'processed': processed})

    @detail_route(methods=['put', 'patch'], url_path='rebuild-events', serializer_class=serializers.Serializer)
    def rebuild_events(self, request, pk):
        instance = self.get_object()
        try:
            instance.rebuild_event_schedules()
        except ValueError as e:
            pass
        return Response({'processed': 1})

    @list_route(methods=['post'], url_path='generate-events', serializer_class=serializers.Serializer)
    def generate_events(self, request):
        ret = generate_events.apply_async(kwargs={'master_users': [request.user.master_user.pk]})
        return Response({
            'success': True,
            'task_id': ret.id,
        })

    @list_route(methods=['post'], url_path='system-generate-and-process', serializer_class=serializers.Serializer)
    def system_generate_and_process(self, request):

        ret = generate_events_do_not_inform_apply_default.apply_async()
        return Response({
            'success': True,
            'task_id': ret.id,
        })

    @list_route(methods=['post'], url_path='generate-events-range', serializer_class=serializers.Serializer)
    def generate_events_range(self, request):

        date_from_string = request.query_params.get('effective_date_0', None)
        date_to_string = request.query_params.get('effective_date_1', None)

        if date_from_string is None or date_to_string is None:
            raise ValidationError('Date range is incorrect')

        date_from = datetime.datetime.strptime(date_from_string, '%Y-%m-%d').date()
        date_to = datetime.datetime.strptime(date_to_string, '%Y-%m-%d').date()

        # print('date_from %s' % date_from)
        # print('date_to %s' % date_to)

        dates = [date_from + datetime.timedelta(days=i) for i in range((date_to - date_from).days + 1)]

        tasks_ids = []

        # print('dates %s' % dates)

        for dte in dates:
            res = only_generate_events_at_date.apply_async(
                kwargs={'master_user': request.user.master_user, 'date': dte})
            tasks_ids.append(res.id)

        return Response({
            'success': True,
            'tasks_ids': tasks_ids
        })

    @list_route(methods=['post'], url_path='process-events', serializer_class=serializers.Serializer)
    def process_events(self, request):
        ret = process_events.apply_async(kwargs={'master_users': [request.user.master_user.pk]})
        return Response({
            'success': True,
            'task_id': ret.id,
        })

    @list_route(methods=['post'], url_path='recalculate-prices-accrued-price',
                serializer_class=InstrumentCalculatePricesAccruedPriceSerializer)
    def calculate_prices_accrued_price(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        begin_date = serializer.validated_data['begin_date']
        end_date = serializer.validated_data['end_date']

        calculate_prices_accrued_price(master_user=request.user.master_user, begin_date=begin_date, end_date=end_date)
        # calculate_prices_accrued_price_async.apply_async(
        #     kwargs={
        #         'master_user': request.user.master_user.id,
        #         'begin_date': begin_date.toordinal(),
        #         'end_date': end_date.toordinal(),
        #     }
        # ).wait()

        return Response(serializer.data)


class InstrumentEvGroupViewSet(AbstractEvGroupWithObjectPermissionViewSet, CustomPaginationMixin):
    queryset = Instrument.objects.select_related(
        'instrument_type',
        'instrument_type__instrument_class',
        'pricing_currency',
        'accrued_currency',
        'payment_size_detail',
        'daily_pricing_model',
        'price_download_scheme',
        'price_download_scheme__provider',
    ).prefetch_related(
        # Prefetch(
        #     'attributes',
        #     queryset=InstrumentAttribute.objects.select_related('attribute_type', 'classifier')
        # ),
        Prefetch(
            'manual_pricing_formulas',
            queryset=ManualPricingFormula.objects.select_related('pricing_policy')
        ),
        Prefetch(
            'accrual_calculation_schedules',
            queryset=AccrualCalculationSchedule.objects.select_related('accrual_calculation_model', 'periodicity')
        ),
        'factor_schedules',
        Prefetch(
            'event_schedules',
            queryset=EventSchedule.objects.select_related(
                'event_class', 'notification_class', 'periodicity'
            ).prefetch_related(
                Prefetch(
                    'actions',
                    queryset=EventScheduleAction.objects.select_related(
                        'transaction_type',
                        'transaction_type__group'
                    ).prefetch_related(
                        *get_permissions_prefetch_lookups(
                            ('transaction_type', TransactionType),
                            ('transaction_type__group', TransactionTypeGroup)
                        )
                    )
                ),
            )),
        get_attributes_prefetch(),
        get_tag_prefetch(),
        *get_permissions_prefetch_lookups(
            (None, Instrument),
            ('instrument_type', InstrumentType),
            # ('attributes__attribute_type', InstrumentAttributeType),
        )
    )
    serializer_class = InstrumentSerializer
    pagination_class = api_settings.DEFAULT_PAGINATION_CLASS
    filter_class = InstrumentFilterSet

    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter,
        GroupsAttributeFilter
    ]


class PriceHistoryFilterSet(FilterSet):
    id = NoOpFilter()
    instrument = ModelExtWithPermissionMultipleChoiceFilter(model=Instrument)
    pricing_policy = ModelExtMultipleChoiceFilter(model=PricingPolicy)
    date = django_filters.DateFromToRangeFilter()
    principal_price = django_filters.RangeFilter()
    accrued_price = django_filters.RangeFilter()

    class Meta:
        model = PriceHistory
        fields = []


class PriceHistoryViewSet(AbstractModelViewSet):
    queryset = PriceHistory.objects.select_related(
        'instrument',
        'instrument__instrument_type',
        'instrument__instrument_type__instrument_class',
        'pricing_policy'
    ).prefetch_related(
        *get_permissions_prefetch_lookups(
            ('instrument', Instrument),
            ('instrument__instrument_type', InstrumentType),
        )
    )
    serializer_class = PriceHistorySerializer
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByInstrumentFilter,
        PriceHistoryObjectPermissionFilter,
        AttributeFilter,
        GroupsAttributeFilter,
    ]
    filter_class = PriceHistoryFilterSet
    ordering_fields = [
        'instrument', 'instrument__user_code', 'instrument__name', 'instrument__short_name', 'instrument__public_name',
        'pricing_policy', 'pricing_policy__user_code', 'pricing_policy__name', 'pricing_policy__short_name',
        'pricing_policy__public_name',
        'date', 'principal_price', 'accrued_price',
    ]


class PriceHistoryEvGroupViewSet(AbstractEvGroupWithObjectPermissionViewSet, CustomPaginationMixin):
    queryset = PriceHistory.objects.select_related(
        'instrument',
        'instrument__instrument_type',
        'instrument__instrument_type__instrument_class',
        'pricing_policy'
    ).prefetch_related(
        *get_permissions_prefetch_lookups(
            ('instrument', Instrument),
            ('instrument__instrument_type', InstrumentType),
        )
    )
    serializer_class = PriceHistorySerializer
    pagination_class = api_settings.DEFAULT_PAGINATION_CLASS
    filter_class = PriceHistoryFilterSet

    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByInstrumentFilter,
        PriceHistoryObjectPermissionFilter,
        AttributeFilter,
        GroupsAttributeFilter
    ]


class GeneratedEventFilterSet(FilterSet):
    id = NoOpFilter()
    # is_need_reaction = django_filters.MethodFilter(action='filter_is_need_reaction')
    is_need_reaction = django_filters.BooleanFilter()
    status = django_filters.MultipleChoiceFilter(choices=GeneratedEvent.STATUS_CHOICES)
    status_date = django_filters.DateFromToRangeFilter()
    instrument = ModelExtWithPermissionMultipleChoiceFilter(model=Instrument)
    portfolio = ModelExtWithPermissionMultipleChoiceFilter(model=Portfolio)
    account = ModelExtWithPermissionMultipleChoiceFilter(model=Account)
    strategy1 = ModelExtWithPermissionMultipleChoiceFilter(model=Strategy1)
    strategy2 = ModelExtWithPermissionMultipleChoiceFilter(model=Strategy2)
    strategy3 = ModelExtWithPermissionMultipleChoiceFilter(model=Strategy3)
    member = ModelExtMultipleChoiceFilter(model=Strategy3)

    effective_date = django_filters.DateFromToRangeFilter()
    notification_date = django_filters.DateFromToRangeFilter()

    class Meta:
        model = GeneratedEvent
        fields = []

        # def filter_is_need_reaction(self, qs, value):
        #     value = force_text(value).lower()
        #     now = date_now()
        #     expr = Q(status=GeneratedEvent.NEW, action__isnull=True) & (
        #         Q(notification_date=now,
        #           event_schedule__notification_class__in=NotificationClass.get_need_reaction_on_notification_date_classes())
        #         | Q(effective_date=now,
        #             event_schedule__notification_class__in=NotificationClass.get_need_reaction_on_effective_date_classes())
        #     )
        #     if value in ['true', '1', 'yes']:
        #         qs = qs.filter(expr)
        #     elif value in ['false', '0', 'no']:
        #         qs = qs.exclude(expr)
        #
        #     return qs


class GeneratedEventViewSet(UpdateModelMixinExt, AbstractReadOnlyModelViewSet):
    queryset = GeneratedEvent.objects.select_related(
        'master_user',
        'event_schedule',
        'event_schedule__event_class',
        'event_schedule__notification_class',
        'event_schedule__periodicity',
        'instrument',
        'instrument__instrument_type',
        'instrument__instrument_type__instrument_class',
        'portfolio',
        'account',
        'strategy1',
        'strategy1__subgroup',
        'strategy1__subgroup__group',
        'strategy2',
        'strategy2__subgroup',
        'strategy2__subgroup__group',
        'strategy3',
        'strategy3__subgroup',
        'strategy3__subgroup__group',
        'action',
        'transaction_type',
        'transaction_type__group',
        'member'
    ).prefetch_related(
        *get_permissions_prefetch_lookups(
            ('instrument', Instrument),
            ('instrument__instrument_type', InstrumentType),
            ('portfolio', Portfolio),
            ('account', Account),
            ('account__type', AccountType),
            ('strategy1', Strategy1),
            ('strategy1__subgroup', Strategy1Subgroup),
            ('strategy1__subgroup__group', Strategy1Group),
            ('strategy2', Strategy2),
            ('strategy2__subgroup', Strategy2Subgroup),
            ('strategy2__subgroup__group', Strategy2Group),
            ('strategy3', Strategy3),
            ('strategy3__subgroup', Strategy3Subgroup),
            ('strategy3__subgroup__group', Strategy3Group),
            ('transaction_type', TransactionType),
        )
    )
    serializer_class = GeneratedEventSerializer
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByInstrumentFilter,
        GeneratedEventPermissionFilter,
    ]
    filter_class = GeneratedEventFilterSet
    ordering_fields = [
        'status', 'status_date',
        'effective_date', 'notification_date',
        'instrument', 'instrument__user_code', 'instrument__name', 'instrument__short_name', 'instrument__public_name',
        'portfolio', 'portfolio__user_code', 'portfolio__name', 'portfolio__short_name', 'portfolio__public_name',
        'account', 'account__user_code', 'account__name', 'account__short_name', 'account__public_name',
        'date', 'principal_price', 'accrued_price',
        'strategy1', 'strategy1__user_code', 'strategy1__name', 'strategy1__short_name', 'strategy1__public_name',
        'strategy2', 'strategy2__user_code', 'strategy2__name', 'strategy2__short_name', 'strategy2__public_name',
        'strategy3', 'strategy3__user_code', 'strategy3__name', 'strategy3__short_name', 'strategy3__public_name',
        'member',
    ]

    def get_queryset(self):
        qs = super(GeneratedEventViewSet, self).get_queryset()
        now = date_now()
        qs = qs.annotate(
            is_need_reaction=Case(
                When(
                    Q(status=GeneratedEvent.NEW, action__isnull=True) & (
                            Q(notification_date__lte=now,
                              event_schedule__notification_class__in=NotificationClass.get_need_reaction_on_notification_date_classes())
                            | Q(effective_date__lte=now,
                                event_schedule__notification_class__in=NotificationClass.get_need_reaction_on_effective_date_classes())
                    ),
                    then=Value(True)
                ),
                default=Value(False),
                output_field=BooleanField(),
            )
        )
        return qs

    @detail_route(methods=['get', 'put'], url_path='book', serializer_class=TransactionTypeProcessSerializer)
    def process(self, request, pk=None):
        generated_event = self.get_object()

        # if not generated_event.is_need_reaction:
        #     raise ValidationError('event already processed or future event')

        # if generated_event.status != GeneratedEvent.NEW:
        #     raise PermissionDenied()

        action_pk = request.query_params.get('action', None)

        action = None
        if action_pk:
            try:
                action = generated_event.event_schedule.actions.get(pk=action_pk)
            except ObjectDoesNotExist:
                pass
        if action is None:
            raise ValidationError('Require "action" query parameter')

        instance = GeneratedEventProcess(
            generated_event=generated_event,
            action=action,
            context=self.get_serializer_context()
        )

        if request.method == 'GET':
            serializer = self.get_serializer(instance=instance)
            return Response(serializer.data)
        else:
            try:
                history.set_flag_addition()

                status = request.query_params.get('event_status', None)

                if status is None:
                    raise ValidationError('Require "event_status" query parameter')

                serializer = self.get_serializer(instance=instance, data=request.data)

                serializer.is_valid(raise_exception=True)
                serializer.save()

                print('generated_event.id %s ' % generated_event.id)
                print('status %s ' % status)
                print('instance.has_errors %s ' % instance.has_errors)

                if not instance.has_errors:
                    generated_event.processed(self.request.user.member, action, instance.complex_transaction,
                                              status)
                    generated_event.save()

                history.set_actor_content_object(instance.complex_transaction)

                return Response(serializer.data)
            finally:
                if instance.has_errors:
                    transaction.set_rollback(True)

    @detail_route(methods=['put'], url_path='informed')
    def ignore(self, request, pk=None):
        generated_event = self.get_object()

        if generated_event.status != GeneratedEvent.NEW:
            raise PermissionDenied()

        generated_event.status = GeneratedEvent.INFORMED
        generated_event.status_date = timezone.now()
        generated_event.member = self.request.user.member
        generated_event.save()

        serializer = self.get_serializer(instance=generated_event)
        return Response(serializer.data)

    @detail_route(methods=['put'], url_path='error')
    def error(self, request, pk=None):
        generated_event = self.get_object()

        if generated_event.status != GeneratedEvent.NEW:
            raise PermissionDenied()

        generated_event.status = GeneratedEvent.ERROR
        generated_event.status_date = timezone.now()
        generated_event.member = self.request.user.member
        generated_event.save()

        serializer = self.get_serializer(instance=generated_event)
        return Response(serializer.data)


class EventScheduleConfigViewSet(AbstractModelViewSet):
    queryset = EventScheduleConfig.objects.select_related(
        'notification_class'
    )
    serializer_class = EventScheduleConfigSerializer
    permission_classes = AbstractModelViewSet.permission_classes + [
        SuperUserOrReadOnly,
    ]
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]

    def get_object(self):
        try:
            return self.request.user.master_user.instrument_event_schedule_config
        except ObjectDoesNotExist:
            obj = EventScheduleConfig.create_default(master_user=self.request.user.master_user)
            return obj

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed(method=request.method)
