import logging
import time
from datetime import timedelta

from django.core.cache import cache
from django_filters.rest_framework import FilterSet
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from poms.common.filters import CharFilter, NoOpFilter
from poms.common.utils import get_closest_bday_of_yesterday
from poms.common.views import AbstractModelViewSet, AbstractViewSet
from poms.reports.models import (
    BalanceReportCustomField,
    PLReportCustomField,
    ReportSummary,
    ReportSummaryInstance,
    TransactionReportCustomField,
)
from poms.reports.performance_report import PerformanceReportBuilder
from poms.reports.serializers import (
    BackendBalanceReportGroupsSerializer,
    BackendBalanceReportItemsSerializer,
    BackendPLReportGroupsSerializer,
    BackendPLReportItemsSerializer,
    BackendTransactionReportGroupsSerializer,
    BackendTransactionReportItemsSerializer,
    BalanceReportCustomFieldSerializer,
    BalanceReportSerializer,
    PerformanceReportSerializer,
    PLReportCustomFieldSerializer,
    PLReportSerializer,
    PriceHistoryCheckSerializer,
    SummarySerializer,
    TransactionReportCustomFieldSerializer,
    TransactionReportSerializer,
)
from poms.reports.sql_builders.balance import BalanceReportBuilderSql
from poms.reports.sql_builders.pl import PLReportBuilderSql
from poms.reports.sql_builders.price_checkers import PriceHistoryCheckerSql
from poms.reports.sql_builders.transaction import TransactionReportBuilderSql
from poms.reports.utils import generate_report_unique_hash
from poms.transactions.models import Transaction
from poms.users.filters import OwnerByMasterUserFilter

_l = logging.getLogger("poms.reports")


class BalanceReportCustomFieldFilterSet(FilterSet):
    id = NoOpFilter()
    name = CharFilter()

    class Meta:
        model = BalanceReportCustomField
        fields = []


class BalanceReportCustomFieldViewSet(AbstractModelViewSet):
    queryset = BalanceReportCustomField.objects.select_related("master_user")
    serializer_class = BalanceReportCustomFieldSerializer
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    filter_class = BalanceReportCustomFieldFilterSet
    ordering_fields = [
        "name",
    ]


class PLReportCustomFieldFilterSet(FilterSet):
    id = NoOpFilter()
    name = CharFilter()

    class Meta:
        model = PLReportCustomField
        fields = []


class PLReportCustomFieldViewSet(AbstractModelViewSet):
    queryset = PLReportCustomField.objects.select_related("master_user")
    serializer_class = PLReportCustomFieldSerializer
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    filter_class = PLReportCustomFieldFilterSet
    ordering_fields = [
        "name",
    ]


class TransactionReportCustomFieldFilterSet(FilterSet):
    id = NoOpFilter()
    name = CharFilter()

    class Meta:
        model = TransactionReportCustomField
        fields = []


class TransactionReportCustomFieldViewSet(AbstractModelViewSet):
    queryset = TransactionReportCustomField.objects.select_related("master_user")
    serializer_class = TransactionReportCustomFieldSerializer
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    filter_class = TransactionReportCustomFieldFilterSet
    ordering_fields = [
        "name",
    ]


