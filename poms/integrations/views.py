from __future__ import unicode_literals, print_function

import django_filters
from celery.result import AsyncResult
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.signing import TimestampSigner
from django.db.models import Prefetch
from django_filters.rest_framework import FilterSet, DjangoFilterBackend
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.filters import OrderingFilter

from django.db import transaction
from rest_framework.viewsets import ModelViewSet

from poms.common.mixins import UpdateModelMixinExt, DestroyModelFakeMixin, BulkModelMixin
from poms.common.utils import date_now, datetime_now

from poms.accounts.models import Account, AccountType
from poms.celery_tasks.models import CeleryTask
from poms.common.filters import CharFilter, ModelExtWithPermissionMultipleChoiceFilter, NoOpFilter, \
    ModelExtMultipleChoiceFilter, ByIdFilterBackend
from poms.common.views import AbstractViewSet, AbstractModelViewSet, AbstractReadOnlyModelViewSet, \
    AbstractClassModelViewSet, AbstractAsyncViewSet, AbstractApiView
from poms.counterparties.models import Counterparty, Responsible
from poms.currencies.models import Currency
from poms.instruments.models import InstrumentType, AccrualCalculationModel, Periodicity, Instrument, PaymentSizeDetail, \
    PricingPolicy, PricingCondition
from poms.integrations.filters import TaskFilter, InstrumentAttributeValueMappingObjectPermissionFilter, \
    InstrumentTypeMappingObjectPermissionFilter, AccountMappingObjectPermissionFilter, \
    InstrumentMappingObjectPermissionFilter, CounterpartyMappingObjectPermissionFilter, \
    ResponsibleMappingObjectPermissionFilter, PortfolioMappingObjectPermissionFilter, \
    Strategy1MappingObjectPermissionFilter, Strategy2MappingObjectPermissionFilter, \
    Strategy3MappingObjectPermissionFilter, AccountTypeMappingObjectPermissionFilter
from poms.integrations.models import ImportConfig, Task, InstrumentDownloadScheme, ProviderClass, \
    FactorScheduleDownloadMethod, AccrualScheduleDownloadMethod, PriceDownloadScheme, CurrencyMapping, \
    InstrumentTypeMapping, InstrumentAttributeValueMapping, AccrualCalculationModelMapping, PeriodicityMapping, \
    PricingAutomatedSchedule, InstrumentDownloadSchemeAttribute, AccountMapping, InstrumentMapping, CounterpartyMapping, \
    ResponsibleMapping, PortfolioMapping, Strategy1Mapping, Strategy2Mapping, Strategy3Mapping, \
    DailyPricingModelMapping, \
    PaymentSizeDetailMapping, PriceDownloadSchemeMapping, ComplexTransactionImportScheme, PortfolioClassifierMapping, \
    AccountClassifierMapping, CounterpartyClassifierMapping, ResponsibleClassifierMapping, PricingPolicyMapping, \
    InstrumentClassifierMapping, AccountTypeMapping, BloombergDataProviderCredential, PricingConditionMapping, \
    TransactionFileResult, DataProvider
from poms.integrations.serializers import ImportConfigSerializer, TaskSerializer, ImportInstrumentSerializer, \
    ImportPricingSerializer, InstrumentDownloadSchemeSerializer, ProviderClassSerializer, \
    FactorScheduleDownloadMethodSerializer, AccrualScheduleDownloadMethodSerializer, PriceDownloadSchemeSerializer, \
    CurrencyMappingSerializer, InstrumentTypeMappingSerializer, InstrumentAttributeValueMappingSerializer, \
    AccrualCalculationModelMappingSerializer, PeriodicityMappingSerializer, PricingAutomatedScheduleSerializer, \
    ComplexTransactionCsvFileImportSerializer, AccountMappingSerializer, \
    InstrumentMappingSerializer, CounterpartyMappingSerializer, ResponsibleMappingSerializer, \
    PortfolioMappingSerializer, \
    Strategy1MappingSerializer, Strategy2MappingSerializer, Strategy3MappingSerializer, \
    DailyPricingModelMappingSerializer, PaymentSizeDetailMappingSerializer, PriceDownloadSchemeMappingSerializer, \
    ComplexTransactionImportSchemeSerializer, PortfolioClassifierMappingSerializer, AccountClassifierMappingSerializer, \
    CounterpartyClassifierMappingSerializer, ResponsibleClassifierMappingSerializer, PricingPolicyMappingSerializer, \
    InstrumentClassifierMappingSerializer, AccountTypeMappingSerializer, TestCertificateSerializer, \
    ComplexTransactionImportSchemeLightSerializer, BloombergDataProviderCredentialSerializer, \
    PricingConditionMappingSerializer, TransactionFileResultSerializer, DataProviderSerializer, \
    InstrumentDownloadSchemeLightSerializer, ImportInstrumentCbondsSerializer, ImportUnifiedDataProviderSerializer, \
    ImportCurrencyCbondsSerializer
from poms.integrations.tasks import complex_transaction_csv_file_import, complex_transaction_csv_file_import_validate, \
    complex_transaction_csv_file_import_by_procedure, complex_transaction_csv_file_import_parallel, \
    complex_transaction_csv_file_import_validate_parallel
from poms.csv_import.tasks import data_csv_file_import_by_procedure
from poms.obj_attrs.models import GenericAttributeType, GenericClassifier
from poms.obj_perms.permissions import PomsFunctionPermission, PomsConfigurationPermission
from poms.obj_perms.utils import get_permissions_prefetch_lookups
from poms.portfolios.models import Portfolio
from poms.procedures.models import RequestDataFileProcedureInstance
from poms.strategies.models import Strategy1, Strategy2, Strategy3
from poms.system_messages.handlers import send_system_message
from poms.users.filters import OwnerByMasterUserFilter
from poms.users.models import Member, MasterUser
from poms.users.permissions import SuperUserOrReadOnly, SuperUserOnly

