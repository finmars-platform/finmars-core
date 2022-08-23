import uuid


from rest_framework import serializers

from poms.users.fields import MasterUserField

from poms.system_messages.models import SystemMessage, SystemMessageAttachment


class SystemMessageAttachmentSerializer(serializers.ModelSerializer):

    class Meta:
        model = SystemMessageAttachment
        fields = ('id', 'file_url', 'file_name', 'notes', 'file_report')

    def __init__(self, *args, **kwargs):
        super(SystemMessageAttachmentSerializer, self).__init__(*args, **kwargs)

        from poms.file_reports.serializers import FileReportSerializer
        self.fields['file_report_object'] = FileReportSerializer(source='file_report',  read_only=True)


class SystemMessageSerializer(serializers.ModelSerializer):
    master_user = MasterUserField()

    attachments = SystemMessageAttachmentSerializer(many=True)

    class Meta:

        model = SystemMessage
        fields = ('id', 'master_user',
                  'section', 'type', 'action_status',
                  'title', 'description',
                  'created',
                  'linked_event',
                  'performed_by', 'created',
                  'attachments')


class SystemMessageActionSerializer(serializers.Serializer):
    ids = serializers.PrimaryKeyRelatedField(many=True, queryset=SystemMessage.objects.all())
