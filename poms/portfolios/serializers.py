from datetime import timedelta
from logging import getLogger

from django.db import models, transaction
from django.views.generic.dates import timezone_today
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from typing import Type

from poms.common.serializers import (
    ModelWithTimeStampSerializer,
    ModelWithUserCodeSerializer, ModelMetaSerializer, PomsClassSerializer,
)
from poms.currencies.fields import CurrencyField, CurrencyDefault
from poms.instruments.fields import PricingPolicyField, SystemPricingPolicyDefault, CostMethodField
from poms.instruments.handlers import InstrumentTypeProcess
from poms.instruments.models import Instrument, InstrumentType, CostMethod
from poms.instruments.serializers import (
    InstrumentSerializer,
    InstrumentViewSerializer,
    PricingPolicySerializer,
)
from poms.obj_attrs.serializers import ModelWithAttributesSerializer
from poms.portfolios.fields import PortfolioField
from poms.portfolios.models import (
    Portfolio,
    PortfolioBundle,
    PortfolioRegister,
    PortfolioRegisterRecord, PortfolioHistory, PortfolioType, PortfolioClass,
)
from poms.portfolios.utils import get_price_calculation_type
from poms.users.fields import MasterUserField, HiddenMemberField
from poms.users.models import EcosystemDefault

_l = getLogger("poms.portfolios")

class PortfolioClassSerializer(PomsClassSerializer):
    class Meta(PomsClassSerializer.Meta):
        model = PortfolioClass


class PortfolioTypeSerializer(
    ModelWithUserCodeSerializer,
    ModelWithAttributesSerializer,
    ModelWithTimeStampSerializer,
    ModelMetaSerializer,
):
    master_user = MasterUserField()

    portfolio_class_object = PortfolioClassSerializer(
        source="portfolio_class", read_only=True
    )

    class Meta:
        model = PortfolioType
        fields = [
            "id",
            "master_user",
            "user_code",
            "configuration_code",
            "name",
            "short_name",
            "public_name",
            "notes",
            "is_deleted",
            "is_enabled",

            "portfolio_class",
            "portfolio_class_object",
        ]


class PortfolioTypeLightSerializer(ModelWithUserCodeSerializer):
    master_user = MasterUserField()

    class Meta:
        model = PortfolioType
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




class PortfolioPortfolioRegisterSerializer(
    ModelWithAttributesSerializer,
    ModelWithUserCodeSerializer,
    ModelWithTimeStampSerializer,
):
    master_user = MasterUserField()

    valuation_currency = CurrencyField(default=CurrencyDefault())
    valuation_pricing_policy = PricingPolicyField()

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
        from poms.currencies.serializers import CurrencyViewSerializer

        super().__init__(*args, **kwargs)

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
    registers = PortfolioPortfolioRegisterSerializer(
        many=True,
        allow_null=True,
        required=False,
        read_only=True,
    )

    first_transaction = serializers.SerializerMethodField(read_only=True)

    first_transaction_date = serializers.ReadOnlyField()
    first_cash_flow_date = serializers.ReadOnlyField()

    portfolio_type_object = PortfolioTypeSerializer(source="portfolio_type", read_only=True)

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
            "registers",
            "first_transaction", # possible deprecated, do not delete yet

            "first_transaction_date",
            "first_cash_flow_date",

            "portfolio_type",
            "portfolio_type_object"
        ]

    def get_first_transaction(self, instance):

        date_field = "accounting_date"

        first_date = instance.get_first_transaction_date(date_field)
        return {
            "date_field": date_field,
            "date": first_date,
        }

    def __init__(self, *args, **kwargs):
        from poms.accounts.serializers import AccountViewSerializer
        from poms.counterparties.serializers import (
            CounterpartyViewSerializer,
            ResponsibleViewSerializer,
        )
        from poms.transactions.serializers import TransactionTypeViewSerializer

        super().__init__(*args, **kwargs)

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
            PortfolioRegister.objects.get(
                master_user=master_user,
                portfolio=instance,
                user_code=instance.user_code,
            )

        except Exception:
            ecosystem_default = EcosystemDefault.objects.get(master_user=master_user)

            # TODO maybe create new instr instead of existing?
            try:
                new_instrument = Instrument.objects.get(
                    master_user=master_user, user_code=instance.user_code
                )
            except Exception:
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
                except Exception:
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

            _l.info(
                f"{self.__class__.__name__}.create_register_if_not_exists "
                f"new_instrument={new_instrument}"
            )

            PortfolioRegister.objects.create(
                master_user=master_user,
                owner=instance.owner,
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
        instance = super().create(validated_data)

        self.create_register_if_not_exists(instance)

        return instance

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)

        self.create_register_if_not_exists(instance)

        return instance


class PortfolioLightSerializer(ModelWithUserCodeSerializer):
    master_user = MasterUserField()

    first_transaction = serializers.SerializerMethodField(read_only=True)

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
            "first_transaction"
        ]

    def get_first_transaction(self, instance):
        date_field = "accounting_date"

        first_date = instance.get_first_transaction_date(date_field)
        return {
            "date_field": date_field,
            "date": first_date,
        }


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


