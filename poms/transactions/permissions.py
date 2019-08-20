from rest_framework.permissions import BasePermission

from poms.obj_perms.permissions import PomsObjectPermission


class TransactionObjectPermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        member = request.user.member
        if member.is_superuser:
            return True
        p = lambda obj1: PomsObjectPermission().simple_has_object_permission(member, 'GET', obj1)
        return p(obj.portfolio) and (p(obj.account_position) | p (obj.account_cash) | p(obj.account_interim))


class ComplexTransactionPermission(BasePermission):

    def has_permission(self, request, view):
        # if request.method in ['POST']:
        #     return False
        return True