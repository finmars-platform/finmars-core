from __future__ import unicode_literals

from poms.accounts.fields import AccountTypeField, AccountTypeDefault
from poms.accounts.models import Account, AccountType
from poms.common.fields import ExpressionField
from poms.common.models import EXPRESSION_FIELD_LENGTH
from poms.common.serializers import ModelWithUserCodeSerializer, ModelWithTimeStampSerializer
from poms.obj_attrs.serializers import ModelWithAttributesSerializer
from poms.obj_perms.serializers import ModelWithObjectPermissionSerializer
from poms.portfolios.fields import PortfolioField
from poms.tags.serializers import ModelWithTagSerializer
from poms.users.fields import MasterUserField


class AccountTypeSerializer(ModelWithObjectPermissionSerializer, ModelWithUserCodeSerializer,
                            ModelWithTagSerializer, ModelWithAttributesSerializer, ModelWithTimeStampSerializer):
    master_user = MasterUserField()
    transaction_details_expr = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, allow_blank=True,
                                               allow_null=True, default='""')

    # tags = TagField(many=True, required=False, allow_null=True)
    # # tags_object = ReadonlyNamedModelWithObjectPermissionSerializer(source='tags', many=True)
    # tags_object = TagViewSerializer(source='tags', many=True, read_only=True)

    class Meta(ModelWithObjectPermissionSerializer.Meta):
        model = AccountType
        fields = [
            'id', 'master_user', 'user_code', 'name', 'short_name', 'public_name', 'notes',
            'show_transaction_details', 'transaction_details_expr', 'is_default', 'is_deleted',
            'is_enabled'
            # 'tags', 'tags_object'
        ]


class AccountTypeViewSerializer(ModelWithObjectPermissionSerializer):
    class Meta(ModelWithObjectPermissionSerializer.Meta):
        model = AccountType
        fields = [
            'id', 'user_code', 'name', 'short_name', 'public_name',
        ]


class AccountSerializer(ModelWithObjectPermissionSerializer, ModelWithAttributesSerializer,
                        ModelWithUserCodeSerializer, ModelWithTagSerializer, ModelWithTimeStampSerializer):
    master_user = MasterUserField()
    type = AccountTypeField(default=AccountTypeDefault())
    portfolios = PortfolioField(many=True, required=False, allow_null=True)

    # portfolios_object = serializers.PrimaryKeyRelatedField(source='portfolios', many=True, read_only=True)
    # type_object = AccountTypeViewSerializer(source='type', read_only=True)

    # attributes = AccountAttributeSerializer(many=True, required=False, allow_null=True)

    # tags = TagField(many=True, required=False, allow_null=True)
    # tags_object = TagViewSerializer(source='tags', many=True, read_only=True)

    class Meta(ModelWithObjectPermissionSerializer.Meta):
        model = Account
        fields = [
            'id', 'master_user', 'type', 'user_code', 'name', 'short_name', 'public_name',
            'notes', 'is_default', 'is_valid_for_all_portfolios', 'is_deleted', 'portfolios',
            'is_enabled'
            # 'type_object',  'portfolios_object',
            # 'attributes',
            # 'tags', 'tags_object',
        ]

    def __init__(self, *args, **kwargs):
        super(AccountSerializer, self).__init__(*args, **kwargs)

        from poms.portfolios.serializers import PortfolioViewSerializer
        self.fields['type_object'] = AccountTypeViewSerializer(source='type', read_only=True)
        self.fields['portfolios_object'] = PortfolioViewSerializer(source='portfolios', many=True, read_only=True)


class AccountLightSerializer(ModelWithObjectPermissionSerializer, ModelWithUserCodeSerializer):

    master_user = MasterUserField()

    class Meta(ModelWithObjectPermissionSerializer.Meta):
        model = Account
        fields = [
            'id', 'master_user', 'user_code', 'name', 'short_name', 'public_name',
            'is_default', 'is_deleted',
            'is_enabled'
        ]


class AccountViewSerializer(ModelWithObjectPermissionSerializer):
    type = AccountTypeField(default=AccountTypeDefault())
    type_object = AccountTypeViewSerializer(source='type', read_only=True)

    class Meta(ModelWithObjectPermissionSerializer.Meta):
        model = Account
        fields = [
            'id', 'type', 'type_object', 'user_code', 'name', 'short_name', 'public_name',
        ]
