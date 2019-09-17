from django_filters.rest_framework import FilterSet
from rest_framework.parsers import MultiPartParser

from poms.common.filters import NoOpFilter, CharFilter
from poms.complex_import.serializers import ComplexImportSchemeSerializer, ComplexImportSerializer

from poms.common.views import AbstractModelViewSet
from poms.obj_perms.views import AbstractWithObjectPermissionViewSet
from poms.users.filters import OwnerByMasterUserFilter

from .models import ComplexImportScheme, ComplexImport

from logging import getLogger

_l = getLogger('poms.csv_import')


class ComplexImportSchemeFilterSet(FilterSet):
    id = NoOpFilter()
    name = CharFilter()

    class Meta:
        model = ComplexImportScheme
        fields = []


class ComplexImportSchemeViewSet(AbstractModelViewSet):
    queryset = ComplexImportScheme.objects.select_related(
        'master_user',
    )
    serializer_class = ComplexImportSchemeSerializer
    filter_class = ComplexImportSchemeFilterSet
    filter_backends = [
        OwnerByMasterUserFilter,
    ]


class ComplexImportViewSet(AbstractModelViewSet):
    parser_classes = (MultiPartParser,)
    queryset = ComplexImport.objects.select_related(
        'master_user',
    )
    serializer_class = ComplexImportSerializer
    http_method_names = ['get', 'post', 'head']