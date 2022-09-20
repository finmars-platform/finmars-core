from __future__ import unicode_literals

import django_filters
from django_filters.rest_framework import FilterSet

from rest_framework.settings import api_settings

from poms.common.filters import CharFilter, ModelExtWithPermissionMultipleChoiceFilter, NoOpFilter, AttributeFilter, \
    GroupsAttributeFilter, EntitySpecificFilter
from poms.common.pagination import CustomPaginationMixin
from poms.obj_attrs.views import GenericAttributeTypeViewSet
from poms.obj_perms.filters import ObjectPermissionMemberFilter, ObjectPermissionGroupFilter, \
    ObjectPermissionPermissionFilter
from poms.obj_perms.permissions import PomsConfigurationPermission
from poms.obj_perms.utils import get_permissions_prefetch_lookups
from poms.obj_perms.views import AbstractWithObjectPermissionViewSet, AbstractEvGroupWithObjectPermissionViewSet
from poms.strategies.models import Strategy1Group, Strategy1Subgroup, Strategy1, Strategy2Group, Strategy2Subgroup, \
    Strategy2, Strategy3Group, Strategy3Subgroup, Strategy3
from poms.strategies.serializers import Strategy1GroupSerializer, Strategy1Serializer, Strategy2GroupSerializer, \
    Strategy2SubgroupSerializer, Strategy2Serializer, Strategy1SubgroupSerializer, Strategy3GroupSerializer, \
    Strategy3SubgroupSerializer, Strategy3Serializer, Strategy1LightSerializer, Strategy2LightSerializer, \
    Strategy3LightSerializer, Strategy1EvSerializer, Strategy2EvSerializer, Strategy3EvSerializer
from poms.users.filters import OwnerByMasterUserFilter
from poms.obj_attrs.utils import get_attributes_prefetch


class Strategy1GroupFilterSet(FilterSet):
    id = NoOpFilter()
    is_deleted = django_filters.BooleanFilter()
    user_code = CharFilter()
    name = CharFilter()
    short_name = CharFilter()
    public_name = CharFilter()
    member = ObjectPermissionMemberFilter(object_permission_model=Strategy1Group)
    member_group = ObjectPermissionGroupFilter(object_permission_model=Strategy1Group)
    permission = ObjectPermissionPermissionFilter(object_permission_model=Strategy1Group)

    class Meta:
        model = Strategy1Group
        fields = []


class Strategy1GroupViewSet(AbstractWithObjectPermissionViewSet):
    queryset = Strategy1Group.objects.select_related(
        'master_user'
    ).prefetch_related(
        *get_permissions_prefetch_lookups(
            (None, Strategy1Group),
        )
    )
    serializer_class = Strategy1GroupSerializer
    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter,
        GroupsAttributeFilter,
    ]
    filter_class = Strategy1GroupFilterSet
    ordering_fields = [
        'user_code', 'name', 'short_name', 'public_name',
    ]


class Strategy1GroupEvGroupViewSet(AbstractEvGroupWithObjectPermissionViewSet, CustomPaginationMixin):
    queryset = Strategy1Group.objects.select_related(
        'master_user'
    ).prefetch_related(
        *get_permissions_prefetch_lookups(
            (None, Strategy1Group),
        )
    )
    serializer_class = Strategy1GroupSerializer
    pagination_class = api_settings.DEFAULT_PAGINATION_CLASS
    filter_class = Strategy1GroupFilterSet

    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter
    ]


class Strategy1SubgroupFilterSet(FilterSet):
    id = NoOpFilter()
    is_deleted = django_filters.BooleanFilter()
    user_code = CharFilter()
    name = CharFilter()
    short_name = CharFilter()
    public_name = CharFilter()
    group = ModelExtWithPermissionMultipleChoiceFilter(model=Strategy1Group)
    member = ObjectPermissionMemberFilter(object_permission_model=Strategy1Subgroup)
    member_group = ObjectPermissionGroupFilter(object_permission_model=Strategy1Subgroup)
    permission = ObjectPermissionPermissionFilter(object_permission_model=Strategy1Subgroup)

    class Meta:
        model = Strategy1Subgroup
        fields = []


