from __future__ import unicode_literals

import django_filters
from django.db.models import Prefetch
from rest_framework.filters import FilterSet
from rest_framework.settings import api_settings

from poms.common.filters import CharFilter, NoOpFilter, ModelExtWithPermissionMultipleChoiceFilter, AttributeFilter, \
    GroupsAttributeFilter
from poms.common.pagination import CustomPaginationMixin
from poms.counterparties.models import Counterparty, Responsible, CounterpartyGroup, ResponsibleGroup
from poms.counterparties.serializers import CounterpartySerializer, ResponsibleSerializer, CounterpartyGroupSerializer, \
    ResponsibleGroupSerializer
from poms.obj_attrs.filters import AttributeTypeValueTypeFilter
from poms.obj_attrs.utils import get_attributes_prefetch
from poms.obj_attrs.views import AbstractAttributeTypeViewSet, AbstractClassifierViewSet, GenericAttributeTypeViewSet, \
    GenericClassifierViewSet
from poms.obj_perms.filters import ObjectPermissionMemberFilter, ObjectPermissionGroupFilter, \
    ObjectPermissionPermissionFilter
from poms.obj_perms.utils import get_permissions_prefetch_lookups
from poms.obj_perms.views import AbstractWithObjectPermissionViewSet, AbstractEvGroupWithObjectPermissionViewSet
from poms.portfolios.models import Portfolio
from poms.tags.filters import TagFilter
from poms.tags.utils import get_tag_prefetch
from poms.users.filters import OwnerByMasterUserFilter


# class CounterpartyAttributeTypeFilterSet(FilterSet):
#     id = NoOpFilter()
#     user_code = CharFilter()
#     name = CharFilter()
#     short_name = CharFilter()
#     public_name = CharFilter()
#     value_type = AttributeTypeValueTypeFilter()
#     member = ObjectPermissionMemberFilter(object_permission_model=CounterpartyAttributeType)
#     member_group = ObjectPermissionGroupFilter(object_permission_model=CounterpartyAttributeType)
#     permission = ObjectPermissionPermissionFilter(object_permission_model=CounterpartyAttributeType)
#
#     class Meta:
#         model = CounterpartyAttributeType
#         fields = []
#
#
# class CounterpartyAttributeTypeViewSet(AbstractAttributeTypeViewSet):
#     queryset = CounterpartyAttributeType.objects.select_related(
#         'master_user'
#     ).prefetch_related(
#         'classifiers',
#         *get_permissions_prefetch_lookups(
#             (None, CounterpartyAttributeType)
#         )
#     )
#     serializer_class = CounterpartyAttributeTypeSerializer
#     filter_class = CounterpartyAttributeTypeFilterSet


class CounterpartyAttributeTypeViewSet(GenericAttributeTypeViewSet):
    target_model = Counterparty


# class CounterpartyClassifierFilterSet(FilterSet):
#     id = NoOpFilter()
#     name = CharFilter()
#     level = django_filters.NumberFilter()
#     attribute_type = ModelExtWithPermissionMultipleChoiceFilter(model=CounterpartyAttributeType)
#
#     class Meta:
#         model = CounterpartyClassifier
#         fields = []
#
#
# class CounterpartyClassifierViewSet(AbstractClassifierViewSet):
#     queryset = CounterpartyClassifier.objects.select_related('attribute_type')
#     serializer_class = CounterpartyClassifierNodeSerializer
#     filter_class = CounterpartyClassifierFilterSet


class CounterpartyClassifierViewSet(GenericClassifierViewSet):
    target_model = Counterparty


class CounterpartyGroupFilterSet(FilterSet):
    id = NoOpFilter()
    is_deleted = django_filters.BooleanFilter()
    user_code = CharFilter()
    name = CharFilter()
    short_name = CharFilter()
    public_name = CharFilter()
    tag = TagFilter(model=CounterpartyGroup)
    member = ObjectPermissionMemberFilter(object_permission_model=CounterpartyGroup)
    member_group = ObjectPermissionGroupFilter(object_permission_model=CounterpartyGroup)
    permission = ObjectPermissionPermissionFilter(object_permission_model=CounterpartyGroup)

    class Meta:
        model = CounterpartyGroup
        fields = []


class CounterpartyGroupViewSet(AbstractWithObjectPermissionViewSet):
    queryset = CounterpartyGroup.objects.select_related(
        'master_user'
    ).prefetch_related(
        get_tag_prefetch(),
        *get_permissions_prefetch_lookups(
            (None, CounterpartyGroup),
        )
    )
    serializer_class = CounterpartyGroupSerializer
    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    filter_class = CounterpartyGroupFilterSet
    ordering_fields = [
        'user_code', 'name', 'short_name', 'public_name',
    ]

    def perform_destroy(self, instance):
        super(CounterpartyGroupViewSet, self).perform_destroy(instance)

        items_qs = Counterparty.objects.filter(master_user=instance.master_user, group=instance)
        default_group = CounterpartyGroup.objects.get(master_user=instance.master_user, user_code='-')

        items_qs.update(group=default_group)


