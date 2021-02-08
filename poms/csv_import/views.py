from celery.result import AsyncResult
from django.core.signing import TimestampSigner
from django_filters.rest_framework import FilterSet

from rest_framework.response import Response
from rest_framework import status

from poms.common.filters import CharFilter
from poms.common.utils import date_now, datetime_now

from poms.celery_tasks.models import CeleryTask
from poms.common.views import AbstractModelViewSet, AbstractAsyncViewSet

from poms.csv_import.tasks import data_csv_file_import, data_csv_file_import_validate
from poms.obj_perms.permissions import PomsFunctionPermission, PomsConfigurationPermission

from poms.users.filters import OwnerByMasterUserFilter

from .filters import SchemeContentTypeFilter
from .models import CsvDataImport, CsvImportScheme
from .serializers import CsvDataImportSerializer, CsvImportSchemeSerializer, CsvImportSchemeLightSerializer

from django.forms.models import model_to_dict

from rest_framework.exceptions import PermissionDenied

import time

from logging import getLogger

_l = getLogger('poms.csv_import')


class SchemeFilterSet(FilterSet):
    scheme_name = CharFilter()
    content_type = SchemeContentTypeFilter(field_name='content_type')

    class Meta:
        model = CsvImportScheme
        fields = []


def utf_8_encoder(unicode_csv_data):
    for line in unicode_csv_data:
        yield line.encode('utf-8')


class SchemeViewSet(AbstractModelViewSet):
    queryset = CsvImportScheme.objects
    serializer_class = CsvImportSchemeSerializer
    filter_class = SchemeFilterSet
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    permission_classes = AbstractModelViewSet.permission_classes + [
        PomsConfigurationPermission
    ]


class SchemeLightViewSet(AbstractModelViewSet):
    queryset = CsvImportScheme.objects
    serializer_class = CsvImportSchemeLightSerializer
    filter_class = SchemeFilterSet
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    permission_classes = AbstractModelViewSet.permission_classes + [
        PomsConfigurationPermission
    ]



class CsvDataImportViewSet(AbstractAsyncViewSet):
    serializer_class = CsvDataImportSerializer
    celery_task = data_csv_file_import

    permission_classes = AbstractModelViewSet.permission_classes + [
        PomsFunctionPermission
    ]

    def get_serializer_context(self):
        context = super(AbstractAsyncViewSet, self).get_serializer_context()
        context['show_object_permissions'] = False
        return context

    def create(self, request, *args, **kwargs):

        _l.debug('TASK: data_csv_file_import')

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        task_id = instance.task_id

        # signer = TimestampSigner()

        if task_id:

            # res = AsyncResult(signer.unsign(task_id))
            res = AsyncResult(task_id)

            try:
                celery_task = CeleryTask.objects.get(master_user=request.user.master_user, celery_task_id=task_id)
            except CeleryTask.DoesNotExist:
                # celery_task = None
                _l.debug("Cant create Celery Task")
                raise PermissionDenied()

            st = time.perf_counter()

            if res.ready():

                instance = res.result

                if celery_task:
                    celery_task.finished_at = datetime_now()
                    celery_task.file_report_id = instance.stats_file_report

            else:

                if res.result:

                    #  DEPRECATED, REMOVE IN FUTURE
                    if 'processed_rows' in res.result:
                        instance.processed_rows = res.result['processed_rows']
                    if 'total_rows' in res.result:
                        instance.total_rows = res.result['total_rows']

                    if celery_task:

                        celery_task_data = {}

                        if 'total_rows' in res.result:
                            celery_task_data["total_rows"] = res.result['total_rows']

                        if 'processed_rows' in res.result:
                            celery_task_data["processed_rows"] = res.result['processed_rows']

                        if 'scheme_name' in res.result:
                            celery_task_data["scheme_name"] = res.result['scheme_name']

                        if 'file_name' in res.result:
                            celery_task_data["file_name"]  = res.result['file_name']

                        celery_task.data = celery_task_data

            _l.debug('AsyncResult res.ready: %s' % (time.perf_counter() - st))

            if instance.master_user.id != request.user.master_user.id:
                raise PermissionDenied()

            instance.task_id = task_id
            instance.task_status = res.status

            if celery_task:
                celery_task.task_status = res.status
                celery_task.save()

            serializer = self.get_serializer(instance=instance, many=False)
            return Response(serializer.data, status=status.HTTP_200_OK)

        else:

            res = self.celery_task.apply_async(kwargs={'instance': instance})
            # instance.task_id = signer.sign('%s' % res.id)
            instance.task_id = res.id

            celery_task = CeleryTask.objects.create(master_user=request.user.master_user,
                                                    member=request.user.member,
                                                    type='simple_import', celery_task_id=res.id)

            celery_task.save()

            instance.task_status = res.status
            serializer = self.get_serializer(instance=instance, many=False)
            return Response(serializer.data, status=status.HTTP_200_OK)


