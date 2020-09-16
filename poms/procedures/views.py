from django_filters import FilterSet

from poms.common.filters import CharFilter
from poms.common.views import AbstractModelViewSet
from poms.integrations.providers.base import parse_date_iso
from poms.procedures.handlers import RequestDataFileProcedureProcess
from poms.procedures.models import RequestDataFileProcedure
from poms.procedures.serializers import RequestDataFileProcedureSerializer, RunRequestDataFileProcedureSerializer

from poms.users.filters import OwnerByMasterUserFilter
from rest_framework.decorators import action
from rest_framework.response import Response

from logging import getLogger

_l = getLogger('poms.procedures')



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

