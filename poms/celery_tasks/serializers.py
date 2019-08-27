from rest_framework import serializers

from .models import CeleryTask
from poms.users.fields import MasterUserField


class CeleryTaskSerializer(serializers.ModelSerializer):
    master_user = MasterUserField()
    data = serializers.JSONField(allow_null=False)

    class Meta:

        model = CeleryTask
        fields = ('id', 'master_user', 'task_type', 'task_id', 'task_status', 'data')
