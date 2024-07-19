from logging import getLogger

from django_filters.rest_framework import FilterSet

from poms.common.views import AbstractModelViewSet
from poms.system.models import EcosystemConfiguration
from poms.system.serializers import EcosystemConfigurationSerializer

_l = getLogger('poms.system')


class SchemeFilterSet(FilterSet):
    class Meta:
        model = EcosystemConfiguration
        fields = []


class EcosystemConfigurationViewSet(AbstractModelViewSet):
    queryset = EcosystemConfiguration.objects
    serializer_class = EcosystemConfigurationSerializer
    filter_class = SchemeFilterSet
