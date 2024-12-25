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
    first_name = CharFilter()
    last_name = CharFilter()
    telephone = CharFilter()
    email = CharFilter()
    portfolios = CharFilter(
        field_name="portfolios__user_code", lookup_expr="icontains"
    )
    client_secrets = CharFilter(
        field_name="client_secrets__user_code", lookup_expr="icontains"
    )

    class Meta:
        model = Client
        fields = []


class ClientSecretFilterSet(FilterSet):
    id = NoOpFilter()
    user_code = CharFilter()
    client = CharFilter(
        field_name="client__user_code", lookup_expr="icontains"
    )
    provider = CharFilter()
    portfolio = CharFilter()
    path_to_secret = CharFilter()
    notes = CharFilter()

    class Meta:
        model = ClientSecret
        fields = []
