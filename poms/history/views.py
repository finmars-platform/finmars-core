import json
import logging

import django_filters
from django_filters.fields import Lookup
from django_filters.rest_framework import FilterSet
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from poms.celery_tasks.models import CeleryTask
from poms.common.filters import NoOpFilter

from poms.common.views import AbstractModelViewSet
from poms.history.filters import (
    HistoryActionFilter,
    HistoryContentTypeFilter,
    HistoryDateRangeFilter,
    HistoryMemberFilter,
    HistoryQueryFilter,
)
from poms.history.models import HistoricalRecord
from poms.history.serializers import ExportJournalSerializer, HistoricalRecordSerializer
from poms.users.filters import OwnerByMasterUserFilter

_l = logging.getLogger("poms.history")


class ContentTypeFilter(django_filters.CharFilter):
    def filter(self, qs, value):
        if isinstance(value, Lookup):
            lookup = str(value.lookup_type)
            value = value.value
        else:
            lookup = self.lookup_expr
        if value in ([], (), {}, None, ""):
            return qs
        if self.distinct:
            qs = qs.distinct()
        try:
            app_label, model = value.split(".", maxsplit=1)
        except ValueError:
            # skip on invalid value
            app_label, model = "", ""
        qs = self.get_method(qs)(
            **{
                "content_type__app_label": app_label,
                f"content_type__model__{lookup}": model,
            }
        )
        return qs


class HistoricalRecordFilterSet(FilterSet):
    id = NoOpFilter()
    created_at = django_filters.DateFromToRangeFilter()

    class Meta:
        model = HistoricalRecord
        fields = []


class HistoricalRecordViewSet(AbstractModelViewSet):
    queryset = HistoricalRecord.objects.select_related("master_user", "member", "content_type")
    serializer_class = HistoricalRecordSerializer

    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        HistoryDateRangeFilter,
        HistoryQueryFilter,
        HistoryActionFilter,
        HistoryMemberFilter,
        HistoryContentTypeFilter,
    ]
    filter_class = HistoricalRecordFilterSet

    ordering_fields = ["created_at", "user_code", "member"]

    @action(detail=False, methods=["post"], url_path="export", serializer_class=ExportJournalSerializer)
    def export(self, request, realm_code=None, space_code=None):
        from poms_app import celery_app

        serializer = ExportJournalSerializer(data=request.data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        options_object = {}

        task = CeleryTask.objects.create(
            master_user=request.user.master_user,
            member=request.user.member,
            options_object=options_object,
            verbose_name="Export Journal To Storage",
            type="export_journal_to_storage",
        )
        task.options_object = serializer.validated_data
        task.save()

        celery_app.send_task(
            "history.export_journal_to_storage",
            kwargs={
                "task_id": task.id,
                "context": {"realm_code": task.realm_code, "space_code": task.space_code},
            },
            queue="backend-background-queue",
        )
        return Response({"task_id": task.id})

    @action(detail=True, methods=["get"], url_path="data")
    def get_data(self, request, pk, realm_code=None, space_code=None):
        instance = self.get_object()
        return Response(json.loads(instance.data))

    @action(detail=False, methods=["get"], url_path="content-types")
    def get_content_types(self, request, realm_code=None, space_code=None):
        result = {"results": []}
        items = (
            HistoricalRecord.objects.select_related("content_type")
            .order_by()
            .values("content_type__app_label", "content_type__model")
            .distinct()
        )

        for item in items:
            result["results"].append(
                {"key": item["content_type__app_label"] + "." + item["content_type__model"]}
            )

        return Response(result)

    def create(self, request, *args, **kwargs):
        raise PermissionDenied("History could not be created")

    def update(self, request, *args, **kwargs):
        raise PermissionDenied("History could not be updated")

    def perform_destroy(self, request, *args, **kwargs):
        raise PermissionDenied("History could not be deleted")
