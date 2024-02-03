from django.contrib.contenttypes.models import ContentType
from rest_framework.filters import BaseFilterBackend

from poms.portfolios.models import PortfolioRegister, PortfolioRegisterRecord, PortfolioHistory, PortfolioType, \
    PortfolioReconcileGroup, PortfolioReconcileHistory
from poms.pricing.models import PriceHistoryError, CurrencyHistoryError
from poms.reports.models import BalanceReport, PLReport, PerformanceReport, CashFlowReport, TransactionReport


class LayoutContentTypeFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        from poms.accounts.models import AccountType, Account
        from poms.currencies.models import Currency, CurrencyHistory
        from poms.instruments.models import InstrumentType, Instrument, PriceHistory, PricingPolicy, GeneratedEvent
        from poms.counterparties.models import Counterparty, Responsible, CounterpartyGroup, ResponsibleGroup
        from poms.strategies.models import Strategy1Group, Strategy1Subgroup, Strategy1, Strategy2Group, \
            Strategy2Subgroup, Strategy2, Strategy3Group, Strategy3Subgroup, Strategy3
        from poms.portfolios.models import Portfolio
        from poms.transactions.models import TransactionTypeGroup, TransactionType, Transaction, ComplexTransaction
        from poms.ui.models import Dashboard

        from poms.integrations.models import ComplexTransactionImportScheme
        from poms.csv_import.models import CsvImportScheme
        models = [AccountType, Account, Currency, InstrumentType, Instrument,
                  PriceHistory, CurrencyHistory,
                  PriceHistoryError, CurrencyHistoryError,
                  PricingPolicy, CounterpartyGroup, Counterparty, Responsible, ResponsibleGroup, PortfolioType,
                  PortfolioReconcileHistory,
                  PortfolioReconcileGroup, Portfolio,
                  PortfolioRegister, PortfolioRegisterRecord, PortfolioHistory,
                  TransactionTypeGroup, TransactionType, Transaction, ComplexTransaction,
                  Strategy1Group, Strategy1Subgroup, Strategy1,
                  Strategy2Group, Strategy2Subgroup, Strategy2,
                  Strategy3Group, Strategy3Subgroup, Strategy3,
                  BalanceReport, PLReport, PerformanceReport, CashFlowReport, TransactionReport,
                  Dashboard, GeneratedEvent, ComplexTransactionImportScheme, CsvImportScheme]
        ctypes = [ContentType.objects.get_for_model(model).pk for model in models]
        return queryset.filter(pk__in=ctypes).order_by('model')


class MyLayoutFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        return queryset.filter(mamber=request.user.member)
