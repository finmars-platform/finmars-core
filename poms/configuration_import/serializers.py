
from rest_framework import serializers

from poms.users.fields import MasterUserField, MemberField, HiddenMemberField


class ConfigurationImportAsJson:
    def __init__(self, task_id=None, task_status=None, master_user=None, status=None,
                 data=None, member=None,
                 total_rows=0, processed_rows=0, stats=None, imported=None):
        self.task_id = task_id
        self.task_status = task_status

        self.data = data
        self.master_user = master_user
        self.member = member
        self.status = status

        self.stats = stats

        self.imported = imported

        self.total_rows = total_rows
        self.processed_rows = processed_rows

    def __str__(self):
        return '%s' % (getattr(self.master_user, 'name', None))


class ConfigurationImportAsJsonSerializer(serializers.Serializer):
    task_id = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    task_status = serializers.ReadOnlyField()

    data = serializers.JSONField(allow_null=True, )

    master_user = MasterUserField()
    member = HiddenMemberField()

    stats = serializers.ReadOnlyField()
    imported = serializers.ReadOnlyField()

    processed_rows = serializers.ReadOnlyField()
    total_rows = serializers.ReadOnlyField()

    def create(self, validated_data):
        if validated_data.get('task_id', None):
            validated_data.pop('data', None)

        return ConfigurationImportAsJson(**validated_data)
