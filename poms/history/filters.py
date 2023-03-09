from django.db.models import Q
from rest_framework.filters import BaseFilterBackend


class HistoryQueryFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        query = request.query_params.get('query', False)

        if query:

            pieces = query.split(' ')


            user_code_q = Q()
            created_q = Q()
            member_username_q = Q()
            notes_q = Q()
            action_q = Q()
            content_type_q = Q()

            for piece in pieces:
                user_code_q.add(Q(user_code__icontains=piece), Q.AND)
                created_q.add(Q(created__icontains=piece), Q.AND)
                member_username_q.add(Q(member__username__icontains=piece), Q.AND)
                notes_q.add(Q(notes__icontains=piece), Q.AND)
                action_q.add(Q(action__icontains=piece), Q.AND)
                content_type_q.add(Q(content_type__model__icontains=piece), Q.AND)

            options = Q()

            options.add(user_code_q, Q.OR)
            options.add(created_q, Q.OR)
            options.add(member_username_q, Q.OR)
            options.add(notes_q, Q.OR)
            options.add(action_q, Q.OR)
            options.add(content_type_q, Q.OR)

            return queryset.filter(options)

        return queryset
