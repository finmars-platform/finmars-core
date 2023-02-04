from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers
from poms.history.models import HistoricalRecord


class ContentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentType
        fields = ['name', ]
        read_only_fields = fields


class HistoricalRecordSerializer(serializers.ModelSerializer):
    data = serializers.JSONField(allow_null=False)
    member_object = serializers.SerializerMethodField()
    content_type = serializers.SerializerMethodField()

    class Meta:
        model = HistoricalRecord
        fields = (
            'member',
            'member_object',
            'id',
            'notes',
            'user_code',
            'data',
            'content_type'
        )

        read_only_fields = fields

    def get_member_object(self, instance):
        return {
            'id': instance.member.id,
            'username': instance.member.username
        }

    def get_content_type(self, instance):
        return instance.content_type.app_label + '.' + instance.content_type.model

