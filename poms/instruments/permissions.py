from rest_framework.permissions import BasePermission


class GeneratedEventPermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.is_need_reaction
