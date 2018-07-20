from __future__ import unicode_literals

import django_filters

from django.db.models import Prefetch, FieldDoesNotExist
from rest_framework.filters import FilterSet
from rest_framework.viewsets import ModelViewSet

from poms.accounts.models import Account, AccountType
from poms.common.filters import CharFilter, ModelExtWithPermissionMultipleChoiceFilter, NoOpFilter, \
    ModelExtMultipleChoiceFilter, GroupsAttributeFilter, AttributeFilter

from poms.common.mixins import DestroyModelFakeMixin
from poms.common.pagination import CustomPaginationMixin
from poms.counterparties.models import Responsible, Counterparty, CounterpartyGroup, ResponsibleGroup
from poms.obj_attrs.models import GenericAttribute, GenericAttributeType
from poms.obj_attrs.utils import get_attributes_prefetch
from poms.obj_attrs.views import GenericAttributeTypeViewSet, \
    GenericClassifierViewSet
from poms.obj_perms.filters import ObjectPermissionMemberFilter, ObjectPermissionGroupFilter, \
    ObjectPermissionPermissionFilter
from poms.obj_perms.utils import get_permissions_prefetch_lookups
from poms.obj_perms.views import AbstractWithObjectPermissionViewSet, AbstractEvGroupWithObjectPermissionViewSet
from poms.portfolios.models import Portfolio
from poms.portfolios.serializers import PortfolioSerializer, PortfolioGroupSerializer
from poms.tags.filters import TagFilter
from poms.tags.utils import get_tag_prefetch
from poms.transactions.models import TransactionType, TransactionTypeGroup
from poms.users.filters import OwnerByMasterUserFilter

from rest_framework.response import Response

from rest_framework import viewsets, status
from rest_framework.settings import api_settings




# class PortfolioAttributeTypeFilterSet(FilterSet):
#     id = NoOpFilter()
#     user_code = CharFilter()
#     name = CharFilter()
#     short_name = CharFilter()
#     public_name = CharFilter()
#     value_type = AttributeTypeValueTypeFilter()
#     member = ObjectPermissionMemberFilter(object_permission_model=PortfolioAttributeType)
#     member_group = ObjectPermissionGroupFilter(object_permission_model=PortfolioAttributeType)
#     permission = ObjectPermissionPermissionFilter(object_permission_model=PortfolioAttributeType)
#
#     class Meta:
#         model = PortfolioAttributeType
#         fields = []


# class PortfolioAttributeTypeViewSet(AbstractAttributeTypeViewSet):
#     queryset = PortfolioAttributeType.objects.select_related(
#         'master_user'
#     ).prefetch_related(
#         'classifiers',
#         *get_permissions_prefetch_lookups(
#             (None, PortfolioAttributeType)
#         )
#     )
#     serializer_class = PortfolioAttributeTypeSerializer
#     filter_class = PortfolioAttributeTypeFilterSet


class PortfolioAttributeTypeViewSet(GenericAttributeTypeViewSet):
    target_model = Portfolio


# class PortfolioClassifierFilterSet(FilterSet):
#     id = NoOpFilter()
#     name = CharFilter()
#     level = django_filters.NumberFilter()
#     attribute_type = ModelExtWithPermissionMultipleChoiceFilter(model=PortfolioAttributeType)
#
#     class Meta:
#         model = PortfolioClassifier
#         fields = []
#
#
# class PortfolioClassifierViewSet(AbstractClassifierViewSet):
#     queryset = PortfolioClassifier.objects
#     serializer_class = PortfolioClassifierNodeSerializer
#     filter_class = PortfolioClassifierFilterSet


class PortfolioClassifierViewSet(GenericClassifierViewSet):
    target_model = Portfolio


class PortfolioFilterSet(FilterSet):
    id = NoOpFilter()
    is_deleted = django_filters.BooleanFilter()
    user_code = CharFilter()
    name = CharFilter()
    short_name = CharFilter()
    public_name = CharFilter()
    account = ModelExtWithPermissionMultipleChoiceFilter(model=Account, name='accounts')
    responsible = ModelExtWithPermissionMultipleChoiceFilter(model=Responsible, name='responsibles')
    counterparty = ModelExtWithPermissionMultipleChoiceFilter(model=Counterparty, name='counterparties')
    transaction_type = ModelExtWithPermissionMultipleChoiceFilter(model=TransactionType, name='transaction_types')
    tag = TagFilter(model=Portfolio)
    member = ObjectPermissionMemberFilter(object_permission_model=Portfolio)
    member_group = ObjectPermissionGroupFilter(object_permission_model=Portfolio)
    permission = ObjectPermissionPermissionFilter(object_permission_model=Portfolio)
    attribute_types = GroupsAttributeFilter()
    attribute_values = GroupsAttributeFilter()

    class Meta:
        model = Portfolio
        fields = []


class PortfolioViewSet(AbstractWithObjectPermissionViewSet):
    queryset = Portfolio.objects.select_related(
        'master_user',
    ).prefetch_related(
        Prefetch('accounts', queryset=Account.objects.select_related('type')),
        Prefetch('responsibles', queryset=Responsible.objects.select_related('group')),
        Prefetch('counterparties', queryset=Counterparty.objects.select_related('group')),
        Prefetch('transaction_types', queryset=TransactionType.objects.select_related('group')),
        get_attributes_prefetch(),
        get_tag_prefetch(),
        *get_permissions_prefetch_lookups(
            (None, Portfolio),
            ('accounts', Account),
            ('accounts__type', AccountType),
            ('counterparties', Counterparty),
            ('counterparties__group', CounterpartyGroup),
            ('responsibles', Responsible),
            ('responsibles__group', ResponsibleGroup),
            ('transaction_types', TransactionType),
            ('transaction_types__group', TransactionTypeGroup),
        )
    )
    # prefetch_permissions_for = (
    #     ('counterparties', Counterparty),
    #     ('transaction_types', TransactionType),
    #     ('accounts', Account),
    #     ('responsibles', Responsible),
    #     ('attributes__attribute_type', PortfolioAttributeType)
    # )
    serializer_class = PortfolioSerializer
    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter,
        GroupsAttributeFilter,
    ]
    filter_class = PortfolioFilterSet
    ordering_fields = [
        'user_code', 'name', 'short_name', 'public_name',
    ]


class PortfolioEvGroupViewSet(AbstractEvGroupWithObjectPermissionViewSet, CustomPaginationMixin):
    queryset = Portfolio.objects.select_related(
        'master_user',
    ).prefetch_related(
        get_attributes_prefetch()
    )

    serializer_class = PortfolioGroupSerializer
    pagination_class = api_settings.DEFAULT_PAGINATION_CLASS
    filter_class = PortfolioFilterSet

    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter
    ]
