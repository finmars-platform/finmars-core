from __future__ import unicode_literals

from rest_framework import serializers

from poms.common.serializers import ModelWithUserCodeSerializer
from poms.counterparties.fields import CounterpartyGroupField, ResponsibleGroupField
from poms.counterparties.models import Counterparty, Responsible, CounterpartyGroup, ResponsibleGroup
from poms.obj_attrs.serializers import ModelWithAttributesSerializer
from poms.obj_perms.serializers import ModelWithObjectPermissionSerializer
from poms.portfolios.fields import PortfolioField
from poms.tags.serializers import ModelWithTagSerializer
from poms.users.fields import MasterUserField


# class CounterpartyClassifierSerializer(AbstractClassifierSerializer):
#     class Meta(AbstractClassifierSerializer.Meta):
#         model = CounterpartyClassifier
#
#
# class CounterpartyClassifierNodeSerializer(AbstractClassifierNodeSerializer):
#     class Meta(AbstractClassifierNodeSerializer.Meta):
#         model = CounterpartyClassifier
#
#
# class CounterpartyAttributeTypeSerializer(AbstractAttributeTypeSerializer):
#     classifiers = CounterpartyClassifierSerializer(required=False, allow_null=True, many=True)
#
#     class Meta(AbstractAttributeTypeSerializer.Meta):
#         model = CounterpartyAttributeType
#         fields = AbstractAttributeTypeSerializer.Meta.fields + ['classifiers']
#
#
# class CounterpartyAttributeSerializer(AbstractAttributeSerializer):
#     attribute_type = CounterpartyAttributeTypeField()
#     classifier = CounterpartyClassifierField(required=False, allow_null=True)
#
#     class Meta(AbstractAttributeSerializer.Meta):
#         model = CounterpartyAttribute
#         fields = AbstractAttributeSerializer.Meta.fields + ['attribute_type', 'classifier']


class CounterpartyGroupSerializer(ModelWithObjectPermissionSerializer, ModelWithUserCodeSerializer,
                                  ModelWithTagSerializer):
    master_user = MasterUserField()

    # tags = TagField(many=True, required=False, allow_null=True)
    # tags_object = TagViewSerializer(source='tags', many=True, read_only=True)

    class Meta:
        model = CounterpartyGroup
        fields = [
            'id', 'master_user', 'user_code', 'name', 'short_name', 'public_name', 'notes',
            'is_default', 'is_deleted', 'is_enabled'
            # 'tags', 'tags_object',
        ]


class CounterpartyGroupViewSerializer(ModelWithObjectPermissionSerializer):
    class Meta(ModelWithObjectPermissionSerializer.Meta):
        model = CounterpartyGroup
        fields = ['id', 'user_code', 'name', 'short_name', 'public_name', ]


class CounterpartySerializer(ModelWithObjectPermissionSerializer, ModelWithAttributesSerializer,
                             ModelWithUserCodeSerializer, ModelWithTagSerializer):
    master_user = MasterUserField()
    group = CounterpartyGroupField()
    group_object = CounterpartyGroupViewSerializer(source='group', read_only=True)
    portfolios = PortfolioField(many=True, required=False, allow_null=True)
    portfolios_object = serializers.PrimaryKeyRelatedField(source='portfolios', many=True, read_only=True)

    # attributes = CounterpartyAttributeSerializer(many=True, required=False, allow_null=True)

    # tags = TagField(many=True, required=False, allow_null=True)
    # tags_object = TagViewSerializer(source='tags', many=True, read_only=True)

    class Meta:
        model = Counterparty
        fields = [
            'id', 'master_user', 'group', 'group_object', 'user_code', 'name', 'short_name', 'public_name',
            'notes', 'is_default', 'is_valid_for_all_portfolios', 'is_deleted', 'portfolios', 'portfolios_object',
            'is_enabled'
            # 'attributes',
            # 'tags', 'tags_object'
        ]

    def __init__(self, *args, **kwargs):
        super(CounterpartySerializer, self).__init__(*args, **kwargs)

        from poms.portfolios.serializers import PortfolioViewSerializer
        self.fields['portfolios_object'] = PortfolioViewSerializer(source='portfolios', many=True, read_only=True)


class CounterpartyViewSerializer(ModelWithObjectPermissionSerializer):
    group = CounterpartyGroupField()
    group_object = CounterpartyGroupViewSerializer(source='group', read_only=True)

    class Meta(ModelWithObjectPermissionSerializer.Meta):
        model = Counterparty
        fields = [
            'id', 'group', 'group_object', 'user_code', 'name', 'short_name', 'public_name',
        ]


