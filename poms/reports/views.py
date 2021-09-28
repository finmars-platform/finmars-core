from __future__ import unicode_literals

import hashlib
import json
import logging

from django_filters.rest_framework import FilterSet

from poms.common.filters import NoOpFilter, CharFilter
from poms.common.views import AbstractModelViewSet, AbstractAsyncViewSet, AbstractReadOnlyModelViewSet, \
    AbstractSyncViewSet, AbstractViewSet
from poms.reports.builders.balance_pl import ReportBuilder
from poms.reports.builders.balance_serializers import BalanceReportSerializer, PLReportSerializer, \
    BalanceReportSqlSerializer, PLReportSqlSerializer, PriceHistoryCheckSqlSerializer
from poms.reports.builders.cash_flow_projection_serializers import CashFlowProjectionReportSerializer
from poms.reports.builders.performance_serializers import PerformanceReportSerializer
from poms.reports.builders.transaction import TransactionReportBuilder
from poms.reports.builders.transaction_serializers import TransactionReportSerializer, TransactionReportSqlSerializer
from poms.reports.models import BalanceReportCustomField, PLReportCustomField, TransactionReportCustomField
from poms.reports.serializers import BalanceReportCustomFieldSerializer, PLReportCustomFieldSerializer, \
    TransactionReportCustomFieldSerializer
from poms.reports.sql_builders.balance import  BalanceReportBuilderSql
from poms.reports.sql_builders.pl import PLReportBuilderSql
from poms.reports.sql_builders.price_checkers import PriceHistoryCheckerSql
from poms.reports.sql_builders.transaction import TransactionReportBuilderSql

from poms.reports.tasks import balance_report, pl_report, transaction_report, cash_flow_projection_report, \
    performance_report
from poms.reports.utils import generate_report_unique_hash
from poms.users.filters import OwnerByMasterUserFilter

from rest_framework.response import Response
from rest_framework import permissions, status

from django.core.cache import cache

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

class BalanceReportViewSet(AbstractAsyncViewSet):
    serializer_class = BalanceReportSerializer
    celery_task = balance_report


class BalanceReportSyncViewSet(AbstractViewSet):
    serializer_class = BalanceReportSerializer


    def create(self, request, *args, **kwargs):
        print('AbstractSyncViewSet create')

        st = time.perf_counter()

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        builder = ReportBuilder(instance=instance)
        instance = builder.build_balance()

        instance.task_id = 1
        instance.task_status = "SUCCESS"

        serializer = self.get_serializer(instance=instance, many=False)

        _l.debug('Balance Report done: %s' % "{:3.3f}".format(time.perf_counter() - st))

        return Response(serializer.data, status=status.HTTP_200_OK)


class BalanceReportSqlSyncViewSet(AbstractViewSet):
    serializer_class = BalanceReportSqlSerializer


    def create(self, request, *args, **kwargs):

        serialize_report_st = time.perf_counter()

        key = generate_report_unique_hash('report', 'balance', request.data, request.user.master_user, request.user.member)

        cached_data = cache.get(key)

        if not cached_data:

            _l.info("Could not find in cache")

            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            instance = serializer.save()

            builder = BalanceReportBuilderSql(instance=instance)
            instance = builder.build_balance()

            instance.task_id = 1
            instance.task_status = "SUCCESS"

            serializer = self.get_serializer(instance=instance, many=False)

            _l.debug('Balance Report done: %s' % "{:3.3f}".format(time.perf_counter() - serialize_report_st))

            cached_data = serializer.data

            cache.set(key, cached_data)

        return Response(cached_data, status=status.HTTP_200_OK)



class PLReportViewSet(AbstractAsyncViewSet):
    serializer_class = PLReportSerializer
    celery_task = pl_report


class PLReportSyncViewSet(AbstractViewSet):
    serializer_class = PLReportSerializer

    def create(self, request, *args, **kwargs):
        print('AbstractSyncViewSet create')

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        builder = ReportBuilder(instance=instance)
        instance = builder.build_pl()

        instance.task_id = 1
        instance.task_status = "SUCCESS"


        serialize_report_st = time.perf_counter()

        serializer = self.get_serializer(instance=instance, many=False)

        _l.debug('serialize report done: %s' % "{:3.3f}".format(time.perf_counter() - serialize_report_st))

        return Response(serializer.data, status=status.HTTP_200_OK)


class PLReportSqlSyncViewSet(AbstractViewSet):
    serializer_class = PLReportSqlSerializer

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


class TransactionReportViewSet(AbstractAsyncViewSet):
    serializer_class = TransactionReportSerializer
    celery_task = transaction_report

    def get_serializer_context(self):
        context = super(TransactionReportViewSet, self).get_serializer_context()
        context['attributes_hide_objects'] = True
        context['custom_fields_hide_objects'] = True
        return context


class TransactionReportSyncViewSet(AbstractViewSet):
    serializer_class = TransactionReportSerializer

    def get_serializer_context(self):
        context = super(TransactionReportSyncViewSet, self).get_serializer_context()
        context['attributes_hide_objects'] = True
        context['custom_fields_hide_objects'] = True
        return context

    def create(self, request, *args, **kwargs):
        print('AbstractSyncViewSet create')

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        builder = TransactionReportBuilder(instance)
        builder.build()
        instance = builder.instance

        instance.task_id = 1
        instance.task_status = "SUCCESS"


        serialize_report_st = time.perf_counter()

        serializer = self.get_serializer(instance=instance, many=False)

        _l.debug('serialize report done: %s' % "{:3.3f}".format(time.perf_counter() - serialize_report_st))

        return Response(serializer.data, status=status.HTTP_200_OK)


class TransactionReportSqlSyncViewSet(AbstractViewSet):
    serializer_class = TransactionReportSqlSerializer

    def create(self, request, *args, **kwargs):

        serialize_report_st = time.perf_counter()

        key = generate_report_unique_hash('report', 'transaction', request.data, request.user.master_user, request.user.member)

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



class CashFlowProjectionReportViewSet(AbstractAsyncViewSet):
    serializer_class = CashFlowProjectionReportSerializer
    celery_task = cash_flow_projection_report

    def get_serializer_context(self):
        context = super(CashFlowProjectionReportViewSet, self).get_serializer_context()
        context['attributes_hide_objects'] = True
        context['custom_fields_hide_objects'] = True
        return context


class PerformanceReportViewSet(AbstractAsyncViewSet):
    serializer_class = PerformanceReportSerializer
    celery_task = performance_report


class PriceHistoryCheckSqlSyncViewSet(AbstractViewSet):
    serializer_class = PriceHistoryCheckSqlSerializer


    def create(self, request, *args, **kwargs):


        serialize_report_st = time.perf_counter()

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        builder = PriceHistoryCheckerSql(instance=instance)
        instance = builder.process()

        instance.task_id = 1
        instance.task_status = "SUCCESS"

        serializer = self.get_serializer(instance=instance, many=False)

        _l.debug('Balance Report done: %s' % "{:3.3f}".format(time.perf_counter() - serialize_report_st))

        return Response(serializer.data, status=status.HTTP_200_OK)
