import json

from django.utils.encoding import force_str
from rest_framework import serializers

from poms.common.fields import DateTimeTzAwareField
from poms.notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    create_date = DateTimeTzAwareField()
    read_date = DateTimeTzAwareField()
    message = serializers.SerializerMethodField()
    actor = serializers.SerializerMethodField()
    actor_type = serializers.SerializerMethodField()
    actor_repr = serializers.SerializerMethodField()
    action_object = serializers.SerializerMethodField()
    action_object_type = serializers.SerializerMethodField()
    action_object_repr = serializers.SerializerMethodField()
    target = serializers.SerializerMethodField()
    target_type = serializers.SerializerMethodField()
    target_repr = serializers.SerializerMethodField()
    data = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            "id",
            "create_date",
            "read_date",
            "timesince",
            "message",
            "actor",
            "actor_type",
            "actor_repr",
            "verb",
            "action_object",
            "action_object_type",
            "action_object_repr",
            "target",
            "target_type",
            "target_repr",
            "data",
        ]

    def get_message(self, value):
        return force_str(value)

    def get_actor(self, value):
        if value.actor_object_id:
            return int(value.actor_object_id)
        return None

    def get_actor_type(self, value):
        if value.actor_content_type:
            return "%s.%s" % (value.actor_content_type.app_label, value.actor_content_type.model)
        return None

    def get_actor_repr(self, value):
        if value.actor_object_id:
            return "%s" % value.actor
        return None

    def get_action_object(self, value):
        if value.action_object_object_id:
            return int(value.action_object_object_id)
        return None

    def get_action_object_type(self, value):
        if value.action_object_content_type_id:
            return "%s.%s" % (
                value.action_object_content_type.app_label,
                value.action_object_content_type.model,
            )
        return None

    def get_action_object_repr(self, value):
        if value.action_object_object_id:
            return "%s" % value.action_object
        return None

    def get_target(self, value):
        if value.target_object_id:
            return int(value.target_object_id)
        return None

    def get_target_type(self, value):
        if value.target_content_type_id:
            return "%s.%s" % (value.target_content_type.app_label, value.target_content_type.model)
        return None

    def get_target_repr(self, value):
        if value.target_object_id:
            return "%s" % value.target
        return None

    def get_data(self, value):
        if value.data:
            return json.loads(value.data)
        return None
