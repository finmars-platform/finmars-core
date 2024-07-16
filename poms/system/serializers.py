from rest_framework import serializers

from poms.common.serializers import ModelWithTimeStampSerializer, ModelWithUserCodeSerializer
from poms.users.fields import MasterUserField
from poms.system.models import EcosystemConfiguration, VaultRecord


class EcosystemConfigurationSerializer(serializers.ModelSerializer):
    data = serializers.JSONField(allow_null=False)

    class Meta:
        model = EcosystemConfiguration
        fields = ('id', 'name', 'description', 'data')


class VaultRecordSerializer(ModelWithUserCodeSerializer, ModelWithTimeStampSerializer):
    master_user = MasterUserField()
    data = serializers.CharField(allow_null=False)

    class Meta:
        model = VaultRecord
        fields = ('id', 'user_code', 'data', 'master_user')
