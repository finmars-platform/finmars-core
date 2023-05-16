from __future__ import unicode_literals

import django_filters
from django_filters.rest_framework import FilterSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.decorators import action
from poms.common.filters import CharFilter, NoOpFilter, AttributeFilter, \
    GroupsAttributeFilter, EntitySpecificFilter
from poms.common.pagination import CustomPaginationMixin
from poms.common.utils import get_list_of_entity_attributes
from poms.common.views import AbstractModelViewSet
from poms.obj_attrs.utils import get_attributes_prefetch
from poms.obj_attrs.views import GenericAttributeTypeViewSet
from poms.strategies.models import Strategy1Group, Strategy1Subgroup, Strategy1, Strategy2Group, Strategy2Subgroup, \
    Strategy2, Strategy3Group, Strategy3Subgroup, Strategy3
from poms.strategies.serializers import Strategy1GroupSerializer, Strategy1Serializer, Strategy2GroupSerializer, \
    Strategy2SubgroupSerializer, Strategy2Serializer, Strategy1SubgroupSerializer, Strategy3GroupSerializer, \
    Strategy3SubgroupSerializer, Strategy3Serializer, Strategy1LightSerializer, Strategy2LightSerializer, \
    Strategy3LightSerializer
from poms.users.filters import OwnerByMasterUserFilter


class Strategy1GroupFilterSet(FilterSet):
    id = NoOpFilter()
    is_deleted = django_filters.BooleanFilter()
    user_code = CharFilter()
    name = CharFilter()
    short_name = CharFilter()
    public_name = CharFilter()

    class Meta:
        model = Strategy1Group
        fields = []


class Strategy1GroupViewSet(AbstractModelViewSet):
    queryset = Strategy1Group.objects.select_related(
        'master_user'
    )
    serializer_class = Strategy1GroupSerializer
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter,
        GroupsAttributeFilter,
    ]
    filter_class = Strategy1GroupFilterSet
    ordering_fields = [
        'user_code', 'name', 'short_name', 'public_name',
    ]

class Strategy1SubgroupFilterSet(FilterSet):
    id = NoOpFilter()
    is_deleted = django_filters.BooleanFilter()
    user_code = CharFilter()
    name = CharFilter()
    short_name = CharFilter()
    public_name = CharFilter()

    class Meta:
        model = Strategy1Subgroup
        fields = []


class Strategy1SubgroupViewSet(AbstractModelViewSet):
    queryset = Strategy1Subgroup.objects.select_related(
        'master_user',
        'group'
    )
    # prefetch_permissions_for = [
    #     'group'
    # ]
    serializer_class = Strategy1SubgroupSerializer
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter,
        GroupsAttributeFilter,
    ]
    filter_class = Strategy1SubgroupFilterSet
    ordering_fields = [
        'user_code', 'name', 'short_name', 'public_name',
        'group', 'group__user_code', 'group__name', 'group__short_name', 'group__public_name',
    ]

class Strategy1FilterSet(FilterSet):
    id = NoOpFilter()
    is_deleted = django_filters.BooleanFilter()
    user_code = CharFilter()
    name = CharFilter()
    short_name = CharFilter()
    public_name = CharFilter()

    class Meta:
        model = Strategy1
        fields = []


class Strategy1AttributeTypeViewSet(GenericAttributeTypeViewSet):
    target_model = Strategy1
    target_model_serializer = Strategy1Serializer

    permission_classes = GenericAttributeTypeViewSet.permission_classes + [

    ]


class Strategy1ViewSet(AbstractModelViewSet):
    queryset = Strategy1.objects.select_related(
        'master_user',
        'subgroup',
        'subgroup__group'
    ).prefetch_related(
        get_attributes_prefetch()
    )
    # prefetch_permissions_for = [
    #     'subgroup', 'subgroup__group'
    # ]
    serializer_class = Strategy1Serializer
    filter_backends = AbstractModelViewSet.filter_backends + [
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

    @action(detail=False, methods=['get'], url_path='light', serializer_class=Strategy1LightSerializer)
    def list_light(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginator.post_paginate_queryset(queryset, request)
        serializer = self.get_serializer(page, many=True)

        result = self.get_paginated_response(serializer.data)

        return result

    @action(detail=False, methods=['get'], url_path='attributes')
    def list_attributes(self, request, *args, **kwargs):
        items = [
            {
                "key": "name",
                "name": "Name",
                "value_type": 10
            },
            {
                "key": "short_name",
                "name": "Short name",
                "value_type": 10
            },
            {
                "key": "user_code",
                "name": "User code",
                "value_type": 10
            },
            {
                "key": "public_name",
                "name": "Public name",
                "value_type": 10,
            },
            {
                "key": "notes",
                "name": "Notes",
                "value_type": 10
            },
            {
                "key": "subgroup",
                "name": "Group",
                "value_type": "field",
                "value_entity": "strategy-1-subgroup",
                "value_content_type": "strategies.strategy1subgroup",
                "code": "user_code"
            }
        ]

        items = items + get_list_of_entity_attributes('strategies.strategy1')

        result = {
            "count": len(items),
            "next": None,
            "previous": None,
            "results": items
        }

        return Response(result)

# 2
class Strategy2GroupFilterSet(Strategy1GroupFilterSet):

    class Meta(Strategy1GroupFilterSet.Meta):
        model = Strategy2Group


class Strategy2GroupViewSet(Strategy1GroupViewSet):
    queryset = Strategy2Group.objects.select_related(
        'master_user'
    )
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter,
        GroupsAttributeFilter,
    ]
    serializer_class = Strategy2GroupSerializer
    filter_class = Strategy2GroupFilterSet


class Strategy2SubgroupFilterSet(Strategy1SubgroupFilterSet):

    class Meta(Strategy1SubgroupFilterSet.Meta):
        model = Strategy2Subgroup


class Strategy2SubgroupViewSet(Strategy1SubgroupViewSet):
    queryset = Strategy2Subgroup.objects.select_related(
        'master_user',
        'group'
    )
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter,
        GroupsAttributeFilter,
    ]
    serializer_class = Strategy2SubgroupSerializer
    filter_class = Strategy2SubgroupFilterSet

