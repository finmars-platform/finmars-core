import json
from logging import getLogger

from rest_framework import serializers
from poms.csv_import.handlers import SimpleImportProcess

from poms.users.fields import MasterUserField, MemberField
from .models import CeleryTask, CeleryTaskAttachment, CeleryWorker

_l = getLogger("poms.celery_tasks")

class CeleryTaskAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CeleryTaskAttachment
        fields = (
            "id",
            "file_url",
            "file_name",
            "notes",
            "file_report",
        )

    def __init__(self, *args, **kwargs):
        from poms.file_reports.serializers import FileReportSerializer

        super().__init__(*args, **kwargs)

        self.fields["file_report_object"] = FileReportSerializer(
            source="file_report", read_only=True
        )

def _get_result_stats(instance):

    if not hasattr(instance.result_object, "get"):
        return {
            "total_count": None,
            "error_count": None,
            "success_count": None,
            "skip_count": None,
        }

    result_stats = {
        "total_count": 0,
        "error_count": 0,
        "success_count": 0,
        "skip_count": 0,
    }

    if instance.result_object.get("items") is not None:

        for item in instance.result_object["items"]:
            if item["status"] in ["success", "skip", "error"]:
                key = f"{item['status']}_count"
                result_stats[key] = result_stats[key] + 1
            result_stats["total_count"] = result_stats["total_count"] + 1

    return result_stats

class CeleryTaskSerializer(serializers.ModelSerializer):
    master_user = MasterUserField()
    member = MemberField()
    options_object = serializers.JSONField(allow_null=False)
    result_object = serializers.JSONField(allow_null=False)
    progress_object = serializers.JSONField(allow_null=False)
    attachments = CeleryTaskAttachmentSerializer(many=True)
    result_stats = serializers.SerializerMethodField()


    class Meta:
        model = CeleryTask
        fields = (
            "id",
            "member",
            "master_user",
            "parent",
            "children",
            "type",
            "celery_task_id",
            "status",
            "options_object",
            "result_object",
            "is_system_task",
            "created",
            "modified",
            "attachments",
            "notes",
            "verbose_name",
            "verbose_result",
            "progress_object",
            "error_message",
            "finished_at",
            "file_report",
            "worker_name",

            'ttl',
            'expiry_at',
            'result_stats',
        )

    def get_result_stats(self, instance):
        return _get_result_stats(instance)

    def __init__(self, *args, **kwargs):
        from poms.users.serializers import MemberViewSerializer

        super().__init__(*args, **kwargs)

        self.fields["member_object"] = MemberViewSerializer(
            source="member", read_only=True
        )


class CeleryTaskLightSerializer(serializers.ModelSerializer):
    master_user = MasterUserField()
    member = MemberField()
    progress_object = serializers.JSONField(allow_null=False)
    attachments = CeleryTaskAttachmentSerializer(many=True)
    result_stats = serializers.SerializerMethodField()

    class Meta:
        model = CeleryTask
        fields = (
            "id",
            "member",
            "master_user",
            "parent",
            "children",
            "type",
            "celery_task_id",
            "status",
            "is_system_task",
            "created",
            "modified",
            "attachments",
            "notes",
            "verbose_name",
            "verbose_result",
            "progress_object",
            "error_message",
            "finished_at",
            "file_report",
            'result_stats',
        )

    def get_result_stats(self, instance):
        return _get_result_stats(instance)

    def __init__(self, *args, **kwargs):
        from poms.users.serializers import MemberViewSerializer

        super().__init__(*args, **kwargs)

        self.fields["member_object"] = MemberViewSerializer(
            source="member", read_only=True
        )


class CeleryTaskUpdateStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=("success", "error", "timeout", "canceled"))
    result = serializers.JSONField(allow_null=True, required=False)
    error = serializers.CharField(allow_null=True, required=False)


class CeleryWorkerSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()

    class Meta:
        model = CeleryWorker
        fields = ["id", "worker_name", "worker_type", "notes", "memory_limit", "queue", "status"]

    def get_status(self, instance):

        try:
            return json.loads(instance.status)
        except Exception as e:
            return {
                "status": "unknown",
                "error_message": None
            }