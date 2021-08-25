from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers


class SetAuthTokenSerializer(serializers.Serializer):

    key = serializers.CharField(label=_("Key"))

    user_id = serializers.CharField(label=_("User id"))
    user_legacy_id = serializers.IntegerField(required=False, label=_("User legacy id"))

    current_master_user_id = serializers.CharField(label=_("Current master user id"))
    current_master_user_legacy_id = serializers.IntegerField(required=False, label=_("Current master user legacy id"))


class CreateUserSerializer(serializers.Serializer):
    username = serializers.CharField(label=_("Username"))
    email = serializers.CharField(label=_("Email"), required=False, allow_blank=True)
    user_unique_id = serializers.CharField(label=_("User Unique id"))


class CreateMasterUserSerializer(serializers.Serializer):
    name = serializers.CharField(label=_("name"))
    unique_id = serializers.CharField(label=_("Unique id"))
    user_unique_id = serializers.CharField(label=_("User Unique id"))



class CreateMemberSerializer(serializers.Serializer):
    groups = serializers.CharField(required=False, label=_("Groups"))
    user_id = serializers.CharField(label=_("User Id"))
    user_legacy_id = serializers.IntegerField(required=False, label=_("User legacy id"))
    member_id = serializers.CharField(label=_("Member id"))
    master_user_id = serializers.CharField(label=_("Master User id"))
    master_user_legacy_id = serializers.IntegerField(required=False, label=_("Current master user legacy id"))



class DeleteMemberSerializer(serializers.Serializer):
    user_id = serializers.CharField(label=_("User Id"))
    master_user_id = serializers.CharField(label=_("Master User id"))