# TODO implement Pure Balance Report as separate module
class BalanceReportViewSet(AbstractViewSet):
    serializer_class = BalanceReportSerializer

    @action(detail=False, methods=["get"], url_path="attributes")
    def list_attributes(self, request, *args, **kwargs):
        items = [
            {
                "key": "name",
                "name": "Name",
                "value_type": 10,
            },
            {
                "key": "short_name",
                "name": "Short name",
                "value_type": 10,
            },
            {
                "key": "user_code",
                "name": "User code",
                "value_type": 10,
            },
            {
                "key": "item_type_name",
                "name": "Item Type",
                "value_type": 10,
            },
            {
                "key": "fx_rate",
                "name": "FX Rate",
                "value_type": 20,
            },
            {
                "key": "position_size",
                "name": "Position size",
                "value_type": 20,
            },
            {
                "key": "nominal_position_size",
                "name": "Nominal Position size",
                "value_type": 20,
            },
            {
                "key": "pricing_currency",
                "name": "Pricing Currency",
                "value_type": "field",
                "value_entity": "currency",
                "value_content_type": "currencies.currency",
                "code": "user_code",
            },
            {
                "key": "instrument_pricing_currency_fx_rate",
                "name": "Pricing currency fx rate",
                "value_type": 20,
            },
            {
                "key": "instrument_accrued_currency_fx_rate",
                "name": "Accrued currency fx rate",
                "value_type": 20,
            },
            {
                "key": "instrument_accrual_object_accrual_size",
                "name": "Current Payment Size",
                "value_type": 20,
            },
            {
                "key": "instrument_accrual_object_periodicity_object_name",
                "name": "Current Payment Frequency",
                "value_type": 20,
            },
            {
                "key": "instrument_accrual_object_periodicity_n",
                "name": "Current Payment Periodicity N",
                "value_type": 20,
            },
            {
                "key": "date",
                "name": "Date",
                "value_type": 40,
            },
            {
                "key": "ytm",
                "name": "YTM",
                "value_type": 20,
            },
            {
                "key": "modified_duration",
                "name": "Modified duration",
                "value_type": 20,
            },
            {
                "key": "last_notes",
                "name": "Last notes",
                "value_type": 10,
            },
            {
                "key": "gross_cost_price_loc",
                "name": "Gross cost price (Pricing Currency)",
                "value_type": 20,
            },
            {
                "key": "ytm_at_cost",
                "name": "YTM at cost",
                "value_type": 20,
            },
            {
                "key": "time_invested",
                "name": "Time invested",
                "value_type": 20,
            },
            {
                "key": "return_annually",
                "name": "Return annually",
                "value_type": 20,
            },
            {
                "key": "return_annually_fixed",
                "name": "Return Annually Fixed",
                "value_type": 20,
            },
            {
                "key": "net_cost_price_loc",
                "name": "Net cost price (Pricing Currency)",
                "value_type": 20,
            },
            {
                "key": "currency",
                "name": "Currency",
                "value_type": "field",
                "value_entity": "currency",
                "value_content_type": "currencies.currency",
                "code": "user_code",
            },
            {
                "key": "exposure_currency",
                "name": " Exposure Currency",
                "value_type": "field",
                "value_entity": "currency",
                "value_content_type": "currencies.currency",
                "code": "user_code",
            },
            {
                "key": "principal_invested",
                "name": "Principal invested",
                "value_type": 20,
            },
            {
                "key": "principal_invested_loc",
                "name": "Principal invested (Pricing Currency)",
                "value_type": 20,
            },
            {
                "key": "amount_invested",
                "name": "Amount invested",
                "value_type": 20,
            },
            {
                "key": "amount_invested_loc",
                "name": "Amount invested (Pricing Currency)",
                "value_type": 20,
            },
            {
                "key": "principal_invested_fixed",
                "name": "Principal invested Fixed",
                "value_type": 20,
            },
            {
                "key": "principal_invested_fixed_loc",
                "name": "Principal invested Fixed (Pricing Currency)",
                "value_type": 20,
            },
            {
                "key": "amount_invested_fixed",
                "name": "Amount invested Fixed",
                "value_type": 20,
            },
            {
                "key": "amount_invested_fixed_loc",
                "name": "Amount invested Fixed (Pricing Currency)",
                "value_type": 20,
            },
            {
                "key": "market_value",
                "name": "Market value",
                "value_type": 20,
            },
            {
                "key": "market_value_loc",
                "name": "Market value (Pricing Currency)",
                "value_type": 20,
            },
            {
                "key": "market_value_percent",
                "name": "Market value %",
                "value_type": 20,
            },
            {
                "key": "exposure",
                "name": "Exposure",
                "value_type": 20,
            },
            {
                "key": "exposure_percent",
                "name": "Exposure %",
                "value_type": 20,
            },
            {
                "key": "exposure_loc",
                "name": "Exposure (Pricing Currency)",
                "value_type": 20,
            },
            {
                "key": "instrument_principal_price",
                "name": "Current Price",
                "value_type": 20,
            },
            {
                "key": "instrument_accrued_price",
                "name": "Current Accrued",
                "value_type": 20,
            },
            {
                "key": "instrument_factor",
                "name": "Factor",
                "value_type": 20,
            },
            {
                "key": "instrument_ytm",
                "name": "Current YTM",
                "value_type": 20,
            },
            {
                "key": "detail",
                "name": "Transaction Detail",
                "value_type": 10,
            },
        ]

        result = {"count": len(items), "next": None, "previous": None, "results": items}

        return Response(result)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        instance.auth_time = self.auth_time

        builder = BalanceReportBuilderSql(instance=instance)
        instance = builder.build_balance()

        instance.task_id = 1
        instance.task_status = "SUCCESS"

        serialize_report_st = time.perf_counter()
        serializer = self.get_serializer(instance=instance, many=False)

        _l.info(
            "Balance Report done: %s"
            % "{:3.3f}".format(time.perf_counter() - serialize_report_st)
        )

        return Response(serializer.data, status=status.HTTP_200_OK)


