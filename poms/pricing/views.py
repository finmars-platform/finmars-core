from django_filters.rest_framework import FilterSet

from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.views import APIView

from poms.common.filters import NoOpFilter
from poms.common.pagination import CustomPaginationMixin

from poms.common.views import AbstractModelViewSet, AbstractEvGroupViewSet


from poms.pricing.handlers import FillPricesBrokerBloombergProcess, \
    FillPricesBrokerWtradeProcess, FillPricesBrokerFixerProcess, FillPricesBrokerAlphavProcess, \
    FillPricesBrokerBloombergForwardsProcess
from poms.pricing.models import InstrumentPricingScheme, CurrencyPricingScheme, InstrumentPricingSchemeType, \
    CurrencyPricingSchemeType, PricingProcedureInstance, PriceHistoryError, \
    CurrencyHistoryError
from poms.pricing.serializers import InstrumentPricingSchemeSerializer, CurrencyPricingSchemeSerializer, \
    CurrencyPricingSchemeTypeSerializer, InstrumentPricingSchemeTypeSerializer, \
    PriceHistoryErrorSerializer, \
    CurrencyHistoryErrorSerializer

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



class PricingBrokerBloombergHandler(APIView):

    permission_classes = []

    def post(self, request):

        # _l.info('request.data %s' % request.data)

        procedure_id = request.data['procedure']

        _l.info("> handle_callback broker bloomberg: procedure_id %s" % procedure_id)

        try:

            procedure = PricingProcedureInstance.objects.get(pk=procedure_id)

            if not request.data['error_code']:

                instance = FillPricesBrokerBloombergProcess(instance=request.data, master_user=procedure.master_user)
                instance.process()

            else:

                procedure.error_code = request.data['error_code']
                procedure.error_message = request.data['error_message']

                procedure.status = PricingProcedureInstance.STATUS_ERROR
                procedure.save()

        except PricingProcedureInstance.DoesNotExist:

            _l.info("Does not exist? Procedure %s" % procedure_id)

            return Response({'status': '404'})  # TODO handle 404 properly

        return Response({'status': 'ok'})


class PricingBrokerBloombergForwardsHandler(APIView):

    permission_classes = []

    def post(self, request):

        # _l.info('request.data %s' % request.data)

        procedure_id = request.data['procedure']

        _l.info("> handle_callback broker bloomberg forwards: procedure_id %s" % procedure_id)

        try:

            procedure = PricingProcedureInstance.objects.get(pk=procedure_id)

            if not request.data['error_code']:

                instance = FillPricesBrokerBloombergForwardsProcess(instance=request.data, master_user=procedure.master_user)
                instance.process()

            else:

                procedure.error_code = request.data['error_code']
                procedure.error_message = request.data['error_message']

                procedure.status = PricingProcedureInstance.STATUS_ERROR
                procedure.save()

        except PricingProcedureInstance.DoesNotExist:

            _l.info("Does not exist? Procedure %s" % procedure_id)

            return Response({'status': '404'})  # TODO handle 404 properly

        return Response({'status': 'ok'})


class PricingBrokerWtradeHandler(APIView):

    permission_classes = []

    def post(self, request):

        # _l.info('request.data %s' % request.data)

        procedure_id = request.data['procedure']

        _l.info("> handle_callback broker wtrade: procedure_id %s" % procedure_id)

        try:

            procedure = PricingProcedureInstance.objects.get(pk=procedure_id)

            if not request.data['error_code']:

                instance = FillPricesBrokerWtradeProcess(instance=request.data, master_user=procedure.master_user)
                instance.process()

            else:

                procedure.error_code = request.data['error_code']
                procedure.error_message = request.data['error_message']

                procedure.status = PricingProcedureInstance.STATUS_ERROR
                procedure.save()

        except PricingProcedureInstance.DoesNotExist:

            _l.info("Does not exist? Procedure %s" % procedure_id)

            return Response({'status': '404'})  # TODO handle 404 properly

        return Response({'status': 'ok'})


class PricingBrokerFixerHandler(APIView):

    permission_classes = []

    def post(self, request):

        # _l.info('request.data %s' % request.data)

        procedure_id = request.data['procedure']

        _l.info("> handle_callback broker fixer: procedure_id %s" % procedure_id)

        try:

            procedure = PricingProcedureInstance.objects.get(pk=procedure_id)

            if not request.data['error_code']:

                instance = FillPricesBrokerFixerProcess(instance=request.data, master_user=procedure.master_user)
                instance.process()

            else:

                procedure.error_code = request.data['error_code']
                procedure.error_message = request.data['error_message']

                procedure.status = PricingProcedureInstance.STATUS_ERROR
                procedure.save()

        except PricingProcedureInstance.DoesNotExist:

            _l.info("Does not exist? Procedure %s" % procedure_id)

            return Response({'status': '404'})  # TODO handle 404 properly

        return Response({'status': 'ok'})


class PricingBrokerAlphavHandler(APIView):

    permission_classes = []

    def post(self, request):

        # _l.info('request.data %s' % request.data)

        procedure_id = request.data['procedure']

        _l.info("> handle_callback broker alphav: procedure_id %s" % procedure_id)

        try:

            procedure = PricingProcedureInstance.objects.get(pk=procedure_id)

            if not request.data['error_code']:

                instance = FillPricesBrokerAlphavProcess(instance=request.data, master_user=procedure.master_user)
                instance.process()

            else:

                procedure.error_code = request.data['error_code']
                procedure.error_message = request.data['error_message']

                procedure.status = PricingProcedureInstance.STATUS_ERROR
                procedure.save()

        except PricingProcedureInstance.DoesNotExist:

            _l.info("Does not exist? Procedure %s" % procedure_id)

            return Response({'status': '404'})  # TODO handle 404 properly

        return Response({'status': 'ok'})


class PriceHistoryErrorFilterSet(FilterSet):
    id = NoOpFilter()

    class Meta:
        model = PriceHistoryError
        fields = []


class PriceHistoryErrorViewSet(AbstractModelViewSet):
    queryset = PriceHistoryError.objects.select_related(
        'master_user',
    )
    serializer_class = PriceHistoryErrorSerializer
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    filter_class = PriceHistoryErrorFilterSet
    ordering_fields = [
        'date'
    ]


class PriceHistoryErrorEvGroupViewSet(AbstractEvGroupViewSet, CustomPaginationMixin):
    queryset = PriceHistoryError.objects.select_related(
        'master_user',
    )

    serializer_class = PriceHistoryErrorSerializer
    pagination_class = api_settings.DEFAULT_PAGINATION_CLASS
    filter_class = PriceHistoryErrorFilterSet

    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]


class CurrencyHistoryErrorFilterSet(FilterSet):
    id = NoOpFilter()

    class Meta:
        model = CurrencyHistoryError
        fields = []


class CurrencyHistoryErrorViewSet(AbstractModelViewSet):
    queryset = CurrencyHistoryError.objects.select_related(
        'master_user',
    )
    serializer_class = CurrencyHistoryErrorSerializer
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    filter_class = CurrencyHistoryErrorFilterSet
    ordering_fields = [
        'date'
    ]


class CurrencyHistoryErrorEvGroupViewSet(AbstractEvGroupViewSet, CustomPaginationMixin):
    queryset = CurrencyHistoryError.objects.select_related(
        'master_user',
    )

    serializer_class = CurrencyHistoryErrorSerializer
    pagination_class = api_settings.DEFAULT_PAGINATION_CLASS
    filter_class = CurrencyHistoryErrorFilterSet

    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
