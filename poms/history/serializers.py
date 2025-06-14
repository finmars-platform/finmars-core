from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers

from poms.history.models import HistoricalRecord


class ContentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentType
        fields = [
            "name",
        ]
        read_only_fields = fields


class HistoricalRecordSerializer(serializers.ModelSerializer):
    member_object = serializers.SerializerMethodField()
    content_type = serializers.SerializerMethodField()

    class Meta:
        model = HistoricalRecord
        fields = (
            "member",
            "member_object",
            "id",
            "notes",
            "diff",
            "user_code",
            "context_url",
            "action",
            "content_type",
            "created_at",
        )

        read_only_fields = fields

    def get_member_object(self, instance):
        return {"id": instance.member.id, "username": instance.member.username}

    def get_content_type(self, instance):
        return f"{instance.content_type.app_label}.{instance.content_type.model}"


class ExportJournalSerializer(serializers.Serializer):
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=True)
