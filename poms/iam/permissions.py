import logging

from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission

from poms.iam.access_policy import AccessPolicy
from poms.iam.utils import get_statements

_l = logging.getLogger("poms.iam")


def is_admin(user) -> bool:
    return user.is_staff or user.is_superuser if user else False


class AdminPermission(BasePermission):
    def has_object_permission(self, request, *args, **kwargs) -> bool:
        return is_admin(request.user)

    def has_permission(self, request, *args, **kwargs) -> bool:
        return is_admin(request.user)


class FinmarsAccessPolicy(AccessPolicy):
    def get_policy_statements(self, request, view=None):
        if not request.user.member:
            raise PermissionDenied(f"User {request.user.username} has no member")

        return get_statements(member=request.user.member)