import logging

_l = logging.getLogger('poms.integrations')

from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied

import requests
import json
import time


class ProviderClassViewSet(AbstractClassModelViewSet):
    queryset = ProviderClass.objects
    serializer_class = ProviderClassSerializer


class FactorScheduleDownloadMethodViewSet(AbstractClassModelViewSet):
    queryset = FactorScheduleDownloadMethod.objects
    serializer_class = FactorScheduleDownloadMethodSerializer


class AccrualScheduleDownloadMethodViewSet(AbstractClassModelViewSet):
    queryset = AccrualScheduleDownloadMethod.objects
    serializer_class = AccrualScheduleDownloadMethodSerializer


class BloombergDataProviderCredentialViewSet(AbstractApiView, UpdateModelMixinExt, DestroyModelFakeMixin,
                                             BulkModelMixin, ModelViewSet):
    queryset = BloombergDataProviderCredential.objects
    serializer_class = BloombergDataProviderCredentialSerializer
    permission_classes = AbstractModelViewSet.permission_classes + [
        SuperUserOnly,
    ]
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]


class ImportConfigFilterSet(FilterSet):
    provider = django_filters.ModelMultipleChoiceFilter(queryset=ProviderClass.objects)

    class Meta:
        model = ImportConfig
        fields = []


class ImportConfigViewSet(AbstractModelViewSet):
    queryset = ImportConfig.objects
    serializer_class = ImportConfigSerializer
    permission_classes = AbstractModelViewSet.permission_classes + [
        SuperUserOnly,
    ]
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    filter_class = ImportConfigFilterSet


class InstrumentDownloadSchemeFilterSet(FilterSet):
    id = NoOpFilter()
    provider = django_filters.ModelMultipleChoiceFilter(queryset=ProviderClass.objects)
    scheme_name = CharFilter()

    class Meta:
        model = InstrumentDownloadScheme
        fields = []


class InstrumentDownloadSchemeViewSet(AbstractModelViewSet):
    queryset = InstrumentDownloadScheme.objects.select_related(
        'provider', 'payment_size_detail', 'daily_pricing_model', 'factor_schedule_method',
        'accrual_calculation_schedule_method',
    ).prefetch_related(
        'inputs',
        Prefetch(
            'attributes',
            queryset=InstrumentDownloadSchemeAttribute.objects.select_related('attribute_type')
        ),
        *get_permissions_prefetch_lookups(
            ('attributes__attribute_type', GenericAttributeType),
        )
    )
    serializer_class = InstrumentDownloadSchemeSerializer
    permission_classes = AbstractModelViewSet.permission_classes + [
        PomsConfigurationPermission
    ]
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    filter_class = InstrumentDownloadSchemeFilterSet
    ordering_fields = [
        'scheme_name',
        'provider', 'provider__name',
    ]


class InstrumentDownloadSchemeLightViewSet(AbstractModelViewSet):
    queryset = InstrumentDownloadScheme.objects.select_related(
        'provider',
    )
    serializer_class = InstrumentDownloadSchemeLightSerializer
    permission_classes = AbstractModelViewSet.permission_classes + [
        PomsConfigurationPermission
    ]
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    filter_class = InstrumentDownloadSchemeFilterSet
    ordering_fields = [
        'scheme_name',
        'provider', 'provider__name',
    ]


class PriceDownloadSchemeFilterSet(FilterSet):
    id = NoOpFilter()
    provider = django_filters.ModelMultipleChoiceFilter(queryset=ProviderClass.objects)
    scheme_name = CharFilter()

    class Meta:
        model = PriceDownloadScheme
        fields = []


class PriceDownloadSchemeViewSet(AbstractModelViewSet):
    queryset = PriceDownloadScheme.objects.select_related(
        'provider'
    )
    serializer_class = PriceDownloadSchemeSerializer
    # permission_classes = AbstractModelViewSet.permission_classes + [
    #     SuperUserOrReadOnly,
    # ]
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    filter_class = PriceDownloadSchemeFilterSet
    ordering_fields = [
        'scheme_name',
        'provider', 'provider__name',
    ]
    permission_classes = AbstractModelViewSet.permission_classes + [
        PomsConfigurationPermission
    ]


class AbstractMappingFilterSet(FilterSet):
    id = NoOpFilter()
    provider = django_filters.ModelMultipleChoiceFilter(queryset=ProviderClass.objects)
    value = CharFilter()

    class Meta:
        fields = []


class AbstractMappingViewSet(AbstractModelViewSet):
    queryset = None
    serializer_class = None
    permission_classes = AbstractModelViewSet.permission_classes + [
        SuperUserOrReadOnly,
        PomsConfigurationPermission
    ]
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    filter_class = None
    base_ordering_fields = ['provider', 'provider__name', 'value', 'content_object', ]
    ordering_fields = [
        'provider',
        'provider__name',
        'value',
        'content_object',
        'content_object__user_code',
        'content_object__name',
        'content_object__short_name',
        'content_object__public_name',
    ]


class CurrencyMappingFilterSet(AbstractMappingFilterSet):
    content_object = ModelExtMultipleChoiceFilter(model=Currency)

    class Meta(AbstractMappingFilterSet.Meta):
        model = CurrencyMapping


