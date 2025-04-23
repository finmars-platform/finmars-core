import time
from logging import getLogger

from django_filters.rest_framework import FilterSet
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from poms.celery_tasks.models import CeleryTask
from poms.common.filters import CharFilter, GroupsAttributeFilter, AttributeFilter
from poms.common.views import AbstractAsyncViewSet, AbstractModelViewSet
from poms.csv_import.tasks import simple_import
from poms.users.filters import OwnerByMasterUserFilter
from rest_framework.viewsets import ModelViewSet
from ..common.mixins import UpdateModelMixinExt

from ..system_messages.handlers import send_system_message
from .filters import SchemeContentTypeFilter
from .models import CsvImportScheme
from .serializers import (
    CsvDataImportSerializer,
    CsvImportSchemeLightSerializer,
    CsvImportSchemeSerializer,
)

from rest_framework.permissions import IsAuthenticated

_l = getLogger("poms.csv_import")


class SchemeFilterSet(FilterSet):
    user_code = CharFilter()
    content_type = SchemeContentTypeFilter(field_name="content_type")

    class Meta:
        model = CsvImportScheme
        fields = []


def utf_8_encoder(unicode_csv_data):
    for line in unicode_csv_data:
        yield line.encode("utf-8")


class SchemeViewSet(AbstractModelViewSet, UpdateModelMixinExt, ModelViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        GroupsAttributeFilter,
        AttributeFilter,
    ]
    queryset = CsvImportScheme.objects

    serializer_class = CsvImportSchemeSerializer

    filter_class = SchemeFilterSet
    ordering_fields = [
        "scheme_name",
    ]

    @action(
        detail=False,
        methods=["get"],
        url_path="light",
        serializer_class=CsvImportSchemeLightSerializer,
    )
    def list_light(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginator.post_paginate_queryset(queryset, request)
        serializer = self.get_serializer(page, many=True)

        return self.get_paginated_response(serializer.data)


class CsvDataImportViewSet(AbstractAsyncViewSet):
    serializer_class = CsvDataImportSerializer
    celery_task = simple_import

    permission_classes = AbstractModelViewSet.permission_classes + []

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["show_object_permissions"] = False
        return context

    def create(self, request, *args, **kwargs):
        st = time.perf_counter()

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        options_object = {
            "file_path": instance.file_path,
            "filename": instance.filename,
            "scheme_id": instance.scheme.id,
            "execution_context": None,
        }

        celery_task = CeleryTask.objects.create(
            master_user=request.user.master_user,
            member=request.user.member,
            options_object=options_object,
            verbose_name="Simple Import",
            type="simple_import",
        )

        _l.info(f"celery_task {celery_task.pk} created ")

        send_system_message(
            master_user=request.user.master_user,
            performed_by="System",
            description=(
                f"Member {request.user.member.username} started Simple Import "
                f"(scheme {instance.scheme.name})"
            ),
        )

        simple_import.apply_async(
            kwargs={
                "task_id": celery_task.pk,
                "context": {
                    "space_code": celery_task.master_user.space_code,
                    "realm_code": celery_task.master_user.realm_code,
                },
            },
            queue="backend-background-queue",
        )

        _l.info(
            "CsvDataImportViewSet done: %s", "{:3.3f}".format(time.perf_counter() - st)
        )

        return Response(
            {
                "task_id": celery_task.pk,
                "task_status": celery_task.status,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"], url_path="execute")
    def execute(self, request, *args, **kwargs):
        st = time.perf_counter()

        _l.info("SimpleImportViewSet.execute started")

        file_path = request.data.get("file_path")
        options_object = {
            "items": request.data.get("items"),
            "file_path": file_path,
            "filename": file_path.split("/")[-1] if file_path else None,
            "scheme_user_code": request.data["scheme_user_code"],
            "execution_context": None,
        }

        celery_task = CeleryTask.objects.create(
            master_user=request.user.master_user,
            member=request.user.member,
            options_object=options_object,
            verbose_name="Simple Import",
            type="simple_import",
        )

        _l.info(
            f"celery_task {celery_task.pk} created, options_object={options_object}"
        )

        send_system_message(
            master_user=request.user.master_user,
            performed_by="System",
            description=(
                f"Member {request.user.member.username} started Simple Import "
                f"(scheme {options_object['scheme_user_code']})"
            ),
        )

        simple_import.apply_async(
            kwargs={
                "task_id": celery_task.pk,
                "context": {
                    "space_code": celery_task.master_user.space_code,
                    "realm_code": celery_task.master_user.realm_code,
                },
            },
            queue="backend-background-queue",
        )

        _l.info(
            "CsvDataImportViewSet done: %s", "{:3.3f}".format(time.perf_counter() - st)
        )

        return Response(
            {
                "task_id": celery_task.pk,
                "task_status": celery_task.status,
            },
            status=status.HTTP_200_OK,
        )
