from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from rest_framework.filters import BaseFilterBackend

from poms.accounts.models import Account
from poms.counterparties.models import Counterparty
from poms.counterparties.models import Responsible
from poms.currencies.models import Currency
from poms.instruments.models import InstrumentType, Instrument, DailyPricingModel, PaymentSizeDetail, PricingPolicy, \
    Periodicity, AccrualCalculationModel
from poms.integrations.models import PriceDownloadScheme
from poms.portfolios.models import Portfolio
from poms.strategies.models import Strategy1, Strategy2, Strategy3
from poms.transactions.models import EventClass, NotificationClass


class TransactionObjectPermissionFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        master_user = request.user.master_user
        member = request.user.member

        return self.filter_qs(queryset, master_user, member)

    @classmethod
    def filter_qs(self, queryset, master_user, member):
        if member.is_superuser:
            return queryset

        return queryset


class TransactionTypeInputContentTypeFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        models = [Account, Instrument, InstrumentType, Currency, Counterparty, Responsible, Portfolio,
                  Strategy1, Strategy2, Strategy3, DailyPricingModel, PaymentSizeDetail, PriceDownloadScheme,
                  PricingPolicy, Periodicity, AccrualCalculationModel, EventClass, NotificationClass]
        ctypes = [ContentType.objects.get_for_model(model).pk for model in models]
        return queryset.filter(pk__in=ctypes)


class ComplexTransactionPermissionFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        return queryset.filter(master_user=request.user.master_user)


class ComplexTransactionSpecificFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):

        # print("ComplexTransactionSpecificFilter before %s" % len(queryset))

        is_locked = False
        is_unlocked = False
        is_canceled = False
        is_partially_visible = False

        member = request.user.member

        if 'ev_options' in request.data:

            if 'complex_transaction_filters' in request.data['ev_options']:

                if 'locked' in request.data['ev_options']['complex_transaction_filters']:
                    is_locked = True

                if 'unlocked' in request.data['ev_options']['complex_transaction_filters']:
                    is_unlocked = True

                if 'ignored' in request.data['ev_options']['complex_transaction_filters']:
                    is_canceled = True

                if 'partially_visible' in request.data['ev_options']['complex_transaction_filters']:
                    is_partially_visible = True

        # print('is_locked %s' % is_locked)
        # print('is_canceled %s' % is_canceled)
        # print('is_partial_visible %s' % is_partial_visible)
        if is_locked == False and is_unlocked == True:
            queryset = queryset.filter(is_locked=False)

        # Uncomment later
        if is_unlocked == False and is_locked == True:
            queryset = queryset.filter(is_locked=True)

        if is_canceled == False:
            queryset = queryset.filter(is_canceled=is_canceled)

        return queryset
