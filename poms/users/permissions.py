from rest_framework.permissions import BasePermission, SAFE_METHODS


class SuperUserOnly(BasePermission):
    def has_permission(self, request, view):
        return request.user.member.is_superuser

    def has_object_permission(self, request, view, obj):
        return request.user.member.is_superuser


class SuperUserOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method.upper() in SAFE_METHODS:
            return True
        if hasattr(request.user, 'member'):
            return request.user.member.is_superuser
        return False

    def has_object_permission(self, request, view, obj):
        if request.method.upper() in SAFE_METHODS:
            return True

        if hasattr(request.user, 'member'):
            return request.user.member.is_superuser
        return False


class IsCurrentMasterUser(BasePermission):
    # def has_permission(self, request, view):
    #     if request.method in SAFE_METHODS:
    #         return True
    #     return False

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return request.user.master_user.id == obj.id


class IsCurrentUser(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method.upper() in SAFE_METHODS:
            return True
        user = request.user

        return user.id == obj.id
