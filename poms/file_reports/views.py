from celery.result import AsyncResult
from django.core.signing import TimestampSigner
from django_filters.rest_framework import FilterSet

from rest_framework.response import Response
from rest_framework import status

from poms.common.utils import date_now, datetime_now

from poms.celery_tasks.models import CeleryTask
from poms.common.views import AbstractModelViewSet, AbstractAsyncViewSet
from poms.csv_import.filters import SchemeContentTypeFilter

from poms.csv_import.tasks import data_csv_file_import, data_csv_file_import_validate
from poms.file_reports.models import FileReport
from poms.file_reports.serializers import FileReportSerializer
from poms.obj_perms.permissions import PomsFunctionPermission, PomsConfigurationPermission

from poms.users.filters import OwnerByMasterUserFilter


from logging import getLogger

_l = getLogger('poms.csv_import')


class FileReportFilterSet(FilterSet):
    content_type = SchemeContentTypeFilter(field_name='content_type')

    class Meta:
        model = FileReport
        fields = []


class FileReportViewSet(AbstractModelViewSet):
    queryset = FileReport.objects
    serializer_class = FileReportSerializer
    filter_class = FileReportFilterSet
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    # permission_classes = AbstractModelViewSet.permission_classes + [
    #     PomsConfigurationPermission
    # ]
