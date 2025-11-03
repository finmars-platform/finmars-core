from rest_framework import serializers

from poms.clients.models import Client, ClientSecret
from poms.common.fields import UserCodeField
from poms.common.serializers import (
    ModelMetaSerializer,
    ModelOwnerSerializer,
    ModelWithUserCodeSerializer,
)
from poms.portfolios.models import Portfolio
from poms.system_messages.handlers import send_system_message
from poms.users.fields import MasterUserField
from poms.users.utils import (
    get_master_user_from_context,
    get_member_from_context,
)


class ClientSerializer(ModelWithUserCodeSerializer):
    master_user = MasterUserField()

    portfolios = serializers.PrimaryKeyRelatedField(queryset=Portfolio.objects.all(), many=True, required=False)
    portfolios_object = serializers.PrimaryKeyRelatedField(source="portfolios", many=True, read_only=True)

    client_secrets = serializers.PrimaryKeyRelatedField(
        many=True,
        read_only=True,
    )
    client_secrets_object = serializers.PrimaryKeyRelatedField(source="client_secrets", many=True, read_only=True)

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
            "first_name_hash",
            "last_name",
            "last_name_hash",
            "telephone",
            "telephone_hash",
            "email",
            "email_hash",
            "notes",
            "portfolios",
            "portfolios_object",
            "client_secrets",
            "client_secrets_object",
        ]
        # extra_kwargs = {
        #     "telephone": {
        #         "help_text": (
        #             "Telephone number of client (symbol '+' is optional, "
        #             "length from 5 to 15 digits)"
        #         )
        #     },
        #     "email": {
        #         "help_text": "Email address of client (example email@outlook.com)"
        #     },
        # }

    def __init__(self, *args, **kwargs):
        from poms.portfolios.serializers import PortfolioViewSerializer

        super().__init__(*args, **kwargs)

        self.fields["portfolios_object"] = PortfolioViewSerializer(source="portfolios", many=True, read_only=True)

        request = self.context.get("request")
        if request and request.method == "GET":
            self.fields["client_secrets_object"] = ClientSecretLightSerializer(
                source="client_secrets",
                many=True,
                read_only=True,
            )
        else:
            self.fields["client_secrets_object"] = ClientSecretLightSerializer(
                many=True,
                required=False,
            )

    # def validate_telephone(self, value):
    #     if value is None:
    #         return
    #
    #     validator = RegexValidator(
    #         regex=r"^\+?\d{5,15}$",
    #         message=(
    #             "Enter a valid telephone number, vadil format is +123456 "
    #             "(symbol '+' is optional, length from 5 to 15 digits)"
    #         ),
    #     )
    #     validator(value)
    #
    #     return value

    def validate_client_secrets_object(self, value):
        if value is None:
            return

        secret_user_codes = []
        for secret in value:
            user_code = secret.get("user_code")

            if user_code in secret_user_codes:
                raise serializers.ValidationError(f"Duplicate user_code '{user_code}' for Client Secret")

            secret_user_codes.append(user_code)

        return value

    def create(self, validated_data):
        client_secrets_obj = validated_data.pop("client_secrets_object", [])
        client = super().create(validated_data)

        created_secrets = []
        for secret_obj in client_secrets_obj:
            secret = ClientSecret.objects.create(
                client=client,
                owner=client.owner,
                **secret_obj,
            )
            created_secrets.append(secret)

        client.client_secrets_object = created_secrets

        return client

    def update(self, instance, validated_data):
        client_secrets_obj = validated_data.pop("client_secrets_object", [])
        instance = super().update(instance, validated_data)

        updated_secrets = []
        for secret_obj in client_secrets_obj:
            user_code = secret_obj.get("user_code")
            secret, _ = ClientSecret.objects.update_or_create(
                client=instance,
                user_code=user_code,
                defaults={
                    "master_user": instance.master_user,
                    "owner": instance.owner,
                    **secret_obj,
                },
            )

            updated_secrets.append(secret)

        ClientSecret.objects.filter(client=instance).exclude(id__in=[secret.id for secret in updated_secrets]).delete()

        instance.client_secrets_object = updated_secrets

        return instance


class ClientSecretSerializer(ModelMetaSerializer, ModelOwnerSerializer):
    master_user = MasterUserField()

    client = serializers.SlugRelatedField(slug_field="user_code", queryset=Client.objects.all(), required=True)
    client_object = serializers.PrimaryKeyRelatedField(source="client", read_only=True, many=False)

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
        self.fields["client_object"] = ClientSerializer(source="client", many=False, read_only=True)

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
    client = serializers.PrimaryKeyRelatedField(
        read_only=True,
    )

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
