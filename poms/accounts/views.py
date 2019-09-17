from __future__ import unicode_literals

import django_filters
from django_filters.rest_framework import FilterSet
from rest_framework.settings import api_settings

from poms.accounts.models import Account, AccountType
from poms.accounts.serializers import AccountSerializer, AccountTypeSerializer
from poms.common.filters import CharFilter, NoOpFilter, ModelExtWithPermissionMultipleChoiceFilter, \
    GroupsAttributeFilter, AttributeFilter
from poms.common.pagination import CustomPaginationMixin
from poms.obj_attrs.utils import get_attributes_prefetch
from poms.obj_attrs.views import GenericAttributeTypeViewSet, GenericClassifierViewSet
from poms.obj_perms.filters import ObjectPermissionMemberFilter, ObjectPermissionGroupFilter, \
    ObjectPermissionPermissionFilter
from poms.obj_perms.utils import get_permissions_prefetch_lookups
from poms.obj_perms.views import AbstractWithObjectPermissionViewSet, AbstractEvGroupWithObjectPermissionViewSet
from poms.portfolios.models import Portfolio
from poms.tags.filters import TagFilter
from poms.tags.utils import get_tag_prefetch
from poms.users.filters import OwnerByMasterUserFilter

from rest_framework.response import Response
from poms.common.grouping_handlers import handle_groups
from rest_framework import viewsets, status

class AccountTypeAttributeTypeViewSet(GenericAttributeTypeViewSet):
    target_model = AccountType

class AccountTypeFilterSet(FilterSet):
    id = NoOpFilter()
    is_deleted = django_filters.BooleanFilter()
    user_code = CharFilter()
    name = CharFilter()
    short_name = CharFilter()
    public_name = CharFilter()
    show_transaction_details = django_filters.BooleanFilter()
    tag = TagFilter(model=AccountType)
    member = ObjectPermissionMemberFilter(object_permission_model=AccountType)
    member_group = ObjectPermissionGroupFilter(object_permission_model=AccountType)
    permission = ObjectPermissionPermissionFilter(object_permission_model=AccountType)

    class Meta:
        model = AccountType
        fields = []


class AccountTypeViewSet(AbstractWithObjectPermissionViewSet):
    queryset = AccountType.objects.select_related(
        'master_user'
    ).prefetch_related(
        get_tag_prefetch(),
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
        # TagFilterBackend,
    ]
    filter_class = AccountTypeFilterSet
    ordering_fields = [
        'user_code', 'name', 'short_name', 'public_name', 'show_transaction_details'
    ]


class AccountTypeEvGroupViewSet(AbstractEvGroupWithObjectPermissionViewSet, CustomPaginationMixin):
    queryset = AccountType.objects.select_related(
        'master_user'
    ).prefetch_related(
        get_tag_prefetch(),
        *get_permissions_prefetch_lookups(
            (None, AccountType),
        )
    )
    serializer_class = AccountTypeSerializer
    pagination_class = api_settings.DEFAULT_PAGINATION_CLASS
    filter_class = AccountTypeFilterSet

    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter
    ]


# class AccountAttributeTypeFilterSet(FilterSet):
#     id = NoOpFilter()
#     user_code = CharFilter()
#     name = CharFilter()
#     short_name = CharFilter()
#     public_name = CharFilter()
#     value_type = AttributeTypeValueTypeFilter()
#     member = ObjectPermissionMemberFilter(object_permission_model=AccountAttributeType)
#     member_group = ObjectPermissionGroupFilter(object_permission_model=AccountAttributeType)
#     permission = ObjectPermissionPermissionFilter(object_permission_model=AccountAttributeType)
#
#     class Meta:
#         model = AccountAttributeType
#         fields = []
#
#
# class AccountAttributeTypeViewSet(AbstractAttributeTypeViewSet):
#     queryset = AccountAttributeType.objects.select_related(
#         'master_user'
#     ).prefetch_related(
#         'classifiers',
#         *get_permissions_prefetch_lookups(
#             (None, AccountAttributeType)
#         )
#     )
#     serializer_class = AccountAttributeTypeSerializer
#     # bulk_objects_permissions_serializer_class = AccountAttributeTypeBulkObjectPermissionSerializer
#     filter_class = AccountAttributeTypeFilterSet


class AccountAttributeTypeViewSet(GenericAttributeTypeViewSet):
    target_model = Account
    target_model_serializer = AccountSerializer


# class AccountClassifierFilterSet(FilterSet):
#     id = NoOpFilter()
#     name = CharFilter()
#     level = django_filters.NumberFilter()
#     attribute_type = ModelExtWithPermissionMultipleChoiceFilter(model=AccountAttributeType)
#
#     class Meta:
#         model = AccountClassifier
#         fields = []
#
#
# class AccountClassifierViewSet(AbstractClassifierViewSet):
#     queryset = AccountClassifier.objects
#     serializer_class = AccountClassifierNodeSerializer
#     filter_class = AccountClassifierFilterSet


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
    portfolio = ModelExtWithPermissionMultipleChoiceFilter(model=Portfolio, field_name='portfolios')
    tag = TagFilter(model=Account)
    member = ObjectPermissionMemberFilter(object_permission_model=Account)
    member_group = ObjectPermissionGroupFilter(object_permission_model=Account)
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
        get_tag_prefetch(),
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
        # TagFilterBackend,
    ]
    filter_class = AccountFilterSet
    ordering_fields = [
        'user_code', 'name', 'short_name', 'public_name', 'is_valid_for_all_portfolios',
        'type', 'type__user_code', 'type__name', 'type__short_name', 'type__public_name',
    ]


class AccountEvGroupViewSet(AbstractEvGroupWithObjectPermissionViewSet, CustomPaginationMixin):
    queryset = Account.objects.select_related(
        'master_user',
        'type',
    ).prefetch_related(
        'portfolios',
        get_attributes_prefetch(),
        get_tag_prefetch(),
        *get_permissions_prefetch_lookups(
            (None, Account),
            ('type', AccountType),
            ('portfolios', Portfolio),
            # ('attributes__attribute_type', AccountAttributeType),
        )
    )
    serializer_class = AccountSerializer
    pagination_class = api_settings.DEFAULT_PAGINATION_CLASS
    filter_class = AccountFilterSet

    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter
    ]