class CurrencyMappingViewSet(AbstractMappingViewSet):
    queryset = CurrencyMapping.objects.select_related(
        'master_user', 'provider', 'content_object'
    )
    serializer_class = CurrencyMappingSerializer
    filter_class = CurrencyMappingFilterSet


class PricingPolicyMappingFilterSet(AbstractMappingFilterSet):
    content_object = ModelExtMultipleChoiceFilter(model=PricingPolicy)

    class Meta(AbstractMappingFilterSet.Meta):
        model = PricingPolicyMapping


class PricingPolicyMappingViewSet(AbstractMappingViewSet):
    queryset = PricingPolicyMapping.objects.select_related(
        'master_user', 'provider', 'content_object'
    )
    serializer_class = PricingPolicyMappingSerializer
    filter_class = PricingPolicyMappingFilterSet


class AccountTypeMappingFilterSet(AbstractMappingFilterSet):
    content_object = ModelExtWithPermissionMultipleChoiceFilter(model=AccountType)

    class Meta(AbstractMappingFilterSet.Meta):
        model = AccountTypeMapping


class AccountTypeMappingViewSet(AbstractMappingViewSet):
    queryset = AccountTypeMapping.objects.select_related(
        'master_user', 'provider', 'content_object'
    )
    serializer_class = AccountTypeMappingSerializer
    filter_backends = AbstractMappingViewSet.filter_backends + [
        AccountTypeMappingObjectPermissionFilter,
    ]
    filter_class = AccountTypeMappingFilterSet


class InstrumentTypeMappingFilterSet(AbstractMappingFilterSet):
    content_object = ModelExtWithPermissionMultipleChoiceFilter(model=InstrumentType)

    class Meta(AbstractMappingFilterSet.Meta):
        model = InstrumentTypeMapping


class InstrumentTypeMappingViewSet(AbstractMappingViewSet):
    queryset = InstrumentTypeMapping.objects.select_related(
        'master_user', 'provider', 'content_object'
    )
    serializer_class = InstrumentTypeMappingSerializer
    filter_backends = AbstractMappingViewSet.filter_backends + [
        InstrumentTypeMappingObjectPermissionFilter,
    ]
    filter_class = InstrumentTypeMappingFilterSet


class InstrumentAttributeValueMappingFilterSet(AbstractMappingFilterSet):
    content_object = ModelExtWithPermissionMultipleChoiceFilter(model=GenericAttributeType)

    class Meta(AbstractMappingFilterSet.Meta):
        model = InstrumentAttributeValueMapping


class InstrumentAttributeValueMappingViewSet(AbstractMappingViewSet):
    queryset = InstrumentAttributeValueMapping.objects.select_related(
        'master_user', 'provider', 'content_object', 'classifier'
    )
    serializer_class = InstrumentAttributeValueMappingSerializer
    filter_backends = AbstractMappingViewSet.filter_backends + [
        InstrumentAttributeValueMappingObjectPermissionFilter,
    ]
    filter_class = InstrumentAttributeValueMappingFilterSet


class AccrualCalculationModelMappingFilterSet(AbstractMappingFilterSet):
    content_object = django_filters.ModelMultipleChoiceFilter(queryset=AccrualCalculationModel.objects)

    class Meta(AbstractMappingFilterSet.Meta):
        model = AccrualCalculationModelMapping


class AccrualCalculationModelMappingViewSet(AbstractMappingViewSet):
    queryset = AccrualCalculationModelMapping.objects.select_related(
        'master_user', 'provider', 'content_object'
    )
    serializer_class = AccrualCalculationModelMappingSerializer
    filter_class = AccrualCalculationModelMappingFilterSet


class PeriodicityMappingFilterSet(AbstractMappingFilterSet):
    content_object = django_filters.ModelMultipleChoiceFilter(queryset=Periodicity.objects)

    class Meta(AbstractMappingFilterSet.Meta):
        model = PeriodicityMapping


class PeriodicityMappingViewSet(AbstractMappingViewSet):
    queryset = PeriodicityMapping.objects.select_related(
        'master_user', 'provider', 'content_object'
    )
    serializer_class = PeriodicityMappingSerializer
    filter_class = PeriodicityMappingFilterSet


class AccountMappingFilterSet(AbstractMappingFilterSet):
    content_object = ModelExtWithPermissionMultipleChoiceFilter(model=Account)

    class Meta(AbstractMappingFilterSet.Meta):
        model = AccountMapping


class AccountClassifierMappingFilterSet(AbstractMappingFilterSet):
    attribute_type = ModelExtWithPermissionMultipleChoiceFilter(model=GenericAttributeType)

    class Meta(AbstractMappingFilterSet.Meta):
        model = AccountClassifierMapping


class AccountMappingViewSet(AbstractMappingViewSet):
    queryset = AccountMapping.objects.select_related(
        'master_user', 'provider', 'content_object'
    )
    serializer_class = AccountMappingSerializer
    filter_backends = AbstractMappingViewSet.filter_backends + [
        AccountMappingObjectPermissionFilter,
    ]
    filter_class = AccountMappingFilterSet


class AccountClassifierMappingViewSet(AbstractMappingViewSet):
    queryset = AccountClassifierMapping.objects.select_related(
        'master_user', 'provider', 'content_object', 'attribute_type'
    )
    serializer_class = AccountClassifierMappingSerializer
    filter_backends = AbstractMappingViewSet.filter_backends + [
        AccountMappingObjectPermissionFilter,
    ]
    filter_class = AccountClassifierMappingFilterSet


