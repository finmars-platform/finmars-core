from rest_framework.filters import BaseFilterBackend

from poms.users.models import InviteToMasterUser, MasterUser


class OwnerByUserFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        return queryset.filter(user=request.user)


class OwnerByMasterUserFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        # master_user = get_master_user(request)

        if hasattr(request.user, 'master_user'):

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


class MasterUserBackupsForOwnerOnlyFilter(BaseFilterBackend):

    def filter_queryset(self, request, queryset, view):
        user = request.user

        ids = []

        for item in queryset:

            if item.status == MasterUser.STATUS_BACKUP:

                for member in item.members.all():

                    if member.user_id == user.id and member.is_owner:

                        ids.append(item.id)

            else:

                ids.append(item.id)

        return queryset.filter(id__in=ids)


class InviteToMasterUserFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        return queryset.filter(status=InviteToMasterUser.SENT)


class IsMemberFilterBackend(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):

        user = request.user
        master_user = request.user.master_user

        return queryset.filter(user=user, master_user=master_user)
