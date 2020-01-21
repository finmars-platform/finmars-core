from celery.result import AsyncResult
from django.core.signing import TimestampSigner
from django_filters.rest_framework import FilterSet

from rest_framework.response import Response
from rest_framework import status

from poms.common.filters import CharFilter
from poms.common.utils import date_now, datetime_now

from poms.celery_tasks.models import CeleryTask
from poms.common.views import AbstractModelViewSet, AbstractAsyncViewSet
from poms.configuration_sharing.filters import OwnerByRecipient, OwnerBySender
from poms.configuration_sharing.models import SharedConfigurationFile, InviteToSharedConfigurationFile
from poms.configuration_sharing.serializers import SharedConfigurationFileSerializer, \
    InviteToSharedConfigurationFileSerializer, MyInviteToSharedConfigurationFileSerializer

from poms.csv_import.tasks import data_csv_file_import, data_csv_file_import_validate
from poms.obj_perms.permissions import PomsFunctionPermission, PomsConfigurationPermission

from poms.users.filters import OwnerByMasterUserFilter, OwnerByUserFilter


class SharedConfigurationFileFilterSet(FilterSet):

    class Meta:
        model = SharedConfigurationFile
        fields = []


class SharedConfigurationFileViewSet(AbstractModelViewSet):
    queryset = SharedConfigurationFile.objects
    serializer_class = SharedConfigurationFileSerializer
    filter_class = SharedConfigurationFileFilterSet
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByUserFilter
    ]
    permission_classes = AbstractModelViewSet.permission_classes + [
        PomsConfigurationPermission
    ]


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
