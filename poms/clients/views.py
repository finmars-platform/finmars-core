from rest_framework.decorators import action

from poms.clients.filters import ClientSecretFilterSet, ClientsFilterSet
from poms.clients.models import Client, ClientSecret
from poms.clients.serializers import ClientSecretSerializer, ClientSerializer
from poms.common.views import AbstractModelViewSet
from poms.users.filters import OwnerByMasterUserFilter


class ClientsViewSet(AbstractModelViewSet):
    queryset = Client.objects.select_related(
        "master_user",
    )
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    filterset_class = ClientsFilterSet
    serializer_class = ClientSerializer
    ordering_fields = [
        "user_code",
        "name",
        "short_name",
        "public_name",
    ]

    @action(
        detail=False,
        methods=["get"],
        url_path="light",
        serializer_class=ClientSerializer,
    )
    def list_light(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginator.post_paginate_queryset(queryset, request)
        serializer = self.get_serializer(page, many=True)

        return self.get_paginated_response(serializer.data)


class ClientSecretsViewSet(AbstractModelViewSet):
    queryset = ClientSecret.objects.select_related(
        "master_user",
    )
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    filterset_class = ClientSecretFilterSet
    serializer_class = ClientSecretSerializer
    ordering_fields = [
        "user_code",
        "client",
    ]

    @action(
        detail=False,
        methods=["get"],
        url_path="light",
        serializer_class=ClientSecretSerializer,
    )
    def list_light(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginator.post_paginate_queryset(queryset, request)
        serializer = self.get_serializer(page, many=True)

        return self.get_paginated_response(serializer.data)
