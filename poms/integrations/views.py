import json
import logging
import time
import traceback
from typing import Any

import django_filters
from django.conf import settings
from django.db.models import Prefetch
from django.http import HttpResponse
from django_filters.rest_framework import FilterSet
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ViewSet

import requests
from celery.result import AsyncResult

from poms.celery_tasks.models import CeleryTask
from poms.common.filters import (
    CharFilter,
    ModelExtMultipleChoiceFilter,
    NoOpFilter,
    GroupsAttributeFilter,
    AttributeFilter,
)
from poms.common.mixins import (
    BulkModelMixin,
    DestroyModelFakeMixin,
    UpdateModelMixinExt,
)
from poms.common.storage import get_storage
from poms.common.utils import datetime_now
from poms.common.views import (
    AbstractApiView,
    AbstractAsyncViewSet,
    AbstractClassModelViewSet,
    AbstractModelViewSet,
    AbstractReadOnlyModelViewSet,
    AbstractViewSet,
)
from poms.currencies.models import Currency
from poms.instruments.models import (
    AccrualCalculationModel,
    PaymentSizeDetail,
    Periodicity,
    PricingCondition,
    PricingPolicy,
)
from poms.integrations.filters import (
    AccountMappingObjectPermissionFilter,
    AccountTypeMappingObjectPermissionFilter,
    CounterpartyMappingObjectPermissionFilter,
    InstrumentAttributeValueMappingObjectPermissionFilter,
    InstrumentMappingObjectPermissionFilter,
    InstrumentTypeMappingObjectPermissionFilter,
    PortfolioMappingObjectPermissionFilter,
    ResponsibleMappingObjectPermissionFilter,
    Strategy1MappingObjectPermissionFilter,
    Strategy2MappingObjectPermissionFilter,
    Strategy3MappingObjectPermissionFilter,
)
from poms.integrations.models import (
    AccountClassifierMapping,
    AccountMapping,
    AccountTypeMapping,
    AccrualCalculationModelMapping,
    AccrualScheduleDownloadMethod,
    BloombergDataProviderCredential,
    ComplexTransactionImportScheme,
    CounterpartyClassifierMapping,
    CounterpartyMapping,
    CurrencyMapping,
    DailyPricingModelMapping,
    DataProvider,
    FactorScheduleDownloadMethod,
    ImportConfig,
    InstrumentAttributeValueMapping,
    InstrumentClassifierMapping,
    InstrumentDownloadScheme,
    InstrumentDownloadSchemeAttribute,
    InstrumentMapping,
    InstrumentTypeMapping,
    PaymentSizeDetailMapping,
    PeriodicityMapping,
    PortfolioClassifierMapping,
    PortfolioMapping,
    PriceDownloadScheme,
    PriceDownloadSchemeMapping,
    PricingConditionMapping,
    PricingPolicyMapping,
    ProviderClass,
    ResponsibleClassifierMapping,
    ResponsibleMapping,
    Strategy1Mapping,
    Strategy2Mapping,
    Strategy3Mapping,
    TransactionFileResult,
    MappingTable,
)
from poms.integrations.serializers import (
    AccountClassifierMappingSerializer,
    AccountMappingSerializer,
    AccountTypeMappingSerializer,
    AccrualCalculationModelMappingSerializer,
    AccrualScheduleDownloadMethodSerializer,
    BloombergDataProviderCredentialSerializer,
    CallBackDataDictRequestSerializer,
    ComplexTransactionCsvFileImportSerializer,
    ComplexTransactionImportSchemeLightSerializer,
    ComplexTransactionImportSchemeSerializer,
    CounterpartyClassifierMappingSerializer,
    CounterpartyMappingSerializer,
    CurrencyMappingSerializer,
    DailyPricingModelMappingSerializer,
    DataProviderSerializer,
    FactorScheduleDownloadMethodSerializer,
    ImportCompanyDatabaseSerializer,
    ImportConfigSerializer,
    ImportCurrencyDatabaseSerializer,
    ImportInstrumentDatabaseSerializer,
    ImportInstrumentSerializer,
    ImportUnifiedDataProviderSerializer,
    InstrumentAttributeValueMappingSerializer,
    InstrumentClassifierMappingSerializer,
    InstrumentDownloadSchemeLightSerializer,
    InstrumentDownloadSchemeSerializer,
    InstrumentMappingSerializer,
    InstrumentTypeMappingSerializer,
    PaymentSizeDetailMappingSerializer,
    PeriodicityMappingSerializer,
    PortfolioClassifierMappingSerializer,
    PortfolioMappingSerializer,
    PriceDownloadSchemeMappingSerializer,
    PriceDownloadSchemeSerializer,
    PricingConditionMappingSerializer,
    PricingPolicyMappingSerializer,
    ProviderClassSerializer,
    ResponsibleClassifierMappingSerializer,
    ResponsibleMappingSerializer,
    Strategy1MappingSerializer,
    Strategy2MappingSerializer,
    Strategy3MappingSerializer,
    TestCertificateSerializer,
    TransactionFileResultSerializer,
    MappingTableSerializer,
)
from poms.procedures.models import RequestDataFileProcedureInstance
from poms.system_messages.handlers import send_system_message
from poms.transaction_import.handlers import TransactionImportProcess
from poms.transaction_import.tasks import transaction_import
from poms.users.filters import OwnerByMasterUserFilter
from poms.users.models import MasterUser
from poms.users.permissions import SuperUserOnly, SuperUserOrReadOnly

_l = logging.getLogger("poms.integrations")

storage = get_storage()


class ProviderClassViewSet(AbstractClassModelViewSet):
    queryset = ProviderClass.objects
    serializer_class = ProviderClassSerializer


class FactorScheduleDownloadMethodViewSet(AbstractClassModelViewSet):
    queryset = FactorScheduleDownloadMethod.objects
    serializer_class = FactorScheduleDownloadMethodSerializer