class PortfolioRegisterViewSerializer(ModelWithUserCodeSerializer):
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

    valuation_currency = CurrencyField(default=CurrencyDefault())
    valuation_pricing_policy = PricingPolicyField()

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

    @transaction.atomic
    def create(self, validated_data):
        instance = super().create(validated_data)

        new_linked_instrument = self.context["request"].data.get(
            "new_linked_instrument"
        )
        if new_linked_instrument and ("name" in new_linked_instrument):
            _l.info(
                f"{self.__class__.__name__}.create new_linked_instrument="
                f"{new_linked_instrument}"
            )
            self.create_new_instrument(
                instance.master_user,
                new_linked_instrument,
                instance,
            )

        return instance

    def create_new_instrument(
            self,
            master_user,
            new_linked_instrument: dict,
            instance: PortfolioRegister,
    ):
        linked_instrument_type = new_linked_instrument["instrument_type"]
        instrument_type = (
            InstrumentType.objects.filter(
                master_user=master_user,
                id=linked_instrument_type,
            ).first()
            if isinstance(linked_instrument_type, int)
            else InstrumentType.objects.filter(
                master_user=master_user,
                user_code=linked_instrument_type,
            ).first()
        )
        if not instrument_type:
            raise ValidationError(
                detail=f"InstrumentType {linked_instrument_type} doesn't exist!",
                code="invalid instrument_type value in new_linked_instrument",
            )

        process = InstrumentTypeProcess(instrument_type=instrument_type)

        instrument_object = process.instrument
        instrument_object["name"] = new_linked_instrument["name"]
        instrument_object["short_name"] = new_linked_instrument["short_name"]
        instrument_object["user_code"] = new_linked_instrument["user_code"]
        instrument_object["public_name"] = new_linked_instrument["public_name"]
        instrument_object["has_linked_with_portfolio"] = True

        instrument_object["pricing_currency"] = instance.valuation_currency_id
        instrument_object["accrued_currency"] = instance.valuation_currency_id
        instrument_object["co_directional_exposure_currency"] = instance.valuation_currency_id
        instrument_object["counter_directional_exposure_currency"] = instance.valuation_currency_id

        serializer = InstrumentSerializer(
            data=instrument_object,
            context=self.context,
        )

        serializer.is_valid(raise_exception=True)

        serializer.save()

        instance.linked_instrument = serializer.instance

        instance.save()


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
            "nav_valuation_currency",
            "nav_previous_business_day_valuation_currency",
            "nav_previous_register_record_day_valuation_currency",
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
        from poms.currencies.serializers import CurrencyViewSerializer
        from poms.transactions.serializers import (
            TransactionClassSerializer,
        )

        super().__init__(*args, **kwargs)

        self.fields["cash_currency_object"] = CurrencyViewSerializer(
            source="cash_currency", read_only=True
        )
        self.fields["valuation_currency_object"] = CurrencyViewSerializer(
            source="valuation_currency", read_only=True
        )
        self.fields["transaction_class_object"] = TransactionClassSerializer(
            source="transaction_class", read_only=True
        )
        self.fields["portfolio_object"] = PortfolioViewSerializer(
            source="portfolio", read_only=True
        )
        # self.fields["complex_transaction_object"] = ComplexTransactionViewSerializer(
        #     source="complex_transaction", read_only=True
        # )
        self.fields["portfolio_register_object"] = PortfolioRegisterViewSerializer(
            source="portfolio_register", read_only=True
        )
        self.fields["instrument_object"] = InstrumentViewSerializer(
            source="instrument", read_only=True
        )
        self.fields["valuation_pricing_policy_object"] = PricingPolicySerializer(
            source="valuation_pricing_policy", read_only=True
        )

    def create(self, valid_data: dict) -> PortfolioRegisterRecord:
        valid_data["share_price_calculation_type"] = get_price_calculation_type(
            transaction_class=valid_data["transaction_class"],
            transaction=valid_data["transaction"],
        )
        return super().create(valid_data)


class CalculateRecordsSerializer(serializers.Serializer):
    portfolio_register_ids = serializers.CharField(allow_blank=False)


class PortfolioBundleSerializer(ModelWithUserCodeSerializer, ModelWithTimeStampSerializer):
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


def belongs_to_model(field: str, model: Type[models.Model]) -> bool:
    model_fields = model._meta.get_fields()
    field_names = [  # Exclude relation fields
        field.name for field in model_fields if field.is_relation is False
    ]
    return field in field_names


class FirstTransactionDateRequestSerializer(serializers.Serializer):
    portfolio = PortfolioField(required=False)
    date_field = serializers.CharField(default="transaction_date")

    master_user = MasterUserField()

    class Meta:
        model = Portfolio
        fields = [
            "portfolio",
            "date_field",
            "master_user",
        ]
        read_only_fields = fields

    def validate(self, attrs: dict) -> dict:
        from poms.transactions.models import Transaction

        if "portfolio" in attrs:
            attrs["portfolio"] = [
                attrs["portfolio"],
            ]
        else:
            attrs["portfolio"] = list(Portfolio.objects.all())

        date_field = attrs["date_field"]
        if not belongs_to_model(date_field, Transaction) or "date" not in date_field:
            raise ValidationError(f"Transaction has no such date field {date_field}!")

        return attrs


