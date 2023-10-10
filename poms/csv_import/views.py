import time
from logging import getLogger

from django_filters.rest_framework import FilterSet
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from poms.celery_tasks.models import CeleryTask
from poms.common.filters import CharFilter
from poms.common.views import AbstractAsyncViewSet, AbstractModelViewSet
from poms.csv_import.tasks import simple_import
from poms.users.filters import OwnerByMasterUserFilter

from ..system_messages.handlers import send_system_message
from .filters import SchemeContentTypeFilter
from .models import CsvImportScheme
from .serializers import (
    CsvDataImportSerializer,
    CsvImportSchemeLightSerializer,
    CsvImportSchemeSerializer,
)

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


class SchemeViewSet(AbstractModelViewSet):
    queryset = CsvImportScheme.objects
    serializer_class = CsvImportSchemeSerializer
    filter_class = SchemeFilterSet
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    permission_classes = AbstractModelViewSet.permission_classes + []

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

        result = self.get_paginated_response(serializer.data)

        return result


class CsvDataImportViewSet(AbstractAsyncViewSet):
    serializer_class = CsvDataImportSerializer
    celery_task = simple_import

    permission_classes = AbstractModelViewSet.permission_classes + [
        # PomsFunctionPermission
    ]

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

        _l.info("celery_task %s created " % celery_task.pk)

        # celery_task.save()

        send_system_message(
            master_user=request.user.master_user,
            performed_by="System",
            description="Member %s started Simple Import (scheme %s)"
            % (request.user.member.username, instance.scheme.name),
        )

        simple_import.apply_async(
            kwargs={"task_id": celery_task.pk}, queue="backend-background-queue"
        )

        _l.info(
            "CsvDataImportViewSet done: %s", "{:3.3f}".format(time.perf_counter() - st)
        )

        return Response(
            {"task_id": celery_task.pk, "task_status": celery_task.status},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"], url_path="execute")
    def execute(self, request, *args, **kwargs):
        st = time.perf_counter()

        _l.info("SimpleImportViewSet.execute")

        options_object = {
            "items": request.data.get("items", None),
            "file_path": request.data.get("file_path", None),
        }

        if options_object["file_path"]:
            # TODO refactor to file_name
            options_object["filename"] = request.data["file_path"].split("/")[-1]
        else:
            options_object["filename"] = None

        options_object["scheme_user_code"] = request.data["scheme_user_code"]
        options_object["execution_context"] = None

        # _l.info('options_object %s' % options_object)

        celery_task = CeleryTask.objects.create(
            master_user=request.user.master_user,
            member=request.user.member,
            options_object=options_object,
            verbose_name="Simple Import",
            type="simple_import",
        )

        _l.info("celery_task %s created " % celery_task.pk)

        send_system_message(
            master_user=request.user.master_user,
            performed_by="System",
            description="Member %s started Simple Import (scheme %s)"
            % (request.user.member.username, options_object["scheme_user_code"]),
        )

        simple_import.apply_async(
            kwargs={"task_id": celery_task.pk}, queue="backend-background-queue"
        )

        _l.info(
            "CsvDataImportViewSet done: %s", "{:3.3f}".format(time.perf_counter() - st)
        )

        return Response(
            {"task_id": celery_task.pk, "task_status": celery_task.status},
            status=status.HTTP_200_OK,
        )
