from rest_framework.decorators import action
from poms.common.views import AbstractModelViewSet
from poms.clients.serializers import ClientsViewSerializer
from poms.clients.models import Client

from django.db.models import Q
from django_filters.rest_framework import FilterSet
from rest_framework.decorators import action
from poms.common.filters import (
    CharFilter,
    NoOpFilter,
)
from poms.users.filters import OwnerByMasterUserFilter


class ClientsFilterSet(FilterSet):
    id = NoOpFilter()
    user_code = CharFilter()
    name = CharFilter()
    short_name = CharFilter()
    public_name = CharFilter()
    query = CharFilter(method="query_search")

    class Meta:
        model = Client
        fields = []

    def query_search(self, queryset, _, value):
        if value:
            search_terms = value.split()
            conditions = Q()
            for term in search_terms:
                conditions |= (
                    Q(user_code__icontains=term)
                    | Q(name__icontains=term)
                    | Q(short_name__icontains=term)
                    | Q(public_name__icontains=term)
                )
            queryset = queryset.filter(conditions)

        return queryset


class ClietnsViewSet(AbstractModelViewSet):
    queryset = Client.objects.select_related(
        "master_user",
    )
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    filterset_class = ClientsFilterSet
    serializer_class = ClientsViewSerializer
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
        serializer_class=ClientsViewSerializer,
    )
    def list_light(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginator.post_paginate_queryset(queryset, request)
        serializer = self.get_serializer(page, many=True)

        return self.get_paginated_response(serializer.data)