# import logging
# from typing import Optional
#
# from rest_framework.exceptions import PermissionDenied
#
# from poms.explorer.models import DIR_SUFFIX, AccessLevel, get_root_path
# from poms.explorer.policy_handlers import member_has_access_to_path
# from poms.explorer.utils import is_true_value
# from poms.iam.access_policy import AccessPolicy
# from poms.iam.utils import get_statements
#
# _l = logging.getLogger("poms.explorer")
#
#
# class ExplorerRootAccessPermission(AccessPolicy):
#     def has_permission(self, request, view) -> bool:
#         if request.user.is_superuser:
#             return True
#
#         if request.user.member and request.user.member.is_admin:
#             return True
#
#         return self.has_specific_permission(view, request)
#
#     def has_object_permission(self, request, view, obj):
#         return True
#
#     def get_policy_statements(self, request, view=None):
#         member = request.user.member
#         if not member:
#             raise PermissionDenied(f"User {request.user.username} has no member")
#
#         return get_statements(member=member)
#
#     def has_statements(self, view, request) -> Optional[bool]:
#         return bool(self.get_policy_statements(request, view))
#
#     def has_specific_permission(self, view, request, **kwargs):
#         if not self.has_statements(view, request) or request.method != "GET":
#             return False
#
#         return member_has_access_to_path(
#             get_root_path(), request.user.member, AccessLevel.READ
#         )
#
#
# class ExplorerReadDirectoryPathPermission(ExplorerRootAccessPermission):
#     def has_specific_permission(self, view, request, **kwargs):
#         if not self.has_statements(view, request) or request.method != "GET":
#             return False
#
#         path = request.query_params.get("path")
#         if not path:
#             return True
#
#         if not path.endswith(DIR_SUFFIX):
#             path = f"{path.rstrip('/')}{DIR_SUFFIX}/"
#
#         return member_has_access_to_path(path, request.user.member, AccessLevel.READ)
#
#
# class ExplorerReadFilePathPermission(ExplorerRootAccessPermission):
#     def has_specific_permission(self, view, request, **kwargs):
#         if not self.has_statements(view, request):
#             return False
#
#         if request.method == "GET":
#             path = request.query_params.get("path", view.kwargs.get("filepath"))
#         else:
#             path = request.data.get("path")
#         if not path:
#             return True
#
#         return member_has_access_to_path(path, request.user.member, AccessLevel.READ)
#
#
# class ExplorerWriteDirectoryPathPermission(ExplorerRootAccessPermission):
#     def has_specific_permission(self, view, request, **kwargs):
#         if not self.has_statements(view, request) or request.method == "GET":
#             return False
#
#         path = request.data.get("path", get_root_path())
#         if not path.endswith(DIR_SUFFIX):
#             path = f"{path.rstrip('/')}{DIR_SUFFIX}"
#
#         return member_has_access_to_path(path, request.user.member, AccessLevel.WRITE)
#
#
# class ExplorerDeletePathPermission(ExplorerRootAccessPermission):
#     def has_specific_permission(self, view, request, **kwargs):
#         if not self.has_statements(view, request) or request.method == "GET":
#             return False
#
#         path = request.query_params.get("path")
#         if not path:
#             return True
#
#         is_dir = is_true_value(request.query_params.get("is_dir", "false"))
#
#         if is_dir and not path.endswith(DIR_SUFFIX):
#             path = f"{path.rstrip('/')}{DIR_SUFFIX}"
#
#         return member_has_access_to_path(path, request.user.member, AccessLevel.WRITE)
#
#
# class ExplorerRootWritePermission(ExplorerRootAccessPermission):
#     def has_specific_permission(self, view, request, **kwargs):
#         if not self.has_statements(view, request) or request.method == "GET":
#             return False
#
#         path = request.data.get("path")
#         if not path:
#             return True
#
#         return member_has_access_to_path(
#             get_root_path(), request.user.member, AccessLevel.WRITE
#         )
#
#
# class ExplorerZipPathsReadPermission(ExplorerRootAccessPermission):
#     def has_specific_permission(self, view, request, **kwargs):
#         if not self.has_statements(view, request) or request.method == "GET":
#             return False
#
#         paths = request.data.get("paths")
#         if isinstance(paths, str):
#             paths = [paths]
#
#         if not paths:
#             return True
#
#         for path in paths:
#             if path.endswith("/"):
#                 path = f"{path.rstrip('/')}{DIR_SUFFIX}"
#
#             if not member_has_access_to_path(
#                 path, request.user.member, AccessLevel.READ
#             ):
#                 return False
#
#         return True
#
#
# class ExplorerMovePermission(ExplorerRootAccessPermission):
#     def has_specific_permission(self, view, request, **kwargs):
#         if not self.has_statements(view, request) or request.method == "GET":
#             return False
#
#         to_dir = request.data.get("target_directory_path")
#         from_paths = request.data.get("paths")
#
#         if not to_dir and not from_paths:
#             return True
#
#         if not to_dir.endswith(DIR_SUFFIX):
#             to_dir = f"{to_dir.rstrip('/')}{DIR_SUFFIX}"
#         if not member_has_access_to_path(
#             to_dir, request.user.member, AccessLevel.WRITE
#         ):
#             return False
#
#         return all(
#             member_has_access_to_path(path, request.user.member, AccessLevel.READ)
#             for path in from_paths
#         )
#
#
# class ExplorerUnZipPermission(ExplorerRootAccessPermission):
#     def has_specific_permission(self, view, request, **kwargs):
#         if not self.has_statements(view, request) or request.method == "GET":
#             return False
#
#         to_dir = request.data.get("target_directory_path")
#         file_path = request.data.get("file_path")
#
#         if not to_dir and not file_path:
#             return True
#
#         if not to_dir.endswith(DIR_SUFFIX):
#             to_dir = f"{to_dir.rstrip('/')}{DIR_SUFFIX}"
#         if not member_has_access_to_path(
#             to_dir, request.user.member, AccessLevel.WRITE
#         ):
#             return False
#
#         return bool(
#             member_has_access_to_path(file_path, request.user.member, AccessLevel.READ)
#         )
