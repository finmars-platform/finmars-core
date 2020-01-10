from rest_framework import serializers

from .models import CeleryTask
from poms.users.fields import MasterUserField, MemberField


class CeleryTaskSerializer(serializers.ModelSerializer):
    master_user = MasterUserField()
    member = MemberField()
    data = serializers.JSONField(allow_null=False)

    class Meta:

        model = CeleryTask
        fields = ('id', 'master_user', 'task_type', 'task_id', 'task_status', 'data', 'is_system_task', 'member', 'started_at', 'finished_at', 'file_report')


    def __init__(self, *args, **kwargs):
        super(CeleryTaskSerializer, self).__init__(*args, **kwargs)

        from poms.users.serializers import MemberViewSerializer
        self.fields['member_object'] = MemberViewSerializer(source='member', read_only=True)