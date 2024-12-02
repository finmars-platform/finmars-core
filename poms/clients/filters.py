from poms.clients.models import Client, ClientSecret
from django.db.models import Q
from django_filters.rest_framework import FilterSet
from django_filters.filters import BaseInFilter
from poms.common.filters import (
    CharFilter,
    NoOpFilter,
)


class ClientsFilterSet(FilterSet):
    id = NoOpFilter()
    user_code = CharFilter()
    name = CharFilter()
    short_name = CharFilter()
    public_name = CharFilter()
    query = CharFilter(method="query_search")
    portfolios = BaseInFilter(field_name="portfolios__id")

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
                    | Q(portfolios__user_code__icontains=term)
                )
            queryset = queryset.filter(conditions)

        return queryset


class ClientSecretFilterSet(FilterSet):
    id = NoOpFilter()
    user_code = CharFilter()
    client = CharFilter()
    query = CharFilter(method="query_search")

    class Meta:
        model = ClientSecret
        fields = []

    def query_search(self, queryset, _, value):
        if value:
            search_terms = value.split()
            conditions = Q()
            for term in search_terms:
                conditions |= (
                    Q(user_code__icontains=term)
                    | Q(client__icontains=term)
                )
            queryset = queryset.filter(conditions)

        return queryset