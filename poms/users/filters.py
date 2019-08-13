from rest_framework.filters import BaseFilterBackend

from poms.users.models import InviteStatusChoice


class OwnerByUserFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        return queryset.filter(user=request.user)


class OwnerByMasterUserFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        # master_user = get_master_user(request)

        if hasattr(request.user, 'master_user'):

            print('OwnerByMasterUserFilter %s' % request.user.master_user.name)

            master_user = request.user.master_user
            return queryset.filter(master_user=master_user)

        return []


class OwnerByMemberFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        # master_user = get_master_user(request)
        member = request.user.member
        return queryset.filter(member=member)


# class GroupOwnerByMasterUserFilter(OwnerByMasterUserFilter):
#     def filter_queryset(self, request, queryset, view):
#         # master_user = get_master_user(request)
#         master_user = request.user.master_user
#         return queryset.filter(master_user=master_user)


class UserFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        # master_user = request.user.master_user
        # return queryset.filter(members__master_user=master_user)
        return queryset.filter(id=request.user.id)


class MasterUserFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        user = request.user

        return queryset.filter(members__user=user)


class InviteToMasterUserFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        return queryset.filter(status=InviteStatusChoice.SENT)

class IsMemberFilterBackend(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):

        user = request.user
        master_user = request.user.master_user

        return queryset.filter(user=user, master_user=master_user)
