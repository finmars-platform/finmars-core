from __future__ import unicode_literals

import django_filters
from django_filters.rest_framework import FilterSet
from rest_framework.settings import api_settings
from rest_framework.decorators import action
from poms.accounts.models import Account, AccountType
from poms.accounts.serializers import AccountSerializer, AccountTypeSerializer, AccountLightSerializer, \
    AccountEvSerializer, AccountTypeEvSerializer
from poms.common.filters import CharFilter, NoOpFilter, ModelExtWithPermissionMultipleChoiceFilter, \
    GroupsAttributeFilter, AttributeFilter, EntitySpecificFilter
from poms.common.pagination import CustomPaginationMixin
from poms.common.utils import get_list_of_entity_attributes
from poms.obj_attrs.models import GenericAttributeType
from poms.obj_attrs.utils import get_attributes_prefetch
from poms.obj_attrs.views import GenericAttributeTypeViewSet, GenericClassifierViewSet
from poms.obj_perms.filters import ObjectPermissionMemberFilter, ObjectPermissionPermissionFilter
from poms.obj_perms.permissions import PomsConfigurationPermission
from poms.obj_perms.utils import get_permissions_prefetch_lookups
from poms.obj_perms.views import AbstractWithObjectPermissionViewSet, AbstractEvGroupWithObjectPermissionViewSet
from poms.portfolios.models import Portfolio
from poms.users.filters import OwnerByMasterUserFilter
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema

class AccountTypeAttributeTypeViewSet(GenericAttributeTypeViewSet):
    target_model = AccountType

    permission_classes = GenericAttributeTypeViewSet.permission_classes + [
        PomsConfigurationPermission
    ]


class AccountTypeFilterSet(FilterSet):
    id = NoOpFilter()
    is_deleted = django_filters.BooleanFilter()
    user_code = CharFilter()
    name = CharFilter()
    short_name = CharFilter()
    public_name = CharFilter()
    show_transaction_details = django_filters.BooleanFilter()
    member = ObjectPermissionMemberFilter(object_permission_model=AccountType)
    # member_group = ObjectPermissionGroupFilter(object_permission_model=AccountType)
    permission = ObjectPermissionPermissionFilter(object_permission_model=AccountType)

    class Meta:
        model = AccountType
        fields = []


class AccountTypeViewSet(AbstractWithObjectPermissionViewSet):

    queryset = AccountType.objects.select_related(
        'master_user'
    ).prefetch_related(
        get_attributes_prefetch(),
        *get_permissions_prefetch_lookups(
            (None, AccountType),
        )
    )
    serializer_class = AccountTypeSerializer
    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter,
        GroupsAttributeFilter,
        EntitySpecificFilter
    ]
    filter_class = AccountTypeFilterSet
    ordering_fields = [
        'user_code', 'name', 'short_name', 'public_name', 'show_transaction_details'
    ]

    @action(detail=False, methods=['get'], url_path='attributes')
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
                "value_type": 10
            }
        ]

        items = items + get_list_of_entity_attributes('accounts.accounttype')

        result = {
            "count": len(items),
            "next": None,
            "previous": None,
            "results": items
        }

        return Response(result)

    # @swagger_auto_schema(operation_id="Account Type List")
    # def list(self, request, *args, **kwargs):
    #     return super().list(request, *args, **kwargs)
    # @swagger_auto_schema(operation_id="Account Type Retrieve")
    # def retrieve(self, request, *args, **kwargs):
    #     return super().retrieve(request, *args, **kwargs)
    #
    # @swagger_auto_schema(operation_id="Account Type Create")
    # def create(self, request, *args, **kwargs):
    #     return super().create(request, *args, **kwargs)
    #
    # @swagger_auto_schema(operation_id="Account Type Update")
    # def update(self, request, *args, **kwargs):
    #     return super().update(request, *args, **kwargs)
    #
    # @swagger_auto_schema(operation_id="Account Type Partial Update")
    # def partial_update(self, request, *args, **kwargs):
    #     return super().partial_update(request, *args, **kwargs)
    #
    # @swagger_auto_schema(operation_id="Account Type Delete")
    # def destroy(self, request, *args, **kwargs):
    #     return super().destroy(request, *args, **kwargs)

class AccountTypeEvFilterSet(FilterSet):
    id = NoOpFilter()
    is_deleted = django_filters.BooleanFilter()
    user_code = CharFilter()
    name = CharFilter()
    short_name = CharFilter()
    public_name = CharFilter()
    show_transaction_details = django_filters.BooleanFilter()
    member = ObjectPermissionMemberFilter(object_permission_model=AccountType)
    # member_group = ObjectPermissionGroupFilter(object_permission_model=AccountType)
    permission = ObjectPermissionPermissionFilter(object_permission_model=AccountType)

    class Meta:
        model = AccountType
        fields = []


class AccountAttributeTypeViewSet(GenericAttributeTypeViewSet):
    target_model = Account
    target_model_serializer = AccountSerializer

    permission_classes = GenericAttributeTypeViewSet.permission_classes + [
        PomsConfigurationPermission
    ]


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
    type = ModelExtWithPermissionMultipleChoiceFilter(model=AccountType)
    member = ObjectPermissionMemberFilter(object_permission_model=Account)
    # member_group = ObjectPermissionGroupFilter(object_permission_model=Account)
    permission = ObjectPermissionPermissionFilter(object_permission_model=Account)
    attribute_types = GroupsAttributeFilter()
    attribute_values = GroupsAttributeFilter()

    class Meta:
        model = Account
        fields = []


class AccountViewSet(AbstractWithObjectPermissionViewSet):
    queryset = Account.objects.select_related(
        'master_user',
        'type',
    ).prefetch_related(
        'portfolios',
        # Prefetch('attributes', queryset=AccountAttribute.objects.select_related(
        #     'attribute_type', 'classifier'
        # ).prefetch_related(
        #     'attribute_type__options'
        # )),
        get_attributes_prefetch(),
        *get_permissions_prefetch_lookups(
            (None, Account),
            ('type', AccountType),
            ('portfolios', Portfolio),
            # ('attributes__attribute_type', AccountAttributeType),
        )
    )
    # prefetch_permissions_for = (
    #     ('type', AccountType),
    #     ('portfolios', Portfolio),
    #     ('attributes__attribute_type', AccountAttributeType),
    # )
    serializer_class = AccountSerializer
    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        GroupsAttributeFilter,
        AttributeFilter
    ]
    filter_class = AccountFilterSet
    ordering_fields = [
        'user_code', 'name', 'short_name', 'public_name', 'is_valid_for_all_portfolios',
        'type', 'type__user_code', 'type__name', 'type__short_name', 'type__public_name',
    ]

    @action(detail=False, methods=['get'], url_path='light', serializer_class=AccountLightSerializer)
    def list_light(self, request, *args, **kwargs):

        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginator.post_paginate_queryset(queryset, request)
        serializer = self.get_serializer(page, many=True)

        result = self.get_paginated_response(serializer.data)

        return result

    @action(detail=False, methods=['get'], url_path='attributes')
    def list_attributes(self, request, *args, **kwargs):

        items = Account.system_attrs()

        items = items + get_list_of_entity_attributes('accounts.account')

        result = {
            "count": len(items),
            "next": None,
            "previous": None,
            "results": items
        }

        return Response(result)

