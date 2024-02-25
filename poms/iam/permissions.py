import logging

from rest_framework.exceptions import PermissionDenied

from poms.iam.access_policy import AccessPolicy
from poms.iam.utils import get_statements

_l = logging.getLogger("poms.iam")


class FinmarsAccessPolicy(AccessPolicy):
    def get_policy_statements(self, request, view=None) -> list:
        if hasattr(request.user, "member") and request.user.member:
            return get_statements(member=request.user.member)

        else:
            raise PermissionDenied(f"User {request.user.username} has no member")
