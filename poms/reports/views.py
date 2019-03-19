from __future__ import unicode_literals

import logging

from rest_framework.filters import FilterSet

from poms.common.filters import NoOpFilter, CharFilter
from poms.common.views import AbstractModelViewSet, AbstractAsyncViewSet, AbstractReadOnlyModelViewSet, \
    AbstractSyncViewSet, AbstractViewSet
from poms.reports.builders.balance_pl import ReportBuilder
from poms.reports.builders.balance_serializers import BalanceReportSerializer, PLReportSerializer
from poms.reports.builders.cash_flow_projection_serializers import CashFlowProjectionReportSerializer
from poms.reports.builders.performance_serializers import PerformanceReportSerializer
from poms.reports.builders.transaction import TransactionReportBuilder
from poms.reports.builders.transaction_serializers import TransactionReportSerializer
from poms.reports.models import CustomField
from poms.reports.serializers import CustomFieldSerializer
from poms.reports.tasks import balance_report, pl_report, transaction_report, cash_flow_projection_report, \
    performance_report
from poms.users.filters import OwnerByMasterUserFilter

from rest_framework.response import Response
from rest_framework import permissions, status

_l = logging.getLogger('poms.reports')
import time


class CustomFieldFilterSet(FilterSet):
    id = NoOpFilter()
    name = CharFilter()

    class Meta:
        model = CustomField
        fields = []


class CustomFieldViewSet(AbstractModelViewSet):
    queryset = CustomField.objects.select_related(
        'master_user'
    )
    serializer_class = CustomFieldSerializer
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    filter_class = CustomFieldFilterSet
    ordering_fields = [
        'name',
    ]


# class BalanceReportViewSet(AbstractAsyncViewSet):
#     serializer_class = BalanceReportSerializer
#     celery_task = balance_report


class BalanceReportViewSet(AbstractViewSet):
    serializer_class = BalanceReportSerializer


    def create(self, request, *args, **kwargs):
        print('AbstractSyncViewSet create')

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        builder = ReportBuilder(instance=instance)
        instance = builder.build_balance()

        instance.task_id = 1
        instance.task_status = "SUCCESS"


        serialize_report_st = time.perf_counter()

        serializer = self.get_serializer(instance=instance, many=False)

        print('serialize report done: %s' % (time.perf_counter() - serialize_report_st))

        return Response(serializer.data, status=status.HTTP_200_OK)


# class PLReportViewSet(AbstractAsyncViewSet):
#     serializer_class = PLReportSerializer
#     celery_task = pl_report


class PLReportViewSet(AbstractViewSet):
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

        print('serialize report done: %s' % (time.perf_counter() - serialize_report_st))

        return Response(serializer.data, status=status.HTTP_200_OK)
#
# class TransactionReportViewSet(AbstractAsyncViewSet):
#     serializer_class = TransactionReportSerializer
#     celery_task = transaction_report
#
#     def get_serializer_context(self):
#         context = super(TransactionReportViewSet, self).get_serializer_context()
#         context['attributes_hide_objects'] = True
#         context['custom_fields_hide_objects'] = True
#         return context


class TransactionReportViewSet(AbstractViewSet):
    serializer_class = TransactionReportSerializer

    def get_serializer_context(self):
        context = super(TransactionReportViewSet, self).get_serializer_context()
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

        print('serialize report done: %s' % (time.perf_counter() - serialize_report_st))

        return Response(serializer.data, status=status.HTTP_200_OK)



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
