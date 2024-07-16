from logging import getLogger

from django_filters.rest_framework import FilterSet

from poms.common.views import AbstractModelViewSet
from poms.system.models import EcosystemConfiguration, VaultRecord
from poms.system.serializers import EcosystemConfigurationSerializer, VaultRecordSerializer
from poms.users.filters import OwnerByMasterUserFilter

_l = getLogger('poms.system')


class SchemeFilterSet(FilterSet):
    class Meta:
        model = EcosystemConfiguration
        fields = []


class EcosystemConfigurationViewSet(AbstractModelViewSet):
    queryset = EcosystemConfiguration.objects
    serializer_class = EcosystemConfigurationSerializer
    filter_class = SchemeFilterSet


class VaultRecordViewSet(AbstractModelViewSet):
    queryset = VaultRecord.objects
    serializer_class = VaultRecordSerializer

    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
