from celery.result import AsyncResult
from django.core.signing import TimestampSigner
from rest_framework import status

from rest_framework.response import Response

from poms.celery_tasks.models import CeleryTask
from poms.common.views import AbstractModelViewSet, AbstractAsyncViewSet
from poms.configuration_import.serializers import ConfigurationImportAsJsonSerializer

from poms.configuration_import.tasks import configuration_import_as_json


from poms.common.utils import date_now, datetime_now

import time

from rest_framework.exceptions import PermissionDenied


def dump(obj):
    for attr in dir(obj):
        print("obj.%s = %r" % (attr, getattr(obj, attr)))

class ConfigurationImportAsJsonViewSet(AbstractAsyncViewSet):

    serializer_class = ConfigurationImportAsJsonSerializer
    celery_task = configuration_import_as_json

    def get_serializer_context(self):
        context = super(AbstractAsyncViewSet, self).get_serializer_context()
        context['show_object_permissions'] = False
        return context

    def create(self, request, *args, **kwargs):

        print('TASK: configuration_import_as_json')

        request.data['request'] = request

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
                            "file_name": res.result['file_name']
                        }

                # print('TASK ITEMS LEN %s' % len(res.result.items))

            print('AsyncResult res.ready: %s' % (time.perf_counter() - st))

            dump(instance)

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
                                                    task_type='configuration_import', task_id=res.id)

            celery_task.save()

            print('CREATE CELERY TASK celery_task %s' % celery_task)
            print('CREATE CELERY TASK %s' % res.id)

            instance.task_status = res.status
            serializer = self.get_serializer(instance=instance, many=False)
            return Response(serializer.data, status=status.HTTP_200_OK)
