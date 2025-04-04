from logging import getLogger

from django_filters.rest_framework import FilterSet
from rest_framework.parsers import MultiPartParser

from poms.common.filters import CharFilter, NoOpFilter
from poms.common.renderers import FinmarsJSONRenderer
from poms.common.views import AbstractModelViewSet
from poms.complex_import.serializers import (
    ComplexImportSchemeSerializer,
    ComplexImportSerializer,
)
from poms.users.filters import OwnerByMasterUserFilter

from .models import ComplexImport, ComplexImportScheme

_l = getLogger("poms.csv_import")


class ComplexImportSchemeFilterSet(FilterSet):
    id = NoOpFilter()
    user_code = CharFilter()

    class Meta:
        model = ComplexImportScheme
        fields = []


class ComplexImportSchemeViewSet(AbstractModelViewSet):
    queryset = ComplexImportScheme.objects
    serializer_class = ComplexImportSchemeSerializer
    filter_class = ComplexImportSchemeFilterSet
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    permission_classes = AbstractModelViewSet.permission_classes + []
    renderer_classes = [FinmarsJSONRenderer]


class ComplexImportViewSet(AbstractModelViewSet):
    parser_classes = (MultiPartParser,)
    queryset = ComplexImport.objects.select_related(
        "master_user",
    )
    serializer_class = ComplexImportSerializer
    http_method_names = ["get", "post", "head"]
    renderer_classes = [FinmarsJSONRenderer]
