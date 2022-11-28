from __future__ import unicode_literals

import django_filters
from django_filters.rest_framework import FilterSet
from rest_framework.settings import api_settings

from poms.audit.filters import ObjectHistory4ContentTypeMultipleChoiceFilter
from poms.audit.models import AuthLogEntry, ObjectHistory4Entry
from poms.audit.serializers import AuthLogEntrySerializer, ObjectHistory4EntrySerializer
from poms.common.filters import ModelExtMultipleChoiceFilter, NoOpFilter, CharFilter, GroupsAttributeFilter, \
    AttributeFilter
from poms.common.pagination import CustomPaginationMixin
from poms.common.views import AbstractReadOnlyModelViewSet
from poms.obj_perms.views import AbstractWithObjectPermissionViewSet, AbstractEvGroupWithObjectPermissionViewSet
from poms.users.filters import OwnerByUserFilter, OwnerByMasterUserFilter
from poms.users.models import Member
from poms.users.permissions import SuperUserOnly


class AuthLogEntryFilterSet(FilterSet):
    id = NoOpFilter()
    date = django_filters.DateFromToRangeFilter()
    is_success = django_filters.BooleanFilter()
    user_ip = django_filters.CharFilter()

    class Meta:
        model = AuthLogEntry
        fields = []


class AuthLogViewSet(AbstractReadOnlyModelViewSet):
    queryset = AuthLogEntry.objects.select_related(
        'user'
    )
    serializer_class = AuthLogEntrySerializer
    filter_backends = AbstractReadOnlyModelViewSet.filter_backends + [
        OwnerByUserFilter,
    ]
    filter_class = AuthLogEntryFilterSet
    ordering_fields = ('date',)


class ObjectHistory4EntryFilterSet(FilterSet):
    created = django_filters.DateFromToRangeFilter()
    member = ModelExtMultipleChoiceFilter(model=Member, field_name='username')
    group_id = django_filters.NumberFilter()
    actor_content_type = ObjectHistory4ContentTypeMultipleChoiceFilter()
    actor_object_id = django_filters.NumberFilter()
    actor_object_repr = CharFilter()
    content_type = ObjectHistory4ContentTypeMultipleChoiceFilter()
    object_id = django_filters.NumberFilter()
    object_repr = CharFilter()
    # field_name = django_filters.CharFilter()
    value = CharFilter()
    value_content_type = ObjectHistory4ContentTypeMultipleChoiceFilter()
    value_object_id = django_filters.NumberFilter()
    old_value = CharFilter()
    old_value_content_type = ObjectHistory4ContentTypeMultipleChoiceFilter()
    old_value_object_id = django_filters.NumberFilter()

    class Meta:
        model = ObjectHistory4Entry
        fields = []


class ObjectHistory4ViewSet(AbstractReadOnlyModelViewSet):
    queryset = ObjectHistory4Entry.objects.select_related(
        # 'master_user',
        # 'member',
        # 'actor_content_type',
        # 'content_type',
        # 'value_content_type',
        # 'old_value_content_type',
    ).prefetch_related(
        'master_user',
        'member',
        'actor_content_type',
        'content_type',
        'value_content_type',
        'old_value_content_type',
        # TODO: if enable then actor_content_type and other converted to None!!!
        # 'actor_content_object',
        # 'content_object',
        # 'value_content_object',
        # 'old_value_content_object'
    )
    serializer_class = ObjectHistory4EntrySerializer
    filter_backends = AbstractReadOnlyModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    permission_classes = AbstractReadOnlyModelViewSet.permission_classes + [
        SuperUserOnly,
    ]
    filter_class = ObjectHistory4EntryFilterSet
    ordering_fields = ['created', 'member', 'actor_content_type', 'content_type', 'value_content_type',
                       'old_value_content_type', ]


class ObjectHistory4EvViewSet(AbstractWithObjectPermissionViewSet):
    queryset = ObjectHistory4Entry.objects.select_related(
        # 'master_user',
        # 'member',
        # 'actor_content_type',
        # 'content_type',
        # 'value_content_type',
        # 'old_value_content_type',
    ).prefetch_related(
        'master_user',
        'member',
        'actor_content_type',
        'content_type',
        'value_content_type',
        'old_value_content_type',
        # TODO: if enable then actor_content_type and other converted to None!!!
        # 'actor_content_object',
        # 'content_object',
        # 'value_content_object',
        # 'old_value_content_object'
    )
    serializer_class = ObjectHistory4EntrySerializer
    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        GroupsAttributeFilter,
        AttributeFilter,
    ]
    filter_class = ObjectHistory4EntryFilterSet
    ordering_fields = [
        'user_code', 'name', 'short_name', 'public_name'
    ]


class ObjectHistory4EvGroupViewSet(AbstractEvGroupWithObjectPermissionViewSet, CustomPaginationMixin):
    queryset = ObjectHistory4Entry.objects.select_related(
        # 'master_user',
        # 'member',
        # 'actor_content_type',
        # 'content_type',
        # 'value_content_type',
        # 'old_value_content_type',
    ).prefetch_related(
        'master_user',
        'member',
        'actor_content_type',
        'content_type',
        'value_content_type',
        'old_value_content_type',
        # TODO: if enable then actor_content_type and other converted to None!!!
        # 'actor_content_object',
        # 'content_object',
        # 'value_content_object',
        # 'old_value_content_object'
    )
    serializer_class = ObjectHistory4EntrySerializer
    pagination_class = api_settings.DEFAULT_PAGINATION_CLASS
    # filter_class = AccountFilterSet

    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        AttributeFilter
    ]
