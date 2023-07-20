from rest_framework.filters import BaseFilterBackend

from poms.currencies.models import Currency


class OwnerByCurrencyFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        return queryset.filter(
            currency__in=Currency.objects.filter(master_user=request.user.master_user)
        )
