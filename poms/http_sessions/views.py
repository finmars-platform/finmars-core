from __future__ import unicode_literals

import django_filters
from django_filters.rest_framework import FilterSet

from rest_framework.mixins import DestroyModelMixin

from poms.common.filters import CharFilter
from poms.common.views import AbstractReadOnlyModelViewSet
from poms.http_sessions.models import Session
from poms.http_sessions.serializers import SessionSerializer
from poms.users.filters import OwnerByUserFilter


class SessionFilterSet(FilterSet):
    user_ip = django_filters.CharFilter()
    user_agent = CharFilter()

    class Meta:
        model = Session
        fields = []


class SessionViewSet(DestroyModelMixin, AbstractReadOnlyModelViewSet):
    queryset = Session.objects.select_related(
        'user'
    )
    lookup_field = 'id'
    serializer_class = SessionSerializer
    filter_backends = AbstractReadOnlyModelViewSet.filter_backends + [
        OwnerByUserFilter,
    ]
    filter_class = SessionFilterSet
    ordering_fields = [
        'user_ip', 'user_agent',
    ]
