import logging

from rest_framework.exceptions import PermissionDenied

from poms.explorer.models import ROOT_PATH, AccessLevel
from poms.explorer.policy_handlers import member_has_access_to_path
from poms.iam.access_policy import AccessPolicy
from poms.iam.utils import get_statements

_l = logging.getLogger("poms.explorer")


class ExplorerAccessPermission(AccessPolicy):
    def has_specific_permission(self, view, request):
        statements = self.get_policy_statements(request, view)
        if not statements:
            return False

        action = self._get_invoked_action(view)
        allowed = self._evaluate_statements(statements, request, view, action)
        if not allowed:
            return False

        if request.method == "GET":
            params = request.guery_parames
            required_access = AccessLevel.READ
        else:
            params = request.data
            required_access = AccessLevel.WRITE

        path_params = {name: value for name, value in params.items() if "path" in name}

        # TODO get path from request and validate it against request.user.member

        return True


class ExplorerRootAccessPermission(AccessPolicy):
    def has_permission(self, request, view) -> bool:
        if request.user.is_superuser:
            return True

        if request.user.member and request.user.member.is_admin:
            return True

        return self.has_specific_permission(view, request)

    def has_object_permission(self, request, view, obj):
        return True

    def get_policy_statements(self, request, view=None):
        member = request.user.member
        if not member:
            raise PermissionDenied(f"User {request.user.username} has no member")

        return get_statements(member=member)

    def has_specific_permission(self, view, request):
        statements = self.get_policy_statements(request, view)
        if not statements:
            return False

        # action = self._get_invoked_action(view)
        # allowed = self._evaluate_statements(statements, request, view, action)
        # if not allowed:
        #     return False

        if request.method != "GET":
            return False

        return member_has_access_to_path(
            ROOT_PATH, request.user.member, AccessLevel.READ
        )
