
import django_filters
from django.db.models import Q
from rest_framework.filters import BaseFilterBackend


class SystemMessageOnlyNewFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):

        only_new = request.query_params.get('only_new', False)

        if only_new == 'True':
            only_new = True

        if only_new:

            member = request.user.member
            return queryset.filter(members__member=member, members__is_read=False)

        return queryset