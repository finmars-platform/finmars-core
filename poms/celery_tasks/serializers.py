from rest_framework import serializers

from .models import CeleryTask
from poms.users.fields import MasterUserField, MemberField


class CeleryTaskSerializer(serializers.ModelSerializer):
    master_user = MasterUserField()
    member = MemberField()
    options_object = serializers.JSONField(allow_null=False)
    result_object = serializers.JSONField(allow_null=False)

    class Meta:

        model = CeleryTask
        fields = ('id',  'member',
                  'master_user',
                  'parent', 'children',
                  'type', 'celery_task_id', 'status',
                  'options_object', 'result_object',
                  'is_system_task',
                  'created', 'modified',
                  'file_report')


    def __init__(self, *args, **kwargs):
        super(CeleryTaskSerializer, self).__init__(*args, **kwargs)

        from poms.users.serializers import MemberViewSerializer
        self.fields['member_object'] = MemberViewSerializer(source='member', read_only=True)