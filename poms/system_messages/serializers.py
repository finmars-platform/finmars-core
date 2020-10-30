import uuid


from rest_framework import serializers

from poms.users.fields import MasterUserField

from poms.system_messages.models import SystemMessage


class SystemMessageSerializer(serializers.ModelSerializer):
    master_user = MasterUserField()

    class Meta:

        model = SystemMessage
        fields = ('id', 'master_user', 'level', 'status', 'text', 'created', 'source')
