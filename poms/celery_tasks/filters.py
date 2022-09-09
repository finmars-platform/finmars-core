
from rest_framework.filters import BaseFilterBackend

from django.db.models import Q


class CeleryTaskQueryFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):

        query = request.query_params.get('query', False)

        if query:
            member = request.user.member
            return queryset.filter(Q(type__icontains=query) | Q(created__icontains=query) | Q(id=query))

        return queryset