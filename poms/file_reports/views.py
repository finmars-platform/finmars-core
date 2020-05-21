from celery.result import AsyncResult
from django.core.signing import TimestampSigner
from django.http import HttpResponse
from django_filters.rest_framework import FilterSet
from rest_framework.decorators import action

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

    @action(detail=True, methods=['get'], url_path='view')
    def view_file(self, request, pk=None):

        master_user = request.user.master_user

        file_data = None

        try:
            instance = FileReport.objects.get(id=pk, master_user=master_user)

            file_data = instance.get_file()

        except FileReport.DoesNotExist:
            return Response({'status': 'notfound'}, status=status.HTTP_404_NOT_FOUND)

        if file_data is None:
            return Response({'status': 'notfound'}, status=status.HTTP_404_NOT_FOUND)

        response = HttpResponse(file_data, content_type='application/force-download')
        response['Content-Disposition'] = 'attachment; filename=%s' % instance.file_name

        response.write(file_data)

        return response

