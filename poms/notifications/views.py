from __future__ import unicode_literals

import django_filters
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django_filters.rest_framework import FilterSet
from django_filters.widgets import BooleanWidget
from rest_framework import serializers
from rest_framework.decorators import action

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from poms.common.filters import CharFilter, NoOpFilter
from poms.common.views import AbstractReadOnlyModelViewSet
from poms.notifications.filters import NotificationFilter, NotificationContentTypeMultipleChoiceFilter
from poms.notifications.models import Notification
from poms.notifications.serializers import NotificationSerializer


class NotificationFilterSet(FilterSet):
    id = NoOpFilter()
    all = NoOpFilter(widget=BooleanWidget())
    create_date = django_filters.DateFromToRangeFilter()
    read_date = django_filters.DateFromToRangeFilter()
    actor_content_type = NotificationContentTypeMultipleChoiceFilter()
    actor_object_id = django_filters.CharFilter()
    verb = CharFilter()
    action_object_content_type = NotificationContentTypeMultipleChoiceFilter()
    action_object_object_id = django_filters.CharFilter()
    target_content_type = NotificationContentTypeMultipleChoiceFilter()
    target_object_id = django_filters.CharFilter()

    class Meta:
        model = Notification
        fields = []


class NotificationViewSet(AbstractReadOnlyModelViewSet):
    queryset = Notification.objects.select_related(
        'recipient',
        'recipient_member',
        'actor_content_type',
        'action_object_content_type',
        'target_content_type'
    ).prefetch_related(
        'actor',
        'action_object',
        'target',
    )
    serializer_class = NotificationSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = AbstractReadOnlyModelViewSet.filter_backends + [
        NotificationFilter,
    ]
    filter_class = NotificationFilterSet
    ordering_fields = [
        'create_date', 'read_date',
    ]

    @action(detail=False, methods=['get'], url_path='status', serializer_class=serializers.Serializer)
    def get_status(self, request, pk=None):
        unread_count = request.user.notifications.filter(read_date__isnull=True).count()
        return Response({
            "unread_count": unread_count
        })

    @action(detail=False, methods=['post'], url_path='mark-all-as-read', serializer_class=serializers.Serializer)
    def mark_all_as_read(self, request, pk=None):
        request.user.notifications.filter(read_date__isnull=True).update(read_date=timezone.now())
        serializer = self.get_serializer(instance=[], many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='mark-as-read', serializer_class=serializers.Serializer)
    def mark_as_read(self, request, pk=None):
        instance = self.get_object()
        instance.mark_as_read()
        serializer = self.get_serializer(instance=instance)
        return Response(serializer.data)
