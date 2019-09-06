from celery.result import AsyncResult
from django.core.signing import TimestampSigner

from rest_framework.response import Response
from rest_framework import status

from poms.common.utils import date_now, datetime_now

from rest_framework.filters import FilterSet

from poms.celery_tasks.models import CeleryTask
from poms.common.views import AbstractModelViewSet, AbstractAsyncViewSet

from poms.csv_import.tasks import data_csv_file_import, data_csv_file_import_validate

from poms.users.filters import OwnerByMasterUserFilter

from .filters import SchemeContentTypeFilter
from .models import CsvDataImport, CsvImportScheme
from .serializers import CsvDataImportSerializer, CsvImportSchemeSerializer

from rest_framework.exceptions import PermissionDenied

import time

from logging import getLogger

_l = getLogger('poms.csv_import')


class SchemeFilterSet(FilterSet):
    content_type = SchemeContentTypeFilter(name='content_type')

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


class CsvDataImportViewSet(AbstractAsyncViewSet):
    serializer_class = CsvDataImportSerializer
    celery_task = data_csv_file_import

    def get_serializer_context(self):
        context = super(AbstractAsyncViewSet, self).get_serializer_context()
        context['show_object_permissions'] = False
        return context

    def create(self, request, *args, **kwargs):

        print('TASK: data_csv_file_import')

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        task_id = instance.task_id

        signer = TimestampSigner()

        if task_id:

            res = AsyncResult(signer.unsign(task_id))

            try:
                celery_task = CeleryTask.objects.get(master_user=request.user.master_user, task_id=task_id)
            except CeleryTask.DoesNotExist:
                celery_task = None
                print("Cant create Celery Task")

            print('celery_task %s' % celery_task)

            st = time.perf_counter()

            if res.ready():

                instance = res.result

                if celery_task:
                    celery_task.finished_at = datetime_now()

            else:

                if res.result:

                    if 'processed_rows' in res.result:
                        instance.processed_rows = res.result['processed_rows']
                    if 'total_rows' in res.result:
                        instance.total_rows = res.result['total_rows']

                    if celery_task:
                        celery_task.data = {
                            "total_rows": res.result['total_rows'],
                            "processed_rows": res.result['processed_rows'],
                            "scheme_name": res.result['scheme_name'],
                            "file_name": res.result['file_name']
                        }

                # print('TASK ITEMS LEN %s' % len(res.result.items))

            print('AsyncResult res.ready: %s' % (time.perf_counter() - st))

            if instance.master_user.id != request.user.master_user.id:
                raise PermissionDenied()

            # print('TASK RESULT %s' % res.result)
            print('TASK STATUS %s' % res.status)
            print('TASK STATUS celery_task %s' % celery_task)

            instance.task_id = task_id
            instance.task_status = res.status

            if celery_task:
                celery_task.task_status = res.status
                celery_task.save()

            serializer = self.get_serializer(instance=instance, many=False)
            return Response(serializer.data, status=status.HTTP_200_OK)

        else:

            res = self.celery_task.apply_async(kwargs={'instance': instance})
            instance.task_id = signer.sign('%s' % res.id)

            celery_task = CeleryTask.objects.create(master_user=request.user.master_user,
                                                    member=request.user.member,
                                                    started_at=datetime_now(),
                                                    task_type='simple_import', task_id=res.id)

            celery_task.save()

            print('CREATE CELERY TASK celery_task %s' % celery_task)
            print('CREATE CELERY TASK %s' % res.id)

            instance.task_status = res.status
            serializer = self.get_serializer(instance=instance, many=False)
            return Response(serializer.data, status=status.HTTP_200_OK)


class CsvDataImportValidateViewSet(AbstractAsyncViewSet):
    serializer_class = CsvDataImportSerializer
    celery_task = data_csv_file_import_validate

    def get_serializer_context(self):
        context = super(AbstractAsyncViewSet, self).get_serializer_context()
        context['show_object_permissions'] = False
        return context

    def create(self, request, *args, **kwargs):

        print('TASK: data_csv_file_import_validate')

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        task_id = instance.task_id

        signer = TimestampSigner()

        print('validate instance %s' % instance.scheme)

        if task_id:

            res = AsyncResult(signer.unsign(task_id))

            try:
                celery_task = CeleryTask.objects.get(master_user=request.user.master_user, task_id=task_id)
            except CeleryTask.DoesNotExist:
                celery_task = None
                print("Cant create Celery Task")


            print('celery_task %s ' % celery_task)

            st = time.perf_counter()

            if res.ready():

                instance = res.result

                if celery_task:
                    celery_task.finished_at = datetime_now()

            else:

                if res.result:
                    if 'processed_rows' in res.result:
                        instance.processed_rows = res.result['processed_rows']
                    if 'total_rows' in res.result:
                        instance.total_rows = res.result['total_rows']

                    if celery_task:
                        celery_task.data = {
                            "total_rows": res.result['total_rows'],
                            "processed_rows": res.result['processed_rows'],
                            "scheme_name": res.result['scheme_name'],
                            "file_name": res.result['file_name']
                        }

                # print('TASK ITEMS LEN %s' % len(res.result.items))

            print('AsyncResult res.ready: %s' % (time.perf_counter() - st))

            if instance.master_user.id != request.user.master_user.id:
                raise PermissionDenied()

            print('TASK RESULT %s' % res.result)
            print('TASK STATUS %s' % res.status)

            print('instance %s ' % instance)

            instance.task_id = task_id
            instance.task_status = res.status

            if celery_task:
                celery_task.task_status = res.status
                celery_task.save()

            serializer = self.get_serializer(instance=instance, many=False)
            return Response(serializer.data, status=status.HTTP_200_OK)

        else:

            res = self.celery_task.apply_async(kwargs={'instance': instance})
            instance.task_id = signer.sign('%s' % res.id)

            celery_task = CeleryTask.objects.create(master_user=request.user.master_user,
                                                    member=request.user.member,
                                                    started_at=datetime_now(),
                                                    task_type='validate_simple_import', task_id=instance.task_id)

            celery_task.save()

            print('CREATE CELERY TASK %s' % res.id)
            print('celery_task %s' % celery_task)

            instance.task_status = res.status
            serializer = self.get_serializer(instance=instance, many=False)
            return Response(serializer.data, status=status.HTTP_200_OK)
