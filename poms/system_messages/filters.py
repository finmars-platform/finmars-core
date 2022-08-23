
import django_filters
from django.db.models import Q
from rest_framework.filters import BaseFilterBackend
class SystemMessageQueryFilter(django_filters.Filter):
    def filter_queryset(self, qs, value):
        return qs.filter(Q(title__icontains=value) | Q(description__icontains=value))


class SystemMessageOnlyNewFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):

        only_new = request.query_params.get('only_new', False)

        if only_new == 'True':
            only_new = True

        if only_new:

            member = request.user.member
            return queryset.filter(members__member=member, members__is_read=False)

        return queryset