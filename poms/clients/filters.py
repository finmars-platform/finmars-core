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
    portfolios = BaseInFilter(field_name="portfolios__user_code")
    client_secrets = BaseInFilter(field_name="client_secrets__user_code")

    class Meta:
        model = Client
        fields = []


class ClientSecretFilterSet(FilterSet):
    id = NoOpFilter()
    user_code = CharFilter()
    client = BaseInFilter(field_name="client__user_code")
    provider = CharFilter()
    portfolio = CharFilter()
    path_to_secret = CharFilter()
    notes = CharFilter()

    class Meta:
        model = ClientSecret
        fields = []