class InstrumentMappingFilterSet(AbstractMappingFilterSet):
    content_object = ModelExtWithPermissionMultipleChoiceFilter(model=Instrument)

    class Meta(AbstractMappingFilterSet.Meta):
        model = InstrumentMapping


class InstrumentMappingViewSet(AbstractMappingViewSet):
    queryset = InstrumentMapping.objects.select_related(
        'master_user', 'provider', 'content_object'
    )
    serializer_class = InstrumentMappingSerializer
    filter_backends = AbstractMappingViewSet.filter_backends + [
        InstrumentMappingObjectPermissionFilter,
    ]
    filter_class = InstrumentMappingFilterSet


class InstrumentClassifierMappingFilterSet(AbstractMappingFilterSet):
    attribute_type = ModelExtWithPermissionMultipleChoiceFilter(model=GenericAttributeType)

    class Meta(AbstractMappingFilterSet.Meta):
        model = InstrumentClassifierMapping


class InstrumentClassifierMappingViewSet(AbstractMappingViewSet):
    queryset = InstrumentClassifierMapping.objects.select_related(
        'master_user', 'provider', 'content_object'
    )
    serializer_class = InstrumentClassifierMappingSerializer
    filter_backends = AbstractMappingViewSet.filter_backends + [
        InstrumentMappingObjectPermissionFilter,
    ]
    filter_class = InstrumentClassifierMappingFilterSet


class CounterpartyMappingFilterSet(AbstractMappingFilterSet):
    content_object = ModelExtWithPermissionMultipleChoiceFilter(model=Counterparty)

    class Meta(AbstractMappingFilterSet.Meta):
        model = CounterpartyMapping


class CounterpartyClassifierMappingFilterSet(AbstractMappingFilterSet):
    attribute_type = ModelExtWithPermissionMultipleChoiceFilter(model=GenericAttributeType)

    class Meta(AbstractMappingFilterSet.Meta):
        model = CounterpartyClassifierMapping


class CounterpartyMappingViewSet(AbstractMappingViewSet):
    queryset = CounterpartyMapping.objects.select_related(
        'master_user', 'provider', 'content_object'
    )
    serializer_class = CounterpartyMappingSerializer
    filter_backends = AbstractMappingViewSet.filter_backends + [
        CounterpartyMappingObjectPermissionFilter,
    ]
    filter_class = CounterpartyMappingFilterSet


class CounterpartyClassifierMappingViewSet(AbstractMappingViewSet):
    queryset = CounterpartyClassifierMapping.objects.select_related(
        'master_user', 'provider', 'content_object', 'attribute_type'
    )
    serializer_class = CounterpartyClassifierMappingSerializer
    filter_backends = AbstractMappingViewSet.filter_backends + [
        CounterpartyMappingObjectPermissionFilter,
    ]
    filter_class = CounterpartyClassifierMappingFilterSet


class ResponsibleMappingFilterSet(AbstractMappingFilterSet):
    content_object = ModelExtWithPermissionMultipleChoiceFilter(model=Responsible)

    class Meta(AbstractMappingFilterSet.Meta):
        model = ResponsibleMapping


class ResponsibleClassifierMappingFilterSet(AbstractMappingFilterSet):
    attribute_type = ModelExtWithPermissionMultipleChoiceFilter(model=GenericAttributeType)

    class Meta(AbstractMappingFilterSet.Meta):
        model = ResponsibleClassifierMapping


class ResponsibleMappingViewSet(AbstractMappingViewSet):
    queryset = ResponsibleMapping.objects.select_related(
        'master_user', 'provider', 'content_object'
    )
    serializer_class = ResponsibleMappingSerializer
    filter_backends = AbstractMappingViewSet.filter_backends + [
        ResponsibleMappingObjectPermissionFilter,
    ]
    filter_class = ResponsibleMappingFilterSet


class ResponsibleClassifierMappingViewSet(AbstractMappingViewSet):
    queryset = ResponsibleClassifierMapping.objects.select_related(
        'master_user', 'provider', 'content_object', 'attribute_type'
    )
    serializer_class = ResponsibleClassifierMappingSerializer
    filter_backends = AbstractMappingViewSet.filter_backends + [
        ResponsibleMappingObjectPermissionFilter,
    ]
    filter_class = ResponsibleClassifierMappingFilterSet


class PortfolioMappingFilterSet(AbstractMappingFilterSet):
    content_object = ModelExtWithPermissionMultipleChoiceFilter(model=Portfolio)

    class Meta(AbstractMappingFilterSet.Meta):
        model = PortfolioMapping


class PortfolioClassifierMappingFilterSet(AbstractMappingFilterSet):
    attribute_type = ModelExtWithPermissionMultipleChoiceFilter(model=GenericAttributeType)

    class Meta(AbstractMappingFilterSet.Meta):
        model = PortfolioClassifierMapping


class PortfolioMappingViewSet(AbstractMappingViewSet):
    queryset = PortfolioMapping.objects.select_related(
        'master_user', 'provider', 'content_object'
    )
    serializer_class = PortfolioMappingSerializer
    filter_backends = AbstractMappingViewSet.filter_backends + [
        PortfolioMappingObjectPermissionFilter,
    ]
    filter_class = PortfolioMappingFilterSet


class PortfolioClassifierMappingViewSet(AbstractMappingViewSet):
    queryset = PortfolioClassifierMapping.objects.select_related(
        'master_user', 'provider', 'content_object', 'attribute_type'
    )
    serializer_class = PortfolioClassifierMappingSerializer
    filter_backends = AbstractMappingViewSet.filter_backends + [
        PortfolioMappingObjectPermissionFilter,
    ]
    filter_class = PortfolioClassifierMappingFilterSet


