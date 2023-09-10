from __future__ import unicode_literals

import logging

from django.core.cache import cache
from django_filters.rest_framework import FilterSet
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from poms.common.filters import NoOpFilter, CharFilter
from poms.common.utils import get_closest_bday_of_yesterday
from poms.common.views import AbstractModelViewSet, AbstractViewSet
from poms.reports.models import BalanceReportCustomField, PLReportCustomField, TransactionReportCustomField, \
    ReportSummary
from poms.reports.performance_report import PerformanceReportBuilder
from poms.reports.serializers import BalanceReportCustomFieldSerializer, PLReportCustomFieldSerializer, \
    TransactionReportCustomFieldSerializer, PerformanceReportSerializer, PriceHistoryCheckSerializer, \
    BalanceReportSerializer, PLReportSerializer, TransactionReportSerializer, SummarySerializer, \
    BackendBalanceReportGroupsSerializer, BackendBalanceReportItemsSerializer, BackendPLReportGroupsSerializer, \
    BackendPLReportItemsSerializer
from poms.reports.sql_builders.balance import BalanceReportBuilderSql
from poms.reports.sql_builders.pl import PLReportBuilderSql
from poms.reports.sql_builders.price_checkers import PriceHistoryCheckerSql
from poms.reports.sql_builders.transaction import TransactionReportBuilderSql
from poms.reports.utils import generate_report_unique_hash
from poms.transactions.models import Transaction
from poms.users.filters import OwnerByMasterUserFilter

_l = logging.getLogger('poms.reports')
import time


class BalanceReportCustomFieldFilterSet(FilterSet):
    id = NoOpFilter()
    name = CharFilter()

    class Meta:
        model = BalanceReportCustomField
        fields = []


class BalanceReportCustomFieldViewSet(AbstractModelViewSet):
    queryset = BalanceReportCustomField.objects.select_related(
        'master_user'
    )
    serializer_class = BalanceReportCustomFieldSerializer
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    filter_class = BalanceReportCustomFieldFilterSet
    ordering_fields = [
        'name',
    ]


class PLReportCustomFieldFilterSet(FilterSet):
    id = NoOpFilter()
    name = CharFilter()

    class Meta:
        model = PLReportCustomField
        fields = []


class PLReportCustomFieldViewSet(AbstractModelViewSet):
    queryset = PLReportCustomField.objects.select_related(
        'master_user'
    )
    serializer_class = PLReportCustomFieldSerializer
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    filter_class = PLReportCustomFieldFilterSet
    ordering_fields = [
        'name',
    ]


class TransactionReportCustomFieldFilterSet(FilterSet):
    id = NoOpFilter()
    name = CharFilter()

    class Meta:
        model = TransactionReportCustomField
        fields = []


class TransactionReportCustomFieldViewSet(AbstractModelViewSet):
    queryset = TransactionReportCustomField.objects.select_related(
        'master_user'
    )
    serializer_class = TransactionReportCustomFieldSerializer
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    filter_class = TransactionReportCustomFieldFilterSet
    ordering_fields = [
        'name',
    ]


# TODO implement Pure Balance Report as separate module
class BalanceReportViewSet(AbstractViewSet):
    serializer_class = BalanceReportSerializer

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

        _l.info('Balance Report done: %s' % "{:3.3f}".format(time.perf_counter() - serialize_report_st))

        return Response(serializer.data, status=status.HTTP_200_OK)

        # _l.info("Create start")
        #
        # st = time.perf_counter()
        #
        # key = generate_report_unique_hash('report', 'balance', request.data, request.user.master_user,
        #                                   request.user.member)
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
        #     instance.auth_time = self.auth_time
        #
        #
        #
        #     builder = BalanceReportBuilderSql(instance=instance)
        #     instance = builder.build_balance()
        #
        #     instance.task_id = 1
        #     instance.task_status = "SUCCESS"
        #
        #     serialize_report_st = time.perf_counter()
        #     serializer = self.get_serializer(instance=instance, many=False)
        #
        #     cached_data = serializer.data
        #
        #     _l.info('serializer.data.auth_time %s' % serializer.data['auth_time'])
        #     _l.info('serializer.data.execution_time %s' % serializer.data['execution_time'])
        #     _l.info('serializer.data.relation_prefetch_time %s' % serializer.data['relation_prefetch_time'])
        #     _l.info('serializer.data.serialization_time %s' % serializer.data['serialization_time'])
        #
        #     cache.set(key, cached_data)
        #
        # _l.debug('BalanceReportViewSet done: %s' % "{:3.3f}".format(time.perf_counter() - st))
        #
        # return Response(cached_data, status=status.HTTP_200_OK)


