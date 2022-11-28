import logging

from django_filters.rest_framework import FilterSet
from rest_framework.response import Response

from poms.common.filters import CharFilter
from poms.common.views import AbstractModelViewSet
from poms.configuration_import.serializers import ConfigurationImportAsJsonSerializer
from poms.configuration_import.tasks import configuration_import_as_json
from poms.configuration_sharing.filters import OwnerByRecipient, OwnerBySender
from poms.configuration_sharing.models import SharedConfigurationFile, InviteToSharedConfigurationFile
from poms.configuration_sharing.serializers import SharedConfigurationFileSerializer, \
    InviteToSharedConfigurationFileSerializer, MyInviteToSharedConfigurationFileSerializer
from poms.obj_perms.permissions import PomsConfigurationPermission
from poms.ui.models import ListLayout

_l = logging.getLogger('poms.configuration_sharing')


class SharedConfigurationFileFilterSet(FilterSet):
    class Meta:
        model = SharedConfigurationFile
        fields = []


class SharedConfigurationFileViewSet(AbstractModelViewSet):
    queryset = SharedConfigurationFile.objects
    serializer_class = SharedConfigurationFileSerializer
    filter_class = SharedConfigurationFileFilterSet
    filter_backends = AbstractModelViewSet.filter_backends + [
        # OwnerByUserFilter
    ]
    permission_classes = AbstractModelViewSet.permission_classes + [
        PomsConfigurationPermission
    ]

    def update(self, request, *args, **kwargs):

        is_force = request.query_params.get('force', False)

        if (is_force == 'true'):
            is_force = True
        else:
            is_force = False

        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if is_force:
            master_user = request.user.master_user
            layouts = ListLayout.objects.filter(member__master_user=master_user, sourced_from_global_layout=instance)

            _l.info("layouts to force update %s" % len(layouts))

            processed = 0

            for layout in layouts:
                serializer = ConfigurationImportAsJsonSerializer(data={
                    "data": instance.data,
                    "master_user": master_user,  # share only inside same ecosystem
                    "member": layout.member,
                    "mode": 'overwrite'
                }, context={
                    "request": request
                })
                serializer.is_valid(raise_exception=True)
                config_import_instance = serializer.save()

                configuration_import_as_json.apply_async(kwargs={'instance': config_import_instance})
                processed = processed + 1

            _l.info("Processed layouts %s" % processed)

        return Response(serializer.data)


class InviteToSharedConfigurationFileFilterSet(FilterSet):
    status = CharFilter()

    class Meta:
        model = InviteToSharedConfigurationFile
        fields = []


class InviteToSharedConfigurationFileViewSet(AbstractModelViewSet):
    queryset = InviteToSharedConfigurationFile.objects
    serializer_class = InviteToSharedConfigurationFileSerializer
    filter_class = InviteToSharedConfigurationFileFilterSet
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerBySender,
    ]
    permission_classes = AbstractModelViewSet.permission_classes + [
        PomsConfigurationPermission
    ]


class MyInviteToSharedConfigurationFileViewSet(AbstractModelViewSet):
    queryset = InviteToSharedConfigurationFile.objects
    serializer_class = MyInviteToSharedConfigurationFileSerializer
    filter_class = InviteToSharedConfigurationFileFilterSet
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByRecipient,
    ]
    permission_classes = AbstractModelViewSet.permission_classes + [
        PomsConfigurationPermission
    ]
