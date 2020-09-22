from django_filters import FilterSet

from poms.common.filters import CharFilter, NoOpFilter
from poms.common.views import AbstractModelViewSet
from poms.integrations.providers.base import parse_date_iso
from poms.pricing.handlers import PricingProcedureProcess
from poms.procedures.handlers import RequestDataFileProcedureProcess
from poms.procedures.models import RequestDataFileProcedure, PricingProcedure, PricingParentProcedureInstance
from poms.procedures.serializers import RequestDataFileProcedureSerializer, RunRequestDataFileProcedureSerializer, \
    PricingProcedureSerializer, RunProcedureSerializer, PricingParentProcedureInstanceSerializer

from poms.users.filters import OwnerByMasterUserFilter
from rest_framework.decorators import action
from rest_framework.response import Response

from logging import getLogger

_l = getLogger('poms.procedures')


class PricingProcedureFilterSet(FilterSet):

    class Meta:
        model = PricingProcedure
        fields = []


class PricingProcedureViewSet(AbstractModelViewSet):
    queryset = PricingProcedure.objects.filter(type=PricingProcedure.CREATED_BY_USER)
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

        _l.info("Run Procedure %s" % pk)

        _l.info("Run Procedure data %s" % request.data)

        procedure = PricingProcedure.objects.get(pk=pk)

        master_user = request.user.master_user

        date_from = None
        date_to = None

        if 'user_price_date_from' in request.data:
            if request.data['user_price_date_from']:
                date_from = parse_date_iso(request.data['user_price_date_from'])

        if 'user_price_date_to' in request.data:
            if request.data['user_price_date_to']:
                date_to = parse_date_iso(request.data['user_price_date_to'])

        instance = PricingProcedureProcess(procedure=procedure, master_user=master_user, date_from=date_from, date_to=date_to)
        instance.process()

        serializer = self.get_serializer(instance=instance)

        return Response(serializer.data)



class PricingParentProcedureInstanceFilterSet(FilterSet):
    id = NoOpFilter()

    class Meta:
        model = PricingParentProcedureInstance
        fields = []


class PricingParentProcedureInstanceViewSet(AbstractModelViewSet):
    queryset = PricingParentProcedureInstance.objects.select_related(
        'master_user',
    )
    serializer_class = PricingParentProcedureInstanceSerializer
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    filter_class = PricingParentProcedureInstanceFilterSet



class RequestDataFileProcedureFilterSet(FilterSet):
    user_code = CharFilter()
    name = CharFilter()

    class Meta:
        model = RequestDataFileProcedure
        fields = []


class RequestDataFileProcedureViewSet(AbstractModelViewSet):
    queryset = RequestDataFileProcedure.objects
    serializer_class = RequestDataFileProcedureSerializer
    filter_class = RequestDataFileProcedureFilterSet
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]

    permission_classes = []

    @action(detail=True, methods=['post'], url_path='run-procedure', serializer_class=RunRequestDataFileProcedureSerializer)
    def run_procedure(self, request, pk=None):

        _l.info("Run Procedure %s" % pk)

        _l.info("Run Procedure data %s" % request.data)

        procedure = RequestDataFileProcedure.objects.get(pk=pk)

        master_user = request.user.master_user

        # date_from = None
        # date_to = None
        #
        # if 'user_price_date_from' in request.data:
        #     if request.data['user_price_date_from']:
        #         date_from = parse_date_iso(request.data['user_price_date_from'])
        #
        # if 'user_price_date_to' in request.data:
        #     if request.data['user_price_date_to']:
        #         date_to = parse_date_iso(request.data['user_price_date_to'])

        # instance = RequestDataFileProcedureProcess(procedure=procedure, master_user=master_user, date_from=date_from, date_to=date_to)
        instance = RequestDataFileProcedureProcess(procedure=procedure, master_user=master_user)
        instance.process()

        serializer = self.get_serializer(instance=instance)

        return Response(serializer.data)

