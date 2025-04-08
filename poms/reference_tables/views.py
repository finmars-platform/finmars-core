from django_filters.rest_framework import FilterSet

from poms.common.filters import CharFilter, NoOpFilter
from poms.common.renderers import FinmarsJSONRenderer, BrowsableAPIRenderer
from poms.common.views import AbstractModelViewSet
from poms.reference_tables.models import ReferenceTable
from poms.reference_tables.serializers import ReferenceTableSerializer
from poms.users.filters import OwnerByMasterUserFilter


class ReferenceTableFilterSet(FilterSet):
    id = NoOpFilter()
    name = CharFilter()

    class Meta:
        model = ReferenceTable
        fields = []


class ReferenceTableViewSet(AbstractModelViewSet):
    queryset = ReferenceTable.objects
    serializer_class = ReferenceTableSerializer
    filter_backends = [OwnerByMasterUserFilter]
    renderer_classes = [FinmarsJSONRenderer, BrowsableAPIRenderer]
    filter_class = ReferenceTableFilterSet
    ordering_fields = ["name"]
