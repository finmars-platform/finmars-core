from __future__ import unicode_literals

import django_filters

from django.db.models import Prefetch
from django_filters.rest_framework import FilterSet

from poms.accounts.models import Account, AccountType
from poms.common.filters import CharFilter, ModelExtWithPermissionMultipleChoiceFilter, NoOpFilter, \
    GroupsAttributeFilter, AttributeFilter, EntitySpecificFilter

from poms.common.pagination import CustomPaginationMixin
from poms.counterparties.models import Responsible, Counterparty, CounterpartyGroup, ResponsibleGroup
from poms.obj_attrs.utils import get_attributes_prefetch
from poms.obj_attrs.views import GenericAttributeTypeViewSet, \
    GenericClassifierViewSet
from poms.obj_perms.filters import ObjectPermissionMemberFilter, ObjectPermissionGroupFilter, \
    ObjectPermissionPermissionFilter
from poms.obj_perms.permissions import PomsConfigurationPermission
from poms.obj_perms.utils import get_permissions_prefetch_lookups
from poms.obj_perms.views import AbstractWithObjectPermissionViewSet, AbstractEvGroupWithObjectPermissionViewSet
from poms.portfolios.models import Portfolio
from poms.portfolios.serializers import PortfolioSerializer, PortfolioLightSerializer
from poms.tags.filters import TagFilter
from poms.tags.utils import get_tag_prefetch
from poms.transactions.models import TransactionType, TransactionTypeGroup
from poms.users.filters import OwnerByMasterUserFilter


from rest_framework.settings import api_settings


class PortfolioAttributeTypeViewSet(GenericAttributeTypeViewSet):
    target_model = Portfolio
    target_model_serializer = PortfolioSerializer

    permission_classes = GenericAttributeTypeViewSet.permission_classes + [
        PomsConfigurationPermission
    ]


class PortfolioClassifierViewSet(GenericClassifierViewSet):
    target_model = Portfolio


class PortfolioFilterSet(FilterSet):
    id = NoOpFilter()
    is_deleted = django_filters.BooleanFilter()
    user_code = CharFilter()
    name = CharFilter()
    short_name = CharFilter()
    public_name = CharFilter()
    account = ModelExtWithPermissionMultipleChoiceFilter(model=Account, field_name='accounts')
    responsible = ModelExtWithPermissionMultipleChoiceFilter(model=Responsible, field_name='responsibles')
    counterparty = ModelExtWithPermissionMultipleChoiceFilter(model=Counterparty, field_name='counterparties')
    transaction_type = ModelExtWithPermissionMultipleChoiceFilter(model=TransactionType, field_name='transaction_types')
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
    serializer_class = PortfolioSerializer
    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter,
        GroupsAttributeFilter,
        EntitySpecificFilter
    ]
    filter_class = PortfolioFilterSet
    ordering_fields = [
        'user_code', 'name', 'short_name', 'public_name',
    ]


class PortfolioLightFilterSet(FilterSet):
    id = NoOpFilter()
    is_deleted = django_filters.BooleanFilter()
    user_code = CharFilter()
    name = CharFilter()
    short_name = CharFilter()
    public_name = CharFilter()

    class Meta:
        model = Portfolio
        fields = []


class PortfolioLightViewSet(AbstractWithObjectPermissionViewSet):
    queryset = Portfolio.objects.select_related(
        'master_user',
    ).prefetch_related(
        *get_permissions_prefetch_lookups(
            (None, Portfolio),
        )
    )
    serializer_class = PortfolioLightSerializer
    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter
    ]
    filter_class = PortfolioLightFilterSet
    ordering_fields = [
        'user_code', 'name', 'short_name', 'public_name',
    ]


class PortfolioEvGroupViewSet(AbstractEvGroupWithObjectPermissionViewSet, CustomPaginationMixin):
    queryset = Portfolio.objects.select_related(
        'master_user',
    ).prefetch_related(
        get_attributes_prefetch()
    )

    serializer_class = PortfolioSerializer
    pagination_class = api_settings.DEFAULT_PAGINATION_CLASS
    filter_class = PortfolioFilterSet

    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter
    ]