class CsvDataImportValidateViewSet(AbstractAsyncViewSet):
    serializer_class = CsvDataImportSerializer
    celery_task = data_csv_file_import_validate

    permission_classes = AbstractModelViewSet.permission_classes + [
        PomsFunctionPermission
    ]

    def get_serializer_context(self):
        context = super(AbstractAsyncViewSet, self).get_serializer_context()
        context['show_object_permissions'] = False
        return context

    def create(self, request, *args, **kwargs):

        _l.debug('TASK: data_csv_file_import_validate')

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        task_id = instance.task_id

        # signer = TimestampSigner()

        if task_id:

            # res = AsyncResult(signer.unsign(task_id))
            res = AsyncResult(task_id)

            try:
                celery_task = CeleryTask.objects.get(master_user=request.user.master_user, celery_task_id=task_id)
            except CeleryTask.DoesNotExist:
                celery_task = None
                _l.debug("Cant create Celery Task")
                raise PermissionDenied()

            st = time.perf_counter()

            if res.ready():

                instance = res.result

                if celery_task:
                    celery_task.finished_at = datetime_now()
                    celery_task.file_report_id = instance.stats_file_report

            else:

                if res.result:
                    if 'processed_rows' in res.result:
                        instance.processed_rows = res.result['processed_rows']
                    if 'total_rows' in res.result:
                        instance.total_rows = res.result['total_rows']

                    if celery_task:

                        celery_task_data = {}

                        if 'total_rows' in res.result:
                            celery_task_data["total_rows"] = res.result['total_rows']

                        if 'processed_rows' in res.result:
                            celery_task_data["processed_rows"] = res.result['processed_rows']

                        if 'scheme_name' in res.result:
                            celery_task_data["scheme_name"] = res.result['scheme_name']

                        if 'file_name' in res.result:
                            celery_task_data["file_name"]  = res.result['file_name']

                        celery_task.data = celery_task_data

            if instance.master_user.id != request.user.master_user.id:
                raise PermissionDenied()

            instance.task_id = task_id
            instance.task_status = res.status

            if celery_task:
                celery_task.task_status = res.status
                celery_task.save()

            serializer = self.get_serializer(instance=instance, many=False)
            return Response(serializer.data, status=status.HTTP_200_OK)

        else:

            # delattr(instance, 'file')

            res = self.celery_task.apply_async(kwargs={'instance': instance})
            # instance.task_id = signer.sign('%s' % res.id)
            instance.task_id = res.id

            celery_task = CeleryTask.objects.create(master_user=request.user.master_user,
                                                    member=request.user.member,
                                                    type='validate_simple_import', celery_task_id=instance.task_id)

            celery_task.save()

            instance.task_status = res.status
            serializer = self.get_serializer(instance=instance, many=False)
            return Response(serializer.data, status=status.HTTP_200_OK)
