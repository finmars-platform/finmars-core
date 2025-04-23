import logging
from datetime import datetime, timedelta

from django.db.models import Q
from rest_framework.filters import BaseFilterBackend

_l = logging.getLogger("poms.history")


class HistoryQueryFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        query = request.query_params.get("query", None)

        if query:
            pieces = query.split(" ")

            user_code_q = Q()
            created_q = Q()
            notes_q = Q()
            context_url_q = Q()

            for piece in pieces:
                user_code_q.add(Q(user_code__icontains=piece), Q.AND)
                created_q.add(Q(created_at__icontains=piece), Q.AND)
                notes_q.add(Q(notes__icontains=piece), Q.AND)
                context_url_q.add(Q(context_url__icontains=piece), Q.AND)

            options = Q()

            options.add(user_code_q, Q.OR)
            options.add(created_q, Q.OR)
            options.add(notes_q, Q.OR)
            options.add(context_url_q, Q.OR)

            return queryset.filter(options)

        return queryset


class HistoryDateRangeFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        date_from = request.query_params.get("date_from", None)
        date_to = request.query_params.get("date_to", None)

        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)

        if date_to:
            date_to = datetime.strptime(date_to, "%Y-%m-%d") + timedelta(
                days=1, microseconds=-1
            )

            queryset = queryset.filter(created_at__lte=date_to)

        return queryset


class HistoryActionFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        action = request.query_params.getlist("action", None)

        _l.info("action %s" % action)

        if action:
            return queryset.filter(action__in=action)

        return queryset


class HistoryMemberFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        member = request.query_params.getlist("member", None)

        if member:
            return queryset.filter(member__username__in=member)

        return queryset


class HistoryContentTypeFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        content_type = request.query_params.getlist("content_type", None)

        if content_type:
            app_labels = []
            models = []

            for item in content_type:
                pieces = item.split(".")
                app_labels.append(pieces[0])
                models.append(pieces[1])

            return queryset.filter(
                content_type__app_label__in=app_labels, content_type__model__in=models
            )

        return queryset
