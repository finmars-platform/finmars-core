from django.db.models import Q
from rest_framework.filters import BaseFilterBackend

from datetime import datetime, timedelta


class CeleryTaskQueryFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        query = request.query_params.get("query", False)

        if query:
            return queryset.filter(
                Q(type__icontains=query)
                | Q(created__icontains=query)
                | Q(id__icontains=query)
                | Q(member__username__icontains=query)
                | Q(celery_task_id__icontains=query)
            )

        return queryset


class CeleryTaskDateRangeFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        date_from = request.query_params.get("date_from", None)
        date_to = request.query_params.get("date_to", None)

        if date_from:
            queryset = queryset.filter(created__gte=date_from)

        if date_to:
            date_to = datetime.strptime(date_to, "%Y-%m-%d") + timedelta(
                days=1, microseconds=-1
            )

            queryset = queryset.filter(created__lte=date_to)

        return queryset