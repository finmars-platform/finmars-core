from celery.result import AsyncResult
from django.core.signing import TimestampSigner
from django_filters.rest_framework import FilterSet


from poms.common.views import AbstractModelViewSet, AbstractAsyncViewSet
from poms.layout_recovery.models import LayoutArchetype
from poms.layout_recovery.serializers import LayoutArchetypeSerializer, GenerateLayoutArchetypeSerializer, \
    FixLayoutSerializer
from poms.layout_recovery.tasks import generate_layout_archetype, fix_layout

from poms.users.filters import OwnerByMasterUserFilter
from rest_framework.response import Response

import time

from rest_framework import status
from rest_framework.exceptions import PermissionDenied


from logging import getLogger

_l = getLogger('poms.layout_recovery')


class LayoutArchetypeFilterSet(FilterSet):

    class Meta:
        model = LayoutArchetype
        fields = []


class LayoutArchetypeViewSet(AbstractModelViewSet):
    queryset = LayoutArchetype.objects
    serializer_class = LayoutArchetypeSerializer
    filter_class = LayoutArchetypeFilterSet
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]


class GenerateLayoutArchetypeViewSet(AbstractAsyncViewSet):
    serializer_class = GenerateLayoutArchetypeSerializer
    celery_task = generate_layout_archetype

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

            print('AsyncResult res.ready: %s' % (time.perf_counter() - st))

            if instance.master_user.id != request.user.master_user.id:
                raise PermissionDenied()

            print('TASK RESULT %s' % res.result)
            print('TASK STATUS %s' % res.status)

            instance.task_id = task_id
            instance.task_status = res.status

            serializer = self.get_serializer(instance=instance, many=False)
            return Response(serializer.data, status=status.HTTP_200_OK)

        else:

            res = self.celery_task.apply_async(kwargs={'instance': instance})
            instance.task_id = signer.sign('%s' % res.id)

            print('CREATE CELERY TASK %s' % res.id)

            instance.task_status = res.status
            serializer = self.get_serializer(instance=instance, many=False)
            return Response(serializer.data, status=status.HTTP_200_OK)


class FixLayoutViewSet(AbstractAsyncViewSet):
    serializer_class = FixLayoutSerializer
    celery_task = fix_layout

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

            print('AsyncResult res.ready: %s' % (time.perf_counter() - st))

            if instance.master_user.id != request.user.master_user.id:
                raise PermissionDenied()

            print('TASK RESULT %s' % res.result)
            print('TASK STATUS %s' % res.status)

            instance.task_id = task_id
            instance.task_status = res.status

            serializer = self.get_serializer(instance=instance, many=False)
            return Response(serializer.data, status=status.HTTP_200_OK)

        else:

            res = self.celery_task.apply_async(kwargs={'instance': instance})
            instance.task_id = signer.sign('%s' % res.id)

            print('CREATE CELERY TASK %s' % res.id)

            instance.task_status = res.status
            serializer = self.get_serializer(instance=instance, many=False)
            return Response(serializer.data, status=status.HTTP_200_OK)
