from __future__ import unicode_literals

from rest_framework import permissions


class IsOwnerOrReadonly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        else:
            return obj.master_user_id is not None
