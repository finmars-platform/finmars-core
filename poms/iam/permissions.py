import logging

from rest_framework.exceptions import PermissionDenied

from poms.iam.access_policy import AccessPolicy
from poms.iam.utils import get_statements

_l = logging.getLogger("poms.iam")


class FinmarsAccessPolicy(AccessPolicy):
    def get_policy_statements(self, request, view=None):
        if not request.user.member:
            raise PermissionDenied(f"User {request.user.username} has no member")

        return get_statements(member=request.user.member)