class CounterpartyGroupEvGroupViewSet(AbstractEvGroupWithObjectPermissionViewSet, CustomPaginationMixin):
    queryset = CounterpartyGroup.objects.select_related(
        'master_user'
    ).prefetch_related(
        get_tag_prefetch(),
        *get_permissions_prefetch_lookups(
            (None, CounterpartyGroup),
        )
    )
    serializer_class = CounterpartyGroupSerializer
    pagination_class = api_settings.DEFAULT_PAGINATION_CLASS
    filter_class = CounterpartyGroupFilterSet

    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter
    ]

class CounterpartyFilterSet(FilterSet):
    id = NoOpFilter()
    is_deleted = django_filters.BooleanFilter()
    user_code = CharFilter()
    name = CharFilter()
    short_name = CharFilter()
    is_valid_for_all_portfolios = django_filters.BooleanFilter()
    group = ModelExtWithPermissionMultipleChoiceFilter(model=CounterpartyGroup)
    portfolio = ModelExtWithPermissionMultipleChoiceFilter(model=Portfolio, name='portfolios')
    tag = TagFilter(model=Counterparty)
    member = ObjectPermissionMemberFilter(object_permission_model=Counterparty)
    member_group = ObjectPermissionGroupFilter(object_permission_model=Counterparty)
    permission = ObjectPermissionPermissionFilter(object_permission_model=Counterparty)

    class Meta:
        model = Counterparty
        fields = []


class CounterpartyViewSet(AbstractWithObjectPermissionViewSet):
    queryset = Counterparty.objects.select_related(
        'master_user',
        'group',
    ).prefetch_related(
        'portfolios',
        # Prefetch('attributes', queryset=CounterpartyAttribute.objects.select_related('attribute_type', 'classifier')),
        get_attributes_prefetch(),
        get_tag_prefetch(),
        *get_permissions_prefetch_lookups(
            (None, Counterparty),
            ('group', CounterpartyGroup),
            ('portfolios', Portfolio),
            # ('attributes__attribute_type', CounterpartyAttributeType),
        )
    )
    serializer_class = CounterpartySerializer
    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter,
        GroupsAttributeFilter,
    ]
    filter_class = CounterpartyFilterSet
    ordering_fields = [
        'user_code', 'name', 'short_name', 'public_name',
        'group', 'group__user_code', 'group__name', 'group__short_name', 'group__public_name',
    ]


class CounterpartyEvGroupViewSet(AbstractEvGroupWithObjectPermissionViewSet, CustomPaginationMixin):
    queryset = Counterparty.objects.select_related(
        'master_user',
        'group',
    ).prefetch_related(
        'portfolios',
        # Prefetch('attributes', queryset=CounterpartyAttribute.objects.select_related('attribute_type', 'classifier')),
        get_attributes_prefetch(),
        get_tag_prefetch(),
        *get_permissions_prefetch_lookups(
            (None, Counterparty),
            ('group', CounterpartyGroup),
            ('portfolios', Portfolio),
            # ('attributes__attribute_type', CounterpartyAttributeType),
        )
    )
    serializer_class = CounterpartySerializer
    pagination_class = api_settings.DEFAULT_PAGINATION_CLASS
    filter_class = CounterpartyFilterSet

    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter
    ]


# Responsible ----


# class ResponsibleAttributeTypeFilterSet(FilterSet):
#     id = NoOpFilter()
#     user_code = CharFilter()
#     name = CharFilter()
#     short_name = CharFilter()
#     public_name = CharFilter()
#     value_type = AttributeTypeValueTypeFilter()
#     member = ObjectPermissionMemberFilter(object_permission_model=ResponsibleAttributeType)
#     member_group = ObjectPermissionGroupFilter(object_permission_model=ResponsibleAttributeType)
#     permission = ObjectPermissionPermissionFilter(object_permission_model=ResponsibleAttributeType)
#
#     class Meta:
#         model = ResponsibleAttributeType
#         fields = []
#
#
# class ResponsibleAttributeTypeViewSet(AbstractAttributeTypeViewSet):
#     queryset = ResponsibleAttributeType.objects.select_related(
#         'master_user'
#     ).prefetch_related(
#         'classifiers',
#         *get_permissions_prefetch_lookups(
#             (None, ResponsibleAttributeType)
#         )
#     )
#     serializer_class = ResponsibleAttributeTypeSerializer
#     filter_class = ResponsibleAttributeTypeFilterSet


class ResponsibleAttributeTypeViewSet(GenericAttributeTypeViewSet):
    target_model = Responsible


# class ResponsibleClassifierFilterSet(FilterSet):
#     id = NoOpFilter()
#     name = CharFilter()
#     level = django_filters.NumberFilter()
#     attribute_type = ModelExtWithPermissionMultipleChoiceFilter(model=ResponsibleAttributeType)
#
#     class Meta:
#         model = ResponsibleClassifier
#         fields = []
#
#
# class ResponsibleClassifierViewSet(AbstractClassifierViewSet):
#     queryset = ResponsibleClassifier.objects
#     serializer_class = ResponsibleClassifierNodeSerializer
#     filter_class = ResponsibleClassifierFilterSet