class SummaryViewSet(AbstractViewSet):
    serializer_class = SummarySerializer

    def list(self, request):
        serializer = self.get_serializer(data=request.GET)
        serializer.is_valid(raise_exception=True)

        validated_data = serializer.validated_data

        _l.info(f"Validated_data {validated_data} ")

        calculate_new = validated_data["calculate_new"]

        date_from = validated_data["date_from"]
        date_to = validated_data["date_to"]
        portfolios = validated_data["portfolios"]
        currency = validated_data["currency"]
        pricing_policy = validated_data["pricing_policy"]
        allocation_mode = validated_data["allocation_mode"]

        if not date_to:
            date_to = get_closest_bday_of_yesterday()

        if date_from >= date_to:
            date_from = date_to - timedelta(days=1)

        _l.info(f"SummaryViewSet.list.date_from {date_from} date_to {date_to}")

        summary_record_count = ReportSummaryInstance.objects.filter(
            member=request.user.member,
            owner=request.user.member,
            date_from=date_from,
            date_to=date_to,
            portfolios=portfolios,
            pricing_policy=pricing_policy,
            currency=currency,
            allocation_mode=allocation_mode,
        ).count()

        _l.info(f"summary_record_count {summary_record_count}")

        if calculate_new or summary_record_count == 0:
            bundles = []

            context = self.get_serializer_context()

            report_summary = ReportSummary(
                date_from,
                date_to,
                portfolios,
                bundles,
                currency,
                pricing_policy,
                allocation_mode,
                request.user.master_user,
                request.user.member,
                context,
            )

            report_summary.build_balance()
            report_summary.build_pl_range()
            report_summary.build_pl_daily()
            report_summary.build_pl_mtd()
            report_summary.build_pl_ytd()

            result = {
                "total": {
                    "nav": report_summary.get_nav(),
                    "pl_range": report_summary.get_total_pl_range(),
                    "pl_range_percent": report_summary.get_total_position_return_pl_range(),  # deprecated, wrong figures
                    "pl_daily": report_summary.get_total_pl_daily(),
                    "pl_daily_percent": report_summary.get_total_position_return_pl_daily(),  # deprecated, wrong figures
                    "pl_mtd": report_summary.get_total_pl_mtd(),
                    "pl_mtd_percent": report_summary.get_total_position_return_pl_mtd(),  # deprecated, wrong figures
                    "pl_ytd": report_summary.get_total_pl_ytd(),
                    "pl_ytd_percent": report_summary.get_total_position_return_pl_ytd(),  # deprecated, wrong figures
                },
                "performance": {
                    "daily": {
                        "grand_return": report_summary.get_daily_performance(),
                    },
                    "mtd": {
                        "grand_return": report_summary.get_mtd_performance(),
                    },
                    "ytd": {
                        "grand_return": report_summary.get_ytd_performance(),
                    },
                },
            }

            report_summary_record = ReportSummaryInstance.objects.create(
                master_user=request.user.master_user,
                member=request.user.member,
                owner=request.user.member,
                date_from=date_from,
                date_to=date_to,
                portfolios=portfolios,
                currency=currency,
                allocation_mode=allocation_mode,
                pricing_policy=pricing_policy,
                data=result,
            )

        else:
            report_summary_record = ReportSummaryInstance.objects.filter(
                member=request.user.member,
                owner=request.user.member,
                date_from=date_from,
                date_to=date_to,
                portfolios=portfolios,
                allocation_mode=allocation_mode,
                currency=currency,
            ).last()

            result = report_summary_record.data

        result["report_summary_id"] = report_summary_record.id
        result["created"] = report_summary_record.created

        return Response(result)

    @action(detail=False, methods=["get"], url_path="portfolios")
    def list_portfolios(self, request, realm_code=None, space_code=None):
        serializer = self.get_serializer(data=request.GET)
        serializer.is_valid(raise_exception=True)

        validated_data = serializer.validated_data

        _l.info(f"Validated_data {validated_data} ")

        date_from = validated_data["date_from"]
        date_to = validated_data["date_to"]
        portfolios = validated_data["portfolios"]
        currency = validated_data["currency"]

        bundles = []

        if not date_to:
            date_to = get_closest_bday_of_yesterday()

        context = self.get_serializer_context()

        report_summary = ReportSummary(
            date_from,
            date_to,
            portfolios,
            bundles,
            currency,
            None,  # pricing policy
            None,  # allocation _mode
            request.user.master_user,
            request.user.member,
            context,
        )

        report_summary.build_balance()
        report_summary.build_pl_daily()
        report_summary.build_pl_mtd()
        report_summary.build_pl_ytd()
        report_summary.build_pl_inception_to_date()

        results = []

        for portfolio in portfolios:
            result_object = {
                "portfolio": portfolio.id,
                "portfolio_object": {
                    "id": portfolio.id,
                    "name": portfolio.name,
                    "user_code": portfolio.user_code,
                },
                "metrics": {
                    "nav": report_summary.get_nav(portfolio.id),
                    "pl_daily": report_summary.get_total_pl_daily(portfolio.id),
                    "pl_daily_percent": report_summary.get_total_position_return_pl_daily(
                        portfolio.id
                    ),
                    "pl_mtd": report_summary.get_total_pl_mtd(portfolio.id),
                    "pl_mtd_percent": report_summary.get_total_position_return_pl_mtd(
                        portfolio.id
                    ),
                    "pl_ytd": report_summary.get_total_pl_ytd(portfolio.id),
                    "pl_ytd_percent": report_summary.get_total_position_return_pl_ytd(
                        portfolio.id
                    ),
                    "pl_inception_to_date": report_summary.get_total_pl_inception_to_date(
                        portfolio.id
                    ),
                    "pl_inception_to_date_percent": report_summary.get_total_position_return_pl_inception_to_date(
                        portfolio.id
                    ),
                },
            }

            results.append(result_object)

        result = {"results": results}

        return Response(result)


