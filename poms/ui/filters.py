from django.contrib.contenttypes.models import ContentType
from rest_framework.filters import BaseFilterBackend

from poms.pricing.models import PriceHistoryError, CurrencyHistoryError
from poms.reports.models import BalanceReport, PLReport, PerformanceReport, CashFlowReport, TransactionReport


class LayoutContentTypeFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        from poms.accounts.models import AccountType, Account
        from poms.audit.models import InstrumentAudit,TransactionAudit, ObjectHistory4Entry, AuthLogEntry
        from poms.currencies.models import Currency, CurrencyHistory
        from poms.instruments.models import InstrumentType, Instrument, PriceHistory, PricingPolicy
        from poms.counterparties.models import Counterparty, Responsible, CounterpartyGroup, ResponsibleGroup
        from poms.strategies.models import Strategy1Group, Strategy1Subgroup, Strategy1, Strategy2Group, \
            Strategy2Subgroup, Strategy2, Strategy3Group, Strategy3Subgroup, Strategy3
        from poms.portfolios.models import Portfolio
        from poms.transactions.models import TransactionTypeGroup, TransactionType, Transaction, ComplexTransaction
        from poms.tags.models import Tag
        from poms.ui.models import Dashboard

        models = [AccountType, Account, Currency, CurrencyHistory, InstrumentType, Instrument, PriceHistory,
                  PricingPolicy, CounterpartyGroup, Counterparty, Responsible, ResponsibleGroup, Portfolio,
                  TransactionTypeGroup, TransactionType, Transaction, ComplexTransaction, Tag,
                  PriceHistoryError, CurrencyHistoryError,
                  Strategy1Group, Strategy1Subgroup, Strategy1,
                  Strategy2Group, Strategy2Subgroup, Strategy2,
                  Strategy3Group, Strategy3Subgroup, Strategy3,
                  BalanceReport, PLReport, PerformanceReport, CashFlowReport, TransactionReport,
                  InstrumentAudit, TransactionAudit, ObjectHistory4Entry, AuthLogEntry,
                  Dashboard]
        ctypes = [ContentType.objects.get_for_model(model).pk for model in models]
        return queryset.filter(pk__in=ctypes).order_by('model')


class MyLayoutFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        return queryset.filter(mamber=request.user.member)
