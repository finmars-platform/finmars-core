from django.db.models import Q
from rest_framework.filters import BaseFilterBackend

import logging
_l = logging.getLogger('poms.history')

class HistoryQueryFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        query = request.query_params.get('query', False)

        if query:

            pieces = query.split(' ')

            user_code_q = Q()
            created_q = Q()
            notes_q = Q()
            content_type_q = Q()

            for piece in pieces:
                user_code_q.add(Q(user_code__icontains=piece), Q.AND)
                created_q.add(Q(created__icontains=piece), Q.AND)
                notes_q.add(Q(notes__icontains=piece), Q.AND)
                content_type_q.add(Q(content_type__model__icontains=piece), Q.AND)

            options = Q()

            options.add(user_code_q, Q.OR)
            options.add(created_q, Q.OR)
            options.add(notes_q, Q.OR)
            options.add(content_type_q, Q.OR)

            return queryset.filter(options)

        return queryset


class HistoryActionFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        action = request.query_params.getlist('action', None)

        _l.info('action %s' % action)

        if action:
            return queryset.filter(action__in=action)

        return queryset


class HistoryMemberFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        member = request.query_params.getlist('member', None)

        if member:
            return queryset.filter(member__username__in=member)

        return queryset