class PLReportViewSet(AbstractViewSet):
    serializer_class = PLReportSerializer

    @action(detail=False, methods=["get"], url_path="attributes")
    def list_attributes(self, request, *args, **kwargs):
        items = [
            {"key": "name", "name": "Name", "value_type": 10},
            {"key": "short_name", "name": "Short name", "value_type": 10},
            {"key": "user_code", "name": "User code", "value_type": 10},
            {"key": "item_type_name", "name": "Item Type", "value_type": 10},
            {"key": "position_size", "name": "Position size", "value_type": 20},
            {
                "key": "nominal_position_size",
                "name": "Nominal Position size",
                "value_type": 20,
            },
            {
                "key": "pricing_currency",
                "name": "Pricing Currency",
                "value_content_type": "currencies.currency",
                "value_entity": "currency",
                "code": "user_code",
                "value_type": "field",
            },
            {
                "key": "instrument_pricing_currency_fx_rate",
                "name": "Pricing currency fx rate",
                "value_type": 20,
            },
            {
                "key": "instrument_accrued_currency_fx_rate",
                "name": "Accrued currency FX rate",
                "value_type": 20,
            },
            {
                "key": "instrument_accrual_object_accrual_size",
                "name": "Current Payment Size",
                "value_type": 20,
            },
            {
                "key": "instrument_accrual_object_periodicity_object_name",
                "name": "Current Payment Frequency",
                "value_type": 20,
            },
            {
                "key": "instrument_accrual_object_periodicity_n",
                "name": "Current Payment Periodicity N",
                "value_type": 20,
            },
            {"key": "date", "name": "Date", "value_type": 40},
            {"key": "ytm", "name": "YTM", "value_type": 20},
            {"key": "ytm_at_cost", "name": "YTM at cost", "value_type": 20},
            {"key": "modified_duration", "name": "Modified duration", "value_type": 20},
            {"key": "last_notes", "name": "Last notes", "value_type": 10},
            {"key": "mismatch", "name": "Mismatch", "value_type": 20},
            {
                "key": "gross_cost_price_loc",
                "name": "Gross cost price (Pricing Currency)",
                "value_type": 20,
            },
            {
                "key": "net_cost_price_loc",
                "name": "Net cost price (Pricing Currency)",
                "value_type": 20,
            },
            {
                "key": "currency",
                "name": "Currency",
                "value_content_type": "currencies.currency",
                "value_entity": "currency",
                "code": "user_code",
                "value_type": "field",
            },
            {"key": "market_value", "name": "Market value", "value_type": 20},
            {
                "key": "market_value_loc",
                "name": "Market value (Pricing Currency)",
                "value_type": 20,
            },
            {"key": "market_value_percent", "name": "Market value %", "value_type": 20},
            {"key": "exposure", "name": "Exposure", "value_type": 20},
            {"key": "exposure_percent", "name": "Exposure %", "value_type": 20},
            {
                "key": "exposure_loc",
                "name": "Exposure (Pricing Currency)",
                "value_type": 20,
            },
            {
                "key": "instrument_principal_price",
                "name": "Current Price",
                "value_type": 20,
            },
            {
                "key": "instrument_accrued_price",
                "name": "Current Accrued",
                "value_type": 20,
            },
            {"key": "instrument_factor", "name": "Factor", "value_type": 20},
            {"key": "detail", "name": "Transaction Detail", "value_type": 10},
        ]

        result = {"count": len(items), "next": None, "previous": None, "results": items}

        return Response(result)

    def create(self, request, *args, **kwargs):
        serialize_report_st = time.perf_counter()

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        builder = PLReportBuilderSql(instance=instance)
        instance = builder.build_report()

        instance.task_id = 1
        instance.task_status = "SUCCESS"

        instance.auth_time = self.auth_time

        serializer = self.get_serializer(instance=instance, many=False)

        _l.debug(
            "PL Report done: %s"
            % "{:3.3f}".format(time.perf_counter() - serialize_report_st)
        )

        return Response(serializer.data, status=status.HTTP_200_OK)

        # Cache (DEPRECATED)
        # serialize_report_st = time.perf_counter()
        #
        # key = generate_report_unique_hash('report', 'pl', request.data, request.user.master_user, request.user.member)
        #
        # cached_data = cache.get(key)
        #
        # if not cached_data:
        #     serializer = self.get_serializer(data=request.data)
        #     serializer.is_valid(raise_exception=True)
        #     instance = serializer.save()
        #
        #     builder = PLReportBuilderSql(instance=instance)
        #     instance = builder.build_report()
        #
        #     instance.task_id = 1
        #     instance.task_status = "SUCCESS"
        #
        #     instance.auth_time = self.auth_time
        #
        #     serializer = self.get_serializer(instance=instance, many=False)
        #
        #     _l.debug('PL Report done: %s' % "{:3.3f}".format(time.perf_counter() - serialize_report_st))
        #
        #     cached_data = serializer.data
        #
        #     cache.set(key, cached_data)
        #
        # return Response(cached_data, status=status.HTTP_200_OK)


