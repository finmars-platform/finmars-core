from logging import getLogger

from rest_framework import serializers

from poms.common.serializers import (
    ModelWithUserCodeSerializer,
    ModelWithTimeStampSerializer,
)
from poms.instruments.handlers import InstrumentTypeProcess
from poms.instruments.models import InstrumentType, Instrument
from poms.instruments.serializers import (
    InstrumentViewSerializer,
    PricingPolicySerializer,
    InstrumentSerializer,
)
from poms.obj_attrs.serializers import ModelWithAttributesSerializer
from poms.portfolios.models import (
    Portfolio,
    PortfolioRegister,
    PortfolioRegisterRecord,
    PortfolioBundle,
)
from poms.portfolios.utils import get_price_calculation_type
from poms.users.fields import MasterUserField
from poms.users.models import EcosystemDefault

_l = getLogger("poms.portfolios")


class PortfolioPortfolioRegisterSerializer(
    ModelWithAttributesSerializer,
    ModelWithUserCodeSerializer,
    ModelWithTimeStampSerializer,
):
    master_user = MasterUserField()

    valuation_currency_object = serializers.PrimaryKeyRelatedField(
        source="valuation_currency", read_only=True
    )
    linked_instrument_object = serializers.PrimaryKeyRelatedField(
        source="linked_instrument", read_only=True
    )
    valuation_pricing_policy_object = serializers.PrimaryKeyRelatedField(
        source="valuation_pricing_policy", read_only=True
    )

    class Meta:
        model = PortfolioRegister
        fields = [
            "id",
            "master_user",
            "user_code",
            "name",
            "short_name",
            "public_name",
            "notes",
            "is_deleted",
            "is_enabled",
            "linked_instrument",
            "linked_instrument_object",
            "valuation_currency",
            "valuation_currency_object",
            "valuation_pricing_policy",
            "valuation_pricing_policy_object",
            "default_price",
        ]

    def __init__(self, *args, **kwargs):
        super(PortfolioPortfolioRegisterSerializer, self).__init__(*args, **kwargs)

        from poms.currencies.serializers import CurrencyViewSerializer

        self.fields["valuation_currency_object"] = CurrencyViewSerializer(
            source="valuation_currency", read_only=True
        )

        self.fields["linked_instrument_object"] = InstrumentViewSerializer(
            source="linked_instrument", read_only=True
        )
        self.fields["valuation_pricing_policy_object"] = PricingPolicySerializer(
            source="valuation_pricing_policy", read_only=True
        )