class Strategy1SubgroupViewSet(AbstractWithObjectPermissionViewSet):
    queryset = Strategy1Subgroup.objects.select_related(
        'master_user',
        'group'
    ).prefetch_related(
        *get_permissions_prefetch_lookups(
            (None, Strategy1Subgroup),
            ('group', Strategy1Group),
        )
    )
    # prefetch_permissions_for = [
    #     'group'
    # ]
    serializer_class = Strategy1SubgroupSerializer
    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter,
        GroupsAttributeFilter,
    ]
    filter_class = Strategy1SubgroupFilterSet
    ordering_fields = [
        'user_code', 'name', 'short_name', 'public_name',
        'group', 'group__user_code', 'group__name', 'group__short_name', 'group__public_name',
    ]


class Strategy1SubgroupEvGroupViewSet(AbstractEvGroupWithObjectPermissionViewSet, CustomPaginationMixin):
    queryset = Strategy1Subgroup.objects.select_related(
        'master_user',
        'group'
    ).prefetch_related(
        *get_permissions_prefetch_lookups(
            (None, Strategy1Subgroup),
            ('group', Strategy1Group),
        )
    )
    serializer_class = Strategy1SubgroupSerializer
    pagination_class = api_settings.DEFAULT_PAGINATION_CLASS
    filter_class = Strategy1SubgroupFilterSet

    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter
    ]


class Strategy1FilterSet(FilterSet):
    id = NoOpFilter()
    is_deleted = django_filters.BooleanFilter()
    user_code = CharFilter()
    name = CharFilter()
    short_name = CharFilter()
    public_name = CharFilter()
    subgroup__group = ModelExtWithPermissionMultipleChoiceFilter(model=Strategy1Group)
    subgroup = ModelExtWithPermissionMultipleChoiceFilter(model=Strategy1Subgroup)
    member = ObjectPermissionMemberFilter(object_permission_model=Strategy1)
    member_group = ObjectPermissionGroupFilter(object_permission_model=Strategy1)
    permission = ObjectPermissionPermissionFilter(object_permission_model=Strategy1)

    class Meta:
        model = Strategy1
        fields = []


class Strategy1AttributeTypeViewSet(GenericAttributeTypeViewSet):
    target_model = Strategy1
    target_model_serializer = Strategy1Serializer

    permission_classes = GenericAttributeTypeViewSet.permission_classes + [
        PomsConfigurationPermission
    ]


class Strategy1ViewSet(AbstractWithObjectPermissionViewSet):
    queryset = Strategy1.objects.select_related(
        'master_user',
        'subgroup',
        'subgroup__group'
    ).prefetch_related(
        get_attributes_prefetch(),
        *get_permissions_prefetch_lookups(
            (None, Strategy1),
            ('subgroup', Strategy1Subgroup),
            ('subgroup__group', Strategy1Group),
        )
    )
    # prefetch_permissions_for = [
    #     'subgroup', 'subgroup__group'
    # ]
    serializer_class = Strategy1Serializer
    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter,
        GroupsAttributeFilter,
        EntitySpecificFilter
    ]
    filter_class = Strategy1FilterSet
    ordering_fields = [
        'user_code', 'name', 'short_name', 'public_name',
        'subgroup__group', 'subgroup__group__user_code', 'subgroup__group__name', 'subgroup__group__short_name',
        'subgroup__group__public_name',
        'subgroup', 'subgroup__user_code', 'subgroup__name', 'subgroup__short_name', 'subgroup__public_name',
    ]


class Strategy1EvFilterSet(FilterSet):
    id = NoOpFilter()
    is_deleted = django_filters.BooleanFilter()
    user_code = CharFilter()
    name = CharFilter()
    short_name = CharFilter()
    public_name = CharFilter()
    subgroup__group = ModelExtWithPermissionMultipleChoiceFilter(model=Strategy1Group)
    subgroup = ModelExtWithPermissionMultipleChoiceFilter(model=Strategy1Subgroup)
    member = ObjectPermissionMemberFilter(object_permission_model=Strategy1)
    member_group = ObjectPermissionGroupFilter(object_permission_model=Strategy1)
    permission = ObjectPermissionPermissionFilter(object_permission_model=Strategy1)

    class Meta:
        model = Strategy1
        fields = []