class AccrualScheduleDownloadMethodViewSet(AbstractClassModelViewSet):
    queryset = AccrualScheduleDownloadMethod.objects
    serializer_class = AccrualScheduleDownloadMethodSerializer


class BloombergDataProviderCredentialViewSet(
    AbstractApiView,
    UpdateModelMixinExt,
    DestroyModelFakeMixin,
    BulkModelMixin,
    ModelViewSet,
):
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
        "provider",
        "payment_size_detail",
        "daily_pricing_model",
        "factor_schedule_method",
        "accrual_calculation_schedule_method",
    ).prefetch_related(
        "inputs",
        Prefetch(
            "attributes",
            queryset=InstrumentDownloadSchemeAttribute.objects.select_related(
                "attribute_type"
            ),
        ),
    )
    serializer_class = InstrumentDownloadSchemeSerializer
    permission_classes = AbstractModelViewSet.permission_classes + []
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    filter_class = InstrumentDownloadSchemeFilterSet
    ordering_fields = [
        "scheme_name",
        "provider",
        "provider__name",
    ]

    @action(
        detail=False,
        methods=["get"],
        url_path="light",
        serializer_class=InstrumentDownloadSchemeLightSerializer,
    )
    def list_light(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginator.post_paginate_queryset(queryset, request)
        serializer = self.get_serializer(page, many=True)

        return self.get_paginated_response(serializer.data)


# DEPRECATED
class InstrumentDownloadSchemeLightViewSet(AbstractModelViewSet):
    queryset = InstrumentDownloadScheme.objects.select_related(
        "provider",
    )
    serializer_class = InstrumentDownloadSchemeLightSerializer
    permission_classes = AbstractModelViewSet.permission_classes + []
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    filter_class = InstrumentDownloadSchemeFilterSet
    ordering_fields = [
        "scheme_name",
        "provider",
        "provider__name",
    ]


class PriceDownloadSchemeFilterSet(FilterSet):
    id = NoOpFilter()
    provider = django_filters.ModelMultipleChoiceFilter(queryset=ProviderClass.objects)
    scheme_name = CharFilter()

    class Meta:
        model = PriceDownloadScheme
        fields = []


class PriceDownloadSchemeViewSet(AbstractModelViewSet):
    queryset = PriceDownloadScheme.objects.select_related("provider")
    serializer_class = PriceDownloadSchemeSerializer
    # permission_classes = AbstractModelViewSet.permission_classes + [
    #     SuperUserOrReadOnly,
    # ]
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    filter_class = PriceDownloadSchemeFilterSet
    ordering_fields = [
        "scheme_name",
        "provider",
        "provider__name",
    ]
    permission_classes = AbstractModelViewSet.permission_classes + []


class MappingTableFilterSet(FilterSet):
    id = NoOpFilter()
    name = CharFilter()
    user_code = CharFilter()

    class Meta:
        fields = []


class MappingTableViewSet(AbstractModelViewSet):
    queryset = MappingTable.objects.prefetch_related("items")
    serializer_class = MappingTableSerializer
    permission_classes = AbstractModelViewSet.permission_classes + [SuperUserOrReadOnly]
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    filter_class = MappingTableFilterSet
    ordering_fields = ["name", "user_code"]


class AbstractMappingFilterSet(FilterSet):
    id = NoOpFilter()
    provider = django_filters.ModelMultipleChoiceFilter(queryset=ProviderClass.objects)
    value = CharFilter()

    class Meta:
        fields = []


class AbstractMappingViewSet(AbstractModelViewSet):
    queryset = None
    serializer_class = None
    permission_classes = AbstractModelViewSet.permission_classes + [SuperUserOrReadOnly]
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    filter_class = None
    base_ordering_fields = [
        "provider",
        "provider__name",
        "value",
        "content_object",
    ]
    ordering_fields = [
        "provider",
        "provider__name",
        "value",
        "content_object",
        "content_object__user_code",
        "content_object__name",
        "content_object__short_name",
        "content_object__public_name",
    ]


class CurrencyMappingFilterSet(AbstractMappingFilterSet):
    content_object = ModelExtMultipleChoiceFilter(model=Currency)

    class Meta(AbstractMappingFilterSet.Meta):
        model = CurrencyMapping


class CurrencyMappingViewSet(AbstractMappingViewSet):
    queryset = CurrencyMapping.objects.select_related(
        "master_user", "provider", "content_object"
    )
    serializer_class = CurrencyMappingSerializer
    filter_class = CurrencyMappingFilterSet


class PricingPolicyMappingFilterSet(AbstractMappingFilterSet):
    content_object = ModelExtMultipleChoiceFilter(model=PricingPolicy)

    class Meta(AbstractMappingFilterSet.Meta):
        model = PricingPolicyMapping


class PricingPolicyMappingViewSet(AbstractMappingViewSet):
    queryset = PricingPolicyMapping.objects.select_related(
        "master_user", "provider", "content_object"
    )
    serializer_class = PricingPolicyMappingSerializer
    filter_class = PricingPolicyMappingFilterSet


class AccountTypeMappingFilterSet(AbstractMappingFilterSet):
    class Meta(AbstractMappingFilterSet.Meta):
        model = AccountTypeMapping


class AccountTypeMappingViewSet(AbstractMappingViewSet):
    queryset = AccountTypeMapping.objects.select_related(
        "master_user", "provider", "content_object"
    )
    serializer_class = AccountTypeMappingSerializer
    filter_backends = AbstractMappingViewSet.filter_backends + [
        AccountTypeMappingObjectPermissionFilter,
    ]
    filter_class = AccountTypeMappingFilterSet


class InstrumentTypeMappingFilterSet(AbstractMappingFilterSet):
    class Meta(AbstractMappingFilterSet.Meta):
        model = InstrumentTypeMapping


class InstrumentTypeMappingViewSet(AbstractMappingViewSet):
    queryset = InstrumentTypeMapping.objects.select_related(
        "master_user", "provider", "content_object"
    )
    serializer_class = InstrumentTypeMappingSerializer
    filter_backends = AbstractMappingViewSet.filter_backends + [
        InstrumentTypeMappingObjectPermissionFilter,
    ]
    filter_class = InstrumentTypeMappingFilterSet


class InstrumentAttributeValueMappingFilterSet(AbstractMappingFilterSet):
    class Meta(AbstractMappingFilterSet.Meta):
        model = InstrumentAttributeValueMapping


class InstrumentAttributeValueMappingViewSet(AbstractMappingViewSet):
    queryset = InstrumentAttributeValueMapping.objects.select_related(
        "master_user", "provider", "content_object", "classifier"
    )
    serializer_class = InstrumentAttributeValueMappingSerializer
    filter_backends = AbstractMappingViewSet.filter_backends + [
        InstrumentAttributeValueMappingObjectPermissionFilter,
    ]
    filter_class = InstrumentAttributeValueMappingFilterSet


class AccrualCalculationModelMappingFilterSet(AbstractMappingFilterSet):
    content_object = django_filters.ModelMultipleChoiceFilter(
        queryset=AccrualCalculationModel.objects
    )

    class Meta(AbstractMappingFilterSet.Meta):
        model = AccrualCalculationModelMapping


class AccrualCalculationModelMappingViewSet(AbstractMappingViewSet):
    queryset = AccrualCalculationModelMapping.objects.select_related(
        "master_user", "provider", "content_object"
    )
    serializer_class = AccrualCalculationModelMappingSerializer
    filter_class = AccrualCalculationModelMappingFilterSet


class PeriodicityMappingFilterSet(AbstractMappingFilterSet):
    content_object = django_filters.ModelMultipleChoiceFilter(
        queryset=Periodicity.objects
    )

    class Meta(AbstractMappingFilterSet.Meta):
        model = PeriodicityMapping


class PeriodicityMappingViewSet(AbstractMappingViewSet):
    queryset = PeriodicityMapping.objects.select_related(
        "master_user", "provider", "content_object"
    )
    serializer_class = PeriodicityMappingSerializer
    filter_class = PeriodicityMappingFilterSet


class AccountMappingFilterSet(AbstractMappingFilterSet):
    class Meta(AbstractMappingFilterSet.Meta):
        model = AccountMapping


class AccountClassifierMappingFilterSet(AbstractMappingFilterSet):
    class Meta(AbstractMappingFilterSet.Meta):
        model = AccountClassifierMapping


class AccountMappingViewSet(AbstractMappingViewSet):
    queryset = AccountMapping.objects.select_related(
        "master_user", "provider", "content_object"
    )
    serializer_class = AccountMappingSerializer
    filter_backends = AbstractMappingViewSet.filter_backends + [
        AccountMappingObjectPermissionFilter,
    ]
    filter_class = AccountMappingFilterSet


class AccountClassifierMappingViewSet(AbstractMappingViewSet):
    queryset = AccountClassifierMapping.objects.select_related(
        "master_user", "provider", "content_object", "attribute_type"
    )
    serializer_class = AccountClassifierMappingSerializer
    filter_backends = AbstractMappingViewSet.filter_backends + [
        AccountMappingObjectPermissionFilter,
    ]
    filter_class = AccountClassifierMappingFilterSet


class InstrumentMappingFilterSet(AbstractMappingFilterSet):
    class Meta(AbstractMappingFilterSet.Meta):
        model = InstrumentMapping


class InstrumentMappingViewSet(AbstractMappingViewSet):
    queryset = InstrumentMapping.objects.select_related(
        "master_user", "provider", "content_object"
    )
    serializer_class = InstrumentMappingSerializer
    filter_backends = AbstractMappingViewSet.filter_backends + [
        InstrumentMappingObjectPermissionFilter,
    ]
    filter_class = InstrumentMappingFilterSet


class InstrumentClassifierMappingFilterSet(AbstractMappingFilterSet):
    class Meta(AbstractMappingFilterSet.Meta):
        model = InstrumentClassifierMapping


class InstrumentClassifierMappingViewSet(AbstractMappingViewSet):
    queryset = InstrumentClassifierMapping.objects.select_related(
        "master_user", "provider", "content_object"
    )
    serializer_class = InstrumentClassifierMappingSerializer
    filter_backends = AbstractMappingViewSet.filter_backends + [
        InstrumentMappingObjectPermissionFilter,
    ]
    filter_class = InstrumentClassifierMappingFilterSet


class CounterpartyMappingFilterSet(AbstractMappingFilterSet):
    class Meta(AbstractMappingFilterSet.Meta):
        model = CounterpartyMapping


class CounterpartyClassifierMappingFilterSet(AbstractMappingFilterSet):
    class Meta(AbstractMappingFilterSet.Meta):
        model = CounterpartyClassifierMapping


class CounterpartyMappingViewSet(AbstractMappingViewSet):
    queryset = CounterpartyMapping.objects.select_related(
        "master_user", "provider", "content_object"
    )
    serializer_class = CounterpartyMappingSerializer
    filter_backends = AbstractMappingViewSet.filter_backends + [
        CounterpartyMappingObjectPermissionFilter,
    ]
    filter_class = CounterpartyMappingFilterSet


class CounterpartyClassifierMappingViewSet(AbstractMappingViewSet):
    queryset = CounterpartyClassifierMapping.objects.select_related(
        "master_user", "provider", "content_object", "attribute_type"
    )
    serializer_class = CounterpartyClassifierMappingSerializer
    filter_backends = AbstractMappingViewSet.filter_backends + [
        CounterpartyMappingObjectPermissionFilter,
    ]
    filter_class = CounterpartyClassifierMappingFilterSet


class ResponsibleMappingFilterSet(AbstractMappingFilterSet):
    class Meta(AbstractMappingFilterSet.Meta):
        model = ResponsibleMapping


class ResponsibleClassifierMappingFilterSet(AbstractMappingFilterSet):
    class Meta(AbstractMappingFilterSet.Meta):
        model = ResponsibleClassifierMapping


class ResponsibleMappingViewSet(AbstractMappingViewSet):
    queryset = ResponsibleMapping.objects.select_related(
        "master_user", "provider", "content_object"
    )
    serializer_class = ResponsibleMappingSerializer
    filter_backends = AbstractMappingViewSet.filter_backends + [
        ResponsibleMappingObjectPermissionFilter,
    ]
    filter_class = ResponsibleMappingFilterSet


class ResponsibleClassifierMappingViewSet(AbstractMappingViewSet):
    queryset = ResponsibleClassifierMapping.objects.select_related(
        "master_user", "provider", "content_object", "attribute_type"
    )
    serializer_class = ResponsibleClassifierMappingSerializer
    filter_backends = AbstractMappingViewSet.filter_backends + [
        ResponsibleMappingObjectPermissionFilter,
    ]
    filter_class = ResponsibleClassifierMappingFilterSet


class PortfolioMappingFilterSet(AbstractMappingFilterSet):
    class Meta(AbstractMappingFilterSet.Meta):
        model = PortfolioMapping


class PortfolioClassifierMappingFilterSet(AbstractMappingFilterSet):
    class Meta(AbstractMappingFilterSet.Meta):
        model = PortfolioClassifierMapping


class PortfolioMappingViewSet(AbstractMappingViewSet):
    queryset = PortfolioMapping.objects.select_related(
        "master_user", "provider", "content_object"
    )
    serializer_class = PortfolioMappingSerializer
    filter_backends = AbstractMappingViewSet.filter_backends + [
        PortfolioMappingObjectPermissionFilter,
    ]
    filter_class = PortfolioMappingFilterSet


class PortfolioClassifierMappingViewSet(AbstractMappingViewSet):
    queryset = PortfolioClassifierMapping.objects.select_related(
        "master_user", "provider", "content_object", "attribute_type"
    )
    serializer_class = PortfolioClassifierMappingSerializer
    filter_backends = AbstractMappingViewSet.filter_backends + [
        PortfolioMappingObjectPermissionFilter,
    ]
    filter_class = PortfolioClassifierMappingFilterSet


class Strategy1MappingFilterSet(AbstractMappingFilterSet):
    class Meta(AbstractMappingFilterSet.Meta):
        model = Strategy1Mapping


class Strategy1MappingViewSet(AbstractMappingViewSet):
    queryset = Strategy1Mapping.objects.select_related(
        "master_user", "provider", "content_object"
    )
    serializer_class = Strategy1MappingSerializer
    filter_backends = AbstractMappingViewSet.filter_backends + [
        Strategy1MappingObjectPermissionFilter,
    ]
    filter_class = Strategy1MappingFilterSet


class Strategy2MappingFilterSet(AbstractMappingFilterSet):
    class Meta(AbstractMappingFilterSet.Meta):
        model = Strategy2Mapping


class Strategy2MappingViewSet(AbstractMappingViewSet):
    queryset = Strategy2Mapping.objects.select_related(
        "master_user", "provider", "content_object"
    )
    serializer_class = Strategy2MappingSerializer
    filter_backends = AbstractMappingViewSet.filter_backends + [
        Strategy2MappingObjectPermissionFilter,
    ]
    filter_class = Strategy2MappingFilterSet


class Strategy3MappingFilterSet(AbstractMappingFilterSet):
    class Meta(AbstractMappingFilterSet.Meta):
        model = Strategy3Mapping


class Strategy3MappingViewSet(AbstractMappingViewSet):
    queryset = Strategy3Mapping.objects.select_related(
        "master_user", "provider", "content_object"
    )
    serializer_class = Strategy3MappingSerializer
    filter_backends = AbstractMappingViewSet.filter_backends + [
        Strategy3MappingObjectPermissionFilter,
    ]
    filter_class = Strategy3MappingFilterSet


class DailyPricingModelMappingFilterSet(AbstractMappingFilterSet):
    content_object = django_filters.ModelMultipleChoiceFilter(
        queryset=DailyPricingModelMapping.objects
    )

    class Meta(AbstractMappingFilterSet.Meta):
        model = DailyPricingModelMapping


class DailyPricingModelMappingViewSet(AbstractMappingViewSet):
    queryset = DailyPricingModelMapping.objects.select_related(
        "master_user", "provider", "content_object"
    )
    serializer_class = DailyPricingModelMappingSerializer
    filter_class = DailyPricingModelMappingFilterSet


class PaymentSizeDetailMappingFilterSet(AbstractMappingFilterSet):
    content_object = django_filters.ModelMultipleChoiceFilter(
        queryset=PaymentSizeDetail.objects
    )

    class Meta(AbstractMappingFilterSet.Meta):
        model = PaymentSizeDetailMapping


class PaymentSizeDetailMappingViewSet(AbstractMappingViewSet):
    queryset = PaymentSizeDetailMapping.objects.select_related(
        "master_user", "provider", "content_object"
    )
    serializer_class = PaymentSizeDetailMappingSerializer
    filter_class = PaymentSizeDetailMappingFilterSet


class PricingConditionMappingFilterSet(AbstractMappingFilterSet):
    content_object = django_filters.ModelMultipleChoiceFilter(
        queryset=PricingCondition.objects
    )

    class Meta(AbstractMappingFilterSet.Meta):
        model = PricingConditionMapping


class PricingConditionMappingViewSet(AbstractMappingViewSet):
    queryset = PricingConditionMapping.objects.select_related(
        "master_user", "provider", "content_object"
    )
    serializer_class = PricingConditionMappingSerializer
    filter_class = PricingConditionMappingFilterSet


class PriceDownloadSchemeMappingFilterSet(AbstractMappingFilterSet):
    content_object = ModelExtMultipleChoiceFilter(
        model=PriceDownloadScheme, field_name="scheme_name"
    )

    class Meta(AbstractMappingFilterSet.Meta):
        model = PriceDownloadSchemeMapping


class PriceDownloadSchemeMappingViewSet(AbstractMappingViewSet):
    queryset = PriceDownloadSchemeMapping.objects.select_related(
        "master_user", "provider", "content_object"
    )
    serializer_class = PriceDownloadSchemeMappingSerializer
    filter_class = PriceDownloadSchemeMappingFilterSet
    ordering_fields = AbstractMappingViewSet.base_ordering_fields + [
        "content_object__scheme_name",
    ]


class ImportInstrumentViewSet(AbstractViewSet):
    permission_classes = AbstractViewSet.permission_classes + []
    serializer_class = ImportInstrumentSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ImportUnifiedDataProviderViewSet(AbstractViewSet):
    permission_classes = AbstractViewSet.permission_classes + []
    serializer_class = ImportUnifiedDataProviderSerializer

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


# database import callbacks FN-1736
class UnifiedCallBackDatabaseViewSet(ViewSet):
    permission_classes = []
    authentication_classes = []
    callback_serializer_class = CallBackDataDictRequestSerializer

    def handle_callback(self, validated_data: dict) -> dict:
        raise NotImplementedError

    def error_task_response(self, e: Exception, task: CeleryTask) -> dict:
        func = f"{self.__class__.__name__} task.id={task.id}"

        err_msg = f"{func} callback {repr(e)}\n {traceback.format_exc()}"
        _l.error(err_msg)
        task.status = CeleryTask.STATUS_ERROR
        task.notes = err_msg
        task.save()

        return {
            "status": "error",
            "notes": err_msg,
            "request_id": task.id,
        }

    def success_task_response(self, task: CeleryTask, instance: Any) -> dict:
        func = f"{self.__class__.__name__} task.id={task.id}"
        _l.info(f"{func} success, {type(instance)}.id={instance.id} ")

        task.result_object = {
            "result_id": instance.id,
            "name": instance.name,
            "user_code": instance.user_code,
            "short_name": instance.short_name,
        }
        task.status = CeleryTask.STATUS_DONE
        task.save()

        return {
            "status": "ok",
            "notes": None,
            "request_id": task.id,
        }

    @swagger_auto_schema(
        request_body=CallBackDataDictRequestSerializer,
        responses={200: "ok"},
        operation_description="receive database info and update task",
    )
    def create(self, request, *args, **kwargs):
        _l.info(f"{self.__class__.__name__}.callback request.data={request.data}")

        serializer = self.callback_serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(self.handle_callback(serializer.validated_data))


# database import callbacks FN-1736
class InstrumentCallBackViewSet(UnifiedCallBackDatabaseViewSet):
    def handle_callback(self, validated_data: dict) -> dict:
        from poms.integrations.tasks import handle_currency_and_instrument_api_data

        task = validated_data["task"]
        data = validated_data["data"]
        if "instruments" not in data or "currencies" not in data:
            err_msg = "no 'instruments' or 'currencies' in request.data"
            raise ValidationError(err_msg)

        try:
            instrument = handle_currency_and_instrument_api_data(
                api_data=data,
                task=task,
                caller=f"{self.__class__.__name__} task.id={task.id}",
            )

        except Exception as e:
            return self.error_task_response(e, task)

        else:
            return self.success_task_response(task, instrument)


# database import callbacks FN-1736
class CurrencyCallBackViewSet(UnifiedCallBackDatabaseViewSet):
    def handle_callback(self, validated_data: dict) -> dict:
        from poms.integrations.tasks import create_currency_from_callback_data

        task = validated_data["task"]
        data = validated_data["data"]
        try:
            currency = create_currency_from_callback_data(
                data,
                task.master_user,
                task.member,
            )

        except Exception as e:
            return self.error_task_response(e, task)

        else:
            return self.success_task_response(task, currency)


# database import callbacks FN-1736
class CompanyCallBackViewSet(UnifiedCallBackDatabaseViewSet):
    def handle_callback(self, validated_data: dict) -> dict:
        from poms.integrations.tasks import create_counterparty_from_callback_data

        task = validated_data["task"]
        data = validated_data["data"]
        try:
            company = create_counterparty_from_callback_data(
                data,
                task.master_user,
                task.member,
            )

        except Exception as e:
            return self.error_task_response(e, task)

        else:
            return self.success_task_response(task, company)


class ImportInstrumentDatabaseViewSet(AbstractViewSet):
    serializer_class = ImportInstrumentDatabaseSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.create_task(serializer.validated_data))


