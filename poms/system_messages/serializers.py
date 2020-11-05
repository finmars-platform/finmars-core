import uuid


from rest_framework import serializers

from poms.users.fields import MasterUserField

from poms.system_messages.models import SystemMessage, SystemMessageAttachment


class SystemMessageAttachmentSerializer(serializers.ModelSerializer):

    class Meta:
        model = SystemMessageAttachment
        fields = ('id', 'file_url', 'file_name' 'notes', 'file_report')


class SystemMessageSerializer(serializers.ModelSerializer):
    master_user = MasterUserField()

    attachments = SystemMessageAttachmentSerializer(many=True)

    class Meta:

        model = SystemMessage
        fields = ('id', 'master_user', 'level', 'status', 'text', 'created', 'source', 'attachments')


