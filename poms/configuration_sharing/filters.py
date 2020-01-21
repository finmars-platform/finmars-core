from rest_framework.filters import BaseFilterBackend


class OwnerBySender(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        # master_user = get_master_user(request)

        if hasattr(request.user, 'member'):

            member = request.user.member
            return queryset.filter(member_from=member)

        return []


class OwnerByRecipient(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        # master_user = get_master_user(request)

        if hasattr(request.user, 'member'):

            member = request.user.member

            return queryset.filter(member_to=member.pk)

        return []