class Strategy1EvViewSet(AbstractWithObjectPermissionViewSet):
    queryset = Strategy1.objects.select_related(
        'master_user',
        'subgroup',
        'subgroup__group'
    ).prefetch_related(
        get_attributes_prefetch(),
        *get_permissions_prefetch_lookups(
            (None, Strategy1),
            ('subgroup', Strategy1Subgroup),
            ('subgroup__group', Strategy1Group),
        )
    )
    serializer_class = Strategy1EvSerializer
    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter,
        GroupsAttributeFilter,
        EntitySpecificFilter
    ]
    filter_class = Strategy1EvFilterSet
    ordering_fields = [
        'user_code', 'name', 'short_name', 'public_name',
        'subgroup__group', 'subgroup__group__user_code', 'subgroup__group__name', 'subgroup__group__short_name',
        'subgroup__group__public_name',
        'subgroup', 'subgroup__user_code', 'subgroup__name', 'subgroup__short_name', 'subgroup__public_name',
    ]


class Strategy1LightFilterSet(FilterSet):
    id = NoOpFilter()
    is_deleted = django_filters.BooleanFilter()
    user_code = CharFilter()
    name = CharFilter()
    short_name = CharFilter()
    public_name = CharFilter()

    class Meta:
        model = Strategy1
        fields = []


class Strategy1LightViewSet(AbstractWithObjectPermissionViewSet):
    queryset = Strategy1.objects.select_related(
        'master_user'
    ).prefetch_related(
        *get_permissions_prefetch_lookups(
            (None, Strategy1)
        )
    )
    serializer_class = Strategy1LightSerializer
    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    filter_class = Strategy1LightFilterSet
    ordering_fields = [
        'user_code', 'name', 'short_name', 'public_name'
    ]


class Strategy1EvGroupViewSet(AbstractEvGroupWithObjectPermissionViewSet, CustomPaginationMixin):
    queryset = Strategy1.objects.select_related(
        'master_user',
        'subgroup',
        'subgroup__group'
    ).prefetch_related(
        *get_permissions_prefetch_lookups(
            (None, Strategy1),
            ('subgroup', Strategy1Subgroup),
            ('subgroup__group', Strategy1Group),
        )
    )
    serializer_class = Strategy1Serializer
    pagination_class = api_settings.DEFAULT_PAGINATION_CLASS
    filter_class = Strategy1FilterSet

    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter
    ]


# 2


class Strategy2GroupFilterSet(Strategy1GroupFilterSet):
    member = ObjectPermissionMemberFilter(object_permission_model=Strategy2Group)
    member_group = ObjectPermissionGroupFilter(object_permission_model=Strategy2Group)
    permission = ObjectPermissionPermissionFilter(object_permission_model=Strategy2Group)

    class Meta(Strategy1GroupFilterSet.Meta):
        model = Strategy2Group


class Strategy2GroupViewSet(Strategy1GroupViewSet):
    queryset = Strategy2Group.objects.select_related(
        'master_user'
    ).prefetch_related(
        *get_permissions_prefetch_lookups(
            (None, Strategy2Group),
        )
    )
    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter,
        GroupsAttributeFilter,
    ]
    serializer_class = Strategy2GroupSerializer
    filter_class = Strategy2GroupFilterSet


class Strategy2GroupEvGroupViewSet(AbstractEvGroupWithObjectPermissionViewSet, CustomPaginationMixin):
    queryset = Strategy2Group.objects.select_related(
        'master_user'
    ).prefetch_related(
        *get_permissions_prefetch_lookups(
            (None, Strategy2Group),
        )
    )
    serializer_class = Strategy2GroupSerializer
    pagination_class = api_settings.DEFAULT_PAGINATION_CLASS
    filter_class = Strategy2GroupFilterSet

    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter
    ]


