from logging import getLogger

from django.http import HttpResponse
from django_filters.rest_framework import FilterSet
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response


from poms.common.views import AbstractModelViewSet
from poms.csv_import.filters import SchemeContentTypeFilter
from poms.file_reports.models import FileReport
from poms.file_reports.serializers import FileReportSerializer
from poms.users.filters import OwnerByMasterUserFilter

_l = getLogger("poms.csv_import")


class FileReportFilterSet(FilterSet):
    content_type = SchemeContentTypeFilter(field_name="content_type")

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

    @action(detail=True, methods=["get"], url_path="view")
    def view_file(self, request, pk=None, realm_code=None, space_code=None):
        master_user = request.user.master_user

        try:
            instance = FileReport.objects.get(id=pk, master_user=master_user)

            file_data = instance.get_file()

        except FileReport.DoesNotExist:
            return Response({"status": "notfound"}, status=status.HTTP_404_NOT_FOUND)

        if file_data is None:
            return Response({"status": "notfound"}, status=status.HTTP_404_NOT_FOUND)

        response = HttpResponse(file_data, content_type="application/force-download")
        response["Content-Disposition"] = f"attachment; filename={instance.file_name}"
        return response
