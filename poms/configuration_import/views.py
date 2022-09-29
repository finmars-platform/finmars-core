from celery.result import AsyncResult
from django.core.signing import TimestampSigner
from rest_framework import status
from django.db import transaction
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
        _l.debug("obj.%s = %r" % (attr, getattr(obj, attr)))


class ConfigurationImportAsJsonViewSet(AbstractAsyncViewSet):
    serializer_class = ConfigurationImportAsJsonSerializer
    celery_task = configuration_import_as_json

    def get_serializer_context(self):
        context = super(AbstractAsyncViewSet, self).get_serializer_context()
        context['show_object_permissions'] = False
        return context

    def create(self, request, *args, **kwargs):

        _l.debug('TASK: configuration_import_as_json')

        # request.data['request'] = request

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        if instance.task_id:

            celery_task = CeleryTask.objects.get(id=instance.task_id)

            if celery_task.status == CeleryTask.STATUS_DONE:

                instance.stats = celery_task.result_object
                instance.task_status = 'SUCCESS'

        else:

            celery_task = CeleryTask.objects.create(master_user=request.user.master_user,
                                                    member=request.user.member,
                                                    type='configuration_import')

            options_object = {
                'data': request.data['data'],
                'mode': request.data['mode']
            }

            celery_task.options_object = options_object
            celery_task.save()

            instance.task_id = celery_task.id

            transaction.on_commit(
                lambda: configuration_import_as_json.apply_async(kwargs={'task_id': celery_task.id}))

        serializer = self.get_serializer(instance=instance, many=False)
        return Response(serializer.data, status=status.HTTP_200_OK)


# DEPRECATED
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

            _l.debug('AsyncResult res.ready: %s' % (time.perf_counter() - st))

            if instance.master_user.id != request.user.master_user.id:
                raise PermissionDenied()

            _l.debug('TASK RESULT %s' % res.result)
            _l.debug('TASK STATUS %s' % res.status)

            instance.task_id = task_id
            instance.task_status = res.status

            serializer = self.get_serializer(instance=instance, many=False)
            return Response(serializer.data, status=status.HTTP_200_OK)

        else:

            res = self.celery_task.apply_async(kwargs={'instance': instance})
            instance.task_id = signer.sign('%s' % res.id)

            _l.debug('CREATE CELERY TASK %s' % res.id)

            instance.task_status = res.status
            serializer = self.get_serializer(instance=instance, many=False)
            return Response(serializer.data, status=status.HTTP_200_OK)
