import logging

from django_filters.rest_framework import FilterSet
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from poms.celery_tasks.models import CeleryTask
from poms.common.authentication import get_access_token
from poms.common.filters import CharFilter
from poms.common.storage import get_storage
from poms.common.views import AbstractModelViewSet
from poms.configuration.models import Configuration, NewMemberSetupConfiguration
from poms.configuration.serializers import ConfigurationSerializer, ConfigurationImportSerializer, \
    NewMemberSetupConfigurationSerializer

storage = get_storage()

from poms.configuration.tasks import import_configuration, push_configuration_to_marketplace, \
    install_configuration_from_marketplace, install_package_from_marketplace, export_configuration

_l = logging.getLogger('poms.configuration')


class ConfigurationFilterSet(FilterSet):
    name = CharFilter()
    short_name = CharFilter()
    version = CharFilter()

    class Meta:
        model = Configuration
        fields = []


class ConfigurationViewSet(AbstractModelViewSet):
    queryset = Configuration.objects
    serializer_class = ConfigurationSerializer
    filter_class = ConfigurationFilterSet
    filter_backends = AbstractModelViewSet.filter_backends + [

    ]
    permission_classes = AbstractModelViewSet.permission_classes + [

    ]

    @action(detail=True, methods=['get'], url_path='export-configuration')
    def export_configuration(self, request, pk=None):
        task = CeleryTask.objects.create(
            master_user=request.user.master_user,
            member=request.user.member,
            type="export_configuration",
        )

        configuration = self.get_object()

        options_object = {
            'configuration_code': configuration.configuration_code,
        }

        task.options_object = options_object
        task.save()

        try:

            export_configuration.apply_async(kwargs={'task_id': task.id})

            return Response({"status": "ok"})

        except Exception as e:

            task.status = CeleryTask.STATUS_ERROR
            task.error_message = str(e)
            task.save()
            raise Exception(e)

    @action(detail=True, methods=['get'], url_path='configure')
    def configure(self, request, pk=None):
        configuration = self.get_object()

        # RESPONSE WITH HUGE JSON OF CONFIG, AND USER CAN SELECT WHAT TO DO WITH IT

        return Response({"status": "ok"})

    @action(detail=False, methods=['POST'], url_path='import-configuration',
            serializer_class=ConfigurationImportSerializer)
    def import_configuration(self, request, pk=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        celery_task = CeleryTask.objects.create(master_user=request.user.master_user,
                                                member=request.user.member,
                                                verbose_name="Configuration Import",
                                                type='configuration_import')

        options_object = {
            'file_path': instance.file_path,
        }

        celery_task.options_object = options_object
        celery_task.save()

        instance.task_id = celery_task.id

        import_configuration.apply_async(kwargs={'task_id': celery_task.id})

        _l.info('celery_task %s' % celery_task.id)

        return Response({'task_id': celery_task.id}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['PUT'], url_path='push-configuration-to-marketplace')
    def push_configuration_to_marketplace(self, request, pk=None):

        configuration = self.get_object()

        options_object = {
            "configuration_code": configuration.configuration_code,
            "changelog": request.data.get("changelog", ""),
            "access_token": get_access_token(request)
            # TODO check this later, important security thins, need to be destroyed inside task
        }

        celery_task = CeleryTask.objects.create(
            master_user=request.user.master_user,
            member=request.user.member,
            type="push_configuration_to_marketplace",
            options_object=options_object
        )

        push_configuration_to_marketplace.apply_async(kwargs={'task_id': celery_task.id})

        return Response({"task_id": celery_task.id})

    @action(detail=False, methods=['POST'], url_path='install-configuration-from-marketplace')
    def install_configuration_from_marketplace(self, request, pk=None):

        celery_task = CeleryTask.objects.create(master_user=request.user.master_user,
                                                member=request.user.member,
                                                verbose_name="Install Configuration From Marketplace",
                                                type='install_configuration_from_marketplace')

        options_object = {
            'configuration_code': request.data.get('configuration_code', None),
            'version': request.data.get('version', None),
            'is_package': request.data.get('is_package', False),
            "access_token": get_access_token(request)
            # TODO check this later, important security thins, need to be destroyed inside task
        }

        celery_task.options_object = options_object
        celery_task.save()

        if request.data.get('is_package', False):
            install_package_from_marketplace.apply_async(kwargs={'task_id': celery_task.id})
        else:
            install_configuration_from_marketplace.apply_async(kwargs={'task_id': celery_task.id})

        _l.info('celery_task %s' % celery_task.id)

        return Response({'task_id': celery_task.id}, status=status.HTTP_200_OK)


class NewMemberSetupConfigurationFilterSet(FilterSet):
    name = CharFilter()
    user_code = CharFilter()
    notes = CharFilter()
    target_configuration_code = CharFilter()
    target_configuration_version = CharFilter()

    class Meta:
        model = NewMemberSetupConfiguration
        fields = []


class NewMemberSetupConfigurationViewSet(AbstractModelViewSet):
    queryset = NewMemberSetupConfiguration.objects
    serializer_class = NewMemberSetupConfigurationSerializer
    filter_class = NewMemberSetupConfigurationFilterSet
    filter_backends = AbstractModelViewSet.filter_backends + [

    ]
    permission_classes = AbstractModelViewSet.permission_classes + [

    ]

    @action(detail=True, methods=['PUT'], url_path='install')
    def install(self, request, pk=None):
        new_member_setup_configuration = self.get_object()

        # TODO implement install from local zip file
        options_object = {
            "configuration_code": new_member_setup_configuration.target_configuration_code,
            "configuration_version": new_member_setup_configuration.target_configuration_version,
        }

        celery_task = CeleryTask.objects.create(
            master_user=request.user.master_user,
            member=request.user.member,
            type="install_initial_configuration",
            options_object=options_object
        )

        # push_configuration_to_marketplace.apply_async(kwargs={'task_id': celery_task.id})

        return Response({"task_id": celery_task.id})
