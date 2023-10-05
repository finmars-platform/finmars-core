from rest_framework import serializers

from poms.file_reports.models import FileReport
from poms.users.fields import MasterUserField


class FileReportSerializer(serializers.ModelSerializer):
    master_user = MasterUserField()
    content_type_verbose = serializers.SerializerMethodField()

    @staticmethod
    def get_content_type_verbose(instance) -> str:
        content_type = getattr(instance, "content_type", None)

        return content_type.split("/")[1] if content_type else ""

    class Meta:
        model = FileReport
        fields = (
            "id",
            "master_user",
            "name",
            "notes",
            "type",
            "created_at",
            "content_type",
            "content_type_verbose",
            "file_url",
        )