class Strategy1MappingFilterSet(AbstractMappingFilterSet):
    content_object = ModelExtWithPermissionMultipleChoiceFilter(model=Strategy1)

    class Meta(AbstractMappingFilterSet.Meta):
        model = Strategy1Mapping


class Strategy1MappingViewSet(AbstractMappingViewSet):
    queryset = Strategy1Mapping.objects.select_related(
        'master_user', 'provider', 'content_object'
    )
    serializer_class = Strategy1MappingSerializer
    filter_backends = AbstractMappingViewSet.filter_backends + [
        Strategy1MappingObjectPermissionFilter,
    ]
    filter_class = Strategy1MappingFilterSet


class Strategy2MappingFilterSet(AbstractMappingFilterSet):
    content_object = ModelExtWithPermissionMultipleChoiceFilter(model=Strategy2)

    class Meta(AbstractMappingFilterSet.Meta):
        model = Strategy2Mapping


class Strategy2MappingViewSet(AbstractMappingViewSet):
    queryset = Strategy2Mapping.objects.select_related(
        'master_user', 'provider', 'content_object'
    )
    serializer_class = Strategy2MappingSerializer
    filter_backends = AbstractMappingViewSet.filter_backends + [
        Strategy2MappingObjectPermissionFilter,
    ]
    filter_class = Strategy2MappingFilterSet


class Strategy3MappingFilterSet(AbstractMappingFilterSet):
    content_object = ModelExtWithPermissionMultipleChoiceFilter(model=Strategy3)

    class Meta(AbstractMappingFilterSet.Meta):
        model = Strategy3Mapping


class Strategy3MappingViewSet(AbstractMappingViewSet):
    queryset = Strategy3Mapping.objects.select_related(
        'master_user', 'provider', 'content_object'
    )
    serializer_class = Strategy3MappingSerializer
    filter_backends = AbstractMappingViewSet.filter_backends + [
        Strategy3MappingObjectPermissionFilter,
    ]
    filter_class = Strategy3MappingFilterSet


class DailyPricingModelMappingFilterSet(AbstractMappingFilterSet):
    content_object = django_filters.ModelMultipleChoiceFilter(queryset=DailyPricingModelMapping.objects)

    class Meta(AbstractMappingFilterSet.Meta):
        model = DailyPricingModelMapping


class DailyPricingModelMappingViewSet(AbstractMappingViewSet):
    queryset = DailyPricingModelMapping.objects.select_related(
        'master_user', 'provider', 'content_object'
    )
    serializer_class = DailyPricingModelMappingSerializer
    filter_class = DailyPricingModelMappingFilterSet


class PaymentSizeDetailMappingFilterSet(AbstractMappingFilterSet):
    content_object = django_filters.ModelMultipleChoiceFilter(queryset=PaymentSizeDetail.objects)

    class Meta(AbstractMappingFilterSet.Meta):
        model = PaymentSizeDetailMapping


class PaymentSizeDetailMappingViewSet(AbstractMappingViewSet):
    queryset = PaymentSizeDetailMapping.objects.select_related(
        'master_user', 'provider', 'content_object'
    )
    serializer_class = PaymentSizeDetailMappingSerializer
    filter_class = PaymentSizeDetailMappingFilterSet


class PricingConditionMappingFilterSet(AbstractMappingFilterSet):
    content_object = django_filters.ModelMultipleChoiceFilter(queryset=PricingCondition.objects)

    class Meta(AbstractMappingFilterSet.Meta):
        model = PricingConditionMapping


class PricingConditionMappingViewSet(AbstractMappingViewSet):
    queryset = PricingConditionMapping.objects.select_related(
        'master_user', 'provider', 'content_object'
    )
    serializer_class = PricingConditionMappingSerializer
    filter_class = PricingConditionMappingFilterSet


class PriceDownloadSchemeMappingFilterSet(AbstractMappingFilterSet):
    content_object = ModelExtMultipleChoiceFilter(model=PriceDownloadScheme, field_name='scheme_name')

    class Meta(AbstractMappingFilterSet.Meta):
        model = PriceDownloadSchemeMapping


class PriceDownloadSchemeMappingViewSet(AbstractMappingViewSet):
    queryset = PriceDownloadSchemeMapping.objects.select_related(
        'master_user', 'provider', 'content_object'
    )
    serializer_class = PriceDownloadSchemeMappingSerializer
    filter_class = PriceDownloadSchemeMappingFilterSet
    ordering_fields = AbstractMappingViewSet.base_ordering_fields + [
        'content_object__scheme_name',
    ]


# ---------


class TaskFilterSet(FilterSet):
    id = NoOpFilter()
    provider = django_filters.ModelMultipleChoiceFilter(queryset=ProviderClass.objects)
    member = ModelExtMultipleChoiceFilter(model=Member, field_name='username')
    action = CharFilter()
    created = django_filters.DateFromToRangeFilter()
    modified = django_filters.DateFromToRangeFilter()

    class Meta:
        model = Task
        fields = []


class TaskViewSet(AbstractReadOnlyModelViewSet):
    queryset = Task.objects.select_related(
        'provider'
    ).prefetch_related(
        'children'
    )
    serializer_class = TaskSerializer
    filter_backends = AbstractReadOnlyModelViewSet.filter_backends + [
        TaskFilter,
    ]
    filter_class = TaskFilterSet
    ordering_fields = [
        'action', 'created', 'modified'
    ]


