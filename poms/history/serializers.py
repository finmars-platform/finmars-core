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
    content_type = ContentTypeSerializer()

    class Meta:
        model = HistoricalRecord
        fields = (
            'member',
            'id',
            'notes'
            'user_code',
            'data',
            'content_type'
        )

        readonly_fields = fields
