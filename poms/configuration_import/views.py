from celery.result import AsyncResult
from django.core.signing import TimestampSigner
from rest_framework import status

from rest_framework.response import Response

from poms.celery_tasks.models import CeleryTask
from poms.common.views import AbstractModelViewSet, AbstractAsyncViewSet
from poms.configuration_import.serializers import ConfigurationImportAsJsonSerializer, \
    GenerateConfigurationEntityArchetypeSerializer

from poms.configuration_import.tasks import configuration_import_as_json, generate_configuration_entity_archetype

from poms.common.utils import date_now, datetime_now

import time

from rest_framework.exceptions import PermissionDenied

from logging import getLogger

_l = getLogger('poms.configuration_import')


def dump(obj):
    for attr in dir(obj):
        _l.info("obj.%s = %r" % (attr, getattr(obj, attr)))

class ConfigurationImportAsJsonViewSet(AbstractAsyncViewSet):

    serializer_class = ConfigurationImportAsJsonSerializer
    celery_task = configuration_import_as_json

    def get_serializer_context(self):
        context = super(AbstractAsyncViewSet, self).get_serializer_context()
        context['show_object_permissions'] = False
        return context

    def create(self, request, *args, **kwargs):

        _l.info('TASK: configuration_import_as_json')

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
                _l.info("Cant create Celery Task")

            _l.info('celery_task %s' % celery_task)

            st = time.perf_counter()

            if res.ready():

                instance = res.result

                if celery_task:
                    celery_task.finished_at = datetime_now()

            else:

                if res.result:

                    try:
                        if 'processed_rows' in res.result:
                            instance.processed_rows = res.result['processed_rows']
                        if 'total_rows' in res.result:
                            instance.total_rows = res.result['total_rows']

                        if celery_task:
                            celery_task.data = {
                                "total_rows": res.result['total_rows'],
                                "processed_rows": res.result['processed_rows']
                            }
                    except TypeError:
                        _l.info('Type erro')

                # _l.info('TASK ITEMS LEN %s' % len(res.result.items))

            _l.info('AsyncResult res.ready: %s' % (time.perf_counter() - st))

            _l.info('instance %s' % instance)
            _l.info('res.status %s' % res.status)
            _l.info('celery_task %s' % celery_task)

            _l.info('request.user %s' % request.user)
            _l.info('request.user.master_user %s' % request.user.master_user)

            _l.info('instance.master_user %s' % instance.master_user)

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
            instance.task_id = signer.sign('%s' % res.id)

            celery_task = CeleryTask.objects.create(master_user=request.user.master_user,
                                                    member=request.user.member,
                                                    started_at=datetime_now(),
                                                    task_type='configuration_import', task_id=instance.task_id)

            celery_task.save()


            _l.info('celery_task.task_status %s ' % celery_task.task_status)

            instance.task_status = res.status
            serializer = self.get_serializer(instance=instance, many=False)
            return Response(serializer.data, status=status.HTTP_200_OK)


class GenerateConfigurationEntityArchetypeViewSet(AbstractAsyncViewSet):
    serializer_class = GenerateConfigurationEntityArchetypeSerializer
    celery_task = generate_configuration_entity_archetype

    permission_classes = AbstractModelViewSet.permission_classes + [
        # PomsFunctionPermission
    ]

    def create(self, request, *args, **kwargs):

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        task_id = instance.task_id

        signer = TimestampSigner()

        if task_id:

            res = AsyncResult(signer.unsign(task_id))

            st = time.perf_counter()

            if res.ready():

                instance = res.result

            _l.info('AsyncResult res.ready: %s' % (time.perf_counter() - st))

            if instance.master_user.id != request.user.master_user.id:
                raise PermissionDenied()

            _l.info('TASK RESULT %s' % res.result)
            _l.info('TASK STATUS %s' % res.status)

            instance.task_id = task_id
            instance.task_status = res.status

            serializer = self.get_serializer(instance=instance, many=False)
            return Response(serializer.data, status=status.HTTP_200_OK)

        else:

            res = self.celery_task.apply_async(kwargs={'instance': instance})
            instance.task_id = signer.sign('%s' % res.id)

            _l.info('CREATE CELERY TASK %s' % res.id)

            instance.task_status = res.status
            serializer = self.get_serializer(instance=instance, many=False)
            return Response(serializer.data, status=status.HTTP_200_OK)

