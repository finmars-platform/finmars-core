from __future__ import unicode_literals

import logging
import traceback

from django.core.cache import cache
from django_filters.rest_framework import FilterSet
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.serializers import Serializer

from poms.common.filters import NoOpFilter, CharFilter
from poms.common.views import AbstractModelViewSet, AbstractViewSet
from poms.reports.models import BalanceReportCustomField, PLReportCustomField, TransactionReportCustomField
from poms.reports.performance_report import PerformanceReportBuilder
from poms.reports.serializers import BalanceReportCustomFieldSerializer, PLReportCustomFieldSerializer, \
    TransactionReportCustomFieldSerializer, PerformanceReportSerializer, PriceHistoryCheckSerializer, \
    BalanceReportSerializer, PLReportSerializer, TransactionReportSerializer
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

        _l.info("Create start")

        st = time.perf_counter()

        key = generate_report_unique_hash('report', 'balance', request.data, request.user.master_user,
                                          request.user.member)

        cached_data = cache.get(key)

        if not cached_data:
            _l.info("Could not find in cache")


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

            cached_data = serializer.data

            _l.info('serializer.data.auth_time %s' % serializer.data['auth_time'])
            _l.info('serializer.data.execution_time %s' % serializer.data['execution_time'])
            _l.info('serializer.data.relation_prefetch_time %s' % serializer.data['relation_prefetch_time'])
            _l.info('serializer.data.serialization_time %s' % serializer.data['serialization_time'])

            cache.set(key, cached_data)

        _l.debug('BalanceReportViewSet done: %s' % "{:3.3f}".format(time.perf_counter() - st))

        return Response(cached_data, status=status.HTTP_200_OK)


class PLReportViewSet(AbstractViewSet):
    serializer_class = PLReportSerializer

    def create(self, request, *args, **kwargs):
        serialize_report_st = time.perf_counter()

        key = generate_report_unique_hash('report', 'pl', request.data, request.user.master_user, request.user.member)

        cached_data = cache.get(key)

        if not cached_data:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            instance = serializer.save()

            builder = PLReportBuilderSql(instance=instance)
            instance = builder.build_balance()

            instance.task_id = 1
            instance.task_status = "SUCCESS"

            serializer = self.get_serializer(instance=instance, many=False)

            _l.debug('PL Report done: %s' % "{:3.3f}".format(time.perf_counter() - serialize_report_st))

            cached_data = serializer.data

            cache.set(key, cached_data)

        return Response(cached_data, status=status.HTTP_200_OK)


class TransactionReportViewSet(AbstractViewSet):
    serializer_class = TransactionReportSerializer

    def create(self, request, *args, **kwargs):
        serialize_report_st = time.perf_counter()

        key = generate_report_unique_hash('report', 'transaction', request.data, request.user.master_user,
                                          request.user.member)

        cached_data = cache.get(key)

        if not cached_data:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            instance = serializer.save()

            builder = TransactionReportBuilderSql(instance=instance)
            instance = builder.build_transaction()

            instance.task_id = 1
            instance.task_status = "SUCCESS"

            serializer = self.get_serializer(instance=instance, many=False)

            _l.debug('Balance Report done: %s' % "{:3.3f}".format(time.perf_counter() - serialize_report_st))

            cached_data = serializer.data

            cache.set(key, cached_data)

        return Response(cached_data, status=status.HTTP_200_OK)


class PriceHistoryCheckViewSet(AbstractViewSet):
    serializer_class = PriceHistoryCheckSerializer

    def create(self, request, *args, **kwargs):
        st = time.perf_counter()

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        builder = PriceHistoryCheckerSql(instance=instance)
        instance = builder.process()

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