class Strategy2AttributeTypeViewSet(GenericAttributeTypeViewSet):
    target_model = Strategy2
    target_model_serializer = Strategy2Serializer

    permission_classes = GenericAttributeTypeViewSet.permission_classes + [

    ]


class Strategy2FilterSet(Strategy1FilterSet):

    class Meta:
        model = Strategy2
        fields = []


class Strategy2ViewSet(Strategy1ViewSet):
    queryset = Strategy2.objects.select_related(
        'master_user',
        'subgroup',
        'subgroup__group'
    ).prefetch_related(
        get_attributes_prefetch()
    )
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter,
        GroupsAttributeFilter,
        EntitySpecificFilter
    ]
    serializer_class = Strategy2Serializer
    filter_class = Strategy2FilterSet

    @action(detail=False, methods=['get'], url_path='light', serializer_class=Strategy2LightSerializer)
    def list_light(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginator.post_paginate_queryset(queryset, request)
        serializer = self.get_serializer(page, many=True)

        result = self.get_paginated_response(serializer.data)

        return result

    @action(detail=False, methods=['get'], url_path='attributes')
    def list_attributes(self, request, *args, **kwargs):
        items = [
            {
                "key": "name",
                "name": "Name",
                "value_type": 10
            },
            {
                "key": "short_name",
                "name": "Short name",
                "value_type": 10
            },
            {
                "key": "user_code",
                "name": "User code",
                "value_type": 10
            },
            {
                "key": "public_name",
                "name": "Public name",
                "value_type": 10,
            },
            {
                "key": "notes",
                "name": "Notes",
                "value_type": 10
            },
            {
                "key": "subgroup",
                "name": "Group",
                "value_type": "field",
                "value_entity": "strategy-2-subgroup",
                "value_content_type": "strategies.strategy2subgroup",
                "code": "user_code"
            }
        ]

        items = items + get_list_of_entity_attributes('strategies.strategy2')

        result = {
            "count": len(items),
            "next": None,
            "previous": None,
            "results": items
        }

        return Response(result)

# 3

class Strategy3GroupFilterSet(Strategy1GroupFilterSet):

    class Meta(Strategy1GroupFilterSet.Meta):
        model = Strategy3Group


class Strategy3GroupViewSet(Strategy1GroupViewSet):
    queryset = Strategy3Group.objects.prefetch_related('master_user')
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter,
        GroupsAttributeFilter,
    ]
    serializer_class = Strategy3GroupSerializer
    filter_class = Strategy3GroupFilterSet


class Strategy3SubgroupFilterSet(Strategy1SubgroupFilterSet):

    class Meta(Strategy1SubgroupFilterSet.Meta):
        model = Strategy3Subgroup


class Strategy3SubgroupViewSet(Strategy1SubgroupViewSet):
    queryset = Strategy3Subgroup.objects.select_related(
        'master_user',
        'group'
    )
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter,
        GroupsAttributeFilter,
    ]
    serializer_class = Strategy3SubgroupSerializer
    filter_class = Strategy3SubgroupFilterSet


class Strategy3AttributeTypeViewSet(GenericAttributeTypeViewSet):
    target_model = Strategy3
    target_model_serializer = Strategy3Serializer

    permission_classes = GenericAttributeTypeViewSet.permission_classes + [

    ]


class Strategy3FilterSet(Strategy1FilterSet):

    class Meta:
        model = Strategy3
        fields = []


class Strategy3ViewSet(Strategy1ViewSet):
    queryset = Strategy3.objects.select_related(
        'master_user',
        'subgroup',
        'subgroup__group'
    ).prefetch_related(
        get_attributes_prefetch()
    )
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter,
        GroupsAttributeFilter,
        EntitySpecificFilter
    ]
    serializer_class = Strategy3Serializer
    filter_class = Strategy3FilterSet

    @action(detail=False, methods=['get'], url_path='light', serializer_class=Strategy3LightSerializer)
    def list_light(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginator.post_paginate_queryset(queryset, request)
        serializer = self.get_serializer(page, many=True)

        result = self.get_paginated_response(serializer.data)

        return result

    @action(detail=False, methods=['get'], url_path='attributes')
    def list_attributes(self, request, *args, **kwargs):
        items = [
            {
                "key": "name",
                "name": "Name",
                "value_type": 10
            },
            {
                "key": "short_name",
                "name": "Short name",
                "value_type": 10
            },
            {
                "key": "user_code",
                "name": "User code",
                "value_type": 10
            },
            {
                "key": "public_name",
                "name": "Public name",
                "value_type": 10,
            },
            {
                "key": "notes",
                "name": "Notes",
                "value_type": 10
            },
            {
                "key": "subgroup",
                "name": "Group",
                "value_type": "field",
                "value_entity": "strategy-3-subgroup",
                "value_content_type": "strategies.strategy3subgroup",
                "code": "user_code"
            }
        ]

        items = items + get_list_of_entity_attributes('strategies.strategy3')

        result = {
            "count": len(items),
            "next": None,
            "previous": None,
            "results": items
        }

        return Response(result)