class ResponsibleClassifierViewSet(GenericClassifierViewSet):
    target_model = Responsible


class ResponsibleGroupFilterSet(FilterSet):
    id = NoOpFilter()
    is_deleted = django_filters.BooleanFilter()
    user_code = CharFilter()
    name = CharFilter()
    short_name = CharFilter()
    tag = TagFilter(model=ResponsibleGroup)
    member = ObjectPermissionMemberFilter(object_permission_model=ResponsibleGroup)
    member_group = ObjectPermissionGroupFilter(object_permission_model=ResponsibleGroup)
    permission = ObjectPermissionPermissionFilter(object_permission_model=ResponsibleGroup)

    class Meta:
        model = ResponsibleGroup
        fields = []


class ResponsibleGroupViewSet(AbstractWithObjectPermissionViewSet):
    queryset = ResponsibleGroup.objects.select_related(
        'master_user'
    ).prefetch_related(
        get_tag_prefetch(),
        *get_permissions_prefetch_lookups(
            (None, ResponsibleGroup),
        )
    )
    serializer_class = ResponsibleGroupSerializer
    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    filter_class = ResponsibleGroupFilterSet
    ordering_fields = [
        'user_code', 'name', 'short_name', 'public_name',
    ]

    def perform_destroy(self, instance):
        super(ResponsibleGroupViewSet, self).perform_destroy(instance)

        items_qs = Responsible.objects.filter(master_user=instance.master_user, group=instance)
        default_group = ResponsibleGroup.objects.get(master_user=instance.master_user, user_code='-')

        items_qs.update(group=default_group)


class ResponsibleGroupEvGroupViewSet(AbstractEvGroupWithObjectPermissionViewSet, CustomPaginationMixin):
    queryset = ResponsibleGroup.objects.select_related(
        'master_user'
    ).prefetch_related(
        get_tag_prefetch(),
        *get_permissions_prefetch_lookups(
            (None, ResponsibleGroup),
        )
    )
    serializer_class = ResponsibleGroupSerializer
    pagination_class = api_settings.DEFAULT_PAGINATION_CLASS
    filter_class = ResponsibleGroupFilterSet

    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter
    ]


class ResponsibleFilterSet(FilterSet):
    id = NoOpFilter()
    is_deleted = django_filters.BooleanFilter()
    user_code = CharFilter()
    name = CharFilter()
    short_name = CharFilter()
    public_name = CharFilter()
    is_valid_for_all_portfolios = django_filters.BooleanFilter()
    group = ModelExtWithPermissionMultipleChoiceFilter(model=CounterpartyGroup)
    portfolio = ModelExtWithPermissionMultipleChoiceFilter(model=Portfolio, name='portfolios')
    tag = TagFilter(model=Responsible)
    member = ObjectPermissionMemberFilter(object_permission_model=Responsible)
    member_group = ObjectPermissionGroupFilter(object_permission_model=Responsible)
    permission = ObjectPermissionPermissionFilter(object_permission_model=Responsible)

    class Meta:
        model = Responsible
        fields = []


class ResponsibleViewSet(AbstractWithObjectPermissionViewSet):
    queryset = Responsible.objects.select_related(
        'master_user',
        'group',
    ).prefetch_related(
        'portfolios',
        get_attributes_prefetch(),
        get_tag_prefetch(),
        # Prefetch('attributes', queryset=ResponsibleAttribute.objects.select_related('attribute_type', 'classifier')),
        *get_permissions_prefetch_lookups(
            (None, Responsible),
            ('group', ResponsibleGroup),
            ('portfolios', Portfolio),
            # ('attributes__attribute_type', ResponsibleAttributeType),
        )
    )
    # prefetch_permissions_for = (
    #     ('group', ResponsibleGroup),
    #     ('portfolios', Portfolio),
    #     ('attributes__attribute_type', ResponsibleAttributeType)
    # )
    serializer_class = ResponsibleSerializer
    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter,
        GroupsAttributeFilter,
    ]
    filter_class = ResponsibleFilterSet
    ordering_fields = [
        'user_code', 'name', 'short_name', 'public_name',
        'group', 'group__user_code', 'group__name', 'group__short_name', 'group__public_name',
    ]


class ResponsibleEvGroupViewSet(AbstractEvGroupWithObjectPermissionViewSet, CustomPaginationMixin):
    queryset = Responsible.objects.select_related(
        'master_user',
        'group',
    ).prefetch_related(
        'portfolios',
        get_attributes_prefetch(),
        get_tag_prefetch(),
        # Prefetch('attributes', queryset=ResponsibleAttribute.objects.select_related('attribute_type', 'classifier')),
        *get_permissions_prefetch_lookups(
            (None, Responsible),
            ('group', ResponsibleGroup),
            ('portfolios', Portfolio),
            # ('attributes__attribute_type', ResponsibleAttributeType),
        )
    )
    serializer_class = ResponsibleSerializer
    pagination_class = api_settings.DEFAULT_PAGINATION_CLASS
    filter_class = ResponsibleFilterSet

    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter
    ]
