from logging import getLogger

from django.conf import settings
from django_filters.rest_framework import FilterSet

from poms.common.views import AbstractModelViewSet
from poms.system.models import EcosystemConfiguration, WhitelabelModel
from poms.system.serializers import (
    EcosystemConfigurationSerializer,
    WhitelabelListSerializer,
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
    filter_class = IsDefaultFilterSet
    pagination_class = None

    def get_serializer_context(self, *args, **kwargs):
        context = super().get_serializer_context()
        context.update(
            {
                "realm_code": self.request.realm_code,
                "space_code": self.request.space_code,
                "host_url": settings.DOMAIN_NAME,
            }
        )
        return context

    def get_serializer_class(self):
        if self.action in {"list", "retrieve"}:
            return WhitelabelListSerializer
        else:
            return WhitelabelSerializer

    def get_serializer(self, *args, **kwargs):
        serializer_class = self.get_serializer_class()
        kwargs["context"] = self.get_serializer_context()
        return serializer_class(*args, **kwargs)