class SummaryViewSet(AbstractViewSet):

    serializer_class = SummarySerializer

    def list(self, request):

        serializer = self.get_serializer(data=request.GET)
        serializer.is_valid(raise_exception=True)

        validated_data = serializer.validated_data

        _l.info("Validated_data %s " % validated_data)

        date_from = validated_data["date_from"]
        date_to = validated_data["date_to"]
        portfolios = validated_data["portfolios"]
        currency = validated_data["currency"]

        bundles = []

        if not date_to:
            date_to = get_closest_bday_of_yesterday()


        context = self.get_serializer_context()

        report_summary = ReportSummary(date_from, date_to, portfolios, bundles, currency, request.user.master_user,
                                       request.user.member, context)

        report_summary.build_balance()
        report_summary.build_pl_daily()
        report_summary.build_pl_mtd()
        report_summary.build_pl_ytd()

        result = {
            "total": {
                "nav": report_summary.get_nav(),
                "pl_daily": report_summary.get_total_pl_daily(),
                "pl_daily_percent": report_summary.get_total_position_return_pl_daily(),
                "pl_mtd": report_summary.get_total_pl_mtd(),
                "pl_mtd_percent": report_summary.get_total_position_return_pl_mtd(),
                "pl_ytd": report_summary.get_total_pl_ytd(),
                "pl_ytd_percent": report_summary.get_total_position_return_pl_ytd()
            }
        }

        return Response(result)

    @action(detail=False, methods=['get'], url_path='portfolios')
    def list_portfolios(self, request):

        serializer = self.get_serializer(data=request.GET)
        serializer.is_valid(raise_exception=True)

        validated_data = serializer.validated_data

        _l.info("Validated_data %s " % validated_data)

        date_from = validated_data["date_from"]
        date_to = validated_data["date_to"]
        portfolios = validated_data["portfolios"]
        currency = validated_data["currency"]

        bundles = []

        if not date_to:
            date_to = get_closest_bday_of_yesterday()


        context = self.get_serializer_context()

        report_summary = ReportSummary(date_from, date_to, portfolios, bundles, currency, request.user.master_user,
                                       request.user.member, context)

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
                    "user_code":  portfolio.user_code
                },
                "metrics": {
                    "nav": report_summary.get_nav(portfolio.id),
                    "pl_daily": report_summary.get_total_pl_daily(portfolio.id),
                    "pl_daily_percent": report_summary.get_total_position_return_pl_daily(portfolio.id),

                    "pl_mtd": report_summary.get_total_pl_mtd(portfolio.id),
                    "pl_mtd_percent": report_summary.get_total_position_return_pl_mtd(portfolio.id),

                    "pl_ytd": report_summary.get_total_pl_ytd(portfolio.id),
                    "pl_ytd_percent": report_summary.get_total_position_return_pl_ytd(portfolio.id),

                    "pl_inception_to_date": report_summary.get_total_pl_inception_to_date(portfolio.id),
                    "pl_inception_to_date_percent": report_summary.get_total_position_return_pl_inception_to_date(portfolio.id),


                }
            }

            results.append(result_object)




        result = {
            "results": results
        }

        return Response(result)

class PLReportViewSet(AbstractViewSet):
    serializer_class = PLReportSerializer

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

        _l.debug('PL Report done: %s' % "{:3.3f}".format(time.perf_counter() - serialize_report_st))

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

        _l.debug('Transaction Report done: %s' % "{:3.3f}".format(time.perf_counter() - serialize_report_st))

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

        _l.debug('PriceHistoryCheckerSql done: %s' % "{:3.3f}".format(time.perf_counter() - st))

        return Response(serializer.data, status=status.HTTP_200_OK)


