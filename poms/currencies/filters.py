from rest_framework.filters import BaseFilterBackend

from poms.currencies.models import Currency


class OwnerByCurrencyFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        return queryset.filter(
            currency__in=Currency.objects.filter(master_user=request.user.master_user)
        )


class ListDatesFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):

        dates = request.query_params.get('dates', None)

        if dates:
            return queryset.filter(date__in=dates.split(','))

        return queryset