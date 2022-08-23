
import django_filters
from django.db.models import Q

class SystemMessageQueryFilter(django_filters.Filter):
    def filter_queryset(self, qs, value):
        return qs.filter(Q(title__icontains=value) | Q(description__icontains=value))