class PricingAutomatedScheduleViewSet(AbstractModelViewSet):
    queryset = PricingAutomatedSchedule.objects
    serializer_class = PricingAutomatedScheduleSerializer
    permission_classes = AbstractModelViewSet.permission_classes + [
        SuperUserOrReadOnly,
    ]
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]

    def get_object(self):
        try:
            return self.request.user.master_user.pricing_automated_schedule
        except ObjectDoesNotExist:
            obj = PricingAutomatedSchedule.objects.create(master_user=self.request.user.master_user)
            return obj

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed(method=request.method)


class ImportInstrumentViewSet(AbstractViewSet):
    serializer_class = ImportInstrumentSerializer
    permission_classes = AbstractViewSet.permission_classes + [
        PomsFunctionPermission
    ]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ImportInstrumentCbondsViewSet(AbstractViewSet):
    serializer_class = ImportInstrumentCbondsSerializer
    permission_classes = AbstractViewSet.permission_classes + [
        PomsFunctionPermission
    ]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ImportCurrencyCbondsViewSet(AbstractViewSet):
    serializer_class = ImportCurrencyCbondsSerializer
    permission_classes = AbstractViewSet.permission_classes + [
        PomsFunctionPermission
    ]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ImportUnifiedDataProviderViewSet(AbstractViewSet):
    serializer_class = ImportUnifiedDataProviderSerializer
    permission_classes = AbstractViewSet.permission_classes + [
        PomsFunctionPermission
    ]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ImportPricingViewSet(AbstractViewSet):
    serializer_class = ImportPricingSerializer
    permission_classes = AbstractViewSet.permission_classes + [
        PomsFunctionPermission
    ]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class TestCertificateViewSet(AbstractViewSet):
    serializer_class = TestCertificateSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


# ----------------------------------------


class ComplexTransactionImportSchemeFilterSet(FilterSet):
    id = NoOpFilter()
    provider = django_filters.ModelMultipleChoiceFilter(queryset=ProviderClass.objects)
    scheme_name = CharFilter()

    class Meta:
        model = ComplexTransactionImportScheme
        fields = []


class ComplexTransactionImportSchemeViewSet(AbstractApiView, UpdateModelMixinExt, ModelViewSet):
    permission_classes = [
        IsAuthenticated,
        PomsConfigurationPermission
    ]
    filter_backends = [
        ByIdFilterBackend,
        DjangoFilterBackend,
        OrderingFilter,
        OwnerByMasterUserFilter,
    ]
    queryset = ComplexTransactionImportScheme.objects

    serializer_class = ComplexTransactionImportSchemeSerializer

    filter_class = ComplexTransactionImportSchemeFilterSet
    ordering_fields = [
        'scheme_name',
    ]


class ComplexTransactionImportSchemeLightViewSet(AbstractModelViewSet):
    queryset = ComplexTransactionImportScheme.objects

    serializer_class = ComplexTransactionImportSchemeLightSerializer
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    filter_class = ComplexTransactionImportSchemeFilterSet
    ordering_fields = [
        'scheme_name',
    ]
    permission_classes = AbstractModelViewSet.permission_classes + [
        PomsConfigurationPermission
    ]


class ComplexTransactionCsvFileImportViewSet(AbstractAsyncViewSet):
    serializer_class = ComplexTransactionCsvFileImportSerializer

    permission_classes = AbstractModelViewSet.permission_classes + [
        PomsFunctionPermission
    ]

    def get_serializer_context(self):
        context = super(AbstractAsyncViewSet, self).get_serializer_context()
        context['show_object_permissions'] = False
        return context

    def get_status(self, request, *args, **kwargs):

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        task_id = instance.task_id

        if task_id:

            # res = AsyncResult(signer.unsign(task_id))
            res = AsyncResult(task_id)

            try:
                celery_task = CeleryTask.objects.get(master_user=request.user.master_user, celery_task_id=task_id)
            except CeleryTask.DoesNotExist:
                celery_task = None
                raise PermissionDenied()

            st = time.perf_counter()

            if res.ready():

                instance = res.result
                if celery_task:
                    celery_task.finished_at = datetime_now()
                    celery_task.file_report_id = instance.stats_file_report

            else:

                if res.result:

                    if 'processed_rows' in res.result:
                        instance.processed_rows = res.result['processed_rows']
                    if 'total_rows' in res.result:
                        instance.total_rows = res.result['total_rows']

                    if celery_task:

                        celery_task_data = {}

                        if 'total_rows' in res.result:
                            celery_task_data["total_rows"] = res.result['total_rows']

                        if 'processed_rows' in res.result:
                            celery_task_data["processed_rows"] = res.result['processed_rows']

                        if 'scheme_name' in res.result:
                            celery_task_data["scheme_name"] = res.result['scheme_name']

                        if 'file_name' in res.result:
                            celery_task_data["file_name"] = res.result['file_name']

                        celery_task.data = celery_task_data

                # print('TASK ITEMS LEN %s' % len(res.result.items))

            print('AsyncResult res.ready: %s' % (time.perf_counter() - st))

            if instance.master_user.id != request.user.master_user.id:
                raise PermissionDenied()

            print('TASK RESULT %s' % res.result)
            print('TASK STATUS %s' % res.status)

            if celery_task:
                celery_task.task_status = res.status
                celery_task.save()

            instance.task_id = task_id
            instance.task_status = res.status

            serializer = self.get_serializer(instance=instance, many=False)
            return Response(serializer.data, status=status.HTTP_200_OK)

        else:

            return Response({"message": "Task not found"}, status=status.HTTP_400_BAD_REQUEST)

    def create(self, request, *args, **kwargs):

        st = time.perf_counter()

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        # REFACTOR THIS

        options_object = {}
        options_object['filename'] = instance.filename
        options_object['file_path'] = instance.file_path
        options_object['scheme_id'] = instance.scheme.id
        options_object['execution_context'] = None

        celery_task = CeleryTask.objects.create(master_user=request.user.master_user,
                                                member=request.user.member,
                                                options_object=options_object,
                                                type='transaction_import')

        _l.info('celery_task %s created ' % celery_task.pk)

        # celery_task.save()

        send_system_message(master_user=request.user.master_user,
                            source="Transaction Import Service",
                            text='Member %s started Transaction Import (scheme %s)' % (
                            request.user.member.username, instance.scheme.name))

        complex_transaction_csv_file_import_parallel(task_id=celery_task.pk)

        # def oncommit():
        #
        #     # res = complex_transaction_csv_file_import_parallel.apply_async(kwargs={'task_id': celery_task.pk})
        #     complex_transaction_csv_file_import_parallel(task_id=celery_task.pk)
        #
        #     _l.info('ComplexTransactionCsvFileImportViewSet complex_transaction_csv_file_import_parallel' )
        #
        #     # celery_task.celery_task_id = res.id
        #
        #     celery_task.save()
        #
        # transaction.on_commit(oncommit)

        _l.info('ComplexTransactionCsvFileImportViewSet done: %s', "{:3.3f}".format(time.perf_counter() - st))

        return Response({"task_id": celery_task.pk, "task_status": celery_task.status}, status=status.HTTP_200_OK)


