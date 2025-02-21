import logging

import django_filters
from django_filters.filters import BooleanFilter
from django_filters.rest_framework import FilterSet
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from poms.celery_tasks.models import CeleryTask
from poms.common.authentication import get_access_token
from poms.common.filters import CharFilter
from poms.common.storage import get_storage
from poms.common.views import AbstractModelViewSet
from poms.configuration.filters import ConfigurationQueryFilter
from poms.configuration.models import Configuration, NewMemberSetupConfiguration
from poms.configuration.serializers import (
    ConfigurationImportSerializer,
    ConfigurationSerializer,
    NewMemberSetupConfigurationSerializer,
)
from poms.configuration.tasks import (
    export_configuration,
    import_configuration,
    install_configuration_from_marketplace,
    install_package_from_marketplace,
    push_configuration_to_marketplace,
)

storage = get_storage()

_l = logging.getLogger("poms.configuration")


class ConfigurationFilterSet(FilterSet):
    name = CharFilter()
    short_name = CharFilter()
    version = CharFilter()
    type = CharFilter()
    is_primary = django_filters.BooleanFilter()
    is_package = django_filters.BooleanFilter()

    class Meta:
        model = Configuration
        fields = []


class ConfigurationViewSet(AbstractModelViewSet):
    queryset = Configuration.objects
    serializer_class = ConfigurationSerializer
    filter_class = ConfigurationFilterSet
    filter_backends = AbstractModelViewSet.filter_backends + [ConfigurationQueryFilter]
    permission_classes = AbstractModelViewSet.permission_classes + []

    @action(detail=True, methods=["get"], url_path="export-configuration")
    def export_configuration(self, request, pk=None, realm_code=None, space_code=None):
        task = CeleryTask.objects.create(
            master_user=request.user.master_user,
            member=request.user.member,
            type="export_configuration",
        )

        configuration = self.get_object()

        options_object = {
            "configuration_code": configuration.configuration_code,
        }

        task.options_object = options_object
        task.save()

        try:
            export_configuration.apply_async(kwargs={"task_id": task.id, 'context': {
                'space_code': task.master_user.space_code,
                'realm_code': task.master_user.realm_code
            }})

            return Response({"status": "ok", "task_id": task.id})

        except Exception as e:
            task.status = CeleryTask.STATUS_ERROR
            task.error_message = str(e)
            task.save()
            raise e

    @action(detail=True, methods=["get"], url_path="configure")
    def configure(self, request, pk=None, realm_code=None, space_code=None):
        configuration = self.get_object()

        # RESPONSE WITH HUGE JSON OF CONFIG, AND USER CAN SELECT WHAT TO DO WITH IT

        return Response({"status": "ok"})

    @action(
        detail=False,
        methods=["POST"],
        url_path="import-configuration",
        serializer_class=ConfigurationImportSerializer,
    )
    def import_configuration(self, request, pk=None, realm_code=None, space_code=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        celery_task = CeleryTask.objects.create(
            master_user=request.user.master_user,
            member=request.user.member,
            verbose_name="Configuration Import",
            type="configuration_import",
        )

        options_object = {
            "file_path": instance.file_path,
        }

        celery_task.options_object = options_object
        celery_task.save()

        instance.task_id = celery_task.id

        import_configuration.apply_async(kwargs={"task_id": celery_task.id, 'context': {
            'space_code': celery_task.master_user.space_code,
            'realm_code': celery_task.master_user.realm_code
        }})

        _l.info(f"ConfigurationViewSet.import_configuration celery_task {celery_task.id}")

        return Response({"task_id": celery_task.id}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["PUT"], url_path="push-configuration-to-marketplace")
    def push_configuration_to_marketplace(self, request, pk=None, realm_code=None, space_code=None):
        configuration = self.get_object()

        options_object = {
            "configuration_code": configuration.configuration_code,
            "changelog": request.data.get("changelog", ""),
            "username": request.data.get("username", ""),
            "password": request.data.get("password", ""),
        }

        celery_task = CeleryTask.objects.create(
            master_user=request.user.master_user,
            member=request.user.member,
            type="push_configuration_to_marketplace",
            options_object=options_object,
        )

        push_configuration_to_marketplace.apply_async(
            kwargs={"task_id": celery_task.id, 'context': {
                'space_code': celery_task.master_user.space_code,
                'realm_code': celery_task.master_user.realm_code
            }}
        )

        return Response({"task_id": celery_task.id})

    @action(
        detail=False,
        methods=["POST"],
        url_path="install-configuration-from-marketplace",
    )
    def install_configuration_from_marketplace(self, request, pk=None, realm_code=None, space_code=None):
        celery_task = CeleryTask.objects.create(
            master_user=request.user.master_user,
            member=request.user.member,
            verbose_name="Install Configuration From Marketplace",
            type="install_configuration_from_marketplace",
        )

        # TODO check this later, important security thins,
        #  need to be destroyed inside task
        options_object = {
            "configuration_code": request.data.get("configuration_code", None),
            "channel": request.data.get("channel", "stable"),
            "version": request.data.get("version", None),
            "is_package": request.data.get("is_package", False),
            "access_token": get_access_token(request)
        }

        celery_task.options_object = options_object
        celery_task.save()

        if request.data.get("is_package", False):
            install_package_from_marketplace.apply_async(
                kwargs={"task_id": celery_task.id, "context": {
                    "realm_code": request.realm_code,
                    "space_code": request.space_code
                }}
            )
        else:
            install_configuration_from_marketplace.apply_async(
                kwargs={"task_id": celery_task.id, "context": {
                    "realm_code": request.realm_code,
                    "space_code": request.space_code
                }}
            )

        _l.info(
            f"ConfigurationViewSet.import_configuration_from_marketplace "
            f"celery_task {celery_task.id}"
        )

        return Response({"task_id": celery_task.id}, status=status.HTTP_200_OK)


class NewMemberSetupConfigurationFilterSet(FilterSet):
    name = CharFilter()
    user_code = CharFilter()
    notes = CharFilter()
    target_configuration_code = CharFilter()
    target_configuration_version = CharFilter()

    class Meta:
        model = NewMemberSetupConfiguration
        fields = []


# class NewMemberSetupConfigurationViewSet(AbstractModelViewSet):
#     parser_classes = (MultiPartParser, FormParser, JSONParser)
#
#     queryset = NewMemberSetupConfiguration.objects
#     serializer_class = NewMemberSetupConfigurationSerializer
#     filter_class = NewMemberSetupConfigurationFilterSet
#     filter_backends = AbstractModelViewSet.filter_backends + []
#     permission_classes = AbstractModelViewSet.permission_classes + []
#
#     @action(detail=True, methods=["PUT"], url_path="install", serializer_class=None)
#     def install(self, request, pk=None, realm_code=None, space_code=None):
#         new_member_setup_configuration = self.get_object()
#
#         celery_task = None
#
#         # TODO refactor
#         if (
#             new_member_setup_configuration.target_configuration_code
#             and new_member_setup_configuration.target_configuration_code != "null"
#         ):
#             celery_task = CeleryTask.objects.create(
#                 master_user=request.user.master_user,
#                 member=request.user.member,
#                 type="install_initial_configuration",
#             )
#
#             options_object = {
#                 "configuration_code": new_member_setup_configuration.target_configuration_code,
#                 "version": new_member_setup_configuration.target_configuration_version,
#                 "channel": new_member_setup_configuration.target_configuration_channel,
#                 "is_package": new_member_setup_configuration.target_configuration_is_package,
#                 "access_token": get_access_token(request),
#             }
#
#             celery_task.options_object = options_object
#             celery_task.save()
#
#             if request.data.get("is_package", False):
#                 install_package_from_marketplace.apply_async(
#                     kwargs={"task_id": celery_task.id, 'context': {
#                         'space_code': celery_task.master_user.space_code,
#                         'realm_code': celery_task.master_user.realm_code
#                     }}
#                 )
#             else:
#                 install_configuration_from_marketplace.apply_async(
#                     kwargs={"task_id": celery_task.id, 'context': {
#                         'space_code': celery_task.master_user.space_code,
#                         'realm_code': celery_task.master_user.realm_code
#                     }}
#                 )
#
#         elif new_member_setup_configuration.file_url:
#             celery_task = CeleryTask.objects.create(
#                 master_user=request.user.master_user,
#                 member=request.user.member,
#                 type="install_initial_configuration",
#             )
#
#             options_object = {
#                 "file_path": new_member_setup_configuration.file_url,
#             }
#
#             celery_task.options_object = options_object
#             celery_task.save()
#
#             import_configuration.apply_async(kwargs={"task_id": celery_task.id, 'context': {
#                 'space_code': celery_task.master_user.space_code,
#                 'realm_code': celery_task.master_user.realm_code
#             }})
#
#         return Response({"task_id": celery_task.id})
