import logging
from typing import Optional
from rest_framework.exceptions import PermissionDenied

from poms.explorer.models import DIR_SUFFIX, ROOT_PATH, AccessLevel
from poms.explorer.policy_handlers import member_has_access_to_path
from poms.iam.access_policy import AccessPolicy
from poms.iam.utils import get_statements

_l = logging.getLogger("poms.explorer")


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

    def has_statements(self, view, request) -> Optional[bool]:
        return bool(self.get_policy_statements(request, view))

    def has_specific_permission(self, view, request):
        if not self.has_statements(view, request) or request.method != "GET":
            return False

        return member_has_access_to_path(
            ROOT_PATH, request.user.member, AccessLevel.READ
        )


class ExplorerReadDirectoryPathPermission(ExplorerRootAccessPermission):
    def has_specific_permission(self, view, request):
        if not self.has_statements(view, request) or request.method != "GET":
            return False

        path = request.query_params.get("path", ROOT_PATH)

        if not path.endswith(DIR_SUFFIX):
            path = f"{path.rstrip('/')}{DIR_SUFFIX}/"

        return member_has_access_to_path(path, request.user.member, AccessLevel.READ)


class ExplorerReadFilePathPermission(ExplorerRootAccessPermission):
    def has_specific_permission(self, view, request):
        if not self.has_statements(view, request) or request.method != "GET":
            return False

        # check path in query params & in url kwargs
        path = request.query_params.get("path", view.kwargs.get("filepath"))
        if not path:
            return False

        return member_has_access_to_path(path, request.user.member, AccessLevel.READ)


class ExplorerWriteDirectoryPathPermission(ExplorerRootAccessPermission):
    def has_specific_permission(self, view, request):
        statements = self.get_policy_statements(request, view)
        if not statements:
            return False

        if request.method == "GET":
            return False

        path = request.data.get("path", ROOT_PATH)

        return member_has_access_to_path(path, request.user.member, AccessLevel.WRITE)
