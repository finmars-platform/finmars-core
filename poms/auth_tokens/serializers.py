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
    email = serializers.CharField(label=_("Email"))
    user_unique_id = serializers.CharField(label=_("User Unique id"))


class CreateMasterUserSerializer(serializers.Serializer):
    name = serializers.CharField(label=_("name"))
    description = serializers.CharField(label=_("description"), default='')
    unique_id = serializers.CharField(label=_("Unique id"))
    user_unique_id = serializers.CharField(label=_("User Unique id"))
