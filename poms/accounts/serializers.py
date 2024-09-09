from poms.accounts.fields import AccountTypeField
from poms.accounts.models import Account, AccountType
from poms.common.fields import ExpressionField
from poms.common.models import EXPRESSION_FIELD_LENGTH
from poms.common.serializers import (
    ModelMetaSerializer,
    ModelWithTimeStampSerializer,
    ModelWithUserCodeSerializer,
    ModelWithObjectStateSerializer,
)
from poms.obj_attrs.serializers import ModelWithAttributesSerializer
from poms.portfolios.fields import PortfolioField
from poms.users.fields import MasterUserField


class AccountTypeSerializer(
    ModelWithUserCodeSerializer,
    ModelWithAttributesSerializer,
    ModelWithTimeStampSerializer,
    ModelMetaSerializer,
):
    master_user = MasterUserField()
    transaction_details_expr = ExpressionField(
        max_length=EXPRESSION_FIELD_LENGTH,
        required=False,
        allow_blank=True,
        allow_null=True,
        default='""',
    )

    class Meta:
        model = AccountType
        fields = [
            "id",
            "master_user",
            "user_code",
            "configuration_code",
            "name",
            "short_name",
            "public_name",
            "notes",
            "show_transaction_details",
            "transaction_details_expr",
            "is_deleted",
            "is_enabled",
        ]


class AccountTypeViewSerializer(ModelWithUserCodeSerializer):
    class Meta:
        model = AccountType
        fields = [
            "id",
            "user_code",
            "name",
            "short_name",
            "public_name",
        ]


class AccountSerializer(
    ModelWithAttributesSerializer,
    ModelWithUserCodeSerializer,
    ModelWithTimeStampSerializer,
    ModelMetaSerializer,
    ModelWithObjectStateSerializer,
):
    master_user = MasterUserField()
    type = AccountTypeField()
    portfolios = PortfolioField(many=True, required=False, allow_null=True)

    class Meta:
        model = Account
        fields = [
            "id",
            "master_user",
            "type",
            "user_code",
            "name",
            "short_name",
            "public_name",
            "notes",
            "is_valid_for_all_portfolios",
            "is_deleted",
            "portfolios",
            "is_enabled",
        ]

    def __init__(self, *args, **kwargs):
        super(AccountSerializer, self).__init__(*args, **kwargs)

        from poms.portfolios.serializers import PortfolioViewSerializer

        self.fields["type_object"] = AccountTypeViewSerializer(
            source="type", read_only=True
        )
        self.fields["portfolios_object"] = PortfolioViewSerializer(
            source="portfolios", many=True, read_only=True
        )


class AccountLightSerializer(ModelWithUserCodeSerializer):
    master_user = MasterUserField()

    class Meta:
        model = Account
        fields = [
            "id",
            "master_user",
            "user_code",
            "name",
            "short_name",
            "public_name",
            "is_deleted",
            "is_enabled",
        ]


class AccountViewSerializer(ModelWithUserCodeSerializer):
    type = AccountTypeField()
    type_object = AccountTypeViewSerializer(source="type", read_only=True)

    class Meta:
        model = Account
        fields = [
            "id",
            "type",
            "type_object",
            "user_code",
            "name",
            "short_name",
            "public_name",
        ]


class AccountTypeEvalSerializer(ModelWithUserCodeSerializer):

    class Meta:
        model = AccountType
        fields = [
            "id",
            "user_code",
            "name",
            "short_name",
            "public_name",
        ]

        read_only_fields = fields


class AccountEvalSerializer(ModelWithUserCodeSerializer):
    type = AccountTypeField()

    class Meta:
        model = Account
        fields = [
            "id",
            "type",
            "user_code",
            "name",
            "short_name",
            "public_name",
        ]

        read_only_fields = fields
