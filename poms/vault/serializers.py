import json

from rest_framework import serializers

from poms.common.serializers import (
    ModelWithTimeStampSerializer,
    ModelWithUserCodeSerializer,
)
from poms.users.fields import MasterUserField
from poms.vault.models import VaultRecord


class VaultStatusSerializer(serializers.Serializer):
    status = serializers.CharField(max_length=255)
    text = serializers.CharField(max_length=255)
    data = serializers.JSONField(allow_null=True, required=False)


class VaultSecretSerializer(serializers.Serializer):
    engine_name = serializers.CharField(required=True, allow_null=False, allow_blank=False)
    path = serializers.CharField(required=True, allow_null=False, allow_blank=False)
    data = serializers.JSONField(allow_null=False)


class UpdateVaultSecretSerializer(serializers.Serializer):
    engine_name = serializers.CharField(required=True, allow_null=False, allow_blank=False)
    path = serializers.CharField(required=True, allow_null=False, allow_blank=False)
    version = serializers.IntegerField(required=True)
    data = serializers.JSONField(allow_null=False)


class GetVaultSecretSerializer(serializers.Serializer):
    engine_name = serializers.CharField(required=True, allow_null=False, allow_blank=False)
    path = serializers.CharField(required=True, allow_null=False, allow_blank=False)


class DeleteVaultSecretSerializer(serializers.Serializer):
    engine_name = serializers.CharField(required=True, allow_null=False, allow_blank=False)
    path = serializers.CharField(required=True, allow_null=False, allow_blank=False)


class VaultEngineSerializer(serializers.Serializer):
    engine_name = serializers.CharField(max_length=255)


class DeleteVaultEngineSerializer(serializers.Serializer):
    engine_name = serializers.CharField(max_length=255)


class VaultSealSerializer(serializers.Serializer):
    action = serializers.CharField(max_length=255, default="seal")


class VaultUnsealSerializer(serializers.Serializer):
    action = serializers.CharField(max_length=255, default="unseal")
    key = serializers.CharField(max_length=255, required=True)


class VaultRecordSerializer(ModelWithUserCodeSerializer, ModelWithTimeStampSerializer):
    master_user = MasterUserField()
    name = serializers.CharField()
    data = serializers.JSONField(allow_null=False)

    class Meta:
        model = VaultRecord
        fields = ("id", "user_code", "name", "data", "master_user")

    @staticmethod
    def validate_data(payload):
        return json.dumps(payload)

    def to_representation(self, instance):
        response = super().to_representation(instance)
        try:
            response["data"] = json.loads(response["data"])
        except Exception as e:
            pass
        return response
