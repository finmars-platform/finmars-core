from rest_framework import serializers

from poms.system_messages.models import (
    SystemMessage,
    SystemMessageAttachment,
    SystemMessageComment,
)
from poms.users.fields import MasterUserField
from poms.users.utils import get_member_from_context


class SystemMessageAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemMessageAttachment
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

        self.fields["file_report_object"] = FileReportSerializer(source="file_report", read_only=True)


class SystemMessageCommentSerializer(serializers.ModelSerializer):
    member_object = serializers.SerializerMethodField()

    class Meta:
        model = SystemMessageComment
        fields = (
            "id",
            "member",
            "member_object",
            "comment",
            "created_at",
            "modified_at",
        )

    def get_member_object(self, instance):
        return {"id": instance.member.id, "username": instance.member.username}


class SystemMessageSerializer(serializers.ModelSerializer):
    master_user = MasterUserField()
    attachments = SystemMessageAttachmentSerializer(many=True, read_only=True)
    comments = SystemMessageCommentSerializer(many=True, read_only=True)

    class Meta:
        model = SystemMessage
        fields = (
            "id",
            "master_user",
            "section",
            "type",
            "action_status",
            "title",
            "description",
            "created_at",
            "linked_event",
            "performed_by",
            "comments",
            "attachments",
        )

    def to_representation(self, instance):
        member = get_member_from_context(self.context)

        result = super().to_representation(instance)

        for member_message in instance.members.all():
            if member_message.member_id == member.id:
                result["is_read"] = member_message.is_read
                result["is_pinned"] = member_message.is_pinned

        if "is_read" not in result:
            result["is_read"] = True

        if "is_pinned" not in result:
            result["is_pinned"] = False

        return result


class SystemMessageActionSerializer(serializers.Serializer):
    ids = serializers.PrimaryKeyRelatedField(many=True, queryset=SystemMessage.objects.all())
    sections = serializers.MultipleChoiceField(
        default=SystemMessage.SECTION_OTHER, choices=SystemMessage.SECTION_CHOICES
    )