class PortfolioSerializer(
    ModelWithAttributesSerializer,
    ModelWithUserCodeSerializer,
    ModelWithTimeStampSerializer,
):
    master_user = MasterUserField()
    # accounts = AccountField(many=True, allow_null=True, required=False)
    # responsibles = ResponsibleField(many=True, allow_null=True, required=False)
    # counterparties = CounterpartyField(many=True, allow_null=True, required=False)
    # transaction_types = TransactionTypeField(many=True, allow_null=True, required=False)

    registers = PortfolioPortfolioRegisterSerializer(
        many=True, allow_null=True, required=False, read_only=True
    )

    class Meta:
        model = Portfolio
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
            # 'accounts', 'responsibles', 'counterparties', 'transaction_types',
            "is_enabled",
            "registers",
        ]

    def __init__(self, *args, **kwargs):
        super(PortfolioSerializer, self).__init__(*args, **kwargs)

        from poms.accounts.serializers import AccountViewSerializer
        from poms.counterparties.serializers import (
            ResponsibleViewSerializer,
            CounterpartyViewSerializer,
        )
        from poms.transactions.serializers import TransactionTypeViewSerializer

        self.fields["accounts_object"] = AccountViewSerializer(
            source="accounts", many=True, read_only=True
        )
        self.fields["responsibles_object"] = ResponsibleViewSerializer(
            source="responsibles", many=True, read_only=True
        )
        self.fields["counterparties_object"] = CounterpartyViewSerializer(
            source="counterparties", many=True, read_only=True
        )
        self.fields["transaction_types_object"] = TransactionTypeViewSerializer(
            source="transaction_types", many=True, read_only=True
        )

    def create_register_if_not_exists(self, instance):
        master_user = instance.master_user

        try:
            portfolio_register = PortfolioRegister.objects.get(
                master_user=master_user,
                portfolio=instance,
                user_code=instance.user_code,
            )

        except Exception as e:
            ecosystem_default = EcosystemDefault.objects.get(master_user=master_user)

            new_instrument = None

            # TODO maybe create new instr instead of existing?
            try:
                new_instrument = Instrument.objects.get(
                    master_user=master_user, user_code=instance.user_code
                )
            except Exception as e:
                new_linked_instrument = {
                    "name": instance.name,
                    "user_code": instance.user_code,
                    "short_name": instance.short_name,
                    "public_name": instance.public_name,
                    "instrument_type": "com.finmars.initial-instrument-type:portfolio",
                }

                try:
                    instrument_type = InstrumentType.objects.get(
                        master_user=master_user,
                        user_code=new_linked_instrument["instrument_type"],
                    )
                except Exception as e:
                    instrument_type = ecosystem_default.instrument_type

                process = InstrumentTypeProcess(instrument_type=instrument_type)

                instrument_object = process.instrument

                instrument_object["name"] = new_linked_instrument["name"]
                instrument_object["short_name"] = new_linked_instrument["short_name"]
                instrument_object["user_code"] = new_linked_instrument["user_code"]
                instrument_object["public_name"] = new_linked_instrument["public_name"]

                serializer = InstrumentSerializer(
                    data=instrument_object, context=self.context
                )

                is_valid = serializer.is_valid(raise_exception=True)

                if is_valid:
                    serializer.save()

                new_instrument = serializer.instance

            _l.info(f"new_instrument {new_instrument}")

            PortfolioRegister.objects.create(
                master_user=master_user,
                valuation_pricing_policy=ecosystem_default.pricing_policy,
                valuation_currency=ecosystem_default.currency,
                portfolio=instance,
                user_code=instance.user_code,
                linked_instrument=new_instrument,
                default_price=1,
                name=instance.name,
                short_name=instance.short_name,
                public_name=instance.public_name,
            )

    def create(self, validated_data):
        instance = super(PortfolioSerializer, self).create(validated_data)

        self.create_register_if_not_exists(instance)

        return instance

    def update(self, instance, validated_data):
        instance = super(PortfolioSerializer, self).update(instance, validated_data)

        self.create_register_if_not_exists(instance)

        return instance


class PortfolioLightSerializer(ModelWithUserCodeSerializer):
    master_user = MasterUserField()

    class Meta:
        model = Portfolio
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


class PortfolioViewSerializer(ModelWithUserCodeSerializer):
    class Meta:
        model = Portfolio
        fields = [
            "id",
            "user_code",
            "name",
            "short_name",
            "public_name",
        ]


class PortfolioGroupSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=256)


