from django.contrib.contenttypes.models import ContentType
from django.apps import apps
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from poms.csv_import.fields import CsvImportContentTypeField
from poms.file_reports.models import FileReport
from poms.users.fields import MasterUserField


class FileReportSerializer(serializers.ModelSerializer):

    master_user = MasterUserField()

    class Meta:
        model = FileReport
        fields = ('id',  'master_user',  'name', 'notes', 'type', 'created_at')
