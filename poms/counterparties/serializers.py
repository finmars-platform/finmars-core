from __future__ import unicode_literals

from rest_framework import serializers

from poms.common.serializers import ModelWithUserCodeSerializer, ModelWithTimeStampSerializer
from poms.counterparties.fields import CounterpartyGroupField, ResponsibleGroupField
from poms.counterparties.models import Counterparty, Responsible, CounterpartyGroup, ResponsibleGroup
from poms.obj_attrs.serializers import ModelWithAttributesSerializer
from poms.obj_perms.serializers import ModelWithObjectPermissionSerializer
from poms.portfolios.fields import PortfolioField
from poms.users.fields import MasterUserField


class CounterpartyGroupSerializer(ModelWithObjectPermissionSerializer, ModelWithUserCodeSerializer):
    master_user = MasterUserField()

    class Meta:
        model = CounterpartyGroup
        fields = [
            'id', 'master_user', 'user_code', 'name', 'short_name', 'public_name', 'notes',
            'is_default', 'is_deleted', 'is_enabled'
        ]


class CounterpartyGroupViewSerializer(ModelWithObjectPermissionSerializer):
    class Meta(ModelWithObjectPermissionSerializer.Meta):
        model = CounterpartyGroup
        fields = ['id', 'user_code', 'name', 'short_name', 'public_name', ]


class CounterpartySerializer(ModelWithObjectPermissionSerializer, ModelWithAttributesSerializer,
                             ModelWithUserCodeSerializer, ModelWithTimeStampSerializer):
    master_user = MasterUserField()
    group = CounterpartyGroupField()
    group_object = CounterpartyGroupViewSerializer(source='group', read_only=True)
    portfolios = PortfolioField(many=True, required=False, allow_null=True)
    portfolios_object = serializers.PrimaryKeyRelatedField(source='portfolios', many=True, read_only=True)

    # attributes = CounterpartyAttributeSerializer(many=True, required=False, allow_null=True)

    class Meta:
        model = Counterparty
        fields = [
            'id', 'master_user', 'group', 'group_object', 'user_code', 'name', 'short_name', 'public_name',
            'notes', 'is_default', 'is_valid_for_all_portfolios', 'is_deleted', 'portfolios', 'portfolios_object',
            'is_enabled'
            # 'attributes',
        ]

    def __init__(self, *args, **kwargs):
        super(CounterpartySerializer, self).__init__(*args, **kwargs)

        from poms.portfolios.serializers import PortfolioViewSerializer
        self.fields['portfolios_object'] = PortfolioViewSerializer(source='portfolios', many=True, read_only=True)


class CounterpartyEvSerializer(ModelWithObjectPermissionSerializer, ModelWithAttributesSerializer,
                               ModelWithUserCodeSerializer):
    master_user = MasterUserField()
    group_object = CounterpartyGroupViewSerializer(source='group', read_only=True)

    class Meta:
        model = Counterparty
        fields = [
            'id', 'master_user',
            'user_code', 'name', 'short_name', 'public_name', 'notes',
            'is_default', 'is_deleted', 'is_enabled',
            'group', 'group_object'
        ]


class CounterpartyLightSerializer(ModelWithObjectPermissionSerializer, ModelWithUserCodeSerializer):
    master_user = MasterUserField()

    class Meta:
        model = Counterparty
        fields = [
            'id', 'master_user', 'user_code', 'name', 'short_name', 'public_name',
            'is_default', 'is_deleted', 'is_enabled'
        ]


class CounterpartyViewSerializer(ModelWithObjectPermissionSerializer):
    group = CounterpartyGroupField()
    group_object = CounterpartyGroupViewSerializer(source='group', read_only=True)

    class Meta(ModelWithObjectPermissionSerializer.Meta):
        model = Counterparty
        fields = [
            'id', 'group', 'group_object', 'user_code', 'name', 'short_name', 'public_name',
        ]


class ResponsibleGroupSerializer(ModelWithObjectPermissionSerializer, ModelWithUserCodeSerializer):
    master_user = MasterUserField()

    class Meta:
        model = ResponsibleGroup
        fields = [
            'id', 'master_user', 'user_code', 'name', 'short_name', 'public_name', 'notes', 'is_default',
            'is_deleted', 'is_enabled'
        ]


class ResponsibleGroupViewSerializer(ModelWithObjectPermissionSerializer):
    class Meta(ModelWithObjectPermissionSerializer.Meta):
        model = ResponsibleGroup
        fields = [
            'id', 'user_code', 'name', 'short_name', 'public_name',
        ]


class ResponsibleSerializer(ModelWithObjectPermissionSerializer, ModelWithAttributesSerializer,
                            ModelWithUserCodeSerializer, ModelWithTimeStampSerializer):
    master_user = MasterUserField()
    group = ResponsibleGroupField()
    group_object = ResponsibleGroupViewSerializer(source='group', read_only=True)
    portfolios = PortfolioField(many=True, required=False, allow_null=True)
    portfolios_object = serializers.PrimaryKeyRelatedField(source='portfolios', many=True, read_only=True)

    # attributes = ResponsibleAttributeSerializer(many=True, required=False, allow_null=True)

    class Meta:
        model = Responsible
        fields = [
            'id', 'master_user', 'group', 'group_object', 'user_code', 'name', 'short_name', 'public_name',
            'notes', 'is_default', 'is_valid_for_all_portfolios', 'is_deleted', 'portfolios', 'portfolios_object',
            'is_enabled'
            # 'attributes'
        ]

    def __init__(self, *args, **kwargs):
        super(ResponsibleSerializer, self).__init__(*args, **kwargs)

        from poms.portfolios.serializers import PortfolioViewSerializer
        self.fields['portfolios_object'] = PortfolioViewSerializer(source='portfolios', many=True, read_only=True)


class ResponsibleEvSerializer(ModelWithObjectPermissionSerializer, ModelWithAttributesSerializer,
                              ModelWithUserCodeSerializer):
    master_user = MasterUserField()
    group_object = ResponsibleGroupViewSerializer(source='group', read_only=True)

    class Meta:
        model = Responsible
        fields = [
            'id', 'master_user',
            'user_code', 'name', 'short_name', 'public_name', 'notes',
            'is_default', 'is_deleted', 'is_enabled',
            'group', 'group_object'
        ]


class ResponsibleLightSerializer(ModelWithObjectPermissionSerializer, ModelWithUserCodeSerializer):
    master_user = MasterUserField()

    class Meta:
        model = Responsible
        fields = [
            'id', 'master_user', 'user_code', 'name', 'short_name', 'public_name',
            'is_default', 'is_deleted', 'is_enabled'
        ]


class ResponsibleViewSerializer(ModelWithObjectPermissionSerializer):
    group = ResponsibleGroupField()
    group_object = ResponsibleGroupViewSerializer(source='group', read_only=True)

    class Meta(ModelWithObjectPermissionSerializer.Meta):
        model = Responsible
        fields = [
            'id', 'group', 'group_object', 'user_code', 'name', 'short_name', 'public_name',
        ]