class TransactionReportViewSet(AbstractViewSet):
    serializer_class = TransactionReportSerializer

    def create(self, request, *args, **kwargs):
        serialize_report_st = time.perf_counter()

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        builder = TransactionReportBuilderSql(instance=instance)
        instance = builder.build_transaction()

        instance.auth_time = self.auth_time

        instance.task_id = 1
        instance.task_status = "SUCCESS"

        serializer = self.get_serializer(instance=instance, many=False)

        _l.debug(
            "Transaction Report done: %s"
            % "{:3.3f}".format(time.perf_counter() - serialize_report_st)
        )

        return Response(serializer.data, status=status.HTTP_200_OK)

        # Cache (DEPRECATED)
        # serialize_report_st = time.perf_counter()
        #
        # key = generate_report_unique_hash('report', 'transaction', request.data, request.user.master_user,
        #                                   request.user.member)
        #
        # cached_data = cache.get(key)
        #
        # if not cached_data:
        #     serializer = self.get_serializer(data=request.data)
        #     serializer.is_valid(raise_exception=True)
        #     instance = serializer.save()
        #
        #     builder = TransactionReportBuilderSql(instance=instance)
        #     instance = builder.build_transaction()
        #
        #     instance.auth_time = self.auth_time
        #
        #     instance.task_id = 1
        #     instance.task_status = "SUCCESS"
        #
        #     serializer = self.get_serializer(instance=instance, many=False)
        #
        #     _l.debug('Transaction Report done: %s' % "{:3.3f}".format(time.perf_counter() - serialize_report_st))
        #
        #     cached_data = serializer.data
        #
        #     cache.set(key, cached_data)

        # return Response(cached_data, status=status.HTTP_200_OK)