class ComplexTransactionCsvFileImportValidateViewSet(AbstractAsyncViewSet):
    serializer_class = ComplexTransactionCsvFileImportSerializer

    permission_classes = AbstractModelViewSet.permission_classes + [
        PomsFunctionPermission
    ]

    def get_serializer_context(self):
        context = super(AbstractAsyncViewSet, self).get_serializer_context()
        context['show_object_permissions'] = False
        return context

    def get_status(self, request, *args, **kwargs):

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        task_id = instance.task_id

        # signer = TimestampSigner()

        if task_id:

            # res = AsyncResult(signer.unsign(task_id))
            res = AsyncResult(task_id)

            try:
                celery_task = CeleryTask.objects.get(master_user=request.user.master_user, task_id=task_id)
            except CeleryTask.DoesNotExist:
                celery_task = None
                raise PermissionDenied()

            st = time.perf_counter()

            if res.ready():

                instance = res.result
                if celery_task:
                    celery_task.finished_at = datetime_now()
                    celery_task.file_report_id = instance.stats_file_report

            else:

                # DEPRECATED
                if res.result:
                    if 'processed_rows' in res.result:
                        instance.processed_rows = res.result['processed_rows']
                    if 'total_rows' in res.result:
                        instance.total_rows = res.result['total_rows']

                    if celery_task:

                        _l.debug('celery_task %s' % celery_task)
                        _l.debug('res %s' % res)

                        celery_task_data = {}

                        if 'total_rows' in res.result:
                            celery_task_data["total_rows"] = res.result['total_rows']

                        if 'processed_rows' in res.result:
                            celery_task_data["processed_rows"] = res.result['processed_rows']

                        if 'scheme_name' in res.result:
                            celery_task_data["scheme_name"] = res.result['scheme_name']

                        if 'file_name' in res.result:
                            celery_task_data["file_name"] = res.result['file_name']

                        celery_task.data = celery_task_data

                # print('TASK ITEMS LEN %s' % len(res.result.items))

            print('AsyncResult res.ready: %s' % (time.perf_counter() - st))

            if instance.master_user.id != request.user.master_user.id:
                raise PermissionDenied()

            print('TASK RESULT %s' % res.result)
            print('TASK STATUS %s' % res.status)

            instance.task_id = task_id
            instance.task_status = res.status

            if celery_task:
                celery_task.task_status = res.status
                celery_task.save()

            serializer = self.get_serializer(instance=instance, many=False)
            return Response(serializer.data, status=status.HTTP_200_OK)

        else:

            return Response({"message": "Task not found"}, status=status.HTTP_400_BAD_REQUEST)

    def create(self, request, *args, **kwargs):

        st = time.perf_counter()

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        # REFACTOR THIS

        options_object = {}
        options_object['filename'] = instance.filename
        options_object['file_path'] = instance.file_path
        options_object['scheme_id'] = instance.scheme.id
        options_object['execution_context'] = None


        celery_task = CeleryTask.objects.create(master_user=request.user.master_user,
                                                member=request.user.member,
                                                options_object=options_object,
                                                type='validate_transaction_import')

        # celery_task.save()

        complex_transaction_csv_file_import_validate_parallel(task_id=celery_task.pk)

        # def oncommit():
        # 
        #     res = complex_transaction_csv_file_import_validate_parallel.apply_async(kwargs={'task_id': celery_task.pk})
        # 
        #     _l.info('ComplexTransactionCsvFileImportViewSet complex_transaction_csv_file_import_validate_parallel %' % res.id)
        # 
        #     celery_task.celery_task_id = res.id
        # 
        #     celery_task.save()
        # 
        # transaction.on_commit(oncommit)

        _l.info('ComplexTransactionCsvFileImportValidateViewSet done: %s', "{:3.3f}".format(time.perf_counter() - st))

        return Response({"task_id": celery_task.pk, "task_status": celery_task.status}, status=status.HTTP_200_OK)


class TransactionFileResultFilterSet(FilterSet):
    scheme_user_code = CharFilter()

    class Meta:
        model = TransactionFileResult
        fields = []


