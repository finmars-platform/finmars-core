import django_filters
from django_filters.rest_framework import FilterSet
from rest_framework.decorators import action
from rest_framework.response import Response

from poms.accounts.models import Account, AccountType
from poms.accounts.serializers import (
    AccountLightSerializer,
    AccountSerializer,
    AccountTypeSerializer,
)
from poms.common.filters import (
    AttributeFilter,
    CharFilter,
    EntitySpecificFilter,
    GroupsAttributeFilter,
    NoOpFilter,
)
from poms.common.utils import get_list_of_entity_attributes
from poms.common.views import AbstractModelViewSet
from poms.obj_attrs.utils import get_attributes_prefetch
from poms.obj_attrs.views import GenericAttributeTypeViewSet, GenericClassifierViewSet
from poms.users.filters import OwnerByMasterUserFilter


class AccountTypeAttributeTypeViewSet(GenericAttributeTypeViewSet):
    target_model = AccountType
    permission_classes = GenericAttributeTypeViewSet.permission_classes + []


class AccountTypeFilterSet(FilterSet):
    id = NoOpFilter()
    is_deleted = django_filters.BooleanFilter()
    user_code = CharFilter()
    name = CharFilter()
    short_name = CharFilter()
    public_name = CharFilter()
    show_transaction_details = django_filters.BooleanFilter()

    class Meta:
        model = AccountType
        fields = []


class AccountTypeViewSet(AbstractModelViewSet):
    queryset = AccountType.objects.select_related("master_user").prefetch_related(
        get_attributes_prefetch(),
    )
    serializer_class = AccountTypeSerializer
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter,
        GroupsAttributeFilter,
        EntitySpecificFilter,
    ]
    filter_class = AccountTypeFilterSet
    ordering_fields = [
        "user_code",
        "name",
        "short_name",
        "public_name",
        "show_transaction_details",
    ]

    @action(detail=False, methods=["get"], url_path="attributes")
    def list_attributes(self, request, *args, **kwargs):
        items = [
            {
                "key": "name",
                "name": "Name",
                "value_type": 10,
            },
            {
                "key": "short_name",
                "name": "Short name",
                "value_type": 10,
            },
            {
                "key": "user_code",
                "name": "User code",
                "value_type": 10,
            },
            {
                "key": "public_name",
                "name": "Public name",
                "value_type": 10,
            },
            {
                "key": "notes",
                "name": "Notes",
                "value_type": 10,
            },
            {
                "key": "show_transaction_details",
                "name": "Show transaction details",
                "value_type": 50,
            },
            {
                "key": "transaction_details_expr",
                "name": "Transaction details expr",
                "value_type": 10,
            },
        ]

        items += get_list_of_entity_attributes("accounts.accounttype")

        result = {"count": len(items), "next": None, "previous": None, "results": items}

        return Response(result)


class AccountTypeEvFilterSet(FilterSet):
    id = NoOpFilter()
    is_deleted = django_filters.BooleanFilter()
    user_code = CharFilter()
    name = CharFilter()
    short_name = CharFilter()
    public_name = CharFilter()
    show_transaction_details = django_filters.BooleanFilter()

    class Meta:
        model = AccountType
        fields = []


class AccountAttributeTypeViewSet(GenericAttributeTypeViewSet):
    target_model = Account
    target_model_serializer = AccountSerializer
    permission_classes = GenericAttributeTypeViewSet.permission_classes + []


class AccountClassifierViewSet(GenericClassifierViewSet):
    target_model = Account


class AccountFilterSet(FilterSet):
    id = NoOpFilter()
    is_deleted = django_filters.BooleanFilter()
    user_code = CharFilter()
    name = CharFilter()
    short_name = CharFilter()
    public_name = CharFilter()
    is_valid_for_all_portfolios = django_filters.BooleanFilter()
    attribute_types = GroupsAttributeFilter()
    attribute_values = GroupsAttributeFilter()

    class Meta:
        model = Account
        fields = []


class AccountViewSet(AbstractModelViewSet):
    queryset = Account.objects.select_related(
        "master_user",
        "type",
    ).prefetch_related(
        "portfolios",
        get_attributes_prefetch(),
    )
    serializer_class = AccountSerializer
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        GroupsAttributeFilter,
        AttributeFilter,
    ]
    filter_class = AccountFilterSet
    ordering_fields = [
        "user_code",
        "name",
        "short_name",
        "public_name",
        "is_valid_for_all_portfolios",
        "type",
        "type__user_code",
        "type__name",
        "type__short_name",
        "type__public_name",
    ]

    @action(
        detail=False,
        methods=["get"],
        url_path="light",
        serializer_class=AccountLightSerializer,
    )
    def list_light(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginator.post_paginate_queryset(queryset, request)
        serializer = self.get_serializer(page, many=True)

        return self.get_paginated_response(serializer.data)

    @action(detail=False, methods=["get"], url_path="attributes")
    def list_attributes(self, request, *args, **kwargs):
        items = Account.get_system_attrs()

        items += get_list_of_entity_attributes("accounts.account")

        result = {
            "count": len(items),
            "next": None,
            "previous": None,
            "results": items,
        }

        return Response(result)
