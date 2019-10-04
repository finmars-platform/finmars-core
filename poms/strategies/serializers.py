from __future__ import unicode_literals

from poms.common.serializers import ModelWithUserCodeSerializer
from poms.obj_attrs.serializers import ModelWithAttributesSerializer
from poms.obj_perms.serializers import ModelWithObjectPermissionSerializer
from poms.strategies.fields import Strategy1GroupField, Strategy1SubgroupField, Strategy2GroupField, \
    Strategy2SubgroupField, Strategy3GroupField, Strategy3SubgroupField, Strategy1GroupDefault, Strategy1SubgroupDefault, \
    Strategy2GroupDefault, Strategy2SubgroupDefault, Strategy3GroupDefault, Strategy3SubgroupDefault
from poms.strategies.models import Strategy1Group, Strategy1Subgroup, Strategy1, Strategy2Group, Strategy2Subgroup, \
    Strategy2, Strategy3Group, Strategy3Subgroup, Strategy3
from poms.tags.serializers import ModelWithTagSerializer
from poms.users.fields import MasterUserField


class Strategy1GroupSerializer(ModelWithObjectPermissionSerializer, ModelWithUserCodeSerializer,
                               ModelWithTagSerializer):
    master_user = MasterUserField()

    # tags = TagField(many=True, required=False, allow_null=True)
    # tags_object = TagViewSerializer(source='tags', many=True, read_only=True)

    class Meta:
        model = Strategy1Group
        fields = [
            'id', 'master_user', 'user_code', 'name', 'short_name', 'public_name', 'notes', 'is_deleted',
            'is_enabled'
            # 'tags', 'tags_object'
        ]


class Strategy1GroupViewSerializer(ModelWithObjectPermissionSerializer):
    class Meta(ModelWithObjectPermissionSerializer.Meta):
        model = Strategy1Group
        fields = [
            'id', 'user_code', 'name', 'short_name', 'public_name', 'notes', 'is_deleted',
        ]


class Strategy1SubgroupSerializer(ModelWithObjectPermissionSerializer, ModelWithUserCodeSerializer,
                                  ModelWithTagSerializer):
    master_user = MasterUserField()
    group = Strategy1GroupField(default=Strategy1GroupDefault())
    group_object = Strategy1GroupViewSerializer(source='group', read_only=True)

    # tags = TagField(many=True, required=False, allow_null=True)
    # tags_object = TagViewSerializer(source='tags', many=True, read_only=True)

    class Meta:
        model = Strategy1Subgroup
        fields = [
            'id', 'master_user', 'group', 'user_code', 'name', 'short_name', 'public_name', 'is_deleted', 'notes',
            'group_object', 'is_enabled'
            # 'tags', 'tags_object',
        ]


class Strategy1SubgroupViewSerializer(ModelWithObjectPermissionSerializer):
    group_object = Strategy1GroupViewSerializer(source='group', read_only=True)

    class Meta(ModelWithObjectPermissionSerializer.Meta):
        model = Strategy1Subgroup
        fields = [
            'id', 'group', 'user_code', 'name', 'short_name', 'public_name', 'is_deleted', 'notes',
            'group_object', 'is_enabled'
        ]


class Strategy1Serializer(ModelWithObjectPermissionSerializer, ModelWithUserCodeSerializer, ModelWithTagSerializer, ModelWithAttributesSerializer):
    master_user = MasterUserField()
    subgroup = Strategy1SubgroupField(default=Strategy1SubgroupDefault())
    subgroup_object = Strategy1SubgroupViewSerializer(source='subgroup', read_only=True)

    # tags = TagField(many=True, required=False, allow_null=True)
    # tags_object = TagViewSerializer(source='tags', many=True, read_only=True)

    class Meta:
        model = Strategy1
        fields = [
            'id', 'master_user', 'subgroup', 'user_code', 'name', 'short_name', 'public_name', 'notes', 'is_deleted',
            'subgroup_object', 'is_enabled'
            # 'tags', 'tags_object'
        ]


class Strategy1ViewSerializer(ModelWithObjectPermissionSerializer):
    subgroup_object = Strategy1SubgroupViewSerializer(source='subgroup', read_only=True)

    class Meta(ModelWithObjectPermissionSerializer.Meta):
        model = Strategy1
        fields = [
            'id', 'subgroup', 'user_code', 'name', 'short_name', 'public_name', 'notes', 'is_deleted',
            'subgroup_object',
        ]


# 2 --------------------------------------------------------------------------------------------------------------------

class Strategy2GroupSerializer(Strategy1GroupSerializer):
    class Meta(Strategy1GroupSerializer.Meta):
        model = Strategy2Group


class Strategy2GroupViewSerializer(Strategy1GroupViewSerializer):
    class Meta(Strategy1GroupViewSerializer.Meta):
        model = Strategy2Group


class Strategy2SubgroupSerializer(Strategy1SubgroupSerializer):
    group = Strategy2GroupField(default=Strategy2GroupDefault())
    group_object = Strategy2GroupViewSerializer(source='group', read_only=True)

    class Meta(Strategy1SubgroupSerializer.Meta):
        model = Strategy2Subgroup


class Strategy2SubgroupViewSerializer(Strategy1SubgroupViewSerializer):
    # group = Strategy2GroupField()
    group_object = Strategy2GroupViewSerializer(source='group', read_only=True)

    class Meta(Strategy1SubgroupViewSerializer.Meta):
        model = Strategy2Subgroup


class Strategy2Serializer(Strategy1Serializer):
    subgroup = Strategy2SubgroupField(default=Strategy2SubgroupDefault())
    subgroup_object = Strategy2SubgroupViewSerializer(source='subgroup', read_only=True)

    class Meta(Strategy1Serializer.Meta):
        model = Strategy2


class Strategy2ViewSerializer(Strategy1ViewSerializer, ModelWithAttributesSerializer):
    subgroup_object = Strategy2SubgroupViewSerializer(source='subgroup', read_only=True)

    class Meta(Strategy1ViewSerializer.Meta):
        model = Strategy2


# 3 --------------------------------------------------------------------------------------------------------------------


class Strategy3GroupSerializer(Strategy1GroupSerializer):
    class Meta(Strategy1GroupSerializer.Meta):
        model = Strategy3Group


class Strategy3GroupViewSerializer(Strategy1GroupViewSerializer):
    class Meta(Strategy1GroupViewSerializer.Meta):
        model = Strategy3Group


class Strategy3SubgroupSerializer(Strategy1SubgroupSerializer):
    group = Strategy3GroupField(default=Strategy3GroupDefault())
    group_object = Strategy3GroupViewSerializer(source='group', read_only=True)

    class Meta(Strategy1SubgroupSerializer.Meta):
        model = Strategy3Subgroup


class Strategy3SubgroupViewSerializer(Strategy1SubgroupViewSerializer):
    # group = Strategy3GroupField()
    group_object = Strategy3GroupViewSerializer(source='group', read_only=True)

    class Meta(Strategy1SubgroupViewSerializer.Meta):
        model = Strategy3Subgroup


class Strategy3Serializer(Strategy1Serializer, ModelWithAttributesSerializer):
    subgroup = Strategy3SubgroupField(default=Strategy3SubgroupDefault())
    subgroup_object = Strategy3SubgroupViewSerializer(source='subgroup', read_only=True)

    class Meta(Strategy1Serializer.Meta):
        model = Strategy3


class Strategy3ViewSerializer(Strategy1ViewSerializer):
    subgroup_object = Strategy3SubgroupViewSerializer(source='subgroup', read_only=True)

    class Meta(Strategy1ViewSerializer.Meta):
        model = Strategy3
