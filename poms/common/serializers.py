from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers
from rest_framework.serializers import ListSerializer

from mptt.utils import get_cached_trees

from poms.common.fields import PrimaryKeyRelatedFilteredField, UserCodeField
from poms.common.filters import ClassifierRootFilter
from poms.iam.serializers import IamProtectedSerializer
from poms.system_messages.handlers import send_system_message
from poms.users.filters import OwnerByMasterUserFilter
from poms.users.utils import get_master_user_from_context, get_member_from_context, get_space_code_from_context, \
    get_realm_code_from_context
from poms_app import settings


class BulkSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.IntegerField())

class PomsClassSerializer(serializers.ModelSerializer):
    class Meta:
        fields = [
            "id",
            "user_code",
            "name",
            "description",
        ]


class ModelOwnerSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        from poms.users.serializers import MemberLightViewSerializer

        representation = super().to_representation(instance)

        serializer = MemberLightViewSerializer(instance=instance.owner)

        representation["owner"] = serializer.data

        return representation

    def create(self, validated_data):
        # You should have 'request' in the serializer context !!!
        request = self.context.get("request", None)
        if request and hasattr(request, "user"):
            validated_data["owner"] = request.user.member

        return super().create(validated_data)


class ModelMetaSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        representation = super().to_representation(instance)

        representation["meta"] = {
            "content_type": f"{self.Meta.model._meta.app_label}.{self.Meta.model._meta.model_name}",
            "app_label": self.Meta.model._meta.app_label,
            "model_name": self.Meta.model._meta.model_name,
            "space_code": get_space_code_from_context(self.context),
            "realm_code": get_realm_code_from_context(self.context),
        }

        return representation


class ModelWithTimeStampSerializer(serializers.ModelSerializer):
    modified = serializers.ReadOnlyField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def validate(self, data):
        if (
            self.instance
            and "modified" in data
            and data["modified"] != self.instance.modified
        ):
            raise serializers.ValidationError("Synchronization error")

        return data


class ModelWithUserCodeSerializer(
    ModelMetaSerializer, ModelOwnerSerializer, IamProtectedSerializer
):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["user_code"] = UserCodeField()
        self.fields["deleted_user_code"] = UserCodeField(read_only=True)

    def to_internal_value(self, data):
        return super().to_internal_value(data)

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
            description=f"New {entity_name} created (manual) - {instance.name}",
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
            description=f"{entity_name} edited (manual) - {instance.name}",
        )

        return instance


class AbstractClassifierField(PrimaryKeyRelatedFilteredField):
    filter_backends = [OwnerByMasterUserFilter]


class AbstractClassifierRootField(PrimaryKeyRelatedFilteredField):
    filter_backends = [OwnerByMasterUserFilter, ClassifierRootFilter]


class ClassifierRecursiveField(serializers.Serializer):
    def to_representation(self, instance):
        if isinstance(self.parent, ListSerializer):
            cls = self.parent.parent.__class__
        else:
            cls = self.parent.__class__
        return cls(instance=instance, context=self.context).data

    def to_internal_value(self, data):
        if isinstance(self.parent, ListSerializer):
            cls = self.parent.parent.__class__
        else:
            cls = self.parent.__class__
        s = cls(context=self.context, data=data)
        s.is_valid(raise_exception=True)
        return s.validated_data


class ClassifierListSerializer(serializers.ListSerializer):
    def get_attribute(self, instance):
        return get_cached_trees(instance.classifiers.all())


class ContentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentType
        fields = [
            "name",
        ]
        read_only_fields = fields