class PriceHistoryCheckViewSet(AbstractViewSet):
    serializer_class = PriceHistoryCheckSerializer

    def create(self, request, *args, **kwargs):
        st = time.perf_counter()

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        builder = PriceHistoryCheckerSql(instance=instance)
        instance = builder.process()

        instance.auth_time = self.auth_time

        instance.task_id = 1
        instance.task_status = "SUCCESS"

        serializer = self.get_serializer(instance=instance, many=False)

        _l.debug(
            "PriceHistoryCheckerSql done: %s"
            % "{:3.3f}".format(time.perf_counter() - st)
        )

        return Response(serializer.data, status=status.HTTP_200_OK)


class PerformanceReportViewSet(AbstractViewSet):
    serializer_class = PerformanceReportSerializer

    @action(detail=False, methods=["get"], url_path="first-transaction-date")
    def filtered_list(self, request, *args, **kwargs):
        from poms.portfolios.models import PortfolioBundle

        bundle = request.query_params.get("bundle", None)

        result = {}

        transactions = Transaction.objects.all()

        if bundle:
            bundle_instance = PortfolioBundle.objects.get(id=bundle)

            portfolios = [item.portfolio_id for item in bundle_instance.registers.all()]

            transactions = transactions.filter(portfolio_id__in=portfolios)

        transactions = transactions.order_by("accounting_date")

        if len(transactions):
            result["code"] = str(transactions[0].complex_transaction.code)
            result["transaction_date"] = str(transactions[0].transaction_date)
            result["accounting_date"] = str(transactions[0].accounting_date)
            result["cash_date"] = str(transactions[0].cash_date)
            result["portfolio"] = {
                "id": transactions[0].portfolio.id,
                "name": transactions[0].portfolio.name,
                "user_code": transactions[0].portfolio.user_code,
            }

        return Response(result)

    def create(self, request, *args, **kwargs):
        serialize_report_st = time.perf_counter()

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        builder = PerformanceReportBuilder(instance=instance)
        instance = builder.build_report()

        instance.task_id = 1
        instance.task_status = "SUCCESS"

        serializer = self.get_serializer(instance=instance, many=False)

        # DEPRECATED
        # key = generate_report_unique_hash(
        #     "report",
        #     "performance",
        #     request.data,
        #     request.user.master_user,
        #     request.user.member,
        # )
        #
        # cached_data = cache.get(key)
        #
        # if not cached_data:
        #     _l.info("Could not find in cache")
        #
        #     serializer = self.get_serializer(data=request.data)
        #     serializer.is_valid(raise_exception=True)
        #     instance = serializer.save()
        #
        #     builder = PerformanceReportBuilder(instance=instance)
        #     instance = builder.build_report()
        #
        #     instance.task_id = 1
        #     instance.task_status = "SUCCESS"
        #
        #     serializer = self.get_serializer(instance=instance, many=False)
        #
        #     _l.debug(
        #         "Performance Report done: %s"
        #         % "{:3.3f}".format(time.perf_counter() - serialize_report_st)
        #     )
        #
        #     cached_data = serializer.data
        #
        #     cache.set(key, cached_data)

        return Response(serializer.data, status=status.HTTP_200_OK)


