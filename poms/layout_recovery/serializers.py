from rest_framework import serializers

from poms.layout_recovery.models import LayoutArchetype
from poms.users.fields import MasterUserField


class GenerateLayoutArchetype:
    def __init__(self, task_id=None, task_status=None):
        self.task_id = task_id
        self.task_status = task_status


class FixLayout:
    def __init__(self, task_id=None, task_status=None):
        self.task_id = task_id
        self.task_status = task_status


class LayoutArchetypeSerializer(serializers.ModelSerializer):
    master_user = MasterUserField()
    data = serializers.JSONField(allow_null=False)

    class Meta:

        model = LayoutArchetype
        fields = ('id', 'master_user', 'name', 'data')


class GenerateLayoutArchetypeSerializer(serializers.Serializer):
    task_id = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    task_status = serializers.ReadOnlyField()

    def create(self, validated_data):
        return GenerateLayoutArchetype(**validated_data)


class FixLayoutSerializer(serializers.Serializer):
    task_id = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    task_status = serializers.ReadOnlyField()

    def create(self, validated_data):
        return FixLayout(**validated_data)