class TransactionFileResultViewSet(AbstractModelViewSet):
    queryset = TransactionFileResult.objects
    serializer_class = TransactionFileResultSerializer
    filter_class = TransactionFileResultFilterSet
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    permission_classes = []


class TransactionImportJson(APIView):
    permission_classes = []

    def get(self, request):
        _l.debug("BACKEND_ROLES %s" % settings.BACKEND_ROLES)

        return Response({'status': 'ok'})

    def post(self, request):
        # _l.debug('request.data %s' % request.data)

        _l.debug('request.data %s' % request.data)

        procedure_id = request.data['procedure_id']

        master_user = MasterUser.objects.get(token=request.data['user']['token'])

        procedure_instance = RequestDataFileProcedureInstance.objects.get(id=procedure_id, master_user=master_user)

        celery_task = CeleryTask.objects.create(master_user=master_user,
                                                type='transaction_import')

        celery_task.options_object = {
            'reader': request.data['transactions']
        }
        celery_task.save()

        complex_transaction_csv_file_import_parallel(task_id=celery_task.pk)


class TransactionFileResultUploadHandler(APIView):
    permission_classes = []

    def get(self, request):

        _l.debug("BACKEND_ROLES %s" % settings.BACKEND_ROLES)

        return Response({'status': 'ok'})

    def post(self, request):

        # _l.debug('request.data %s' % request.data)

        _l.debug('request.data %s' % request.data)

        procedure_id = request.data['id']

        master_user = MasterUser.objects.get(token=request.data['user']['token'])

        _l.debug('master_user %s' % master_user)

        try:

            procedure_instance = RequestDataFileProcedureInstance.objects.get(id=procedure_id, master_user=master_user)

            try:

                item = TransactionFileResult.objects.get(master_user=master_user,
                                                         provider__user_code=request.data['provider'],
                                                         procedure_instance=procedure_instance)

                if (request.data['files'] and len(request.data['files'])):

                    with transaction.atomic():

                        procedure_instance.symmetric_key = request.data['files'][0]['symmetric_key']
                        procedure_instance.save()

                        item.file_path = request.data['files'][0]["path"]

                        item.save()

                        _l.debug("Transaction File saved successfuly")

                        procedure_instance.status = RequestDataFileProcedureInstance.STATUS_DONE
                        procedure_instance.save()

                    if procedure_instance.schedule_instance:
                        procedure_instance.schedule_instance.run_next_procedure()

                    if procedure_instance.procedure.scheme_type == 'transaction_import':
                        complex_transaction_csv_file_import_by_procedure.apply_async(
                            kwargs={'procedure_instance_id': procedure_instance.id,
                                    'transaction_file_result_id': item.id,
                                    })

                    if procedure_instance.procedure.scheme_type == 'simple_import':
                        data_csv_file_import_by_procedure.apply_async(
                            kwargs={'procedure_instance_id': procedure_instance.id,
                                    'transaction_file_result_id': item.id,
                                    })

                else:
                    _l.debug("No files found")

                    text = "Data File Procedure %s. Files not found" % (
                        procedure_instance.procedure.user_code)

                    send_system_message(master_user=procedure_instance.master_user,
                                        source="Data File Procedure Service",
                                        text=text)

                    procedure_instance.status = RequestDataFileProcedureInstance.STATUS_DONE
                    procedure_instance.save()

                return Response({'status': 'ok'})

            except Exception as e:

                _l.debug("Transaction File error happened %s " % e)

                return Response({'status': 'error'})

        except RequestDataFileProcedureInstance.DoesNotExist:

            _l.debug("Does not exist? RequestDataFileProcedureInstance %s" % procedure_id)

            return Response({'status': '404'})  # TODO handle 404 properly


class DataProviderViewSet(AbstractReadOnlyModelViewSet):
    ordering_fields = ['name']
    filter_fields = ['user_code', 'name']
    pagination_class = None
    queryset = DataProvider.objects
    serializer_class = DataProviderSerializer


class SupersetGetSecurityToken(APIView):

    def get_admin_access_token(self):
        data = {
            'username': 'admin',
            "provider": "db",
            "refresh": True,
            'password': 'lr1018hxvb10yq95ip'
        }

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        url = settings.SUPERSET_URL + 'api/v1/security/login'
        response = requests.post(url=url, data=json.dumps(data), headers=headers)

        response_json = response.json()

        return response_json

    def get_csrf_token(self, tokens):
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": "Bearer %s" % tokens["access_token"]
        }

        url = settings.SUPERSET_URL + 'api/v1/security/csrf_token/'
        response = requests.get(url=url, headers=headers)

        response_json = response.json()

        return response_json['result']

    def get(self, request):
        id = request.query_params.get('id', None)

        tokens = self.get_admin_access_token()

        csrf_token = self.get_csrf_token(tokens)

        _l.info("SupersetGetSecurityToken.got tokens %s" % tokens)
        _l.info("SupersetGetSecurityToken.got csrf_token %s" % csrf_token)

        data = {
            "user": {
                "username": "finmars",
                "first_name": "finmars",
                "last_name": "finmars"
            },
            "resources": [{
                "type": "dashboard",
                "id": id
            }],
            "rls": [
            ]
        }

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": "Bearer %s" % tokens["access_token"],
            'X-CSRFToken': csrf_token
        }

        url = settings.SUPERSET_URL + 'api/v1/security/guest_token/'

        _l.info("SupersetGetSecurityToken.Requesting url %s" % url)

        response = requests.post(url=url, data=json.dumps(data), headers=headers)

        _l.info('SupersetGetSecurityToken.response %s' % response.text)

        response_json = response.json()

        return Response(response_json)
