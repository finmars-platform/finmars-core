from django.contrib.contenttypes.models import ContentType
from django.apps import apps
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from poms.common.fields import ExpressionField
from poms.common.models import EXPRESSION_FIELD_LENGTH
from poms.configuration_sharing.models import SharedConfigurationFile, InviteToSharedConfigurationFile
from poms.users.fields import MasterUserField, HiddenMemberField, UserField, HiddenUserField, CurrentUserField
from poms.users.serializers import MemberViewSerializer


class SharedConfigurationFileSerializer(serializers.ModelSerializer):

    data = serializers.JSONField(allow_null=False)
    user = CurrentUserField()
    linked_master_user = MasterUserField()

    class Meta:
        model = SharedConfigurationFile
        fields = ('id', 'name', 'data', 'notes', 'publicity_type', 'user', 'linked_master_user')


class InviteToSharedConfigurationFileSerializer(serializers.ModelSerializer):

    member_from = HiddenMemberField()

    class Meta:
        model = InviteToSharedConfigurationFile
        fields = ('id', 'member_from', 'member_to', 'status', 'shared_configuration_file')


class MyInviteToSharedConfigurationFileSerializer(serializers.ModelSerializer):


    def __init__(self, *args, **kwargs):

        super(MyInviteToSharedConfigurationFileSerializer, self).__init__(*args, **kwargs)

        self.fields['member_from_object'] = MemberViewSerializer(source='member_from', read_only=True)
        self.fields['shared_configuration_file_object'] = SharedConfigurationFileSerializer(source='shared_configuration_file', read_only=True)


    class Meta:
        model = InviteToSharedConfigurationFile
        fields = ('id', 'member_from', 'member_to', 'status', 'shared_configuration_file', 'notes')
