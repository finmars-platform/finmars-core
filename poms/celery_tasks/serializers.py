from rest_framework import serializers

from poms.users.fields import MasterUserField, MemberField

from .models import CeleryTask, CeleryTaskAttachment


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


class CeleryTaskSerializer(serializers.ModelSerializer):
    master_user = MasterUserField()
    member = MemberField()
    options_object = serializers.JSONField(allow_null=False)
    result_object = serializers.JSONField(allow_null=False)
    progress_object = serializers.JSONField(allow_null=False)
    attachments = CeleryTaskAttachmentSerializer(many=True)

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
        )

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
        )

    def __init__(self, *args, **kwargs):
        from poms.users.serializers import MemberViewSerializer

        super().__init__(*args, **kwargs)

        self.fields["member_object"] = MemberViewSerializer(
            source="member", read_only=True
        )
