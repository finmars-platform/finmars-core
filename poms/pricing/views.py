from celery.result import AsyncResult
from django.core.signing import TimestampSigner
from django_filters.rest_framework import FilterSet

from rest_framework.response import Response
from rest_framework import status

from poms.common.utils import date_now, datetime_now

from poms.celery_tasks.models import CeleryTask
from poms.common.views import AbstractModelViewSet, AbstractAsyncViewSet

from poms.csv_import.tasks import data_csv_file_import, data_csv_file_import_validate
from poms.obj_perms.permissions import PomsFunctionPermission, PomsConfigurationPermission
from poms.pricing.models import InstrumentPricingScheme, CurrencyPricingScheme, InstrumentPricingSchemeType, \
    CurrencyPricingSchemeType, PricingProcedure
from poms.pricing.serializers import InstrumentPricingSchemeSerializer, CurrencyPricingSchemeSerializer, \
    CurrencyPricingSchemeTypeSerializer, InstrumentPricingSchemeTypeSerializer, PricingProcedureSerializer

from poms.users.filters import OwnerByMasterUserFilter

from logging import getLogger

_l = getLogger('poms.pricing')


class InstrumentPricingSchemeFilterSet(FilterSet):

    class Meta:
        model = InstrumentPricingScheme
        fields = []


class InstrumentPricingSchemeViewSet(AbstractModelViewSet):
    queryset = InstrumentPricingScheme.objects
    serializer_class = InstrumentPricingSchemeSerializer
    filter_class = InstrumentPricingSchemeFilterSet
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    permission_classes = AbstractModelViewSet.permission_classes + [
        # PomsConfigurationPermission
    ]


class InstrumentPricingSchemeTypeFilterSet(FilterSet):

    class Meta:
        model = InstrumentPricingSchemeType
        fields = []


class InstrumentPricingSchemeTypeViewSet(AbstractModelViewSet):
    queryset = InstrumentPricingSchemeType.objects
    serializer_class = InstrumentPricingSchemeTypeSerializer
    filter_class = InstrumentPricingSchemeTypeFilterSet
    filter_backends = AbstractModelViewSet.filter_backends + [
        # OwnerByMasterUserFilter,
    ]
    permission_classes = AbstractModelViewSet.permission_classes + [
        # PomsConfigurationPermission
    ]


class CurrencyPricingSchemeFilterSet(FilterSet):

    class Meta:
        model = CurrencyPricingScheme
        fields = []


class CurrencyPricingSchemeViewSet(AbstractModelViewSet):
    queryset = CurrencyPricingScheme.objects
    serializer_class = CurrencyPricingSchemeSerializer
    filter_class = CurrencyPricingSchemeFilterSet
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    permission_classes = AbstractModelViewSet.permission_classes + [
        # PomsConfigurationPermission
    ]


class CurrencyPricingSchemeTypeFilterSet(FilterSet):

    class Meta:
        model = CurrencyPricingSchemeType
        fields = []


class CurrencyPricingSchemeTypeViewSet(AbstractModelViewSet):
    queryset = CurrencyPricingSchemeType.objects
    serializer_class = CurrencyPricingSchemeTypeSerializer
    filter_class = CurrencyPricingSchemeTypeFilterSet
    filter_backends = AbstractModelViewSet.filter_backends + [
        # OwnerByMasterUserFilter,
    ]
    permission_classes = AbstractModelViewSet.permission_classes + [
        # PomsConfigurationPermission
    ]


class PricingProcedureFilterSet(FilterSet):

    class Meta:
        model = PricingProcedure
        fields = []


class PricingProcedureViewSet(AbstractModelViewSet):
    queryset = PricingProcedure.objects
    serializer_class = PricingProcedureSerializer
    filter_class = PricingProcedureFilterSet
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    permission_classes = AbstractModelViewSet.permission_classes + [
        # PomsConfigurationPermission
    ]

