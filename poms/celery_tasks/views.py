import json

from celery.result import AsyncResult

from django_filters.rest_framework import FilterSet, DjangoFilterBackend
from rest_framework.response import Response
from rest_framework.viewsets import  ModelViewSet

from poms.common.views import AbstractApiView
from .filters import CeleryTaskQueryFilter
from .models import CeleryTask
from .serializers import CeleryTaskSerializer
from poms.common.filters import CharFilter
from poms.users.filters import OwnerByMasterUserFilter

from rest_framework.decorators import action

from logging import getLogger



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

    @action(detail=True, methods=['get'], url_path='cancel')
    def cancel(self, request, pk=None):

        celery_task_id = request.query_params.get('celery_task_id', None)
        async_result = AsyncResult(celery_task_id).revoke()

        return Response({'status': 'ok'})

    @action(detail=True, methods=['get'], url_path='abort-import')
    def abort_import(self, request, pk=None):

        task = CeleryTask.objects.get(pk=pk)

        from poms.transactions.models import ComplexTransaction

        count = ComplexTransaction.objects.filter(linked_import_task=pk).count()

        complex_transactions = ComplexTransaction.objects.filter(linked_import_task=pk).delete()

        _l.info("%s complex transactions were deleted" % count)

        return Response({'status': 'ok'})
