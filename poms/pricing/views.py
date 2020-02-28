from celery.result import AsyncResult
from django.core.signing import TimestampSigner
from django.views.decorators.csrf import csrf_exempt
from django_filters.rest_framework import FilterSet

from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView

from poms.common.utils import date_now, datetime_now

from poms.celery_tasks.models import CeleryTask
from poms.common.views import AbstractModelViewSet, AbstractAsyncViewSet, AbstractViewSet

from poms.csv_import.tasks import data_csv_file_import, data_csv_file_import_validate
from poms.obj_perms.permissions import PomsFunctionPermission, PomsConfigurationPermission
from poms.pricing.brokers.broker_serializers import DataRequestSerializer
from poms.pricing.handlers import PricingProcedureProcess, FillPricesBrokerBloombergProcess, \
    FillPricesBrokerWtradeProcess
from poms.pricing.models import InstrumentPricingScheme, CurrencyPricingScheme, InstrumentPricingSchemeType, \
    CurrencyPricingSchemeType, PricingProcedure, PricingProcedureInstance
from poms.pricing.serializers import InstrumentPricingSchemeSerializer, CurrencyPricingSchemeSerializer, \
    CurrencyPricingSchemeTypeSerializer, InstrumentPricingSchemeTypeSerializer, PricingProcedureSerializer, \
    RunProcedureSerializer, BrokerBloombergSerializer

from poms.users.filters import OwnerByMasterUserFilter
from rest_framework.decorators import action

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

    @action(detail=True, methods=['post'], url_path='run-procedure', serializer_class=RunProcedureSerializer)
    def run_procedure(self, request, pk=None):

        print("Run Procedure %s" % pk)

        procedure = PricingProcedure.objects.get(pk=pk)

        master_user = request.user.master_user

        instance = PricingProcedureProcess(procedure=procedure, master_user=master_user)
        instance.process()

        serializer = self.get_serializer(instance=instance)

        return Response(serializer.data)


class PricingBrokerBloombergHandler(APIView):

    permission_classes = []

    def post(self, request):

        # print('request.data %s' % request.data)

        procedure_id = request.data['procedure']

        print("> handle_callback broker bloomberg: procedure_id %s" % procedure_id)

        try:

            procedure = PricingProcedureInstance.objects.get(pk=procedure_id)

            instance = FillPricesBrokerBloombergProcess(instance=request.data, master_user=procedure.master_user)
            instance.process()

        except PricingProcedure.DoesNotExist:

            print("Does not exist? Procedure %s" % procedure_id)

            return Response({'status': '404'})  # TODO handle 404 properly

        return Response({'status': 'ok'})


class PricingBrokerWtradeHandler(APIView):

    permission_classes = []

    def post(self, request):

        # print('request.data %s' % request.data)

        procedure_id = request.data['procedure']

        print("> handle_callback broker wtrade: procedure_id %s" % procedure_id)

        try:

            procedure = PricingProcedureInstance.objects.get(pk=procedure_id)

            instance = FillPricesBrokerWtradeProcess(instance=request.data, master_user=procedure.master_user)
            instance.process()

        except PricingProcedure.DoesNotExist:

            print("Does not exist? Procedure %s" % procedure_id)

            return Response({'status': '404'})  # TODO handle 404 properly

        return Response({'status': 'ok'})