class ImportCurrencyDatabaseViewSet(AbstractViewSet):
    serializer_class = ImportCurrencyDatabaseSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.create_task(serializer.validated_data))


class ImportCompanyDatabaseViewSet(AbstractViewSet):
    serializer_class = ImportCompanyDatabaseSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.create_task(serializer.validated_data))


# ----------------------------------------


class ComplexTransactionImportSchemeFilterSet(FilterSet):
    id = NoOpFilter()
    provider = django_filters.ModelMultipleChoiceFilter(queryset=ProviderClass.objects)
    scheme_name = CharFilter()

    class Meta:
        model = ComplexTransactionImportScheme
        fields = []


class ComplexTransactionImportSchemeViewSet(
    AbstractModelViewSet, UpdateModelMixinExt, ModelViewSet
):
    permission_classes = [IsAuthenticated]
    filter_backends = [
        OwnerByMasterUserFilter,
        GroupsAttributeFilter,
        AttributeFilter,
    ]
    queryset = ComplexTransactionImportScheme.objects

    serializer_class = ComplexTransactionImportSchemeSerializer

    filter_class = ComplexTransactionImportSchemeFilterSet
    ordering_fields = [
        "scheme_name",
    ]

    @action(
        detail=False,
        methods=["get"],
        url_path="light",
        serializer_class=ComplexTransactionImportSchemeLightSerializer,
    )
    def list_light(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginator.post_paginate_queryset(queryset, request)
        serializer = self.get_serializer(page, many=True)

        return self.get_paginated_response(serializer.data)


class TransactionImportViewSet(AbstractAsyncViewSet):
    serializer_class = ComplexTransactionCsvFileImportSerializer

    permission_classes = AbstractModelViewSet.permission_classes + []

    def get_serializer_context(self):
        context = super(AbstractAsyncViewSet, self).get_serializer_context()
        context["show_object_permissions"] = False
        return context

    def get_status(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        task_id = instance.task_id

        if task_id:
            res = AsyncResult(task_id)

            try:
                celery_task = CeleryTask.objects.get(
                    master_user=request.user.master_user,
                    celery_task_id=task_id,
                )
            except CeleryTask.DoesNotExist as e:
                raise PermissionDenied from e

            st = time.perf_counter()

            if res.ready():
                instance = res.result
                if celery_task:
                    celery_task.finished_at = datetime_now()
                    celery_task.file_report_id = instance.stats_file_report

            else:
                if res.result:
                    if "processed_rows" in res.result:
                        instance.processed_rows = res.result["processed_rows"]
                    if "total_rows" in res.result:
                        instance.total_rows = res.result["total_rows"]

                    if celery_task:
                        celery_task_data = {}

                        if "total_rows" in res.result:
                            celery_task_data["total_rows"] = res.result["total_rows"]

                        if "processed_rows" in res.result:
                            celery_task_data["processed_rows"] = res.result[
                                "processed_rows"
                            ]

                        if "scheme_name" in res.result:
                            celery_task_data["scheme_name"] = res.result["scheme_name"]

                        if "file_name" in res.result:
                            celery_task_data["file_name"] = res.result["file_name"]

                        celery_task.data = celery_task_data

                # print('TASK ITEMS LEN %s' % len(res.result.items))

            print("AsyncResult res.ready: %s" % (time.perf_counter() - st))

            if instance.master_user.id != request.user.master_user.id:
                raise PermissionDenied()

            print("TASK RESULT %s" % res.result)
            print("TASK STATUS %s" % res.status)

            if celery_task:
                celery_task.task_status = res.status
                celery_task.save()

            instance.task_id = task_id
            instance.task_status = res.status

            serializer = self.get_serializer(instance=instance, many=False)
            return Response(serializer.data, status=status.HTTP_200_OK)

        else:
            return Response(
                {"message": "Task not found"}, status=status.HTTP_400_BAD_REQUEST
            )

    def create(self, request, *args, **kwargs):
        st = time.perf_counter()

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        # REFACTOR THIS

        options_object = {
            "file_name": instance.file_name,
            "file_path": instance.file_path,
            "scheme_id": instance.scheme.id,
            "execution_context": None,
        }
        # _l.info('options_object %s' % options_object)

        celery_task = CeleryTask.objects.create(
            master_user=request.user.master_user,
            member=request.user.member,
            options_object=options_object,
            verbose_name="Transaction Import",
            type="transaction_import",
        )

        _l.info(f"celery_task {celery_task.pk} created ")

        send_system_message(
            master_user=request.user.master_user,
            performed_by="System",
            description=(
                f"Member {request.user.member.username} started Transaction Import "
                f"(scheme {instance.scheme.name})"
            ),
        )

        transaction_import.apply_async(
            kwargs={"task_id": celery_task.pk, 'context': {
                'space_code': celery_task.master_user.space_code,
                'realm_code': celery_task.master_user.realm_code
            }}, queue="backend-background-queue"
        )

        _l.info(
            "ComplexTransactionCsvFileImportViewSet done: %s",
            "{:3.3f}".format(time.perf_counter() - st),
        )

        return Response(
            {"task_id": celery_task.pk, "task_status": celery_task.status},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"], url_path="execute")
    def execute(self, request, *args, **kwargs):
        st = time.perf_counter()

        _l.info("TransactionImportViewSet.execute")
        options_object = {
            "items": request.data.get("items", None),
            "file_path": request.data.get("file_path", None),
        }

        if options_object["file_path"]:
            # TODO refactor to file_name
            options_object["filename"] = request.data["file_path"].split("/")[-1]
        else:
            options_object["filename"] = None
        options_object["scheme_user_code"] = request.data["scheme_user_code"]
        options_object["execution_context"] = None

        # _l.info('options_object %s' % options_object)

        celery_task = CeleryTask.objects.create(
            master_user=request.user.master_user,
            member=request.user.member,
            options_object=options_object,
            verbose_name="Transaction Import",
            type="transaction_import",
        )

        _l.info(f"celery_task {celery_task.pk} created ")

        send_system_message(
            master_user=request.user.master_user,
            performed_by="System",
            description=(
                f"Member {request.user.member.username} started Transaction Import "
                f'(scheme {options_object["scheme_user_code"]})'
            ),
        )

        transaction_import.apply_async(
            kwargs={"task_id": celery_task.pk, 'context': {
                'space_code': celery_task.master_user.space_code,
                'realm_code': celery_task.master_user.realm_code
            }}, queue="backend-background-queue"
        )

        _l.info(
            "ComplexTransactionCsvFileImportViewSet done: %s",
            "{:3.3f}".format(time.perf_counter() - st),
        )

        return Response(
            {"task_id": celery_task.pk, "task_status": celery_task.status},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"], url_path="dry-run")
    def dry_run(self, request, *args, **kwargs):
        from poms.transactions.models import ComplexTransaction

        _l.info("TransactionImportViewSet Dry Run")

        st = time.perf_counter()

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        # REFACTOR THIS

        options_object = {
            "file_name": instance.file_name,
            "file_path": instance.file_path,
            "scheme_id": instance.scheme.id,
            "execution_context": None,
        }

        _l.info(f"options_object {options_object}")

        celery_task = CeleryTask.objects.create(
            master_user=request.user.master_user,
            member=request.user.member,
            options_object=options_object,
            verbose_name="Transaction Import",
            type="transaction_import",
        )

        _l.info(f"celery_task {celery_task.pk} created ")

        transaction_import.apply(
            kwargs={"task_id": celery_task.pk},
            queue="backend-background-queue",
        )

        result = []
        error_message = None

        try:
            task = CeleryTask.objects.get(id=celery_task.id)

            result = task.result_object
        except Exception as e:
            error_message = str(e)

        _l.info(
            "ComplexTransaction Dry Run done: %s",
            "{:3.3f}".format(time.perf_counter() - st),
        )

        ComplexTransaction.objects.filter(linked_import_task=celery_task.pk).delete()

        storage.delete(instance.file_path)

        return Response(
            {
                "task_id": celery_task.pk,
                "task_status": celery_task.status,
                "result": result,
                "error_message": error_message,
            }
        )


# DEPRECATED
class ComplexTransactionImportSchemeLightViewSet(AbstractModelViewSet):
    queryset = ComplexTransactionImportScheme.objects

    serializer_class = ComplexTransactionImportSchemeLightSerializer
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    filter_class = ComplexTransactionImportSchemeFilterSet
    ordering_fields = [
        "scheme_name",
    ]
    permission_classes = AbstractModelViewSet.permission_classes + []


class ComplexTransactionFilePreprocessViewSet(AbstractAsyncViewSet):
    serializer_class = ComplexTransactionCsvFileImportSerializer

    permission_classes = AbstractModelViewSet.permission_classes + []

    def get_serializer_context(self):
        context = super(AbstractAsyncViewSet, self).get_serializer_context()
        context["show_object_permissions"] = False
        return context

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        if not instance.scheme.data_preprocess_expression:
            raise ValidationError(
                {
                    "data_preprocess_expression": "data_preprocess_expression is required to preprocess file"
                }
            )

        options_object = {
            "file_name": instance.file_name,
            "file_path": instance.file_path,
            "scheme_id": instance.scheme.id,
            "execution_context": None,
        }
        celery_task = CeleryTask.objects.create(
            master_user=request.user.master_user,
            member=request.user.member,
            options_object=options_object,
            verbose_name="Transaction Import",
            type="transaction_import",
        )

        transaction_import_process = TransactionImportProcess(task_id=celery_task.id)

        transaction_import_process.fill_with_raw_items()

        new_raw_items = transaction_import_process.whole_file_preprocess()

        filename_without_ext = instance.file_name.split(".")[0]

        response = HttpResponse(
            new_raw_items, content_type="application/force-download"
        )
        response[
            "Content-Disposition"
        ] = f"attachment; filename=preprocessed_{filename_without_ext}.json"

        return response


class ComplexTransactionCsvFileImportViewSet(AbstractAsyncViewSet):
    serializer_class = ComplexTransactionCsvFileImportSerializer
    permission_classes = AbstractModelViewSet.permission_classes + []

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["show_object_permissions"] = False
        return context

    def get_status(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        task_id = instance.task_id

        if task_id:
            res = AsyncResult(task_id)

            try:
                celery_task = CeleryTask.objects.get(
                    master_user=request.user.master_user,
                    celery_task_id=task_id,
                )
            except CeleryTask.DoesNotExist as e:
                raise PermissionDenied(f"invalid task permission {task_id}") from e

            st = time.perf_counter()

            if res.ready():
                instance = res.result
                if celery_task:
                    celery_task.finished_at = datetime_now()
                    celery_task.file_report_id = instance.stats_file_report

            else:
                if res.result:
                    if "processed_rows" in res.result:
                        instance.processed_rows = res.result["processed_rows"]
                    if "total_rows" in res.result:
                        instance.total_rows = res.result["total_rows"]

                    if celery_task:
                        celery_task_data = {}

                        if "total_rows" in res.result:
                            celery_task_data["total_rows"] = res.result["total_rows"]

                        if "processed_rows" in res.result:
                            celery_task_data["processed_rows"] = res.result[
                                "processed_rows"
                            ]

                        if "scheme_name" in res.result:
                            celery_task_data["scheme_name"] = res.result["scheme_name"]

                        if "file_name" in res.result:
                            celery_task_data["file_name"] = res.result["file_name"]

                        celery_task.data = celery_task_data

                # print('TASK ITEMS LEN %s' % len(res.result.items))

            print("AsyncResult res.ready: %s" % (time.perf_counter() - st))

            if instance.master_user.id != request.user.master_user.id:
                raise PermissionDenied()

            print("TASK RESULT %s" % res.result)
            print("TASK STATUS %s" % res.status)

            if celery_task:
                celery_task.task_status = res.status
                celery_task.save()

            instance.task_id = task_id
            instance.task_status = res.status

            serializer = self.get_serializer(instance=instance, many=False)
            return Response(serializer.data, status=status.HTTP_200_OK)

        else:
            return Response(
                {"message": "Task not found"}, status=status.HTTP_400_BAD_REQUEST
            )

    def create(self, request, *args, **kwargs):
        st = time.perf_counter()

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        options_object = {
            "file_name": instance.file_name,
            "file_path": instance.file_path,
            "scheme_id": instance.scheme.id,
            "execution_context": None,
        }

        _l.info(f"options_object {options_object}")

        celery_task = CeleryTask.objects.create(
            master_user=request.user.master_user,
            member=request.user.member,
            options_object=options_object,
            verbose_name="Transaction Import",
            type="transaction_import",
        )

        _l.info(f"celery_task {celery_task.pk} created ")

        send_system_message(
            master_user=request.user.master_user,
            performed_by="System",
            description=(
                f"Member {request.user.member.username} started Transaction Import "
                f"(scheme {instance.scheme.name})"
            ),
        )

        transaction_import.apply_async(
            kwargs={"task_id": celery_task.pk, 'context': {
                'space_code': celery_task.master_user.space_code,
                'realm_code': celery_task.master_user.realm_code
            }},
            queue="backend-background-queue",
        )

        _l.info(
            "ComplexTransactionCsvFileImportViewSet done: %s",
            "{:3.3f}".format(time.perf_counter() - st),
        )

        return Response(
            {"task_id": celery_task.pk, "task_status": celery_task.status},
            status=status.HTTP_200_OK,
        )


class ComplexTransactionCsvFileImportValidateViewSet(AbstractAsyncViewSet):
    serializer_class = ComplexTransactionCsvFileImportSerializer

    permission_classes = AbstractModelViewSet.permission_classes + []

    def get_serializer_context(self):
        context = super(AbstractAsyncViewSet, self).get_serializer_context()
        context["show_object_permissions"] = False
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
                celery_task = CeleryTask.objects.get(
                    master_user=request.user.master_user, task_id=task_id
                )
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
                    if "processed_rows" in res.result:
                        instance.processed_rows = res.result["processed_rows"]
                    if "total_rows" in res.result:
                        instance.total_rows = res.result["total_rows"]

                    if celery_task:
                        _l.debug("celery_task %s" % celery_task)
                        _l.debug("res %s" % res)

                        celery_task_data = {}

                        if "total_rows" in res.result:
                            celery_task_data["total_rows"] = res.result["total_rows"]

                        if "processed_rows" in res.result:
                            celery_task_data["processed_rows"] = res.result[
                                "processed_rows"
                            ]

                        if "scheme_name" in res.result:
                            celery_task_data["scheme_name"] = res.result["scheme_name"]

                        if "file_name" in res.result:
                            celery_task_data["file_name"] = res.result["file_name"]

                        celery_task.data = celery_task_data

                # print('TASK ITEMS LEN %s' % len(res.result.items))

            print("AsyncResult res.ready: %s" % (time.perf_counter() - st))

            if instance.master_user.id != request.user.master_user.id:
                raise PermissionDenied()

            print("TASK RESULT %s" % res.result)
            print("TASK STATUS %s" % res.status)

            instance.task_id = task_id
            instance.task_status = res.status

            if celery_task:
                celery_task.task_status = res.status
                celery_task.save()

            serializer = self.get_serializer(instance=instance, many=False)
            return Response(serializer.data, status=status.HTTP_200_OK)

        else:
            return Response(
                {"message": "Task not found"}, status=status.HTTP_400_BAD_REQUEST
            )

    def create(self, request, *args, **kwargs):
        from poms.integrations.tasks import (
            complex_transaction_csv_file_import_validate_parallel,
        )

        st = time.perf_counter()

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        # REFACTOR THIS

        options_object = {
            "file_name": instance.file_name,
            "file_path": instance.file_path,
            "scheme_id": instance.scheme.id,
            "execution_context": None,
        }
        celery_task = CeleryTask.objects.create(
            master_user=request.user.master_user,
            member=request.user.member,
            options_object=options_object,
            verbose_import="Transaction Import Validation",
            type="validate_transaction_import",
        )

        complex_transaction_csv_file_import_validate_parallel(task_id=celery_task.pk)

        _l.info(
            "ComplexTransactionCsvFileImportValidateViewSet done: %s",
            "{:3.3f}".format(time.perf_counter() - st),
        )

        return Response(
            {"task_id": celery_task.pk, "task_status": celery_task.status},
            status=status.HTTP_200_OK,
        )


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
        return Response({"status": "ok"})

    def post(self, request):
        from poms.integrations.tasks import complex_transaction_csv_file_import_parallel

        # _l.debug('request.data %s' % request.data)

        _l.debug("request.data %s" % request.data)

        procedure_id = request.data["procedure_id"]

        master_user = MasterUser.objects.get(token=request.data["user"]["token"])

        procedure_instance = RequestDataFileProcedureInstance.objects.get(
            id=procedure_id, master_user=master_user
        )

        celery_task = CeleryTask.objects.create(
            master_user=master_user,
            verbose_name="Transaction Import",
            type="transaction_import",
        )

        celery_task.options_object = {"reader": request.data["transactions"]}
        celery_task.save()

        complex_transaction_csv_file_import_parallel(task_id=celery_task.pk)


class DataProviderViewSet(AbstractReadOnlyModelViewSet):
    ordering_fields = ["name"]
    filter_fields = ["user_code", "name"]
    pagination_class = None
    queryset = DataProvider.objects
    serializer_class = DataProviderSerializer


class SupersetGetSecurityToken(APIView):
    def get_admin_access_token(self):
        data = {
            "username": "admin",
            "provider": "db",
            "refresh": True,
            "password": "lr1018hxvb10yq95ip",
        }

        headers = {"Accept": "application/json", "Content-Type": "application/json"}

        url = settings.SUPERSET_URL + "api/v1/security/login"
        response = requests.post(
            url=url, data=json.dumps(data), headers=headers, verify=settings.VERIFY_SSL
        )

        return response.json()

    def get_csrf_token(self, tokens):
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f'Bearer {tokens["access_token"]}',
        }

        url = settings.SUPERSET_URL + "api/v1/security/csrf_token/"
        response = requests.get(url=url, headers=headers, verify=settings.VERIFY_SSL)

        response_json = response.json()

        return response_json["result"]

    def get(self, request):
        id = request.query_params.get("id", None)

        tokens = self.get_admin_access_token()

        csrf_token = self.get_csrf_token(tokens)

        _l.info("SupersetGetSecurityToken.got tokens %s" % tokens)
        _l.info("SupersetGetSecurityToken.got csrf_token %s" % csrf_token)

        data = {
            "user": {
                "username": "finmars",
                "first_name": "finmars",
                "last_name": "finmars",
            },
            "resources": [{"type": "dashboard", "id": id}],
            "rls": [],
        }

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f'Bearer {tokens["access_token"]}',
            "X-CSRFToken": csrf_token,
        }

        url = settings.SUPERSET_URL + "api/v1/security/guest_token/"

        _l.info("SupersetGetSecurityToken.Requesting url %s" % url)

        response = requests.post(
            url=url, data=json.dumps(data), headers=headers, verify=settings.VERIFY_SSL
        )

        _l.info("SupersetGetSecurityToken.response %s" % response.text)

        response_json = response.json()

        return Response(response_json)