# ----

# class ResponsibleClassifierSerializer(AbstractClassifierSerializer):
#     class Meta(AbstractClassifierSerializer.Meta):
#         model = ResponsibleClassifier
#
#
# class ResponsibleClassifierNodeSerializer(AbstractClassifierNodeSerializer):
#     class Meta(AbstractClassifierNodeSerializer.Meta):
#         model = ResponsibleClassifier
#
#
# class ResponsibleAttributeTypeSerializer(AbstractAttributeTypeSerializer):
#     classifiers = ResponsibleClassifierSerializer(required=False, allow_null=True, many=True)
#
#     class Meta(AbstractAttributeTypeSerializer.Meta):
#         model = ResponsibleAttributeType
#         fields = AbstractAttributeTypeSerializer.Meta.fields + ['classifiers']


# class ResponsibleAttributeTypeBulkObjectPermissionSerializer(AbstractBulkObjectPermissionSerializer):
#     content_objects = ResponsibleAttributeTypeField(many=True, allow_null=False, allow_empty=False)
#
#     class Meta:
#         model = ResponsibleAttributeType

#
# class ResponsibleAttributeSerializer(AbstractAttributeSerializer):
#     attribute_type = ResponsibleAttributeTypeField()
#     classifier = ResponsibleClassifierField(required=False, allow_null=True)
#
#     class Meta(AbstractAttributeSerializer.Meta):
#         model = ResponsibleAttribute
#         fields = AbstractAttributeSerializer.Meta.fields + ['attribute_type', 'classifier']


class ResponsibleGroupSerializer(ModelWithObjectPermissionSerializer, ModelWithUserCodeSerializer,
                                 ModelWithTagSerializer):
    master_user = MasterUserField()

    # tags = TagField(many=True, required=False, allow_null=True)
    # tags_object = TagViewSerializer(source='tags', many=True, read_only=True)

    class Meta:
        model = ResponsibleGroup
        fields = [
            'id', 'master_user', 'user_code', 'name', 'short_name', 'public_name', 'notes', 'is_default',
            'is_deleted', 'is_enabled'
            # 'tags', 'tags_object',
        ]


class ResponsibleGroupViewSerializer(ModelWithObjectPermissionSerializer):
    class Meta(ModelWithObjectPermissionSerializer.Meta):
        model = ResponsibleGroup
        fields = [
            'id', 'user_code', 'name', 'short_name', 'public_name',
        ]


class ResponsibleSerializer(ModelWithObjectPermissionSerializer, ModelWithAttributesSerializer,
                            ModelWithUserCodeSerializer, ModelWithTagSerializer):
    master_user = MasterUserField()
    group = ResponsibleGroupField()
    group_object = ResponsibleGroupViewSerializer(source='group', read_only=True)
    portfolios = PortfolioField(many=True, required=False, allow_null=True)
    portfolios_object = serializers.PrimaryKeyRelatedField(source='portfolios', many=True, read_only=True)

    # attributes = ResponsibleAttributeSerializer(many=True, required=False, allow_null=True)

    # tags = TagField(many=True, required=False, allow_null=True)
    # tags_object = TagViewSerializer(source='tags', many=True, read_only=True)

    class Meta:
        model = Responsible
        fields = [
            'id', 'master_user', 'group', 'group_object', 'user_code', 'name', 'short_name', 'public_name',
            'notes', 'is_default', 'is_valid_for_all_portfolios', 'is_deleted', 'portfolios', 'portfolios_object',
            'is_enabled'
            # 'attributes',
            # 'tags', 'tags_object',
        ]

    def __init__(self, *args, **kwargs):
        super(ResponsibleSerializer, self).__init__(*args, **kwargs)

        from poms.portfolios.serializers import PortfolioViewSerializer
        self.fields['portfolios_object'] = PortfolioViewSerializer(source='portfolios', many=True, read_only=True)


class ResponsibleViewSerializer(ModelWithObjectPermissionSerializer):
    group = ResponsibleGroupField()
    group_object = ResponsibleGroupViewSerializer(source='group', read_only=True)

    class Meta(ModelWithObjectPermissionSerializer.Meta):
        model = Responsible
        fields = [
            'id', 'group', 'group_object', 'user_code', 'name', 'short_name', 'public_name',
        ]
