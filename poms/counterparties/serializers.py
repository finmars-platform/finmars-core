from rest_framework import serializers

from poms.common.serializers import (
    ModelWithTimeStampSerializer,
    ModelWithUserCodeSerializer,
    ModelWithObjectStateSerializer,
)
from poms.counterparties.fields import CounterpartyGroupField, ResponsibleGroupField
from poms.counterparties.models import (
    Counterparty,
    CounterpartyGroup,
    Responsible,
    ResponsibleGroup,
)
from poms.iam.serializers import ModelWithResourceGroupSerializer
from poms.obj_attrs.serializers import ModelWithAttributesSerializer
from poms.portfolios.fields import PortfolioField
from poms.users.fields import MasterUserField


class CounterpartyGroupSerializer(ModelWithUserCodeSerializer):
    master_user = MasterUserField()

    class Meta:
        model = CounterpartyGroup
        fields = [
            "id",
            "master_user",
            "user_code",
            "name",
            "short_name",
            "public_name",
            "notes",
            "is_default",
            "is_deleted",
            "is_enabled",
        ]


class CounterpartyGroupViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = CounterpartyGroup
        fields = [
            "id",
            "user_code",
            "name",
            "short_name",
            "public_name",
        ]


class CounterpartySerializer(
    ModelWithAttributesSerializer,
    ModelWithUserCodeSerializer,
    ModelWithTimeStampSerializer,
    ModelWithObjectStateSerializer,
):
    master_user = MasterUserField()
    group = CounterpartyGroupField()
    group_object = CounterpartyGroupViewSerializer(source="group", read_only=True)
    portfolios = PortfolioField(many=True, required=False, allow_null=True)
    portfolios_object = serializers.PrimaryKeyRelatedField(
        source="portfolios", many=True, read_only=True
    )

    class Meta:
        model = Counterparty
        fields = [
            "id",
            "master_user",
            "group",
            "group_object",
            "user_code",
            "name",
            "short_name",
            "public_name",
            "notes",
            "is_default",
            "is_valid_for_all_portfolios",
            "is_deleted",
            "portfolios",
            "portfolios_object",
            "is_enabled"
        ]

    def __init__(self, *args, **kwargs):
        from poms.portfolios.serializers import PortfolioViewSerializer

        super().__init__(*args, **kwargs)
        self.fields["portfolios_object"] = PortfolioViewSerializer(
            source="portfolios",
            many=True,
            read_only=True,
        )


class CounterpartyLightSerializer(ModelWithUserCodeSerializer):
    master_user = MasterUserField()

    class Meta:
        model = Counterparty
        fields = [
            "id",
            "master_user",
            "user_code",
            "name",
            "short_name",
            "public_name",
            "is_default",
            "is_deleted",
            "is_enabled",
        ]


class CounterpartyViewSerializer(ModelWithUserCodeSerializer):
    group = CounterpartyGroupField()
    group_object = CounterpartyGroupViewSerializer(source="group", read_only=True)

    class Meta:
        model = Counterparty
        fields = [
            "id",
            "group",
            "group_object",
            "user_code",
            "name",
            "short_name",
            "public_name",
        ]


class ResponsibleGroupSerializer(ModelWithUserCodeSerializer):
    master_user = MasterUserField()

    class Meta:
        model = ResponsibleGroup
        fields = [
            "id",
            "master_user",
            "user_code",
            "name",
            "short_name",
            "public_name",
            "notes",
            "is_default",
            "is_deleted",
            "is_enabled",
        ]


class ResponsibleGroupViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResponsibleGroup
        fields = [
            "id",
            "user_code",
            "name",
            "short_name",
            "public_name",
        ]


class ResponsibleSerializer(
    ModelWithResourceGroupSerializer,
    ModelWithAttributesSerializer,
    ModelWithUserCodeSerializer,
    ModelWithTimeStampSerializer,
    ModelWithObjectStateSerializer,
):
    master_user = MasterUserField()
    group = ResponsibleGroupField()
    group_object = ResponsibleGroupViewSerializer(source="group", read_only=True)
    portfolios = PortfolioField(many=True, required=False, allow_null=True)
    portfolios_object = serializers.PrimaryKeyRelatedField(
        source="portfolios",
        many=True,
        read_only=True,
    )

    class Meta:
        model = Responsible
        fields = [
            "id",
            "master_user",
            "group",
            "group_object",
            "user_code",
            "name",
            "short_name",
            "public_name",
            "notes",
            "is_default",
            "is_valid_for_all_portfolios",
            "is_deleted",
            "portfolios",
            "portfolios_object",
            "is_enabled",
        ]

    def __init__(self, *args, **kwargs):
        from poms.portfolios.serializers import PortfolioViewSerializer

        super().__init__(*args, **kwargs)
        self.fields["portfolios_object"] = PortfolioViewSerializer(
            source="portfolios",
            many=True,
            read_only=True,
        )


class ResponsibleLightSerializer(ModelWithUserCodeSerializer):
    master_user = MasterUserField()

    class Meta:
        model = Responsible
        fields = [
            "id",
            "master_user",
            "user_code",
            "name",
            "short_name",
            "public_name",
            "is_default",
            "is_deleted",
            "is_enabled",
        ]


class ResponsibleViewSerializer(serializers.ModelSerializer):
    group = ResponsibleGroupField()
    group_object = ResponsibleGroupViewSerializer(source="group", read_only=True)

    class Meta:
        model = Responsible
        fields = [
            "id",
            "group",
            "group_object",
            "user_code",
            "name",
            "short_name",
            "public_name",
        ]


class CounterpartyEvalSerializer(
    ModelWithUserCodeSerializer, ModelWithTimeStampSerializer
):
    master_user = MasterUserField()
    group = CounterpartyGroupField()

    class Meta:
        model = Counterparty
        fields = [
            "id",
            "master_user",
            "group",
            "user_code",
            "name",
            "short_name",
            "public_name",
            "notes",
            "is_default",
            "is_valid_for_all_portfolios",
            "is_deleted",
            "is_enabled",
        ]
        read_only_fields = fields


class ResponsibleEvalSerializer(
    ModelWithUserCodeSerializer, ModelWithTimeStampSerializer
):
    master_user = MasterUserField()
    group = ResponsibleGroupField()

    class Meta:
        model = Responsible
        fields = [
            "id",
            "master_user",
            "group",
            "user_code",
            "name",
            "short_name",
            "public_name",
            "notes",
            "is_default",
            "is_valid_for_all_portfolios",
            "is_deleted",
            "is_enabled"
        ]

        read_only_fields = fields
