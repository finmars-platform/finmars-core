from logging import getLogger

from django_filters.rest_framework import FilterSet
from rest_framework.exceptions import ValidationError

from poms.common.views import AbstractModelViewSet

from poms.system.models import EcosystemConfiguration, WhitelabelModel
from poms.system.serializers import (
    EcosystemConfigurationSerializer,
    WhitelabelSerializer,
)

_l = getLogger("poms.system")


class SchemeFilterSet(FilterSet):
    class Meta:
        model = EcosystemConfiguration
        fields = []


class EcosystemConfigurationViewSet(AbstractModelViewSet):
    queryset = EcosystemConfiguration.objects
    serializer_class = EcosystemConfigurationSerializer
    filter_class = SchemeFilterSet


class IsDefaultFilterSet(FilterSet):
    class Meta:
        model = WhitelabelModel
        fields = ["is_default"]


class WhitelabelViewSet(AbstractModelViewSet):
    queryset = WhitelabelModel.objects
    serializer_class = WhitelabelSerializer
    pagination_class = None
    filter_class = IsDefaultFilterSet

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.is_default:
            raise ValidationError("Can't delete default whitelabel")

        return super().destroy(request, *args, **kwargs)
