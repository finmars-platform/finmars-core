from logging import getLogger

from celery.result import AsyncResult
from django_filters.rest_framework import FilterSet, DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from poms.common.filters import CharFilter
from poms.common.views import AbstractApiView
from poms.users.filters import OwnerByMasterUserFilter
from .filters import CeleryTaskQueryFilter
from .models import CeleryTask
from .serializers import CeleryTaskSerializer

_l = getLogger('poms.celery_tasks')


class CeleryTaskFilterSet(FilterSet):
    id = CharFilter()
    celery_task_id = CharFilter()
    status = CharFilter()
    type = CharFilter()
    created = CharFilter()

    class Meta:
        model = CeleryTask
        fields = []


class CeleryTaskViewSet(AbstractApiView, ModelViewSet):
    queryset = CeleryTask.objects.select_related(
        'master_user'
    )
    serializer_class = CeleryTaskSerializer
    filter_class = CeleryTaskFilterSet
    filter_backends = [
        CeleryTaskQueryFilter,
        DjangoFilterBackend,
        OwnerByMasterUserFilter,
    ]

    @action(detail=True, methods=['get'], url_path='status')
    def status(self, request, pk=None):
        celery_task_id = request.query_params.get('celery_task_id', None)
        async_result = AsyncResult(celery_task_id)

        result = {
            "app": str(async_result.app),
            "id": async_result.id,
            "state": async_result.state,
            "result": async_result.result,
            "date_done": str(async_result.date_done),
            "traceback": str(async_result.traceback),
        }

        return Response(result)

    @action(detail=False, methods=['post'], url_path='execute')
    def execute(self, request, pk=None):

        from poms_app import celery_app

        task_name = request.data.get('task_name')
        payload = request.data.get('payload')

        result = celery_app.send_task(task_name, kwargs={'payload': payload})

        _l.info('result %s' % result)

        return Response({'status': 'ok', 'task_id': None, 'celery_task_id': result.id})

    @action(detail=True, methods=['PUT'], url_path='cancel')
    def cancel(self, request, pk=None):
        celery_task_id = request.query_params.get('celery_task_id', None)
        async_result = AsyncResult(celery_task_id).revoke()

        task = CeleryTask.objects.get(pk=pk)

        task.status = CeleryTask.STATUS_CANCELED

        task.save()

        return Response({'status': 'ok'})

    @action(detail=True, methods=['PUT'], url_path='abort-transaction-import')
    def abort_transaction_import(self, request, pk=None):
        task = CeleryTask.objects.get(pk=pk)

        from poms.transactions.models import ComplexTransaction

        count = ComplexTransaction.objects.filter(linked_import_task=pk).count()

        codes = ComplexTransaction.objects.filter(linked_import_task=pk).values_list('code', flat=True)

        complex_transactions = ComplexTransaction.objects.filter(linked_import_task=pk).delete()

        _l.info("%s complex transactions were deleted" % count)

        task.notes = '%s Transactions were aborted \n' % count

        task.notes = task.notes + (', '.join(str(x) for x in codes))
        task.status = CeleryTask.STATUS_TRANSACTIONS_ABORTED

        task.save()

        return Response({'status': 'ok'})
