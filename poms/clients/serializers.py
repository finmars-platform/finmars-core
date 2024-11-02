from rest_framework import serializers
from poms.common.fields import UserCodeField
from poms.common.serializers import (
    ModelWithUserCodeSerializer,
    ModelMetaSerializer,
    ModelOwnerSerializer,
)
from poms.clients.models import Client, ClientSecret
from poms.users.fields import MasterUserField

from poms.system_messages.handlers import send_system_message
from poms.users.utils import (
    get_master_user_from_context,
    get_member_from_context,
)


class ClientsSerializer(ModelWithUserCodeSerializer):
    master_user = MasterUserField()

    class Meta:
        model = Client
        fields = [
            "id",
            "master_user",
            "user_code",
            "name",
            "short_name",
            "public_name",
            "notes",
        ]


class ClientSecretLightSerializer(ModelMetaSerializer, ModelOwnerSerializer):
    master_user = MasterUserField()
    client = serializers.SlugRelatedField(
        slug_field="user_code",
        queryset=Client.objects.all(),
        required=True
    )
    client_object = serializers.PrimaryKeyRelatedField(
        source="client", read_only=True, many=False
    )

    class Meta:
        model = ClientSecret
        fields = [
            "id",
            "master_user",
            "user_code",
            "client",
            "client_object",
        ]


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["user_code"] = UserCodeField()
        self.fields["deleted_user_code"] = UserCodeField(read_only=True)
        self.fields["client_object"] = ClientsSerializer(
            source="client", many=False, read_only=True
        )


    def create(self, validated_data):
        instance = super().create(validated_data)

        member = get_member_from_context(self.context)
        master_user = get_master_user_from_context(self.context)
        entity_name = self.Meta.model._meta.model_name

        send_system_message(
            master_user=master_user,
            performed_by=member.username,
            section="data",
            type="success",
            title=f"New {entity_name} (manual)",
            description=f"New {entity_name} created (manual) - {instance.user_code}",
        )

        return instance


    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
    
        member = get_member_from_context(self.context)
        master_user = get_master_user_from_context(self.context)
        entity_name = self.Meta.model._meta.model_name

        send_system_message(
            master_user=master_user,
            performed_by=member.username,
            section="data",
            type="warning",
            title=f"Edit {entity_name} (manual)",
            description=f"{entity_name} edited (manual) - {instance.user_code}",
        )

        return instance