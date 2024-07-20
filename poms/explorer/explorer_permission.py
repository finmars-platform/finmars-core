import logging

from rest_framework.exceptions import PermissionDenied

from poms.iam.access_policy import AccessPolicy as FinmarsAccessPermission
from poms.iam.utils import get_statements

_l = logging.getLogger("poms.explorer")


class ExplorerAccessPermission(FinmarsAccessPermission):
    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True

        if not request.user.member:
            raise PermissionDenied(f"User {request.user.username} has no member")

        if request.user.member and request.user.member.is_admin:
            return True

        # check storage path permission
