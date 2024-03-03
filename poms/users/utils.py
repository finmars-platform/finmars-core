import logging

from rest_framework.exceptions import NotFound, PermissionDenied

from poms.users.models import Member

_l = logging.getLogger("poms.users")


def get_master_user_and_member(request) -> tuple:
    if not request.user.is_authenticated:
        raise PermissionDenied("User is not authenticated")

    member = Member.objects.filter(user=request.user).first()
    if not member:
        raise NotFound(f"Member not found for user {request.user.username}")

    master_user = member.master_user

    if member.is_deleted:
        raise PermissionDenied("Member deleted")

    if member.status != Member.STATUS_ACTIVE:
        raise PermissionDenied("Member not active")

    return member, master_user


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
