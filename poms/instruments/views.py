import contextlib
import datetime
import logging

import django_filters
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db import connection, transaction
from django.db.models import Case, Prefetch, Q, Value, When
from django.utils import timezone
from django_filters.rest_framework import FilterSet
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.exceptions import (
    MethodNotAllowed,
    PermissionDenied,
    ValidationError,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.views import APIView

import requests

from poms.common.authentication import get_access_token
from poms.common.filters import (
    AttributeFilter,
    CharFilter,
    CharExactFilter,
    EntitySpecificFilter,
    GroupsAttributeFilter,
    ModelExtMultipleChoiceFilter,
    NoOpFilter,
)
from poms.common.jwt import encode_with_jwt
from poms.common.mixins import UpdateModelMixinExt
from poms.common.utils import date_now, get_list_of_entity_attributes
from poms.common.views import (
    AbstractClassModelViewSet,
    AbstractModelViewSet,
    AbstractReadOnlyModelViewSet,
)
from poms.csv_import.handlers import handler_instrument_object
from poms.currencies.models import Currency
from poms.explorer.serializers import FinmarsFileSerializer
from poms.instruments.filters import (
    GeneratedEventPermissionFilter,
    InstrumentsUserCodeFilter,
    ListDatesFilter,
    PriceHistoryObjectPermissionFilter,
    IdentifierKeysValuesFilter,
)
from poms.instruments.handlers import GeneratedEventProcess, InstrumentTypeProcess
from poms.instruments.models import (
    DATE_FORMAT,
    AccrualCalculationModel,
    AccrualCalculationSchedule,
    CostMethod,
    Country,
    DailyPricingModel,
    EventSchedule,
    EventScheduleConfig,
    ExposureCalculationModel,
    GeneratedEvent,
    Instrument,
    InstrumentClass,
    InstrumentType,
    LongUnderlyingExposure,
    ManualPricingFormula,
    PaymentSizeDetail,
    Periodicity,
    PriceHistory,
    PricingCondition,
    PricingPolicy,
    ShortUnderlyingExposure,
)
from poms.instruments.serializers import (
    AccrualCalculationModelSerializer,
    AttachmentSerializer,
    CostMethodSerializer,
    CountrySerializer,
    DailyPricingModelSerializer,
    DayTimeConventionSerializer,
    EventScheduleConfigSerializer,
    ExposureCalculationModelSerializer,
    GeneratedEventSerializer,
    InstrumentCalculatePricesAccruedPriceSerializer,
    InstrumentClassSerializer,
    InstrumentForSelectSerializer,
    InstrumentLightSerializer,
    InstrumentOnBalanceSerializer,
    InstrumentSerializer,
    InstrumentTypeApplySerializer,
    InstrumentTypeLightSerializer,
    InstrumentTypeProcessSerializer,
    InstrumentTypeSerializer,
    LongUnderlyingExposureSerializer,
    PaymentSizeDetailSerializer,
    PeriodicitySerializer,
    PriceHistorySerializer,
    PriceHistoryRecalculateSerializer,
    PricingConditionSerializer,
    PricingPolicyLightSerializer,
    PricingPolicySerializer,
    ShortUnderlyingExposureSerializer,
)
from poms.instruments.tasks import (
    calculate_prices_accrued_price,
    generate_events,
    generate_events_do_not_inform_apply_default,
    only_generate_events_at_date,
    only_generate_events_at_date_for_single_instrument,
    process_events,
)
from poms.obj_attrs.models import GenericAttributeType
from poms.obj_attrs.utils import get_attributes_prefetch
from poms.obj_attrs.views import GenericAttributeTypeViewSet, GenericClassifierViewSet
from poms.reports.sql_builders.helpers import dictfetchall
from poms.strategies.models import Strategy3
from poms.transactions.models import NotificationClass, Transaction
from poms.transactions.serializers import TransactionTypeProcessSerializer
from poms.users.filters import OwnerByMasterUserFilter
from poms.users.models import EcosystemDefault, MasterUser
from poms.users.permissions import SuperUserOrReadOnly
from poms_app import settings

_l = logging.getLogger("poms.instruments")


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


class PricingConditionViewSet(AbstractClassModelViewSet):
    queryset = PricingCondition.objects
    serializer_class = PricingConditionSerializer


class CountryViewSet(AbstractModelViewSet):
    queryset = Country.objects
    serializer_class = CountrySerializer
    ordering_fields = ["name"]
    filter_fields = ["name"]
    pagination_class = None


class ExposureCalculationModelViewSet(AbstractClassModelViewSet):
    queryset = ExposureCalculationModel.objects
    serializer_class = ExposureCalculationModelSerializer


class LongUnderlyingExposureViewSet(AbstractClassModelViewSet):
    queryset = LongUnderlyingExposure.objects
    serializer_class = LongUnderlyingExposureSerializer


class ShortUnderlyingExposureViewSet(AbstractClassModelViewSet):
    queryset = ShortUnderlyingExposure.objects
    serializer_class = ShortUnderlyingExposureSerializer


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
    short_name = CharFilter()

    class Meta:
        model = PricingPolicy
        fields = []


class PricingPolicyViewSet(AbstractModelViewSet):
    queryset = PricingPolicy.objects.select_related("owner", "master_user")
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
        "user_code",
        "name",
        "short_name",
        "public_name",
    ]
    filter_class = PricingPolicyFilterSet

    @action(
        detail=False,
        methods=["get"],
        url_path="light",
        serializer_class=PricingPolicyLightSerializer,
    )
    def list_light(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginator.post_paginate_queryset(queryset, request)
        serializer = self.get_serializer(page, many=True)

        return self.get_paginated_response(serializer.data)


class InstrumentTypeAttributeTypeViewSet(GenericAttributeTypeViewSet):
    target_model = InstrumentType
    target_model_serializer = InstrumentTypeSerializer

    permission_classes = GenericAttributeTypeViewSet.permission_classes + []


class InstrumentTypeFilterSet(FilterSet):
    id = NoOpFilter()
    is_deleted = django_filters.BooleanFilter()
    user_code = CharFilter()
    name = CharFilter()
    short_name = CharFilter()
    public_name = CharFilter()
    instrument_class = django_filters.ModelMultipleChoiceFilter(
        queryset=InstrumentClass.objects
    )

    class Meta:
        model = InstrumentType
        fields = []


class InstrumentTypeViewSet(AbstractModelViewSet):
    queryset = InstrumentType.objects.select_related(
        "master_user",
        "owner",
        "instrument_class",
        "one_off_event",
        # 'one_off_event__group',
        "regular_event",
        # 'regular_event__group',
        "factor_same",
        # 'factor_same__group',
        "factor_up",
        # 'factor_up__group',
        "factor_down",
        # 'factor_down__group',
    ).prefetch_related(get_attributes_prefetch())
    serializer_class = InstrumentTypeSerializer
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter,
        GroupsAttributeFilter,
        EntitySpecificFilter,
    ]
    filter_class = InstrumentTypeFilterSet
    ordering_fields = [
        "user_code",
        "name",
        "short_name",
        "public_name",
    ]

    @action(
        detail=False,
        methods=["get"],
        url_path="light",
        serializer_class=InstrumentTypeLightSerializer,
    )
    def list_light(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginator.post_paginate_queryset(queryset, request)
        serializer = self.get_serializer(page, many=True)

        return self.get_paginated_response(serializer.data)

    @action(
        detail=True,
        methods=["get", "put"],
        url_path="book",
        serializer_class=InstrumentTypeProcessSerializer,
    )
    def book(self, request, pk=None, realm_code=None, space_code=None):
        instrument_type = InstrumentType.objects.get(pk=pk)

        instance = InstrumentTypeProcess(
            instrument_type=instrument_type, context=self.get_serializer_context()
        )

        serializer = self.get_serializer(instance=instance)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="attributes")
    def list_attributes(self, request, *args, **kwargs):
        items = [
            {
                "key": "name",
                "name": "Name",
                "value_type": 10,
            },
            {
                "key": "short_name",
                "name": "Short name",
                "value_type": 10,
            },
            {
                "key": "user_code",
                "name": "User code",
                "value_type": 10,
            },
            {
                "key": "public_name",
                "name": "Public name",
                "value_type": 10,
            },
            {
                "key": "notes",
                "name": "Notes",
                "value_type": 10,
            },
            {
                "key": "is_active",
                "name": "Is active",
                "value_type": 50,
            },
            {
                "key": "instrument_class",
                "name": "Instrument class",
                "value_type": "field",
                "value_content_type": "instruments.instrumentclass",
                "value_entity": "instrument-class",
                "code": "user_code",
            },
            {
                "key": "one_off_event",
                "name": "One off event",
                "value_type": "field",
                "value_entity": "transaction-type",
                "value_content_type": "transactions.transactiontype",
                "code": "user_code",
            },
            {
                "key": "regular_event",
                "name": "Regular event",
                "value_type": "field",
                "value_entity": "transaction-type",
                "value_content_type": "transactions.transactiontype",
                "code": "user_code",
            },
            {
                "key": "factor_same",
                "name": "Factor same",
                "value_type": "field",
                "value_entity": "transaction-type",
                "value_content_type": "transactions.transactiontype",
                "code": "user_code",
            },
            {
                "key": "factor_up",
                "name": "Factor up",
                "value_type": "field",
                "value_entity": "transaction-type",
                "value_content_type": "transactions.transactiontype",
                "code": "user_code",
            },
            {
                "key": "factor_down",
                "name": "Factor down",
                "value_type": "field",
                "value_entity": "transaction-type",
                "value_content_type": "transactions.transactiontype",
                "code": "user_code",
            },
            {
                "key": "has_second_exposure_currency",
                "name": "Has second exposure currency",
                "value_type": 50,
            },
            {
                "key": "object_permissions",
                "name": "Object permissions",
                "value_type": "mc_field",
            },
            {
                "key": "underlying_long_multiplier",
                "name": "Underlying long multiplier",
                "value_type": 20,
            },
            {
                "key": "underlying_short_multiplier",
                "name": "Underlying short multiplier",
                "value_type": 20,
            },
            {
                "key": "co_directional_exposure_currency",
                "name": "Exposure Co-Directional Currency",
                "value_content_type": "currencies.currency",
                "value_entity": "currency",
                "code": "user_code",
                "value_type": "field",
            },
            {
                "key": "counter_directional_exposure_currency",
                "name": "Exposure Counter-Directional Currency",
                "value_content_type": "currencies.currency",
                "value_entity": "currency",
                "code": "user_code",
                "value_type": "field",
            },
            {
                "key": "long_underlying_exposure",
                "name": "Long Underlying Exposure",
                "value_content_type": "instruments.longunderlyingexposure",
                "value_entity": "long-underlying-exposure",
                "value_type": "field",
            },
            {
                "key": "short_underlying_exposure",
                "name": "Short Underlying Exposure",
                "value_content_type": "instruments.shortunderlyingexposure",
                "value_entity": "short-underlying-exposure",
                "value_type": "field",
            },
            {
                "key": "exposure_calculation_model",
                "name": "Exposure Calculation Model",
                "value_content_type": "instruments.exposurecalculationmodel",
                "value_entity": "exposure-calculation-model",
                "value_type": "field",
            },
            {
                "key": "long_underlying_instrument",
                "name": "Long Underlying Instrument",
                "value_content_type": "instruments.instrument",
                "value_entity": "instrument",
                "value_type": "field",
            },
            {
                "key": "short_underlying_instrument",
                "name": "Short Underlying Instrument",
                "value_content_type": "instruments.instrument",
                "value_entity": "instrument",
                "value_type": "field",
            },
            {
                "key": "accrued_currency",
                "name": "Accrued currency",
                "value_content_type": "currencies.currency",
                "value_entity": "currency",
                "code": "user_code",
                "value_type": "field",
            },
            {
                "key": "accrued_multiplier",
                "name": "Accrued multiplier",
                "value_type": 20,
            },
            {
                "key": "payment_size_detail",
                "name": "Payment size detail",
                "value_content_type": "instruments.paymentsizedetail",
                "value_entity": "payment-size-detail",
                "code": "user_code",
                "value_type": "field",
            },
            {
                "key": "default_accrued",
                "name": "Default accrued",
                "value_type": 20,
            },
            {
                "key": "default_price",
                "name": "Default price",
                "value_type": 20,
            },
            {
                "key": "maturity_date",
                "name": "Maturity date",
                "value_type": 40,
            },
            {
                "key": "maturity_price",
                "name": "Maturity price",
                "value_type": 20,
            },
        ]

        items += get_list_of_entity_attributes("instruments.instrumenttype")

        result = {
            "count": len(items),
            "next": None,
            "previous": None,
            "results": items,
        }

        return Response(result)

    @action(
        detail=True,
        methods=["put"],
        url_path="apply",
        permission_classes=[IsAuthenticated],
        serializer_class=InstrumentTypeApplySerializer,
    )
    def apply_type_to_instruments(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        instrument_type = self.get_object()
        instruments = Instrument.objects.filter(instrument_type=instrument_type)

        _l.info(
            f"instrument_type.apply request.data={request.data} "
            f"instruments affected={len(instruments)}"
        )

        if "pricing_policies" in serializer.data["fields_to_update"]:
            serializer.data["fields_to_update"].remove("pricing_policies")
            self._apply_pricing_to_instruments(
                instrument_type, instruments, serializer.data["mode"]
            )

        to_update = []
        for instrument in instruments:
            for field in serializer.data["fields_to_update"]:
                if (
                    serializer.data["mode"] == "fill"
                    and not getattr(instrument, field)
                    or serializer.data["mode"] == "overwrite"
                ):
                    setattr(instrument, field, getattr(instrument_type, field))
                    to_update.append(instrument)

        if serializer.data["fields_to_update"]:
            Instrument.objects.bulk_update(
                to_update,
                serializer.data["fields_to_update"],
            )

        return Response(
            {
                "status": "ok",
                "data": {"instruments_affected": len(instruments)},
            }
        )

    @staticmethod
    def _apply_pricing_to_instruments(instrument_type, instruments, fill_or_overwrite):
        from poms.instruments.models import InstrumentPricingPolicy

        pricing_policies = instrument_type.pricing_policies.all()
        pricing_policy_ids = [pp.pricing_policy_id for pp in pricing_policies]
        # Add missing pricing policies to each instrument
        instrument_pricing_policies = InstrumentPricingPolicy.objects.filter(
            instrument__in=instruments,
            pricing_policy_id__in=pricing_policy_ids,
        )
        existing_policies = {
            (ip.pricing_policy_id, ip.instrument_id): ip
            for ip in instrument_pricing_policies
        }

        to_create = []
        to_update = []
        for instrument in instruments:
            for instrument_type_pricing_policy in pricing_policies:
                key = (instrument_type_pricing_policy.pricing_policy_id, instrument.id)
                if key in existing_policies:
                    ip = existing_policies[key]

                    ip.target_pricing_schema_user_code = (
                        instrument_type_pricing_policy.target_pricing_schema_user_code
                    )
                    ip.options = instrument_type_pricing_policy.options

                    to_update.append(ip)
                else:
                    to_create.append(
                        InstrumentPricingPolicy(
                            pricing_policy=instrument_type_pricing_policy.pricing_policy,
                            instrument=instrument,
                            target_pricing_schema_user_code=instrument_type_pricing_policy.target_pricing_schema_user_code,
                            options=instrument_type_pricing_policy.options,
                        )
                    )

        if to_create:
            InstrumentPricingPolicy.objects.bulk_create(to_create)

        if fill_or_overwrite == "overwrite":
            InstrumentPricingPolicy.objects.bulk_update(
                to_update,
                ["target_pricing_schema_user_code", "options"],
            )
            # Remove instrument pricing policies that are no longer associated with the given instrument type
            to_delete = InstrumentPricingPolicy.objects.filter(
                instrument__in=instruments
            ).exclude(pricing_policy_id__in=pricing_policy_ids)
            to_delete.delete()

    @action(
        detail=True,
        methods=["get", "put"],
        url_path="update-pricing",
        permission_classes=[IsAuthenticated],
    )
    def update_pricing(self, request, pk=None, realm_code=None, space_code=None):
        instrument_type = self.get_object()
        instruments = Instrument.objects.filter(instrument_type=instrument_type)

        _l.info(
            f"update_pricing request.data={request.data} "
            f"instruments affected={len(instruments)}"
        )

        self._apply_pricing_to_instruments(instrument_type, instruments, "fill")

        return Response(
            {
                "status": "ok",
                "data": {"instruments_affected": len(instruments)},
            }
        )

    @action(detail=False, methods=["patch"], url_path="bulk-update")
    def bulk_update(self, request, realm_code=None, space_code=None):
        request_data = request.data
        if not isinstance(request_data, list):
            raise ValidationError("Required list of data")

        queryset = self.get_queryset()

        instance_serializers = []
        for instance_data in request_data:
            pk = instance_data.get("id")
            try:
                instance = queryset.get(pk=pk)

            except ObjectDoesNotExist:
                err_msg = {
                    api_settings.NON_FIELD_ERRORS_KEY: f"object with id={pk} not found"
                }
                raise ValidationError(err_msg)

            try:
                self.check_object_permissions(request, instance)
            except PermissionDenied:
                raise

            serializer = self.get_serializer(
                instance=instance,
                data=instance_data,
                partial=True,  # cause only patch method is used
            )
            if not serializer.is_valid(raise_exception=False):
                raise ValidationError(serializer.errors)

            instance_serializers.append(serializer)

        instances = []
        for serializer in instance_serializers:
            self.perform_update(serializer)
            instances.append(serializer.instance)

        ret_serializer = self.get_serializer(
            instance=queryset.filter(pk__in=(i.id for i in instances)),
            many=True,
        )
        return Response(list(ret_serializer.data), status=status.HTTP_200_OK)


class InstrumentAttributeTypeViewSet(GenericAttributeTypeViewSet):
    target_model = Instrument
    target_model_serializer = InstrumentSerializer

    permission_classes = GenericAttributeTypeViewSet.permission_classes + []


class InstrumentClassifierViewSet(GenericClassifierViewSet):
    target_model = Instrument


class InstrumentFilterSet(FilterSet):
    id = NoOpFilter()
    is_deleted = django_filters.BooleanFilter()
    user_code = CharFilter()
    user_code__exact = CharExactFilter(field_name="user_code")
    name = CharFilter()
    public_name = CharFilter()
    short_name = CharFilter()
    identifier = IdentifierKeysValuesFilter()
    instrument_type__instrument_class = django_filters.ModelMultipleChoiceFilter(
        queryset=InstrumentClass.objects
    )
    pricing_currency = ModelExtMultipleChoiceFilter(model=Currency)
    price_multiplier = django_filters.RangeFilter()
    accrued_currency = ModelExtMultipleChoiceFilter(model=Currency)
    accrued_multiplier = django_filters.RangeFilter()
    payment_size_detail = django_filters.ModelMultipleChoiceFilter(
        queryset=PaymentSizeDetail.objects
    )
    default_price = django_filters.RangeFilter()
    default_accrued = django_filters.RangeFilter()
    user_text_1 = CharFilter()
    user_text_2 = CharFilter()
    user_text_3 = CharFilter()
    reference_for_pricing = CharFilter()
    daily_pricing_model = django_filters.ModelMultipleChoiceFilter(
        queryset=DailyPricingModel.objects
    )
    maturity_date = django_filters.DateFromToRangeFilter()

    class Meta:
        model = Instrument
        fields = []


class InstrumentViewSet(AbstractModelViewSet):
    queryset = Instrument.objects.select_related(
        "instrument_type",
        "instrument_type__instrument_class",
        "pricing_currency",
        "accrued_currency",
        "payment_size_detail",
        "daily_pricing_model",
    ).prefetch_related(
        Prefetch(
            "manual_pricing_formulas",
            queryset=ManualPricingFormula.objects.select_related("pricing_policy"),
        ),
        Prefetch(
            "accrual_calculation_schedules",
            queryset=AccrualCalculationSchedule.objects.select_related(
                "accrual_calculation_model", "periodicity"
            ),
        ),
        "factor_schedules",
        Prefetch(
            "event_schedules",
            queryset=EventSchedule.objects.select_related(
                "event_class", "notification_class", "periodicity"
            ).prefetch_related(
                Prefetch("actions"),
            ),
        ),
        get_attributes_prefetch(),
    )
    serializer_class = InstrumentSerializer
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter,
        GroupsAttributeFilter,
        EntitySpecificFilter,
    ]
    filter_class = InstrumentFilterSet
    ordering_fields = [
        "user_code",
        "name",
        "short_name",
        "public_name",
        "reference_for_pricing",
        "instrument_type",
        "instrument_type__user_code",
        "instrument_type__name",
        "instrument_type__short_name",
        "instrument_type__public_name",
        "identifier",
        "pricing_currency",
        "pricing_currency__user_code",
        "pricing_currency__name",
        "pricing_currency__short_name",
        "pricing_currency__public_name",
        "price_multiplier",
        "accrued_currency",
        "accrued_currency__user_code",
        "accrued_currency__name",
        "accrued_currency__short_name",
        "accrued_currency__public_name",
        "accrued_multiplier",
        "default_price",
        "default_accrued",
        "user_text_1",
        "user_text_2",
        "user_text_3",
        "reference_for_pricing",
        "maturity_date",
    ]

    @action(
        detail=False,
        methods=["get"],
        url_path="light",
        serializer_class=InstrumentLightSerializer,
    )
    def list_light(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginator.post_paginate_queryset(queryset, request)
        serializer = self.get_serializer(page, many=True)

        return self.get_paginated_response(serializer.data)

    @action(detail=False, methods=["get"], url_path="attributes")
    def list_attributes(self, request, *args, **kwargs):
        items = [
            {"key": "name", "name": "Name", "value_type": 10},
            {"key": "short_name", "name": "Short name", "value_type": 10},
            {"key": "user_code", "name": "User code", "value_type": 10},
            {"key": "public_name", "name": "Public name", "value_type": 10},
            {"key": "notes", "name": "Notes", "value_type": 10},
            {
                "key": "instrument_type",
                "name": "Instrument type",
                "value_type": "field",
                "value_content_type": "instruments.instrumenttype",
                "value_entity": "instrument-type",
                "code": "user_code",
            },
            {"key": "is_active", "name": "Is active", "value_type": 50},
            {
                "key": "has_linked_with_portfolio",
                "name": "Has linked with portfolio",
                "value_type": 50,
            },
            {
                "key": "reference_for_pricing",
                "name": "Reference for pricing",
                "value_type": 10,
            },
            {
                "key": "pricing_currency",
                "name": "Pricing currency",
                "value_content_type": "currencies.currency",
                "value_entity": "currency",
                "code": "user_code",
                "value_type": "field",
            },
            {"key": "price_multiplier", "name": "Price multiplier", "value_type": 20},
            {
                "key": "position_reporting",
                "name": "Position reporting",
                "value_content_type": "instruments.positionreporting",
                "value_entity": "position-reporting",
                "value_type": "field",
            },
            {
                "key": "accrued_currency",
                "name": "Accrued currency",
                "value_content_type": "currencies.currency",
                "value_entity": "currency",
                "code": "user_code",
                "value_type": "field",
            },
            {"key": "maturity_date", "name": "Maturity date", "value_type": 40},
            {"key": "maturity_price", "name": "Maturity price", "value_type": 20},
            {
                "key": "accrued_multiplier",
                "name": "Accrued multiplier",
                "value_type": 20,
            },
            {
                "key": "pricing_condition",
                "name": "Pricing Condition",
                "value_content_type": "instruments.pricingcondition",
                "value_entity": "pricing-condition",
                "code": "user_code",
                "value_type": "field",
            },
            {
                "key": "payment_size_detail",
                "name": "Accrual Size Clarification",
                "value_content_type": "instruments.paymentsizedetail",
                "value_entity": "payment-size-detail",
                "code": "user_code",
                "value_type": "field",
            },
            {"key": "default_price", "name": "Default price", "value_type": 20},
            {"key": "default_accrued", "name": "Default accrued", "value_type": 20},
            {"key": "user_text_1", "name": "User text 1", "value_type": 10},
            {"key": "user_text_2", "name": "User text 2", "value_type": 10},
            {"key": "user_text_3", "name": "User text 3", "value_type": 10},
            {
                "key": "object_permissions",
                "name": "Object permissions",
                "value_type": "mc_field",
            },
            {
                "key": "underlying_long_multiplier",
                "name": "Underlying long multiplier",
                "value_type": 20,
            },
            {
                "key": "underlying_short_multiplier",
                "name": "Underlying short multiplier",
                "value_type": 20,
            },
            {
                "key": "co_directional_exposure_currency",
                "name": "Exposure Co-Directional Currency",
                "value_content_type": "currencies.currency",
                "value_entity": "currency",
                "code": "user_code",
                "value_type": "field",
            },
            {
                "key": "counter_directional_exposure_currency",
                "name": "Exposure Counter-Directional Currency",
                "value_content_type": "currencies.currency",
                "value_entity": "currency",
                "code": "user_code",
                "value_type": "field",
            },
            {
                "key": "long_underlying_exposure",
                "name": "Long Underlying Exposure",
                "value_content_type": "instruments.longunderlyingexposure",
                "value_entity": "long-underlying-exposure",
                "value_type": "field",
            },
            {
                "key": "short_underlying_exposure",
                "name": "Short Underlying Exposure",
                "value_content_type": "instruments.shortunderlyingexposure",
                "value_entity": "short-underlying-exposure",
                "value_type": "field",
            },
            {
                "key": "exposure_calculation_model",
                "name": "Exposure Calculation Model",
                "value_content_type": "instruments.exposurecalculationmodel",
                "value_entity": "exposure-calculation-model",
                "value_type": "field",
            },
            {
                "key": "long_underlying_instrument",
                "name": "Long Underlying Instrument",
                "value_content_type": "instruments.instrument",
                "value_entity": "instrument",
                "value_type": "field",
            },
            {
                "key": "short_underlying_instrument",
                "name": "Short Underlying Instrument",
                "value_content_type": "instruments.instrument",
                "value_entity": "instrument",
                "value_type": "field",
            },
            {
                "key": "country",
                "name": "Country",
                "value_content_type": "instruments.country",
                "value_entity": "country",
                "code": "user_code",
                "value_type": "field",
            },
        ]

        items += get_list_of_entity_attributes("instruments.instrument")

        result = {"count": len(items), "next": None, "previous": None, "results": items}

        return Response(result)

    @action(
        detail=False,
        methods=["post"],
        url_path="is-on-balance",
        serializer_class=InstrumentOnBalanceSerializer,
    )
    def is_on_balance(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        balance_date = serializer.validated_data["date"]
        user_codes = serializer.validated_data["user_codes"]

        queryset = self.filter_queryset(self.get_queryset())
        instruments = queryset.filter(user_code__in=user_codes)
        instrument_ids = [instrument.id for instrument in instruments]

        query = f"""
            SELECT instrument_id, SUM(position_size) as position_size
            FROM (
                SELECT account_position_id, portfolio_id, instrument_id, 
                        SUM(position_size_with_sign) as position_size
                FROM {Transaction._meta.db_table}
                WHERE transaction_date <= %s AND instrument_id = ANY(%s)
                GROUP BY account_position_id, portfolio_id, instrument_id
                HAVING SUM(position_size_with_sign) <> 0
            ) as t
            GROUP BY instrument_id
        """
        with connection.cursor() as cursor:
            cursor.execute(query, [balance_date, instrument_ids])
            transactions = dictfetchall(cursor)
        transactions = {t["instrument_id"]: t["position_size"] for t in transactions}

        items = [
            {
                "id": instrument.id,
                "user_code": instrument.user_code,
                "name": instrument.name,
                "position_size": transactions.get(instrument.id, 0),
                "is_on_balance": bool(transactions.get(instrument.id)),
            }
            for instrument in instruments
        ]

        result = {"date": balance_date, "instruments": items}

        return Response(result)

    @action(
        detail=False,
        methods=["post"],
        url_path="rebuild-events",
        serializer_class=serializers.Serializer,
    )
    def rebuild_all_events(self, request, realm_code=None, space_code=None):
        queryset = self.filter_queryset(self.get_queryset())
        processed = 0
        for instance in queryset:
            with contextlib.suppress(ValueError):
                instance.rebuild_event_schedules()

            processed += 1
        return Response({"processed": processed})

    @action(
        detail=True,
        methods=["put", "patch"],
        url_path="rebuild-events",
        serializer_class=serializers.Serializer,
    )
    def rebuild_events(self, request, pk, realm_code=None, space_code=None):
        instance = self.get_object()
        with contextlib.suppress(ValueError):
            instance.rebuild_event_schedules()

        return Response({"processed": 1})

    @action(
        detail=False,
        methods=["post"],
        url_path="generate-events",
        serializer_class=serializers.Serializer,
    )
    def generate_events(self, request, realm_code=None, space_code=None):
        from poms.celery_tasks.models import CeleryTask

        celery_task = CeleryTask.objects.create(
            master_user=request.user.master_user,
            member=request.user.member,
            verbose_name="Generate Events",
            type="generate_events",
        )

        ret = generate_events.apply_async(
            kwargs={
                "task_id": celery_task.id,
                "context": {
                    "space_code": celery_task.master_user.space_code,
                    "realm_code": celery_task.master_user.realm_code,
                },
            }
        )
        return Response(
            {
                "success": True,
                "task_id": ret.id,
            }
        )

    @action(
        detail=False,
        methods=["post"],
        url_path="system-generate-and-process",
        serializer_class=serializers.Serializer,
    )
    def system_generate_and_process(self, request, realm_code=None, space_code=None):
        ret = generate_events_do_not_inform_apply_default.apply_async()
        return Response(
            {
                "success": True,
                "task_id": ret.id,
            }
        )

    @action(
        detail=False,
        methods=["post"],
        url_path="generate-events-range",
        serializer_class=serializers.Serializer,
    )
    def generate_events_range(self, request, realm_code=None, space_code=None):
        date_from_string = request.data.get("effective_date_0", None)
        date_to_string = request.data.get("effective_date_1", None)

        if date_from_string is None or date_to_string is None:
            raise ValidationError("Date range is incorrect")

        date_from = datetime.datetime.strptime(date_from_string, DATE_FORMAT).date()
        date_to = datetime.datetime.strptime(date_to_string, DATE_FORMAT).date()

        dates = [
            date_from + datetime.timedelta(days=i)
            for i in range((date_to - date_from).days + 1)
        ]

        tasks_ids = []

        for dte in dates:
            res = only_generate_events_at_date.apply_async(
                kwargs={
                    "master_user_id": request.user.master_user.id,
                    "date": dte,
                    "context": {
                        "space_code": request.space_code,
                        "realm_code": request.realm_code,
                    },
                }
            )
            tasks_ids.append(res.id)

        return Response({"success": True, "tasks_ids": tasks_ids})

    @action(
        detail=False,
        methods=["post"],
        url_path="generate-events-range-for-single-instrument",
        serializer_class=serializers.Serializer,
    )
    def generate_events_range_for_single_instrument(self, request, *args, **kwargs):
        print(f"request.data {request.data} ")

        date_from_string = request.data.get("effective_date_0", None)
        date_to_string = request.data.get("effective_date_1", None)

        if date_from_string is None or date_to_string is None:
            raise ValidationError("Date range is incorrect")

        instrument_id = request.data.get("instrument", None)

        if instrument_id is None:
            raise ValidationError("Instrument is not set")

        date_from = datetime.datetime.strptime(date_from_string, DATE_FORMAT).date()
        date_to = datetime.datetime.strptime(date_to_string, DATE_FORMAT).date()

        try:
            instrument = Instrument.objects.get(
                master_user=request.user.master_user, id=instrument_id
            )

        except Instrument.DoesNotExist as e:
            raise ValidationError("Instrument is not found") from e

        dates = [
            date_from + datetime.timedelta(days=i)
            for i in range((date_to - date_from).days + 1)
        ]
        tasks_ids = []
        for dte in dates:
            res = only_generate_events_at_date_for_single_instrument.apply_async(
                kwargs={
                    "master_user_id": request.user.master_user.id,
                    "date": str(dte),
                    "instrument_id": instrument.id,
                    "context": {
                        "space_code": request.space_code,
                        "realm_code": request.realm_code,
                    },
                }
            )
            tasks_ids.append(res.id)

        return Response({"success": True, "tasks_ids": tasks_ids})

    @action(
        detail=False,
        methods=["post"],
        url_path="process-events",
        serializer_class=serializers.Serializer,
    )
    def process_events(self, request, *args, **kwargs):
        ret = process_events.apply_async(
            kwargs={
                "master_users": [request.user.master_user.pk],
                "context": {
                    "space_code": request.space_code,
                    "realm_code": request.realm_code,
                },
            }
        )
        return Response(
            {
                "success": True,
                "task_id": ret.id,
            }
        )

    @action(
        detail=False,
        methods=["post"],
        url_path="recalculate-prices-accrued-price",
        serializer_class=InstrumentCalculatePricesAccruedPriceSerializer,
    )
    def calculate_prices_accrued_price(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        begin_date = serializer.validated_data["begin_date"]
        end_date = serializer.validated_data["end_date"]

        calculate_prices_accrued_price(
            master_user=request.user.master_user,
            begin_date=begin_date,
            end_date=end_date,
        )

        return Response(serializer.data)

    @swagger_auto_schema(
        request_body=AttachmentSerializer,
        responses={
            status.HTTP_200_OK: FinmarsFileSerializer(many=True),
        },
    )
    @action(
        detail=True,
        methods=["patch"],
        url_path="attach-file",
        serializer_class=AttachmentSerializer,
    )
    def attach_file(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = AttachmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.update(instance)
        response_json = FinmarsFileSerializer(instance=instance.files, many=True).data
        return Response(response_json, status=status.HTTP_200_OK)


# Not for getting List
class InstrumentExternalAPIViewSet(APIView):
    permission_classes = []

    def post(self, request, *args, **kwargs):
        token = request.data["token"]

        master_user = MasterUser.objects.get(token=token)

        context = {"request": request, "master_user": master_user}

        ecosystem_defaults = EcosystemDefault.objects.get(master_user=master_user)
        content_type = ContentType.objects.get(
            model="instrument", app_label="instruments"
        )

        _l.info(f"request.data {request.data}")

        instrument_data = {}

        for key, value in request.data["data"].items():
            if key == "attributes":
                for attr_key, attr_value in request.data["data"]["attributes"].items():
                    instrument_data[attr_key] = attr_value

            else:
                instrument_data[key] = value

        attribute_types = GenericAttributeType.objects.filter(
            master_user=master_user, content_type=content_type
        )

        try:
            instrument_type = InstrumentType.objects.get(
                master_user=master_user,
                user_code=instrument_data["instrument_type"],
            )

        except InstrumentType.DoesNotExist as e:
            err_msg = (
                f"Unknown InstrumentType.user_code={instrument_data['instrument_type']}"
            )
            _l.error(err_msg)
            raise ValidationError(err_msg) from e

        object_data = handler_instrument_object(
            instrument_data,
            instrument_type,
            master_user,
            ecosystem_defaults,
            attribute_types,
        )

        serializer = InstrumentSerializer(data=object_data, context=context)

        is_valid = serializer.is_valid()

        if is_valid:
            serializer.save()
        else:
            err_msg = (
                f"InstrumentExternalAPIViewSet serializer.errors={serializer.errors}"
            )
            _l.error(err_msg)
            raise ValidationError(err_msg)

        _l.info(f"Instrument created with request.data={request.data}")

        return Response({"ok"})


# DEPRECATED
class InstrumentFDBCreateFromCallbackViewSet(APIView):
    permission_classes = []

    def get(self, request, *args, **kwargs):
        _l.info("InstrumentFDBCreateFromCallbackViewSet get")

        return Response({"ok"})

    def post(self, request, *args, **kwargs):
        from poms.celery_tasks.models import CeleryTask
        from poms.integrations.tasks import (
            create_currency_from_callback_data,
            create_instrument_cbond,
        )

        try:
            _l.info(
                f"InstrumentFDBCreateFromCallbackViewSet.data {request.data} "
                f"request_id {request.data['request_id']}"
            )

            task = CeleryTask.objects.get(id=request.data["request_id"])

            data = request.data

            if "instruments" in data:
                if "currencies" in data:
                    for item in data["currencies"]:
                        if item:
                            create_currency_from_callback_data(
                                item, task.master_user, task.member
                            )

                for item in data["instruments"]:
                    create_instrument_cbond(item, task.master_user, task.member)

            elif "items" in data["data"]:
                for item in data["data"]["items"]:
                    create_instrument_cbond(item, task.master_user, task.member)

            _l.info("Instrument(s) created")

            return Response({"status": "ok"})

        except Exception as e:
            _l.info(f"InstrumentFDBCreateFromCallbackViewSet error {repr(e)}")

            return Response({"status": "error"})


class CustomInstrumentTypeFilter(django_filters.Filter):
    field_class = django_filters.CharFilter

    def filter(self, qs, value):
        if value:
            qs = qs.filter(instrument_type__user_code__endswith=value)
        return qs


class InstrumentForSelectFilterSet(FilterSet):
    id = NoOpFilter()
    is_deleted = django_filters.BooleanFilter()
    user_code = CharFilter()
    name = CharFilter()
    public_name = CharFilter()
    short_name = CharFilter()
    query = CharFilter(method="filter_query")
    instrument_type = CharFilter(method="filter_instrument_type")

    class Meta:
        model = Instrument
        fields = [
            "id",
            "is_deleted",
            "user_code",
            "name",
            "public_name",
            "short_name",
        ]

    @staticmethod
    def filter_instrument_type(queryset, _, value):
        return (
            queryset.filter(instrument_type__user_code__endswith=value)
            if value
            else queryset
        )

    @staticmethod
    def filter_query(queryset, _, value):
        if value:
            # Split the value by spaces to get individual search terms
            search_terms = value.split()

            # Create an OR condition to search across multiple fields
            conditions = Q()
            for term in search_terms:
                conditions |= (
                    Q(name__icontains=term)
                    | Q(short_name__icontains=term)
                    | Q(user_code__icontains=term)
                )
            queryset = queryset.filter(conditions)

        return queryset


class InstrumentForSelectViewSet(AbstractModelViewSet):
    http_method_names = ["get"]
    queryset = Instrument.objects.select_related(
        "master_user",
        "owner",
        "instrument_type",
        "instrument_type__instrument_class",
    )
    serializer_class = InstrumentForSelectSerializer
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    filter_class = InstrumentForSelectFilterSet
    ordering_fields = [
        "user_code",
        "name",
        "short_name",
        "public_name",
    ]


class InstrumentDatabaseSearchViewSet(APIView):
    permission_classes = []

    def get(self, request, *args, **kwargs):
        if settings.CBONDS_BROKER_URL:
            headers = {"Content-type": "application/json"}

            payload_jwt = {
                "sub": request.space_code,  # "user_id_or_name",
                "role": 0,  # 0 -- ordinary user, 1 -- admin (access to /loadfi and /loadeq)
            }

            token = encode_with_jwt(payload_jwt)

            name = request.query_params.get("name", "")
            instrument_type = request.query_params.get("instrument_type", "")
            page = request.query_params.get("page", 1)

            headers["Authorization"] = f"Bearer {token}"

            _l.info(f"headers {headers}")

            url = str(settings.CBONDS_BROKER_URL) + "instr/find/name/%s?page=%s" % (
                name,
                page,
            )

            if instrument_type:
                url = f"{url}&instrument_type={str(instrument_type)}"

            _l.info(f"Requesting URL {url}")

            response = None

            try:
                response = requests.get(
                    url=url, headers=headers, verify=settings.VERIFY_SSL
                )
            except Exception as e:
                _l.info(f"Request error {repr(e)}")

            try:
                result = response.json()

            except Exception as e:
                if response:
                    _l.info(f"Response error {repr(e)} text={response.text}")
                result = {}

        else:
            size = request.query_params.get("size", 40)

            if settings.FINMARS_DATABASE_URL:
                headers = {
                    "Accept": "application/json",
                    "Content-type": "application/json",
                }

                name = request.query_params.get("name", "")
                size = request.query_params.get("size", 40)
                page = request.query_params.get("page", 1)

                page = int(page)

                if page == 0:
                    page = 1

                instruments_url = (
                    settings.FINMARS_DATABASE_URL
                    + "api/v1/instrument-narrow/?page="
                    + str(page)
                    + "&page_size="
                    + str(size)
                    + "&query="
                    + name
                )

                headers["Authorization"] = f"Bearer {get_access_token(request)}"

                _l.info(
                    f"InstrumentDatabaseSearchViewSet.requesting url {instruments_url}"
                )

                response = requests.get(
                    url=instruments_url, headers=headers, verify=settings.VERIFY_SSL
                )

                response_json = response.json()

                _l.info("response_json %s" % response_json)

                mappedItems = []

                for item in response_json["results"]:
                    mappedItem = {
                        "instrumentType": item["instrument_type"],
                        "issueName": item["name"],
                        "referenceId": item["isin"],
                        "commonCode": "",
                        "figi": "",
                        "issuerName": "",
                        "wkn": "",
                    }

                    mappedItems.append(mappedItem)

                result = {
                    "foundItems": mappedItems,
                    "pageNum": int(page),
                    "pageSize": int(size),
                    "resultCount": response_json["count"],
                }
            else:
                result = {
                    "foundItems": [],
                    "pageNum": 1,
                    "pageSize": int(size),
                    "resultCount": 0,
                }

        return Response(result)


class PriceHistoryFilterSet(FilterSet):
    id = NoOpFilter()
    instrument = ModelExtMultipleChoiceFilter(model=Instrument, field_name="id")
    pricing_policy = CharFilter(
        field_name="pricing_policy__user_code", lookup_expr="icontains"
    )
    date = django_filters.DateFromToRangeFilter()
    principal_price = django_filters.RangeFilter()
    accrued_price = django_filters.RangeFilter()

    class Meta:
        model = PriceHistory
        fields = []


class PriceHistoryViewSet(AbstractModelViewSet):
    queryset = PriceHistory.objects.select_related(
        "instrument",
        "instrument__instrument_type",
        "instrument__instrument_type__instrument_class",
        "pricing_policy",
    )
    serializer_class = PriceHistorySerializer
    filter_backends = AbstractModelViewSet.filter_backends + [
        ListDatesFilter,
        InstrumentsUserCodeFilter,
        PriceHistoryObjectPermissionFilter,
        AttributeFilter,
        GroupsAttributeFilter,
    ]
    filter_class = PriceHistoryFilterSet
    ordering_fields = [
        "instrument",
        "instrument__user_code",
        "instrument__name",
        "instrument__short_name",
        "instrument__public_name",
        "pricing_policy",
        "pricing_policy__user_code",
        "pricing_policy__name",
        "pricing_policy__short_name",
        "pricing_policy__public_name",
        "date",
        "principal_price",
        "accrued_price",
    ]

    @action(
        detail=False,
        methods=["post"],
        url_path="bulk-create",
        serializer_class=PriceHistorySerializer,
    )
    def bulk_create(self, request, *args, **kwargs):
        valid_data = []
        errors = []

        for item in request.data:
            serializer = self.get_serializer(data=item)
            if serializer.is_valid():
                valid_data.append(PriceHistory(**serializer.validated_data))
            else:
                errors.append(serializer.errors)

        _l.info(f"PriceHistoryViewSet.valid_data {len(valid_data)}")

        PriceHistory.objects.bulk_create(
            valid_data,
            update_conflicts=True,
            unique_fields=["instrument", "pricing_policy", "date"],
            update_fields=["principal_price", "accrued_price"],
        )

        if errors:
            _l.info(f"PriceHistoryViewSet.bulk_create.errors {errors}")
            # Here we just return the errors as part of the response.
            # You may want to log them or handle them differently
            # return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

        return Response(status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], url_path="attributes")
    def list_attributes(self, request, *args, **kwargs):
        items = [
            {
                "key": "instrument",
                "name": "Instrument",
                "value_content_type": "instruments.instrument",
                "value_entity": "instrument",
                "code": "user_code",
                "value_type": "field",
            },
            {
                "key": "date",
                "name": "Date",
                "value_type": 40,
            },
            {
                "key": "pricing_policy",
                "name": "Pricing policy",
                "value_content_type": "instruments.pricingpolicy",
                "value_entity": "pricing_policy",
                "code": "user_code",
                "value_type": "field",
            },
            {
                "key": "principal_price",
                "name": "Principal price",
                "value_type": 20,
            },
            {
                "key": "accrued_price",
                "name": "Accrued price",
                "value_type": 20,
            },
            {
                "key": "long_delta",
                "name": "Long delta",
                "value_type": 20,
            },
            {
                "key": "short_delta",
                "name": "Short delta",
                "value_type": 20,
            },
            {
                "key": "nav",
                "name": "NAV",
                "value_type": 20,
            },
            {
                "key": "cash_flow",
                "name": "Cash Flow",
                "value_type": 20,
            },
            {
                "key": "factor",
                "name": "Factor",
                "value_type": 20,
            },
            {
                "key": "procedure_modified_datetime",
                "name": "Modified Date And Time",
                "value_type": 80,
            },
            {
                "key": "is_temporary_price",
                "name": "Is Temporary Price",
                "value_type": 50,
            },
        ]

        result = {
            "count": len(items),
            "next": None,
            "previous": None,
            "results": items,
        }

        return Response(result)

    @action(
        detail=False,
        methods=["put"],
        url_path="recalculate",
        permission_classes=[IsAuthenticated],
        serializer_class=PriceHistoryRecalculateSerializer,
    )
    def recalculate(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        recalculate_inputs = serializer.validated_data.pop("recalculate_inputs")
        instance = PriceHistory(**serializer.validated_data)
        instance.run_auto_calculation(recalculate_inputs)

        serializer = self.get_serializer(instance=instance)

        return Response(serializer.data)


class GeneratedEventFilterSet(FilterSet):
    id = NoOpFilter()
    is_need_reaction = django_filters.BooleanFilter()
    status = django_filters.MultipleChoiceFilter(choices=GeneratedEvent.STATUS_CHOICES)
    status_date = django_filters.DateFromToRangeFilter()
    member = ModelExtMultipleChoiceFilter(model=Strategy3)

    effective_date = django_filters.DateFromToRangeFilter()
    notification_date = django_filters.DateFromToRangeFilter()

    class Meta:
        model = GeneratedEvent
        fields = []


class GeneratedEventViewSet(UpdateModelMixinExt, AbstractReadOnlyModelViewSet):
    queryset = GeneratedEvent.objects.select_related(
        "master_user",
        "event_schedule",
        "event_schedule__event_class",
        "event_schedule__notification_class",
        "event_schedule__periodicity",
        "instrument",
        "instrument__instrument_type",
        "instrument__instrument_type__instrument_class",
        "portfolio",
        "account",
        "strategy1",
        "strategy1__subgroup",
        "strategy1__subgroup__group",
        "strategy2",
        "strategy2__subgroup",
        "strategy2__subgroup__group",
        "strategy3",
        "strategy3__subgroup",
        "strategy3__subgroup__group",
        "action",
        "transaction_type",
        # 'transaction_type__group',
        "member",
    )
    serializer_class = GeneratedEventSerializer
    filter_backends = AbstractModelViewSet.filter_backends + [
        GeneratedEventPermissionFilter,
    ]
    filter_class = GeneratedEventFilterSet
    ordering_fields = [
        "status",
        "status_date",
        "effective_date",
        "notification_date",
        "instrument",
        "instrument__user_code",
        "instrument__name",
        "instrument__short_name",
        "instrument__public_name",
        "portfolio",
        "portfolio__user_code",
        "portfolio__name",
        "portfolio__short_name",
        "portfolio__public_name",
        "account",
        "account__user_code",
        "account__name",
        "account__short_name",
        "account__public_name",
        "date",
        "principal_price",
        "accrued_price",
        "strategy1",
        "strategy1__user_code",
        "strategy1__name",
        "strategy1__short_name",
        "strategy1__public_name",
        "strategy2",
        "strategy2__user_code",
        "strategy2__name",
        "strategy2__short_name",
        "strategy2__public_name",
        "strategy3",
        "strategy3__user_code",
        "strategy3__name",
        "strategy3__short_name",
        "strategy3__public_name",
        "member",
    ]

    def get_queryset(self):
        qs = super(GeneratedEventViewSet, self).get_queryset()
        now = date_now()
        qs = qs.annotate(
            is_need_reaction=Case(
                When(
                    Q(status=GeneratedEvent.NEW, action__isnull=True)
                    & (
                        Q(
                            notification_date__lte=now,
                            event_schedule__notification_class__in=NotificationClass.get_need_reaction_on_notification_date_classes(),
                        )
                        | Q(
                            effective_date__lte=now,
                            event_schedule__notification_class__in=NotificationClass.get_need_reaction_on_effective_date_classes(),
                        )
                    ),
                    then=Value(True),
                ),
                default=Value(False),
                # output_field=BooleanField(),
            )
        )
        return qs

    @action(
        detail=True,
        methods=["get", "put"],
        url_path="book",
        serializer_class=TransactionTypeProcessSerializer,
    )
    def process(self, request, pk=None):
        generated_event = self.get_object()

        action_pk = request.query_params.get("action", None)

        action = None
        if action_pk:
            with contextlib.suppress(ObjectDoesNotExist):
                action = generated_event.event_schedule.actions.get(pk=action_pk)

        if action is None:
            raise ValidationError('Require "action" query parameter')

        instance = GeneratedEventProcess(
            generated_event=generated_event,
            action=action,
            context=self.get_serializer_context(),
        )

        if request.method == "GET":
            serializer = self.get_serializer(instance=instance)
            return Response(serializer.data)
        else:
            try:
                status = request.query_params.get("event_status", None)

                if status is None:
                    raise ValidationError('Require "event_status" query parameter')

                serializer = self.get_serializer(instance=instance, data=request.data)

                serializer.is_valid(raise_exception=True)
                serializer.save()

                print(
                    f"generated_event.id {generated_event.id} status {status} "
                    f"instance.has_errors {instance.has_errors}"
                )

                if not instance.has_errors:
                    generated_event.processed(
                        self.request.user.member,
                        action,
                        instance.complex_transaction,
                        status,
                    )
                else:
                    generated_event.status = GeneratedEvent.ERROR
                    generated_event.status_date = timezone.now()
                    generated_event.member = self.request.user.member

                    instance = GeneratedEventProcess(
                        generated_event=generated_event,
                        action=action,
                        context=self.get_serializer_context(),
                    )

                    instance.process_as_pending()

                    generated_event.processed(
                        self.request.user.member,
                        action,
                        instance.complex_transaction,
                        GeneratedEvent.ERROR,
                    )

                generated_event.save()

                return Response(serializer.data)
            finally:
                if instance.has_errors:
                    transaction.set_rollback(True)

    @action(
        detail=True,
        methods=["put"],
        url_path="informed",
        serializer_class=GeneratedEventSerializer,
    )
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

    @action(detail=True, methods=["put"], url_path="error")
    def error(self, request, pk=None):
        generated_event = self.get_object()

        if generated_event.status != GeneratedEvent.NEW:
            raise PermissionDenied()

        action_pk = request.query_params.get("action", None)

        action = None
        if action_pk:
            with contextlib.suppress(ObjectDoesNotExist):
                action = generated_event.event_schedule.actions.get(pk=action_pk)

        if action is None:
            raise ValidationError('Require "action" query parameter')

        generated_event.status = GeneratedEvent.ERROR
        generated_event.status_date = timezone.now()
        generated_event.member = self.request.user.member

        instance = GeneratedEventProcess(
            generated_event=generated_event,
            action=action,
            context=self.get_serializer_context(),
        )

        instance.process_as_pending()

        generated_event.processed(
            self.request.user.member,
            action,
            instance.complex_transaction,
            GeneratedEvent.ERROR,
        )

        generated_event.save()

        serializer = self.get_serializer(instance=generated_event)
        return Response(serializer.data)


class EventScheduleConfigViewSet(AbstractModelViewSet):
    queryset = EventScheduleConfig.objects.select_related("notification_class")
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
            return EventScheduleConfig.create_default(
                master_user=self.request.user.master_user
            )

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed(method=request.method)


class DayTimeConventionViewSet(AbstractModelViewSet):
    queryset = AccrualCalculationModel.objects.all().order_by("id")
    serializer_class = DayTimeConventionSerializer
    http_method_names = ["get"]
