from django.db.models import Q
from rest_framework.filters import BaseFilterBackend


class HistoryQueryFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        query = request.query_params.get('query', False)

        if query:
            member = request.user.member
            return queryset.filter(
                Q(user_code__icontains=query) | Q(created__icontains=query) | Q(id__icontains=query) | Q(
                    member__username__icontains=query) | Q(notes__icontains=query) | Q(action__icontains=query) | Q(content_type__model__icontains=query))

        return queryset
