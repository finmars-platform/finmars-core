from __future__ import unicode_literals

import django_filters
from django.db.models import Count, Prefetch
from django.utils import timezone
from django_filters.rest_framework import FilterSet
from rest_framework.decorators import action


from rest_framework.response import Response

from poms.chats.filters import MessagePermissionFilter, DirectMessagePermissionFilter
from poms.chats.models import Thread, Message, DirectMessage, ThreadGroup
from poms.chats.permissions import MessagePermission, DirectMessagePermission
from poms.chats.serializers import ThreadSerializer, MessageSerializer, DirectMessageSerializer, ThreadGroupSerializer
from poms.common.filters import CharFilter, NoOpFilter, ModelExtWithPermissionMultipleChoiceFilter, \
    ModelExtMultipleChoiceFilter
from poms.common.views import AbstractModelViewSet
from poms.obj_perms.filters import ObjectPermissionMemberFilter, ObjectPermissionGroupFilter, \
    ObjectPermissionPermissionFilter
from poms.obj_perms.utils import get_permissions_prefetch_lookups
from poms.obj_perms.views import AbstractWithObjectPermissionViewSet
from poms.tags.filters import TagFilter
from poms.tags.models import Tag, TagLink
from poms.tags.utils import get_tag_prefetch
from poms.users.filters import OwnerByMasterUserFilter
from poms.users.models import Member
from poms.users.permissions import SuperUserOrReadOnly, SuperUserOnly


class ThreadGroupFilterSet(FilterSet):
    id = NoOpFilter()
    is_deleted = django_filters.BooleanFilter()
    name = CharFilter()
    tag = TagFilter(model=ThreadGroup)

    class Meta:
        model = ThreadGroup
        fields = []


class ThreadGroupViewSet(AbstractModelViewSet):
    queryset = ThreadGroup.objects.select_related(
        'master_user'
    ).prefetch_related(
        get_tag_prefetch(),
        *get_permissions_prefetch_lookups(
            (None, ThreadGroup),
        )
    )
    serializer_class = ThreadGroupSerializer
    permission_classes = AbstractModelViewSet.permission_classes + [
        SuperUserOrReadOnly
    ]
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    filter_class = ThreadGroupFilterSet
    ordering_fields = [
        'name'
    ]


class ThreadFilterSet(FilterSet):
    id = NoOpFilter()
    is_deleted = django_filters.BooleanFilter()
    subject = CharFilter()
    is_closed = django_filters.BooleanFilter()
    created = django_filters.DateFromToRangeFilter()
    modified = django_filters.DateFromToRangeFilter()
    closed = django_filters.DateFromToRangeFilter()
    thread_group = ModelExtWithPermissionMultipleChoiceFilter(model=ThreadGroup)
    tag = TagFilter(model=Thread)
    member = ObjectPermissionMemberFilter(object_permission_model=Thread)
    member_group = ObjectPermissionGroupFilter(object_permission_model=Thread)
    permission = ObjectPermissionPermissionFilter(object_permission_model=Thread)

    class Meta:
        model = Thread
        fields = []


class ThreadViewSet(AbstractWithObjectPermissionViewSet):
    queryset = Thread.objects.select_related(
        'thread_group'
    ).annotate(
        messages_count=Count('messages')
    ).prefetch_related(
        Prefetch(
            "messages",
            to_attr="messages_last",
            queryset=Message.objects.prefetch_related('sender').filter(
                pk__in=Message.objects.distinct('thread').
                    order_by('thread_id', '-created', '-id').
                    values_list('id', flat=True))

        ),
        get_tag_prefetch(),
        *get_permissions_prefetch_lookups(
            (None, Thread),
            ('thread_group', ThreadGroup),
        )
    )
    serializer_class = ThreadSerializer
    filter_backends = AbstractWithObjectPermissionViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    filter_class = ThreadFilterSet
    ordering_fields = [
        'id', 'created', 'modified', 'closed', 'is_closed', 'subject',
        'thread_group', 'thread_group__name',
    ]

    @action(detail=True, url_path='close',
                  permission_classes=AbstractWithObjectPermissionViewSet.permission_classes + [SuperUserOnly, ])
    def close(self, request, pk=None):
        instance = self.get_object()
        instance.is_closed = True
        instance.closed = timezone.now()
        instance.save(update_fields=['is_closed', 'closed'])
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=True, url_path='reopen',
                  permission_classes=AbstractWithObjectPermissionViewSet.permission_classes + [SuperUserOnly, ])
    def reopen(self, request, pk=None):
        instance = self.get_object()
        instance.is_closed = False
        instance.closed = None
        instance.save(update_fields=['is_closed', 'closed'])
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class MessageFilterSet(FilterSet):
    id = NoOpFilter()
    created = django_filters.DateRangeFilter()
    thread = ModelExtWithPermissionMultipleChoiceFilter(model=Thread, field_name='subject')
    sender = ModelExtMultipleChoiceFilter(model=Member, field_name='username')

    class Meta:
        model = Message
        fields = []


class MessageViewSet(AbstractModelViewSet):
    queryset = Message.objects.select_related(
        'thread',
        'sender'
    )
    serializer_class = MessageSerializer
    permission_classes = AbstractModelViewSet.permission_classes + [
        MessagePermission,
    ]
    filter_backends = AbstractModelViewSet.filter_backends + [
        MessagePermissionFilter,
    ]
    filter_class = MessageFilterSet
    ordering_fields = [
        'id', 'created', 'thread', 'thread__subject', 'sender', 'sender__username'
    ]


class DirectMessageFilterSet(FilterSet):
    id = NoOpFilter()
    created = django_filters.DateFromToRangeFilter()
    recipient = ModelExtMultipleChoiceFilter(model=Member, field_name='username')
    sender = ModelExtMultipleChoiceFilter(model=Member, field_name='username')

    class Meta:
        model = DirectMessage
        fields = []


class DirectMessageViewSet(AbstractModelViewSet):
    queryset = DirectMessage.objects.select_related(
        'sender',
        'recipient'
    )
    serializer_class = DirectMessageSerializer
    permission_classes = AbstractModelViewSet.permission_classes + [
        DirectMessagePermission,
    ]
    filter_backends = AbstractModelViewSet.filter_backends + [
        DirectMessagePermissionFilter,
    ]
    filter_class = DirectMessageFilterSet
    ordering_fields = [
        'id', 'created', 'recipient', 'recipient__username', 'sender', 'sender__username',
    ]
