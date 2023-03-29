from poms.common.views import AbstractModelViewSet
from poms.configuration.models import Configuration
from poms.configuration.serializers import ConfigurationSerializer
from django_filters.rest_framework import FilterSet
from poms.common.filters import CharFilter


class ConfigurationFilterSet(FilterSet):
    name = CharFilter()
    short_name = CharFilter()
    version = CharFilter()

    class Meta:
        model = Configuration
        fields = []


class ConfigurationViewSet(AbstractModelViewSet):
    queryset = Configuration.objects
    serializer_class = ConfigurationSerializer
    filter_class = ConfigurationFilterSet
    filter_backends = AbstractModelViewSet.filter_backends + [

    ]
    permission_classes = AbstractModelViewSet.permission_classes + [

    ]