class FirstTransactionSerializer(serializers.Serializer):
    date_field = serializers.CharField()
    date = serializers.DateField()


class BasicPortfolioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Portfolio
        fields = [
            "id",
            "user_code",
            "name",
            "short_name",
            "public_name",
            "is_default",
            "is_deleted",
            "is_enabled",
        ]


class FirstTransactionDateResponseSerializer(serializers.Serializer):
    portfolio = BasicPortfolioSerializer()
    first_transaction = FirstTransactionSerializer()


class PrCalculateRecordsRequestSerializer(serializers.Serializer):
    portfolios = serializers.ListField(child=serializers.CharField(), required=False)


class PrCalculatePriceHistoryRequestSerializer(serializers.Serializer):
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    portfolios = serializers.ListField(child=serializers.CharField(), required=False)

    def validate(self, attrs: dict) -> dict:
        date_to = attrs.get("date_to") or timezone_today() - timedelta(days=1)
        attrs["date_to"] = date_to

        date_from = attrs.get("date_from")
        if date_from and date_to and (date_from > date_to):
            raise ValidationError("date_from must be <= date_to")

        return attrs


class PortfolioHistorySerializer(ModelWithUserCodeSerializer, ModelWithTimeStampSerializer):
    master_user = MasterUserField()

    portfolio = PortfolioField(required=True)
    currency = CurrencyField(default=CurrencyDefault())
    cost_method = serializers.PrimaryKeyRelatedField(queryset=CostMethod.objects)

    class Meta:
        model = PortfolioHistory
        fields = [
            "id",

            "user_code",

            "master_user",
            "portfolio",
            "currency",
            "pricing_policy",

            "date",
            "date_from",
            "period_type",

            "cost_method",
            "performance_method",

            "benchmark",
            "nav",
            "cash_flow",
            "cash_inflow",
            "cash_outflow",
            "total",

            "cumulative_return",
            "annualized_return",
            "portfolio_volatility",
            "annualized_portfolio_volatility",

            "sharpe_ratio",
            "max_annualized_drawdown",

            "betta",
            "alpha",
            "correlation",
            "weighted_duration",

            "created",
            "modified",

            "is_enabled",

            "error_message",
            "status"

        ]

    def __init__(self, *args, **kwargs):
        from poms.currencies.serializers import CurrencyViewSerializer

        super().__init__(*args, **kwargs)

        self.fields["currency_object"] = CurrencyViewSerializer(
            source="currency", read_only=True
        )

        self.fields["portfolio_object"] = PortfolioViewSerializer(
            source="portfolio", read_only=True
        )

        self.fields["pricing_policy_object"] = PricingPolicySerializer(
            source="pricing_policy", read_only=True
        )


class CalculatePortfolioHistorySerializer(serializers.Serializer):
    master_user = MasterUserField()
    member = HiddenMemberField()

    # SEGMENTATION_TYPE_DAYS = "days"
    SEGMENTATION_TYPE_DAYS = "days"
    SEGMENTATION_TYPE_BUSINESS_DAYS = "business_days"
    SEGMENTATION_TYPE_BUSINESS_DAYS_END_OF_MONTHS = "business_days_end_of_months"
    SEGMENTATION_TYPE_CHOICES = (
        (SEGMENTATION_TYPE_DAYS, "Days"),
        (SEGMENTATION_TYPE_BUSINESS_DAYS, "Business Days"),
        (SEGMENTATION_TYPE_BUSINESS_DAYS_END_OF_MONTHS, "Business Days End Of Months"),
    )

    portfolio = PortfolioField(required=True)
    currency = CurrencyField(default=CurrencyDefault())
    pricing_policy = PricingPolicyField(default=SystemPricingPolicyDefault())

    date = serializers.DateField(required=True)
    calculation_period_date_from = serializers.DateField(required=False)
    # Important, date_from for metrics itself is ready only
    # its is calculated from date and period_type

    segmentation_type = serializers.ChoiceField(required=False, initial=SEGMENTATION_TYPE_BUSINESS_DAYS_END_OF_MONTHS,
                                                default=SEGMENTATION_TYPE_BUSINESS_DAYS_END_OF_MONTHS,
                                                choices=SEGMENTATION_TYPE_CHOICES)
    period_type = serializers.ChoiceField(required=False, default=PortfolioHistory.PERIOD_YTD,
                                          choices=PortfolioHistory.PERIOD_CHOICES)
    cost_method = CostMethodField(required=False, default=CostMethod.AVCO, initial=CostMethod.AVCO)
    performance_method = serializers.ChoiceField(required=False,
                                                 default=PortfolioHistory.PERFORMANCE_METHOD_MODIFIED_DIETZ,
                                                 choices=PortfolioHistory.PERFORMANCE_METHOD_CHOICES)
    benchmark = serializers.CharField(required=False, default="sp_500", initial="sp_500")