class Strategy2SubgroupFilterSet(Strategy1SubgroupFilterSet):
    group = ModelExtWithPermissionMultipleChoiceFilter(model=Strategy2Group)
    member = ObjectPermissionMemberFilter(object_permission_model=Strategy2Subgroup)
    member_group = ObjectPermissionGroupFilter(object_permission_model=Strategy2Subgroup)
    permission = ObjectPermissionPermissionFilter(object_permission_model=Strategy2Subgroup)

    class Meta(Strategy1SubgroupFilterSet.Meta):
        model = Strategy2Subgroup


class Strategy2SubgroupViewSet(Strategy1SubgroupViewSet):
    queryset = Strategy2Subgroup.objects.select_related(
        'master_user',
        'group'
    ).prefetch_related(
        *get_permissions_prefetch_lookups(
            (None, Strategy2Subgroup),
            ('group', Strategy2Group),
        )
    )
    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter,
        GroupsAttributeFilter,
    ]
    serializer_class = Strategy2SubgroupSerializer
    filter_class = Strategy2SubgroupFilterSet


class Strategy2SubgroupEvGroupViewSet(AbstractEvGroupWithObjectPermissionViewSet, CustomPaginationMixin):
    queryset = Strategy2Subgroup.objects.select_related(
        'master_user',
        'group'
    ).prefetch_related(
        *get_permissions_prefetch_lookups(
            (None, Strategy2Subgroup),
            ('group', Strategy2Group),
        )
    )
    serializer_class = Strategy2SubgroupSerializer
    pagination_class = api_settings.DEFAULT_PAGINATION_CLASS
    filter_class = Strategy2SubgroupFilterSet

    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter
    ]


class Strategy2AttributeTypeViewSet(GenericAttributeTypeViewSet):
    target_model = Strategy2
    target_model_serializer = Strategy2Serializer

    permission_classes = GenericAttributeTypeViewSet.permission_classes + [
        PomsConfigurationPermission
    ]


class Strategy2FilterSet(Strategy1FilterSet):
    subgroup__group = ModelExtWithPermissionMultipleChoiceFilter(model=Strategy2Group)
    subgroup = ModelExtWithPermissionMultipleChoiceFilter(model=Strategy2Subgroup)
    member = ObjectPermissionMemberFilter(object_permission_model=Strategy2)
    member_group = ObjectPermissionGroupFilter(object_permission_model=Strategy2)
    permission = ObjectPermissionPermissionFilter(object_permission_model=Strategy2)

    class Meta:
        model = Strategy2
        fields = []


class Strategy2ViewSet(Strategy1ViewSet):
    queryset = Strategy2.objects.select_related(
        'master_user',
        'subgroup',
        'subgroup__group'
    ).prefetch_related(
        get_attributes_prefetch(),
        *get_permissions_prefetch_lookups(
            (None, Strategy2),
            ('subgroup', Strategy2Subgroup),
            ('subgroup__group', Strategy2Group),
        )
    )
    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter,
        GroupsAttributeFilter,
        EntitySpecificFilter
    ]
    serializer_class = Strategy2Serializer
    filter_class = Strategy2FilterSet


class Strategy2EvFilterSet(Strategy1FilterSet):
    subgroup__group = ModelExtWithPermissionMultipleChoiceFilter(model=Strategy2Group)
    subgroup = ModelExtWithPermissionMultipleChoiceFilter(model=Strategy2Subgroup)
    member = ObjectPermissionMemberFilter(object_permission_model=Strategy2)
    member_group = ObjectPermissionGroupFilter(object_permission_model=Strategy2)
    permission = ObjectPermissionPermissionFilter(object_permission_model=Strategy2)

    class Meta:
        model = Strategy2
        fields = []


class Strategy2EvViewSet(Strategy1ViewSet):
    queryset = Strategy2.objects.select_related(
        'master_user',
        'subgroup',
        'subgroup__group'
    ).prefetch_related(
        get_attributes_prefetch(),
        *get_permissions_prefetch_lookups(
            (None, Strategy2),
            ('subgroup', Strategy2Subgroup),
            ('subgroup__group', Strategy2Group),
        )
    )
    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter,
        GroupsAttributeFilter,
        EntitySpecificFilter
    ]
    serializer_class = Strategy2EvSerializer
    filter_class = Strategy2EvFilterSet


