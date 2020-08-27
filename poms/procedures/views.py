from django_filters import FilterSet

from poms.common.filters import CharFilter
from poms.common.views import AbstractModelViewSet
from poms.procedures.models import RequestDataFileProcedure
from poms.procedures.serializers import RequestDataFileProcedureSerializer

from poms.users.filters import OwnerByMasterUserFilter


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

