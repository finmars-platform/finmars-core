import json
from logging import getLogger

from celery.result import AsyncResult
from celery import current_app
from django_filters.rest_framework import DjangoFilterBackend, FilterSet
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from poms.common.filters import CharFilter
from poms.common.views import AbstractApiView, AbstractViewSet
from poms.users.filters import OwnerByMasterUserFilter
from .filters import CeleryTaskDateRangeFilter, CeleryTaskQueryFilter
from .models import CeleryTask, CeleryWorker
from .serializers import (
    CeleryTaskLightSerializer,
    CeleryTaskSerializer,
    CeleryTaskUpdateStatusSerializer,
    CeleryWorkerSerializer,
    CeleryTaskRelaunchSerializer,
)

_l = getLogger("poms.celery_tasks")


class CeleryTaskFilterSet(FilterSet):
    id = CharFilter()
    celery_task_id = CharFilter()
    status = CharFilter()
    statuses = CharFilter(field_name='status', method='filter_status__in')
    type = CharFilter()
    types = CharFilter(field_name='type', method='filter_type__in')
    created_at = CharFilter()

    class Meta:
        model = CeleryTask
        fields = ["status", "type", ]

    @staticmethod
    def filter_status__in(queryset, _, value):
        return queryset.filter(status__in=value.split(','))

    @staticmethod
    def filter_type__in(queryset, _, value):
        return queryset.filter(type__in=value.split(','))


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
        result = self.request.query_params.get("result")

        if result:

            result = result.split(",")

            for filter_condition in result:
                if filter_condition not in ["success", "error", "skip"]:
                    return Response(
                        {
                            "status": status.HTTP_404_NOT_FOUND,
                            "message": f"Invalid condition for a filter by result: {filter_condition}",
                            "results": [],
                        }
                    )

            include_tasks_list = []

            for task in queryset:

                if not task.result:
                    continue

                result_object = json.loads(task.result)

                items = result_object.get("items")

                if items is not None:

                    for item in items:
                        if item["status"] in result:
                            include_tasks_list.append(task.pk)
                            break

            if include_tasks_list:
                queryset = queryset.filter(pk__in=include_tasks_list)
            else:
                queryset = CeleryTask.objects.none()

        page = self.paginate_queryset(queryset)

        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=["get"], url_path="status")
    def status(self, request, pk=None, realm_code=None, space_code=None):
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

    @action(detail=True, methods=["post"], url_path="update-status", serializer_class=CeleryTaskUpdateStatusSerializer)
    def update_status(self, request, pk=None, *args, **kwargs):
        task = CeleryTask.objects.get(pk=pk)
        if task.status in (CeleryTask.STATUS_ERROR, CeleryTask.STATUS_CANCELED):
            response = {"status": "ignored", "error_message": "Task is already finished, update impossible"}
            return Response(response)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        new_status = data["status"]
        if new_status == "error":
            task.status = CeleryTask.STATUS_ERROR
            if data.get("error"):
                task.error_message = request.data["error"]
                task.result = None
        elif new_status == "success":
            task.status = CeleryTask.STATUS_DONE
        elif new_status == "timeout":
            task.status = CeleryTask.STATUS_TIMEOUT
        elif new_status == CeleryTask.STATUS_CANCELED:
            task.cancel()
        else:
            raise ValidationError("unknown status value")
        if data.get("result"):
            task.result_object = data["result"]
        task.save()

        return Response({"status": "ok"})

    @action(detail=False, methods=["post"], url_path="execute")
    def execute(self, request, pk=None, realm_code=None, space_code=None):
        from poms_app import celery_app

        task_name = request.data.get("task_name")
        options = request.data.get("options")

        celery_task = CeleryTask.objects.create(
            master_user=request.user.master_user,
            member=request.user.member,
            type=task_name,
            options_object=options,
        )

        result = celery_app.send_task(task_name, kwargs={"task_id": celery_task.id, "context": {"realm_code": celery_task.master_user.realm_code, "space_code": celery_task.master_user.space_code}})

        _l.info(f"result {result}")

        return Response(
            {
                "status": "ok",
                "task_id": celery_task.id,
                "celery_task_id": result.id,
            }
        )

    @action(detail=True, methods=["PUT"], url_path="cancel")
    def cancel(self, request, pk=None, realm_code=None, space_code=None):
        task = CeleryTask.objects.get(pk=pk)

        task.cancel()

        return Response({"status": "ok"})

    @action(detail=True, methods=["PUT"], url_path="abort-transaction-import")
    def abort_transaction_import(self, request, pk=None, realm_code=None, space_code=None):
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
            kwargs={"task_id": celery_task.id, "context": {"realm_code": celery_task.master_user.realm_code, "space_code": celery_task.master_user.space_code}},
            queue="backend-background-queue",
        )

        _l.info(f"{count} complex transactions were deleted")

        task.notes = f"{count} Transactions were aborted \n" + (
            ", ".join(str(x) for x in codes)
        )
        task.status = CeleryTask.STATUS_TRANSACTIONS_ABORTED

        task.save()

        return Response({"status": "ok"})

    @action(detail=True, methods=["post"], url_path="relaunch", serializer_class=CeleryTaskRelaunchSerializer)
    def relaunch(self, request, pk=None, realm_code=None, space_code=None):
        from poms_app import celery_app

        completed_task = CeleryTask.objects.get(pk=pk)
        options = request.data.get("options", None)
        if not options:
            options = completed_task.options_object

        full_task_name = None
        for registered_task_name in current_app.tasks.keys():
            if completed_task.type in registered_task_name:
                full_task_name = registered_task_name
                _l.info(f"relaunch - full task name is {full_task_name}")
                break
        else:
            err_message = f"Сan't match task {completed_task.type} with any full names of tasks."
            _l.error(err_message)
            return Response(
                {
                    "status": "error",
                    "task_id": completed_task.id,
                    "error_message": err_message,
                },
                status=400,
            )

        reloaded_task = CeleryTask.objects.create(
            master_user=completed_task.master_user,
            member=completed_task.member,
            type=completed_task.type,
            verbose_name=completed_task.verbose_name,
            options_object=options,
        )

        new_celery_task = celery_app.send_task(
            full_task_name,
            kwargs= {
                "task_id": reloaded_task.id,
                "context": {
                    "realm_code": reloaded_task.master_user.realm_code,
                    "space_code": reloaded_task.master_user.space_code,
                }
            }
        )

        _l.info(f"relaunch - result is {new_celery_task}")

        return Response(
            {
                "status": "ok",
                "task_id": reloaded_task.id,
                "celery_task_id": new_celery_task.id,
            }
        )


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
    def create_worker(self, request, pk=None, realm_code=None, space_code=None):
        worker = self.get_object()

        worker.create_worker(request.realm_code)

        return Response({"status": "ok"})

    @action(detail=True, methods=["PUT"], url_path="start")
    def start(self, request, pk=None, realm_code=None, space_code=None):
        worker = self.get_object()

        worker.start(request.realm_code)

        return Response({"status": "ok"})

    @action(detail=True, methods=["PUT"], url_path="stop")
    def stop(self, request, pk=None, realm_code=None, space_code=None):
        worker = self.get_object()

        worker.stop(request.realm_code)

        return Response({"status": "ok"})

    @action(detail=True, methods=["PUT"], url_path="restart")
    def restart(self, request, pk=None, realm_code=None, space_code=None):
        worker = self.get_object()

        worker.restart(request.realm_code)

        return Response({"status": "ok"})

    @action(detail=True, methods=["GET"], url_path="status")
    def status(self, request, pk=None, realm_code=None, space_code=None):
        worker = self.get_object()

        worker.get_status(request.realm_code)

        return Response({"status": "ok"})

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance, request)
        except Exception as e:
            pass
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_destroy(self, instance, request):
        instance.delete_worker(request.realm_code)
        return super(CeleryWorkerViewSet, self).perform_destroy(instance)