class Strategy2LightFilterSet(FilterSet):
    id = NoOpFilter()
    is_deleted = django_filters.BooleanFilter()
    user_code = CharFilter()
    name = CharFilter()
    short_name = CharFilter()
    public_name = CharFilter()

    class Meta:
        model = Strategy2
        fields = []


class Strategy2LightViewSet(Strategy1ViewSet):
    queryset = Strategy2.objects.select_related(
        'master_user',
    ).prefetch_related(
        *get_permissions_prefetch_lookups(
            (None, Strategy2)
        )
    )
    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter
    ]
    serializer_class = Strategy2LightSerializer
    filter_class = Strategy2LightFilterSet


class Strategy2EvGroupViewSet(AbstractEvGroupWithObjectPermissionViewSet, CustomPaginationMixin):
    queryset = Strategy2.objects.select_related(
        'master_user',
        'subgroup',
        'subgroup__group'
    ).prefetch_related(
        *get_permissions_prefetch_lookups(
            (None, Strategy2),
            ('subgroup', Strategy2Subgroup),
            ('subgroup__group', Strategy2Group),
        )
    )
    serializer_class = Strategy2Serializer
    pagination_class = api_settings.DEFAULT_PAGINATION_CLASS
    filter_class = Strategy2FilterSet

    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter
    ]


# 3


class Strategy3GroupFilterSet(Strategy1GroupFilterSet):
    member = ObjectPermissionMemberFilter(object_permission_model=Strategy3Group)
    member_group = ObjectPermissionGroupFilter(object_permission_model=Strategy3Group)
    permission = ObjectPermissionPermissionFilter(object_permission_model=Strategy3Group)

    class Meta(Strategy1GroupFilterSet.Meta):
        model = Strategy3Group


class Strategy3GroupViewSet(Strategy1GroupViewSet):
    queryset = Strategy3Group.objects.prefetch_related('master_user').prefetch_related(
        *get_permissions_prefetch_lookups(
            (None, Strategy3Group),
        )
    )
    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter,
        GroupsAttributeFilter,
    ]
    serializer_class = Strategy3GroupSerializer
    filter_class = Strategy3GroupFilterSet


class Strategy3GroupEvGroupViewSet(AbstractEvGroupWithObjectPermissionViewSet, CustomPaginationMixin):
    queryset = Strategy3Group.objects.prefetch_related('master_user').prefetch_related(
        *get_permissions_prefetch_lookups(
            (None, Strategy3Group),
        )
    )
    serializer_class = Strategy3GroupSerializer
    pagination_class = api_settings.DEFAULT_PAGINATION_CLASS
    filter_class = Strategy3GroupFilterSet

    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter
    ]


class Strategy3SubgroupFilterSet(Strategy1SubgroupFilterSet):
    group = ModelExtWithPermissionMultipleChoiceFilter(model=Strategy3Group)
    member = ObjectPermissionMemberFilter(object_permission_model=Strategy3Subgroup)
    member_group = ObjectPermissionGroupFilter(object_permission_model=Strategy3Subgroup)
    permission = ObjectPermissionPermissionFilter(object_permission_model=Strategy3Subgroup)

    class Meta(Strategy1SubgroupFilterSet.Meta):
        model = Strategy3Subgroup


class Strategy3SubgroupViewSet(Strategy1SubgroupViewSet):
    queryset = Strategy3Subgroup.objects.select_related(
        'master_user',
        'group'
    ).prefetch_related(
        *get_permissions_prefetch_lookups(
            (None, Strategy3Subgroup),
            ('group', Strategy3Group),
        )
    )
    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter,
        GroupsAttributeFilter,
    ]
    serializer_class = Strategy3SubgroupSerializer
    filter_class = Strategy3SubgroupFilterSet


class Strategy3SubgroupEvGroupViewSet(AbstractEvGroupWithObjectPermissionViewSet, CustomPaginationMixin):
    queryset = Strategy3Subgroup.objects.select_related(
        'master_user',
        'group'
    ).prefetch_related(
        *get_permissions_prefetch_lookups(
            (None, Strategy3Subgroup),
            ('group', Strategy3Group),
        )
    )
    serializer_class = Strategy3SubgroupSerializer
    pagination_class = api_settings.DEFAULT_PAGINATION_CLASS
    filter_class = Strategy3SubgroupFilterSet

    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter
    ]