class BackendBalanceReportViewSet(AbstractViewSet):
    @action(
        detail=False,
        methods=["post"],
        url_path="groups",
        serializer_class=BackendBalanceReportGroupsSerializer,
    )
    def groups(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        instance.auth_time = self.auth_time

        if not instance.report_instance_id:
            # Check to_representation comments to find why is that
            builder = BalanceReportBuilderSql(instance=instance)
            instance = builder.build_balance()

            instance.task_id = 1  # deprecated, but not to remove
            instance.task_status = "SUCCESS"  # deprecated, but not to remove

        serialize_report_st = time.perf_counter()
        serializer = self.get_serializer(instance=instance, many=False)

        _l.info(
            "Balance Report done: %s"
            % "{:3.3f}".format(time.perf_counter() - serialize_report_st)
        )

        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=["post"],
        url_path="items",
        serializer_class=BackendBalanceReportItemsSerializer,
    )
    def items(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        instance.auth_time = self.auth_time

        if (
            not instance.report_instance_id
        ):  # Check to_representation comments to find why is that
            builder = BalanceReportBuilderSql(instance=instance)
            instance = builder.build_balance()

            instance.task_id = 1  # deprecated, but not to remove
            instance.task_status = "SUCCESS"  # deprecated, but not to remove

        serialize_report_st = time.perf_counter()
        serializer = self.get_serializer(instance=instance, many=False)

        _l.info(
            "Balance Report done: %s"
            % "{:3.3f}".format(time.perf_counter() - serialize_report_st)
        )

        return Response(serializer.data, status=status.HTTP_200_OK)


class BackendPLReportViewSet(AbstractViewSet):
    @action(
        detail=False,
        methods=["post"],
        url_path="groups",
        serializer_class=BackendPLReportGroupsSerializer,
    )
    def groups(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        instance.auth_time = self.auth_time

        if (
            not instance.report_instance_id
        ):  # Check to_representation comments to find why is that
            builder = PLReportBuilderSql(instance=instance)
            instance = builder.build_report()

            instance.task_id = 1  # deprecated, but not to remove
            instance.task_status = "SUCCESS"  # deprecated, but not to remove

        serialize_report_st = time.perf_counter()
        serializer = self.get_serializer(instance=instance, many=False)

        _l.info(
            "Balance Report done: %s"
            % "{:3.3f}".format(time.perf_counter() - serialize_report_st)
        )

        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=["post"],
        url_path="items",
        serializer_class=BackendPLReportItemsSerializer,
    )
    def items(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        instance.auth_time = self.auth_time

        if (
            not instance.report_instance_id
        ):  # Check to_representation comments to find why is that
            builder = PLReportBuilderSql(instance=instance)
            instance = builder.build_report()

            instance.task_id = 1
            instance.task_status = "SUCCESS"

        serialize_report_st = time.perf_counter()
        serializer = self.get_serializer(instance=instance, many=False)

        _l.info(
            "Balance Report done: %s"
            % "{:3.3f}".format(time.perf_counter() - serialize_report_st)
        )

        return Response(serializer.data, status=status.HTTP_200_OK)


class BackendTransactionReportViewSet(AbstractViewSet):
    @action(
        detail=False,
        methods=["post"],
        url_path="groups",
        serializer_class=BackendTransactionReportGroupsSerializer,
    )
    def groups(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        instance.auth_time = self.auth_time

        if not instance.report_instance_id:
            # Check to_representation comments to find why is that
            builder = TransactionReportBuilderSql(instance=instance)
            instance = builder.build_transaction()

            instance.task_id = 1  # deprecated, but not to remove
            instance.task_status = "SUCCESS"  # deprecated, but not to remove

        serialize_report_st = time.perf_counter()
        serializer = self.get_serializer(instance=instance, many=False)

        _l.info(
            "Balance Report done: %s"
            % "{:3.3f}".format(time.perf_counter() - serialize_report_st)
        )

        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=["post"],
        url_path="items",
        serializer_class=BackendTransactionReportItemsSerializer,
    )
    def items(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        instance.auth_time = self.auth_time

        if not instance.report_instance_id:
            # Check to_representation comments to find why is that
            builder = TransactionReportBuilderSql(instance=instance)
            instance = builder.build_transaction()

            instance.task_id = 1
            instance.task_status = "SUCCESS"

        serialize_report_st = time.perf_counter()
        serializer = self.get_serializer(instance=instance, many=False)

        _l.info(
            "Balance Report done: %s"
            % "{:3.3f}".format(time.perf_counter() - serialize_report_st)
        )

        return Response(serializer.data, status=status.HTTP_200_OK)
