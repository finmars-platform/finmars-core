from logging import getLogger

from django_filters.rest_framework import DjangoFilterBackend, FilterSet
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from celery.result import AsyncResult

from poms.common.filters import CharFilter
from poms.common.views import AbstractApiView, AbstractViewSet
from poms.users.filters import OwnerByMasterUserFilter

from .filters import CeleryTaskDateRangeFilter, CeleryTaskQueryFilter
from .models import CeleryTask, CeleryWorker
from .serializers import (
    CeleryTaskLightSerializer,
    CeleryTaskSerializer,
    CeleryWorkerSerializer,
)

_l = getLogger("poms.celery_tasks")


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
        "master_user",
        "member",
        "parent",
        "file_report",
        "parent__file_report",
    ).prefetch_related("attachments", "children")
    serializer_class = CeleryTaskSerializer
    filter_class = CeleryTaskFilterSet
    filter_backends = [
        CeleryTaskDateRangeFilter,
        CeleryTaskQueryFilter,
        DjangoFilterBackend,
        OwnerByMasterUserFilter,
    ]

    @action(
        detail=False,
        methods=["get"],
        url_path="light",
        serializer_class=CeleryTaskLightSerializer,
    )
    def list_light(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginator.post_paginate_queryset(queryset, request)
        serializer = self.get_serializer(page, many=True)

        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=["get"], url_path="status")
    def status(self, request, pk=None):
        celery_task_id = request.query_params.get("celery_task_id", None)
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

    @action(detail=False, methods=["post"], url_path="execute")
    def execute(self, request, pk=None):
        from poms_app import celery_app

        task_name = request.data.get("task_name")
        options = request.data.get("options")

        celery_task = CeleryTask.objects.create(
            master_user=request.user.master_user,
            member=request.user.member,
            type=task_name,
            options_object=options,
        )

        result = celery_app.send_task(task_name, kwargs={"task_id": celery_task.id})

        _l.info(f"result {result}")

        return Response(
            {
                "status": "ok",
                "task_id": celery_task.id,
                "celery_task_id": result.id,
            }
        )

    @action(detail=True, methods=["PUT"], url_path="cancel")
    def cancel(self, request, pk=None):
        task = CeleryTask.objects.get(pk=pk)

        task.cancel()

        return Response({"status": "ok"})

    @action(detail=True, methods=["PUT"], url_path="abort-transaction-import")
    def abort_transaction_import(self, request, pk=None):
        from poms_app import celery_app
        from poms.transactions.models import ComplexTransaction

        task = CeleryTask.objects.get(pk=pk)

        count = ComplexTransaction.objects.filter(linked_import_task=pk).count()

        codes = ComplexTransaction.objects.filter(linked_import_task=pk).values_list(
            "code", flat=True
        )

        complex_transactions_ids = list(
            ComplexTransaction.objects.filter(linked_import_task=pk).values_list(
                "id", flat=True
            )
        )

        options_object = {
            "content_type": "transactions.complextransaction",
            "ids": complex_transactions_ids,
        }

        celery_task = CeleryTask.objects.create(
            master_user=request.user.master_user,
            member=request.user.member,
            options_object=options_object,
            verbose_name="Bulk Delete",
            type="bulk_delete",
        )

        celery_app.send_task(
            "celery_tasks.bulk_delete",
            kwargs={"task_id": celery_task.id},
            queue="backend-background-queue",
        )

        _l.info(f"{count} complex transactions were deleted")

        task.notes = f"{count} Transactions were aborted \n" + (
            ", ".join(str(x) for x in codes)
        )
        task.status = CeleryTask.STATUS_TRANSACTIONS_ABORTED

        task.save()

        return Response({"status": "ok"})


class CeleryStatsViewSet(AbstractViewSet):
    def list(self, request, *args, **kwargs):
        from poms_app.celery import app

        i = app.control.inspect()
        # d = i.active()
        # workers = list(d.keys()) if d else []

        stats = i.stats()

        return Response(stats)


class CeleryWorkerFilterSet(FilterSet):
    id = CharFilter()
    worker_name = CharFilter()
    queue = CharFilter()
    worker_type = CharFilter()
    notes = CharFilter()

    class Meta:
        model = CeleryWorker
        fields = []


class CeleryWorkerViewSet(AbstractApiView, ModelViewSet):
    queryset = CeleryWorker.objects.all()
    serializer_class = CeleryWorkerSerializer
    filter_class = CeleryWorkerFilterSet
    filter_backends = []

    def update(self, request, *args, **kwargs):
        # Workers could not be updated for now,
        # Consider delete and creating new
        raise PermissionDenied()

    @action(detail=True, methods=["PUT"], url_path="create-worker")
    def create_worker(self, request, pk=None):
        worker = self.get_object()

        worker.create_worker()

        return Response({"status": "ok"})

    @action(detail=True, methods=["PUT"], url_path="start")
    def start(self, request, pk=None):
        worker = self.get_object()

        worker.start()

        return Response({"status": "ok"})

    @action(detail=True, methods=["PUT"], url_path="stop")
    def stop(self, request, pk=None):
        worker = self.get_object()

        worker.stop()

        return Response({"status": "ok"})

    @action(detail=True, methods=["PUT"], url_path="restart")
    def restart(self, request, pk=None):
        worker = self.get_object()

        worker.restart()

        return Response({"status": "ok"})

    @action(detail=True, methods=["GET"], url_path="status")
    def status(self, request, pk=None):
        worker = self.get_object()

        worker.get_status()

        return Response({"status": "ok"})

    def perform_destroy(self, instance):
        instance.delete_worker()
        return super(CeleryWorkerViewSet, self).perform_destroy(instance)
