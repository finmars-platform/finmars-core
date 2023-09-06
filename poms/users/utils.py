import logging

from rest_framework.exceptions import NotFound, PermissionDenied

from poms.users.models import Member

_l = logging.getLogger("poms.users")


def get_master_user_and_member(request):
    if not request.user.is_authenticated:
        raise PermissionDenied()

    try:
        member = Member.objects.get(user=request.user)
        master_user = member.master_user

        if member.is_deleted:
            raise PermissionDenied()

        if member.status != Member.STATUS_ACTIVE:
            raise PermissionDenied()

        return member, master_user

    except Exception as e:
        _l.debug("get_master_user_and_member: token not found")

        raise NotFound() from e


def get_user_from_context(context):
    context = context or {}
    request = context.get("request", None)
    return request.user if request else context.get("user", None)


def get_master_user_from_context(context):
    context = context or {}
    request = context.get("request", None)
    if request:
        return request.user.master_user
    return context.get("master_user", None)


def get_member_from_context(context):
    context = context or {}
    request = context.get("request", None)
    if request:
        return request.user.member if hasattr(request.user, "member") else None

    return context.get("member", None)
