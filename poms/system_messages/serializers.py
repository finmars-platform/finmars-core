from rest_framework import serializers

from poms.system_messages.models import SystemMessage, SystemMessageAttachment
from poms.users.fields import MasterUserField
from poms.users.utils import get_member_from_context


class SystemMessageAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemMessageAttachment
        fields = ('id', 'file_url', 'file_name', 'notes', 'file_report')

    def __init__(self, *args, **kwargs):
        super(SystemMessageAttachmentSerializer, self).__init__(*args, **kwargs)

        from poms.file_reports.serializers import FileReportSerializer
        self.fields['file_report_object'] = FileReportSerializer(source='file_report', read_only=True)


class SystemMessageSerializer(serializers.ModelSerializer):
    master_user = MasterUserField()

    attachments = SystemMessageAttachmentSerializer(many=True, read_only=True)

    class Meta:

        model = SystemMessage
        fields = ('id', 'master_user',
                  'section', 'type', 'action_status',
                  'title', 'description',
                  'created',
                  'linked_event',
                  'performed_by', 'created',
                  'attachments')

    def to_representation(self, instance):

        member = get_member_from_context(self.context)

        result = super(SystemMessageSerializer, self).to_representation(instance)

        for member_message in instance.members.all():

            if member_message.member_id == member.id:
                result['is_read'] = member_message.is_read
                result['is_pinned'] = member_message.is_pinned

        if 'is_read' not in result:
            result['is_read'] = True

        if 'is_pinned' not in result:
            result['is_pinned'] = False

        # _l.debug('InstrumentLightSerializer done: %s', "{:3.3f}".format(time.perf_counter() - st))

        return result


class SystemMessageActionSerializer(serializers.Serializer):
    ids = serializers.PrimaryKeyRelatedField(many=True, queryset=SystemMessage.objects.all())
    sections = serializers.MultipleChoiceField(default=SystemMessage.SECTION_OTHER,
                                               choices=SystemMessage.SECTION_CHOICES)
