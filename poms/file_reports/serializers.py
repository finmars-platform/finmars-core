from rest_framework import serializers

from poms.file_reports.models import FileReport
from poms.users.fields import MasterUserField


class FileReportSerializer(serializers.ModelSerializer):
    master_user = MasterUserField()

    content_type_verbose = serializers.SerializerMethodField()

    def get_content_type_verbose(self, instance):
        content_type = getattr(instance, 'content_type', None)

        result = None

        if content_type:
            result = content_type.split('/')[1]

        return result

    class Meta:
        model = FileReport
        fields = ('id', 'master_user', 'name', 'notes', 'type', 'created_at', 'content_type', 'content_type_verbose', 'file_url')
