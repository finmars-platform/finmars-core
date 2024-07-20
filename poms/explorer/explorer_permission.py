import logging

from poms.iam.permissions import FinmarsAccessPolicy as FinmarsAccessPermission
from poms.iam.access_policy import AccessEnforcement
from poms.explorer.models import AccessLevel
from poms.explorer.policy_handlers import member_has_access_to_path

_l = logging.getLogger("poms.explorer")


class ExplorerAccessPermission(FinmarsAccessPermission):
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

        path_params = {
            name: value for name, value in params.items() if "path" in name
        }

        # TODO get path from request and validate it against request.user.member

        request.access_enforcement = AccessEnforcement(action=action, allowed=allowed)
        return True


class ExplorerRootAccessPermission(FinmarsAccessPermission):
    def has_specific_permission(self, view, request):
        statements = self.get_policy_statements(request, view)
        if not statements:
            return False

        action = self._get_invoked_action(view)
        allowed = self._evaluate_statements(statements, request, view, action)
        if not allowed:
            return False

        if request.method != "GET":
            return False

        return member_has_access_to_path("/*", request.user.member, AccessLevel.READ)