class PortfolioRegisterSerializer(
    ModelWithAttributesSerializer,
    ModelWithUserCodeSerializer,
    ModelWithTimeStampSerializer,
):
    master_user = MasterUserField()

    valuation_currency_object = serializers.PrimaryKeyRelatedField(
        source="valuation_currency", read_only=True
    )
    portfolio_object = serializers.PrimaryKeyRelatedField(
        source="portfolio", read_only=True
    )
    linked_instrument_object = serializers.PrimaryKeyRelatedField(
        source="linked_instrument", read_only=True
    )
    valuation_pricing_policy_object = serializers.PrimaryKeyRelatedField(
        source="valuation_pricing_policy", read_only=True
    )

    class Meta:
        model = PortfolioRegister
        fields = [
            "id",
            "master_user",
            "user_code",
            "name",
            "short_name",
            "public_name",
            "notes",
            "is_deleted",
            "is_enabled",
            "portfolio",
            "portfolio_object",
            "linked_instrument",
            "linked_instrument_object",
            "valuation_currency",
            "valuation_currency_object",
            "valuation_pricing_policy",
            "valuation_pricing_policy_object",
            "default_price",
        ]

    def __init__(self, *args, **kwargs):
        from poms.currencies.serializers import CurrencyViewSerializer

        super().__init__(*args, **kwargs)

        self.fields["valuation_currency_object"] = CurrencyViewSerializer(
            source="valuation_currency", read_only=True
        )
        self.fields["portfolio_object"] = PortfolioViewSerializer(
            source="portfolio", read_only=True
        )
        self.fields["linked_instrument_object"] = InstrumentViewSerializer(
            source="linked_instrument", read_only=True
        )
        self.fields["valuation_pricing_policy_object"] = PricingPolicySerializer(
            source="valuation_pricing_policy", read_only=True
        )

    def create(self, validated_data):
        instance = super(PortfolioRegisterSerializer, self).create(validated_data)

        new_linked_instrument = self.context["request"].data.get(
            "new_linked_instrument"
        )

        master_user = instance.master_user

        print(f"new_linked_instrument {new_linked_instrument}")

        if new_linked_instrument and "name" in new_linked_instrument:
            if isinstance(new_linked_instrument["instrument_type"], int):
                instrument_type = InstrumentType.objects.get(
                    master_user=master_user, id=new_linked_instrument["instrument_type"]
                )
            else:
                instrument_type = InstrumentType.objects.get(
                    master_user=master_user,
                    user_code=new_linked_instrument["instrument_type"],
                )

            process = InstrumentTypeProcess(instrument_type=instrument_type)

            instrument_object = process.instrument

            instrument_object["name"] = new_linked_instrument["name"]
            instrument_object["short_name"] = new_linked_instrument["short_name"]
            instrument_object["user_code"] = new_linked_instrument["user_code"]
            instrument_object["public_name"] = new_linked_instrument["public_name"]

            serializer = InstrumentSerializer(
                data=instrument_object, context=self.context
            )

            is_valid = serializer.is_valid(raise_exception=True)

            if is_valid:
                serializer.save()

            new_instrument = serializer.instance

            instance.linked_instrument_id = new_instrument.id

            instance.save()

        return instance


class PortfolioRegisterRecordSerializer(ModelWithTimeStampSerializer):
    master_user = MasterUserField()

    class Meta:
        model = PortfolioRegisterRecord
        fields = [
            "id",
            "master_user",
            "portfolio",
            "instrument",
            "transaction_class",
            "transaction_code",
            "transaction_date",
            "cash_amount",
            "cash_currency",
            "fx_rate",
            "cash_amount_valuation_currency",
            "valuation_currency",
            "nav_previous_day_valuation_currency",
            "n_shares_previous_day",
            "n_shares_added",
            "dealing_price_valuation_currency",
            "rolling_shares_of_the_day",
            "transaction",
            "complex_transaction",
            "portfolio_register",
            "share_price_calculation_type",
        ]

    def __init__(self, *args, **kwargs):
        super(PortfolioRegisterRecordSerializer, self).__init__(*args, **kwargs)

    def create(self, valid_data: dict) -> PortfolioRegisterRecord:
        valid_data["share_price_calculation_type"] = get_price_calculation_type(
            transaction_class=valid_data["transaction_class"],
            transaction=valid_data["transaction"],
        )
        return super().create(valid_data)


class CalculateRecordsSerializer(serializers.Serializer):
    portfolio_register_ids = serializers.CharField(allow_blank=False)


class PortfolioBundleSerializer(ModelWithTimeStampSerializer):
    master_user = MasterUserField()

    class Meta:
        model = PortfolioBundle
        fields = [
            "id",
            "master_user",
            "name",
            "short_name",
            "user_code",
            "public_name",
            "notes",
            "registers",
        ]

    def __init__(self, *args, **kwargs):
        super(PortfolioBundleSerializer, self).__init__(*args, **kwargs)


class PortfolioEvalSerializer(
    ModelWithUserCodeSerializer, ModelWithTimeStampSerializer
):
    master_user = MasterUserField()

    class Meta:
        model = Portfolio
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

        read_only_fields = fields
