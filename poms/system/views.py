from celery.result import AsyncResult
from django.core.signing import TimestampSigner
from django_filters.rest_framework import FilterSet


from poms.common.views import AbstractModelViewSet, AbstractAsyncViewSet


from poms.system.models import EcosystemConfiguration
from poms.system.serializers import EcosystemConfigurationSerializer

from logging import getLogger

_l = getLogger('poms.system')


class SchemeFilterSet(FilterSet):

    class Meta:
        model = EcosystemConfiguration
        fields = []


class EcosystemConfigurationViewSet(AbstractModelViewSet):
    queryset = EcosystemConfiguration.objects
    serializer_class = EcosystemConfigurationSerializer
    filter_class = SchemeFilterSet