class PerformanceReportViewSet(AbstractViewSet):
    serializer_class = PerformanceReportSerializer

    @action(detail=False, methods=['get'], url_path='first-transaction-date')
    def filtered_list(self, request, *args, **kwargs):

        bundle = request.query_params.get('bundle', None)

        result = {}

        transactions = Transaction.objects.all()

        if bundle:

            from poms.portfolios.models import PortfolioBundle
            bundle_instance = PortfolioBundle.objects.get(id=bundle)

            portfolios = []

            for item in bundle_instance.registers.all():
                portfolios.append(item.portfolio_id)

            transactions = transactions.filter(portfolio_id__in=portfolios)

        transactions = transactions.order_by('accounting_date')

        if (len(transactions)):
            result['code'] = str(transactions[0].complex_transaction.code)
            result['transaction_date'] = str(transactions[0].transaction_date)
            result['accounting_date'] = str(transactions[0].accounting_date)
            result['cash_date'] = str(transactions[0].cash_date)
            result['portfolio'] = {
                'id': transactions[0].portfolio.id,
                'name': transactions[0].portfolio.name,
                'user_code': transactions[0].portfolio.user_code
            }

        return Response(result)

    def create(self, request, *args, **kwargs):

        serialize_report_st = time.perf_counter()

        key = generate_report_unique_hash('report', 'performance', request.data, request.user.master_user,
                                          request.user.member)

        cached_data = cache.get(key)

        if not cached_data:
            _l.info("Could not find in cache")

            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            instance = serializer.save()

            builder = PerformanceReportBuilder(instance=instance)
            instance = builder.build_report()

            instance.task_id = 1
            instance.task_status = "SUCCESS"

            serializer = self.get_serializer(instance=instance, many=False)

            _l.debug('Performance Report done: %s' % "{:3.3f}".format(time.perf_counter() - serialize_report_st))

            cached_data = serializer.data

            cache.set(key, cached_data)

        return Response(cached_data, status=status.HTTP_200_OK)



class BackendBalanceReportViewSet(AbstractViewSet):

    @action(detail=False, methods=['post'], url_path='groups', serializer_class = BackendBalanceReportGroupsSerializer)
    def groups(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        instance.auth_time = self.auth_time

        if not instance.report_instance_id: # Check to_representation comments to find why is that
            builder = BalanceReportBuilderSql(instance=instance)
            instance = builder.build_balance()

            instance.task_id = 1 # deprecated, but not to remove
            instance.task_status = "SUCCESS" # deprecated, but not to remove

        serialize_report_st = time.perf_counter()
        serializer = self.get_serializer(instance=instance, many=False)

        _l.info('Balance Report done: %s' % "{:3.3f}".format(time.perf_counter() - serialize_report_st))

        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='items', serializer_class = BackendBalanceReportItemsSerializer)
    def items(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        instance.auth_time = self.auth_time

        if not instance.report_instance_id: # Check to_representation comments to find why is that
            builder = BalanceReportBuilderSql(instance=instance)
            instance = builder.build_balance()

            instance.task_id = 1  # deprecated, but not to remove
            instance.task_status = "SUCCESS"  # deprecated, but not to remove

        serialize_report_st = time.perf_counter()
        serializer = self.get_serializer(instance=instance, many=False)

        _l.info('Balance Report done: %s' % "{:3.3f}".format(time.perf_counter() - serialize_report_st))

        return Response(serializer.data, status=status.HTTP_200_OK)



class BackendPLReportViewSet(AbstractViewSet):

    @action(detail=False, methods=['post'], url_path='groups', serializer_class = BackendPLReportGroupsSerializer)
    def groups(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        instance.auth_time = self.auth_time

        if not instance.report_instance_id: # Check to_representation comments to find why is that
            builder = PLReportBuilderSql(instance=instance)
            instance = builder.build_report()

            instance.task_id = 1  # deprecated, but not to remove
            instance.task_status = "SUCCESS"  # deprecated, but not to remove

        serialize_report_st = time.perf_counter()
        serializer = self.get_serializer(instance=instance, many=False)

        _l.info('Balance Report done: %s' % "{:3.3f}".format(time.perf_counter() - serialize_report_st))

        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='items', serializer_class = BackendPLReportItemsSerializer)
    def items(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        instance.auth_time = self.auth_time

        if not instance.report_instance_id: # Check to_representation comments to find why is that
            builder = PLReportBuilderSql(instance=instance)
            instance = builder.build_report()

            instance.task_id = 1
            instance.task_status = "SUCCESS"

        serialize_report_st = time.perf_counter()
        serializer = self.get_serializer(instance=instance, many=False)

        _l.info('Balance Report done: %s' % "{:3.3f}".format(time.perf_counter() - serialize_report_st))

        return Response(serializer.data, status=status.HTTP_200_OK)