from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.exceptions import NotFound, PermissionDenied

from poms.http_sessions.models import Session
from poms.users.models import Member, MasterUser, UserProfile

import time

import logging
_l = logging.getLogger('poms.users')


def set_master_user(request, master_user):

    try:

        set_st = time.perf_counter()

        session = Session.objects.get(session_key=request.session.session_key)

        user = User.objects.get(id=request.user.id)
        member = Member.objects.get(user=user, master_user = master_user)

        session.current_master_user = master_user
        session.current_member = member

        session.save()

        # DEPRECATED
        # master_user_id = master_user.id
        # old_master_user_id = session.current_master_user.id
        #
        # sessions = Session.objects.filter(user=request.user.id)
        # user = User.objects.get(id=request.user.id)
        # user_profile = UserProfile.objects.get(user=user)
        #
        # if old_master_user_id != master_user_id:
        #     if master_user_id is None:
        #         del request.session['current_master_user']
        #
        #         for session in sessions:
        #             session.current_master_user = None
        #
        #             session.save()
        #
        #     else:
        #         request.session['current_master_user'] = master_user_id
        #
        #         for session in sessions:
        #             session.current_master_user = MasterUser.objects.get(id=master_user_id)
        #
        #             user_profile.active_master_user = session.current_master_user
        #             print("Set active Master user to User Profile")
        #             user_profile.save()
        #
        #             session.save()

        _l.debug('set_master_user done: %s' % (time.perf_counter() - set_st))

    except Session.DoesNotExist:

        _l.debug('set_master_user: session not found')

        raise NotFound()


def get_master_user_and_member(request):

    if not request.user.is_authenticated:
        raise PermissionDenied()

    try:
        session = Session.objects.get(session_key=request.session.session_key)

        master_user_id = session.current_master_user_id
        member_id = session.current_member_id

        member = None
        master_user = None

        if master_user_id is not None:

            master_user = MasterUser.objects.get(id=master_user_id)

        if member_id is not None:

            try:
                member = Member.objects.get(user=request.user, master_user=master_user_id)
            except Member.DoesNotExist:
                return None, master_user

        return member, master_user

    except Session.DoesNotExist:

        _l.debug('get_master_user_and_member: session not found')

        raise NotFound()


# def get_master_user(request):
#     user = request.user
#     if not user.is_authenticated:
#         raise PermissionDenied()
#
#     master_user_id = request.GET.get('master_user_id', None)
#     if master_user_id is None:
#         master_user_id = request.session.get('master_user_id', None)
#
#     if master_user_id is not None:
#         try:
#             return MasterUser.objects.get(id=master_user_id, members__user=user)
#         except ObjectDoesNotExist:
#             pass
#
#     master_user = MasterUser.objects.filter(members__user=user).first()
#     if master_user is None:
#         raise NotFound()
#
#     request.session['master_user_id'] = master_user.id
#     return master_user
#
#
# def get_member(request):
#     user = request.user
#     if not user.is_authenticated:
#         raise PermissionDenied()
#
#     master_user = user.master_user
#     try:
#         # for member in master_user.members.all():
#         #     if member.master_user_id == master_user.id:
#         #         return member
#         # raise NotFound()
#         # member = Member.objects.select_related('master_user').prefetch_related('groups').get(
#         #     master_user=master_user, user=user)
#         member = Member.objects.prefetch_related('groups').get(master_user=master_user, user=user)
#         return member
#     except ObjectDoesNotExist:
#         raise NotFound()


def get_user_from_context(context):
    context = context or {}
    request = context.get('request', None)
    if request:
        return request.user
    return context.get('user', None)


def get_master_user_from_context(context):
    context = context or {}
    request = context.get('request', None)
    if request:
        return request.user.master_user
    return context.get('master_user', None)


def get_member_from_context(context):
    context = context or {}
    request = context.get('request', None)
    if request:

        if hasattr(request.user, 'member'):
            return request.user.member
        return None

    return context.get('member', None)