class Strategy3AttributeTypeViewSet(GenericAttributeTypeViewSet):
    target_model = Strategy3
    target_model_serializer = Strategy3Serializer

    permission_classes = GenericAttributeTypeViewSet.permission_classes + [
        PomsConfigurationPermission
    ]


class Strategy3FilterSet(Strategy1FilterSet):
    subgroup__group = ModelExtWithPermissionMultipleChoiceFilter(model=Strategy3Group)
    subgroup = ModelExtWithPermissionMultipleChoiceFilter(model=Strategy3Subgroup)
    member = ObjectPermissionMemberFilter(object_permission_model=Strategy3)
    member_group = ObjectPermissionGroupFilter(object_permission_model=Strategy3)
    permission = ObjectPermissionPermissionFilter(object_permission_model=Strategy3)

    class Meta:
        model = Strategy3
        fields = []


class Strategy3ViewSet(Strategy1ViewSet):
    queryset = Strategy3.objects.select_related(
        'master_user',
        'subgroup',
        'subgroup__group'
    ).prefetch_related(
        get_attributes_prefetch(),
        *get_permissions_prefetch_lookups(
            (None, Strategy3),
            ('subgroup', Strategy3Subgroup),
            ('subgroup__group', Strategy3Group),
        )
    )
    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter,
        GroupsAttributeFilter,
        EntitySpecificFilter
    ]
    serializer_class = Strategy3Serializer
    filter_class = Strategy3FilterSet


class Strategy3EvFilterSet(Strategy1FilterSet):
    subgroup__group = ModelExtWithPermissionMultipleChoiceFilter(model=Strategy3Group)
    subgroup = ModelExtWithPermissionMultipleChoiceFilter(model=Strategy3Subgroup)
    member = ObjectPermissionMemberFilter(object_permission_model=Strategy3)
    member_group = ObjectPermissionGroupFilter(object_permission_model=Strategy3)
    permission = ObjectPermissionPermissionFilter(object_permission_model=Strategy3)

    class Meta:
        model = Strategy3
        fields = []


class Strategy3EvViewSet(Strategy1ViewSet):
    queryset = Strategy3.objects.select_related(
        'master_user',
        'subgroup',
        'subgroup__group'
    ).prefetch_related(
        get_attributes_prefetch(),
        *get_permissions_prefetch_lookups(
            (None, Strategy3),
            ('subgroup', Strategy3Subgroup),
            ('subgroup__group', Strategy3Group),
        )
    )
    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter,
        GroupsAttributeFilter,
        EntitySpecificFilter
    ]
    serializer_class = Strategy3EvSerializer
    filter_class = Strategy3EvFilterSet



class Strategy3LightFilterSet(FilterSet):
    id = NoOpFilter()
    is_deleted = django_filters.BooleanFilter()
    user_code = CharFilter()
    name = CharFilter()
    short_name = CharFilter()
    public_name = CharFilter()

    class Meta:
        model = Strategy3
        fields = []


class Strategy3LightViewSet(Strategy1ViewSet):
    queryset = Strategy3.objects.select_related(
        'master_user'
    ).prefetch_related(
        *get_permissions_prefetch_lookups(
            (None, Strategy3),
        )
    )
    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter
    ]
    serializer_class = Strategy3LightSerializer
    filter_class = Strategy3LightFilterSet


class Strategy3EvGroupViewSet(AbstractEvGroupWithObjectPermissionViewSet, CustomPaginationMixin):
    queryset = Strategy3.objects.select_related(
        'master_user',
        'subgroup',
        'subgroup__group'
    ).prefetch_related(
        *get_permissions_prefetch_lookups(
            (None, Strategy3),
            ('subgroup', Strategy3Subgroup),
            ('subgroup__group', Strategy3Group),
        )
    )
    serializer_class = Strategy3Serializer
    pagination_class = api_settings.DEFAULT_PAGINATION_CLASS
    filter_class = Strategy3FilterSet

    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter
    ]
