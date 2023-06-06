from django.db.models import Q
from rest_framework.filters import BaseFilterBackend


class ConfigurationQueryFilter(BaseFilterBackend):

    def filter_queryset(self, request, queryset, view):
        query = request.query_params.get('query', None)

        if query:

            pieces = query.split(' ')

            name_q = Q()
            short_name_q = Q()
            description_q = Q()
            configuration_code_q = Q()

            for piece in pieces:
                name_q.add(Q(name__icontains=piece), Q.AND)
                short_name_q.add(Q(short_name__icontains=piece), Q.AND)
                description_q.add(Q(description__icontains=piece), Q.AND)
                configuration_code_q.add(Q(configuration_code__icontains=piece), Q.AND)

            options = Q()

            options.add(name_q, Q.OR)
            options.add(short_name_q, Q.OR)
            options.add(description_q, Q.OR)
            options.add(configuration_code_q, Q.OR)

            return queryset.filter(options)

        return queryset
