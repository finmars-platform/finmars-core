from rest_framework import serializers
from django.core.validators import EmailValidator, RegexValidator
from poms.common.fields import UserCodeField
from poms.common.serializers import (
    ModelWithUserCodeSerializer,
    ModelMetaSerializer,
    ModelOwnerSerializer,
)
from poms.clients.models import Client, ClientSecret
from poms.portfolios.models import Portfolio
from poms.users.fields import MasterUserField
from poms.system_messages.handlers import send_system_message
from poms.users.utils import (
    get_master_user_from_context,
    get_member_from_context,
)


class ClientsSerializer(ModelWithUserCodeSerializer):
    master_user = MasterUserField()

    portfolios = serializers.PrimaryKeyRelatedField(
        queryset=Portfolio.objects.all(), many=True, required=False
    )
    portfolios_object = serializers.PrimaryKeyRelatedField(
        source="portfolios", many=True, read_only=True
    )

    client_secrets = serializers.PrimaryKeyRelatedField(
        queryset=ClientSecret.objects.all(), many=True, required=False
    )
    client_secrets_object = serializers.PrimaryKeyRelatedField(
        source="client_secrets", many=True, read_only=True
    )

    class Meta:
        model = Client
        fields = [
            "id",
            "master_user",
            "user_code",
            "name",
            "short_name",
            "public_name",
            "first_name",
            "last_name",
            "telephone",
            "email",
            "notes",

            "portfolios",
            "portfolios_object",
            "client_secrets",
            "client_secrets_object",
        ]
        extra_kwargs = {
            'telephone': {
                'help_text':(
                    "Telephone number of client (symbol '+' is optional, "
                    "length from 5 to 15 digits)"
                ) 
            },
            'email': {
                'help_text': 'Email address of client (example email@outlook.com)'
            },
        }

    def __init__(self, *args, **kwargs):
        from poms.portfolios.serializers import PortfolioViewSerializer

        super().__init__(*args, **kwargs)

        self.fields["portfolios_object"] = PortfolioViewSerializer(
            source="portfolios", many=True, read_only=True
        )
        self.fields["client_secrets_object"] = ClientSecretLightSerializer(
            source="client_secrets", many=True, read_only=True,
        )

    def validate_telephone(self, value):
        if value is None:
            return

        validator = RegexValidator(
            regex=r'^\+?\d{5,15}$',
            message=(
                "Enter a valid telephone number, vadil format is +123456 "
                "(symbol '+' is optional, length from 5 to 15 digits)"
            ),
        )
        validator(value)

        return value


class ClientSecretSerializer(ModelMetaSerializer, ModelOwnerSerializer):
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
            "provider",
            "portfolio",
            "path_to_secret",
            "notes",

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


class ClientSecretLightSerializer(ModelMetaSerializer, ModelOwnerSerializer):
    master_user = MasterUserField()

    class Meta:
        model = ClientSecret
        fields = [
            "id",
            "master_user",
            "client",
            "user_code",
            "provider",
            "portfolio",
            "path_to_secret",
            "notes",
        ]
