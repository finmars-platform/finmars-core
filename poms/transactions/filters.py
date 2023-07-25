from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from rest_framework.filters import BaseFilterBackend

from poms.accounts.models import Account
from poms.counterparties.models import Counterparty, Responsible
from poms.currencies.models import Currency
from poms.instruments.models import (
    AccrualCalculationModel,
    DailyPricingModel,
    Instrument,
    InstrumentType,
    PaymentSizeDetail,
    Periodicity,
    PricingPolicy,
)
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
    def filter_qs(cls, queryset, master_user, member):
        from poms.iam.utils import get_allowed_queryset

        if member.is_admin:
            return queryset

        # IAM_SECURITY_VERIFY check if approach is good for business requirements
        allowed_portfolios = get_allowed_queryset(member, Portfolio.objects.all())
        allowed_accounts = get_allowed_queryset(member, Account.objects.all())

        queryset = queryset.filter(portfolio__in=allowed_portfolios).filter(
            Q(account_position__in=allowed_accounts)
            | Q(account_cash__in=allowed_accounts)
            | Q(account_interim__in=allowed_accounts)
        )

        return queryset


class TransactionTypeInputContentTypeFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        models = [
            Account,
            Instrument,
            InstrumentType,
            Currency,
            Counterparty,
            Responsible,
            Portfolio,
            Strategy1,
            Strategy2,
            Strategy3,
            DailyPricingModel,
            PaymentSizeDetail,
            PriceDownloadScheme,
            PricingPolicy,
            Periodicity,
            AccrualCalculationModel,
            EventClass,
            NotificationClass,
        ]
        ctypes = [ContentType.objects.get_for_model(model).pk for model in models]

        return queryset.filter(pk__in=ctypes)


class ComplexTransactionPermissionFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        master_user = request.user.master_user
        member = request.user.member

        return self.filter_qs(queryset, master_user, member)

    @classmethod
    def filter_qs(cls, queryset, master_user, member):
        from poms.iam.utils import get_allowed_queryset

        if member.is_admin:
            return queryset

        """TODO IAM_SECURITY_VERIFY check if appoach is good for business requirements """
        allowed_portfolios = get_allowed_queryset(member, Portfolio.objects.all())
        allowed_accounts = get_allowed_queryset(member, Account.objects.all())

        queryset = queryset.filter(transactions__portfolio__in=allowed_portfolios)

        """TODO check maybe performance issue"""
        queryset = queryset.filter(
            Q(transactions__account_position__in=allowed_accounts)
            | Q(transactions__account_cash__in=allowed_accounts)
            | Q(transactions__account_interim__in=allowed_accounts)
        )

        return queryset


class ComplexTransactionSpecificFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        is_locked = False
        is_unlocked = False
        is_canceled = False

        if (
            "ev_options" in request.data
            and "complex_transaction_filters" in request.data["ev_options"]
        ):
            if "locked" in request.data["ev_options"]["complex_transaction_filters"]:
                is_locked = True

            if "unlocked" in request.data["ev_options"]["complex_transaction_filters"]:
                is_unlocked = True

            if "ignored" in request.data["ev_options"]["complex_transaction_filters"]:
                is_canceled = True

        if not is_locked and is_unlocked:
            queryset = queryset.filter(is_locked=False)

        # Uncomment later
        if not is_unlocked and is_locked:
            queryset = queryset.filter(is_locked=True)

        if not is_canceled:
            queryset = queryset.filter(is_canceled=is_canceled)

        return queryset
