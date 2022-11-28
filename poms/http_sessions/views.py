from __future__ import unicode_literals

from logging import getLogger

import django_filters
from django.contrib.auth.models import User
from django_filters.rest_framework import FilterSet
from rest_framework.decorators import action
from rest_framework.mixins import DestroyModelMixin
from rest_framework.response import Response

from poms.common.filters import CharFilter
from poms.common.views import AbstractReadOnlyModelViewSet
from poms.http_sessions.models import Session
from poms.http_sessions.serializers import SessionSerializer, SetSessionSerializer
from poms.users.filters import OwnerByUserFilter
from poms.users.models import MasterUser, UserProfile, Member

_l = getLogger('poms.http_sessions')


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

    @action(detail=False, methods=('POST',), url_path='set-session', serializer_class=SetSessionSerializer,
            permission_classes=[], filter_backends=[])
    def set_session(self, request):

        _l.info("request.data %s" % request.data)
        _l.info("request.request.session %s" % request.session)

        session = Session.objects.get(session_key=request.session.session_key)
        session.id = request.data['id']

        # session.expire_date = request.data['expire_date']
        # session.session_key = request.data['session_key']
        # session.session_data = request.data['session_data']

        master_user = None
        user = None
        member = None

        if request.data['current_master_user_legacy_id']:
            try:
                master_user = MasterUser.objects.get(id=request.data['current_master_user_legacy_id'])
            except MasterUser.DoesNotExist:
                _l.info("Master user not found")
        else:
            try:
                master_user = MasterUser.objects.get(unique_id=request.data['current_master_user_id'])
            except MasterUser.DoesNotExist:
                _l.info("Master user not found")

        if request.data['user_legacy_id']:
            try:
                user = User.objects.get(id=request.data['user_legacy_id'])
            except User.DoesNotExist:
                _l.info("Master user not found")
        else:
            try:
                user_profile = UserProfile.objects.get(user_unique_id=request.data['user_id'])

                user = user_profile.user
            except  UserProfile.DoesNotExist:
                _l.info("User not found")

        if user:

            try:
                member = Member.objects.get(master_user=master_user, user=user)
            except Member.DoesNotExist:
                _l.info("Member not found")

        session.user = user
        session.current_master_user = master_user
        session.current_member = member

        session.save()

        return Response({'success': True})
