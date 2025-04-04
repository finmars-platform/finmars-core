from datetime import timedelta

import jwt

from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from poms.auth_tokens.models import PersonalAccessToken
from poms.common.serializers import ModelMetaSerializer, ModelWithUserCodeSerializer
from poms.users.fields import MasterUserField
from poms.users.utils import get_master_user_from_context, get_member_from_context
from poms_app import settings


class SetAuthTokenSerializer(serializers.Serializer):
    key = serializers.CharField(label=_("Key"))
    user_id = serializers.CharField(label=_("User id"))
    user_legacy_id = serializers.IntegerField(required=False, label=_("User legacy id"))
    current_master_user_id = serializers.CharField(label=_("Current master user id"))
    current_master_user_legacy_id = serializers.IntegerField(
        required=False, label=_("Current master user legacy id")
    )


class CreateUserSerializer(serializers.Serializer):
    username = serializers.CharField(label=_("Username"))
    email = serializers.CharField(label=_("Email"), required=False, allow_blank=True)
    roles = serializers.CharField(label=_("Roles"), required=False, allow_blank=True, default="")
    groups = serializers.CharField(label=_("Groups"), required=False, allow_blank=True, default="")
    is_admin = serializers.BooleanField(label=_("Is Admin"), required=False, default=False)


class CreateMasterUserSerializer(serializers.Serializer):
    name = serializers.CharField(label=_("name"))
    unique_id = serializers.CharField(label=_("Unique id"))
    user_unique_id = serializers.CharField(label=_("User Unique id"))
    old_backup_name = serializers.CharField(label=_("Old backup name"), required=False, allow_blank=True)


class RenameMasterUserSerializer(serializers.Serializer):
    name = serializers.CharField(label=_("name"))


class MasterUserChangeOwnerSerializer(serializers.Serializer):
    target_member_username = serializers.CharField(label=_("target member username"))
    unique_id = serializers.CharField(label=_("Unique id"))


class CreateMemberSerializer(serializers.Serializer):
    groups = serializers.CharField(required=False, label=_("Groups"), allow_blank=True, allow_null=True)
    username = serializers.CharField(label=_("username"))
    user_id = serializers.CharField(label=_("User Id"))
    user_legacy_id = serializers.IntegerField(required=False, label=_("User legacy id"))
    member_id = serializers.CharField(label=_("Member id"))
    master_user_id = serializers.CharField(label=_("Master User id"))
    master_user_legacy_id = serializers.IntegerField(required=False, label=_("Current master user legacy id"))


class DeleteMemberSerializer(serializers.Serializer):
    username = serializers.CharField(label=_("username"))


class AcceptInviteSerializer(serializers.Serializer):
    username = serializers.CharField(label=_("Username"))


class PersonalAccessTokenSerializer(
    ModelWithUserCodeSerializer,
    ModelMetaSerializer,
):
    master_user = MasterUserField()

    class Meta:
        model = PersonalAccessToken
        fields = [
            "id",
            "master_user",
            "user_code",
            "name",
            "short_name",
            "public_name",
        ]

    def __init__(self, *args, **kwargs):
        super(PersonalAccessTokenSerializer, self).__init__(*args, **kwargs)


class CreatePersonalAccessTokenSerializer(serializers.ModelSerializer):

    days_to_live = serializers.IntegerField(
        write_only=True,
        initial=90,
        min_value=1,
        max_value=365,
        help_text="Number of days until the token expires. Up to 365 days.",
    )
    access_level = serializers.ChoiceField(
        choices=["read", "write", "admin"],
        write_only=True,
        help_text="Access level of the token.",
    )
    name = serializers.CharField(required=True, help_text="Human Readable Name")
    user_code = serializers.CharField(required=True, help_text="User Code for IAM policies")
    notes = serializers.CharField(
        required=False, allow_null=True, allow_blank=True, help_text="Comments or notes about the token."
    )

    class Meta:
        model = PersonalAccessToken
        fields = (
            "name",
            "user_code",
            "notes",
            "access_level",
            "days_to_live",
        )

    def create(self, validated_data):

        days_to_live = validated_data.pop("days_to_live")
        access_level = validated_data.pop("access_level")
        name = validated_data.pop("name")
        user_code = validated_data.pop("user_code")
        notes = validated_data.pop("notes", None)

        expires_at = timezone.now() + timedelta(days=days_to_live)

        master_user = get_master_user_from_context(self.context)
        member = get_member_from_context(self.context)

        refresh = RefreshToken.for_user(member.user)

        access_token = refresh.access_token

        access_token.set_exp(lifetime=timedelta(days=days_to_live))

        decode_token = jwt.decode(str(access_token), settings.SECRET_KEY, algorithms=["HS256"])

        decode_token["username"] = member.user.username
        decode_token["access_level"] = access_level
        decode_token["meta"] = {
            "realm_code": "realm00000",  # fix in 1.7.0
            "space_code": settings.BASE_API_URL,
        }

        # encode
        encoded_token = jwt.encode(decode_token, settings.SECRET_KEY, algorithm="HS256")

        # Create the token instance
        token_instance = PersonalAccessToken.objects.create(
            master_user=master_user,
            member=member,
            owner=member,
            name=name,
            user_code=user_code,
            notes=notes,
            token=encoded_token,
            expires_at=expires_at,
            access_level=access_level,
        )

        return token_instance
