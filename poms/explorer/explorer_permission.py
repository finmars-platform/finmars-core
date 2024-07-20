import logging

from rest_framework.exceptions import PermissionDenied

from poms.iam.permissions import FinmarsAccessPolicy as FinmarsAccessPermission
from poms.iam.access_policy import AccessEnforcement

_l = logging.getLogger("poms.explorer")

path_names = {
    "path",

}

class ExplorerAccessPermission(FinmarsAccessPermission):
    def has_specific_permission(self, view, request):
        statements = self.get_policy_statements(request, view)
        if not statements:
            return False

        action = self._get_invoked_action(view)
        allowed = self._evaluate_statements(statements, request, view, action)
        if not allowed:
            return False

        params = request.guery_parames if request.method == "GET" else request.data
        path_params = {
            param: value for param, value in params.items() if "path" in param
        }

        # TODO get path from request and validate it against request.user.member

        request.access_enforcement = AccessEnforcement(action=action, allowed=allowed)
        return True
