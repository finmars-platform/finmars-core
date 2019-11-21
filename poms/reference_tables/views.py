from __future__ import unicode_literals

from django_filters.rest_framework import FilterSet

from poms.common.filters import CharFilter, NoOpFilter
from poms.common.views import AbstractModelViewSet
from poms.obj_perms.permissions import PomsConfigurationPermission
from poms.obj_perms.views import AbstractWithObjectPermissionViewSet
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
    filter_backends = [
        OwnerByMasterUserFilter,
    ]
    filter_class = ReferenceTableFilterSet
    ordering_fields = [
        'name',
    ]
    permission_classes = AbstractModelViewSet.permission_classes + [
        PomsConfigurationPermission
    ]
