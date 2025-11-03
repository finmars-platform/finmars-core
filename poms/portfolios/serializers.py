from datetime import timedelta
from logging import getLogger

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.views.generic.dates import timezone_today
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from poms.clients.models import Client
from poms.common.fields import UserCodeField
from poms.common.serializers import (
    ModelMetaSerializer,
    ModelWithObjectStateSerializer,
    ModelWithTimeStampSerializer,
    ModelWithUserCodeSerializer,
    PomsClassSerializer,
)
from poms.currencies.fields import CurrencyDefault, CurrencyField
from poms.currencies.serializers import CurrencyViewSerializer
from poms.file_reports.serializers import FileReportSerializer
from poms.iam.serializers import ModelWithResourceGroupSerializer
from poms.instruments.fields import (
    CostMethodField,
    InstrumentTypeField,
    PricingPolicyField,
    SystemPricingPolicyDefault,
)
from poms.instruments.handlers import InstrumentTypeProcess
from poms.instruments.models import CostMethod, Instrument, InstrumentType
from poms.instruments.serializers import (
    InstrumentSerializer,
    InstrumentViewSerializer,
    PricingPolicySerializer,
)
from poms.obj_attrs.serializers import ModelWithAttributesSerializer
from poms.portfolios.fields import (
    PortfolioField,
    PortfolioReconcileGroupField,
    ReconcileStatus,
)
from poms.portfolios.models import (
    Portfolio,
    PortfolioBundle,
    PortfolioClass,
    PortfolioHistory,
    PortfolioReconcileGroup,
    PortfolioReconcileHistory,
    PortfolioRegister,
    PortfolioRegisterRecord,
    PortfolioType,
)
from poms.portfolios.utils import get_price_calculation_type
from poms.users.fields import HiddenMemberField, MasterUserField
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

    portfolio_class_object = PortfolioClassSerializer(source="portfolio_class", read_only=True)

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
    ModelWithObjectStateSerializer,
):
    master_user = MasterUserField()

    valuation_currency = CurrencyField(default=CurrencyDefault())
    valuation_pricing_policy = PricingPolicyField()

    valuation_currency_object = serializers.PrimaryKeyRelatedField(source="valuation_currency", read_only=True)
    linked_instrument_object = serializers.PrimaryKeyRelatedField(source="linked_instrument", read_only=True)
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

        self.fields["valuation_currency_object"] = CurrencyViewSerializer(source="valuation_currency", read_only=True)
        self.fields["linked_instrument_object"] = InstrumentViewSerializer(source="linked_instrument", read_only=True)
        self.fields["valuation_pricing_policy_object"] = PricingPolicySerializer(
            source="valuation_pricing_policy", read_only=True
        )


class PortfolioSerializer(
    ModelWithResourceGroupSerializer,
    ModelWithAttributesSerializer,
    ModelWithUserCodeSerializer,
    ModelWithTimeStampSerializer,
    ModelWithObjectStateSerializer,
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
    client = serializers.PrimaryKeyRelatedField(queryset=Client.objects.all(), required=False, allow_null=True)
    client_object = serializers.PrimaryKeyRelatedField(
        source="client",
        read_only=True,
        many=False,
    )

    register_currency = CurrencyField(required=False, allow_null=True)
    register_currency_object = CurrencyViewSerializer(source="register_currency", read_only=True)
    register_pricing_policy = PricingPolicyField(required=False, allow_null=True)
    register_instrument_type = InstrumentTypeField(required=False, allow_null=True)

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
            "first_transaction",  # possible deprecated, do not delete yet
            "first_transaction_date",
            "first_cash_flow_date",
            "portfolio_type",
            "portfolio_type_object",
            "client",
            "client_object",
            "register_currency",
            "register_currency_object",
            "register_pricing_policy",
            "register_instrument_type",
        ]

    def get_first_transaction(self, instance: Portfolio) -> dict:
        return {
            "date_field": "accounting_date",
            "date": instance.first_transaction_date,
        }

    def __init__(self, *args, **kwargs):
        from poms.accounts.serializers import AccountViewSerializer
        from poms.clients.serializers import ClientSerializer
        from poms.counterparties.serializers import (
            CounterpartyViewSerializer,
            ResponsibleViewSerializer,
        )
        from poms.transactions.serializers import TransactionTypeViewSerializer

        super().__init__(*args, **kwargs)

        self.fields["accounts_object"] = AccountViewSerializer(source="accounts", many=True, read_only=True)
        self.fields["responsibles_object"] = ResponsibleViewSerializer(
            source="responsibles", many=True, read_only=True
        )
        self.fields["counterparties_object"] = CounterpartyViewSerializer(
            source="counterparties", many=True, read_only=True
        )
        self.fields["transaction_types_object"] = TransactionTypeViewSerializer(
            source="transaction_types", many=True, read_only=True
        )
        self.fields["client_object"] = ClientSerializer(source="client", many=False, read_only=True)

    def create_register_if_not_exists(
        self, instance, register_currency=None, register_pricing_policy=None, register_instrument_type=None
    ):
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
                new_instrument = Instrument.objects.get(master_user=master_user, user_code=instance.user_code)
            except Exception:
                new_linked_instrument = {
                    "name": instance.name,
                    "user_code": instance.user_code,
                    "short_name": instance.short_name,
                    "public_name": instance.public_name,
                    "instrument_type": f"{settings.INSTRUMENT_TYPE_PREFIX}:portfolio",
                    "identifier": {},
                }

                instrument_type = None

                if register_instrument_type:
                    instrument_type = register_instrument_type

                else:
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

                serializer = InstrumentSerializer(data=instrument_object, context=self.context)

                is_valid = serializer.is_valid(raise_exception=True)

                if is_valid:
                    serializer.save()

                new_instrument = serializer.instance

            _l.info(f"{self.__class__.__name__}.create_register_if_not_exists new_instrument={new_instrument}")

            _l.info("register_currency %s", register_currency)
            _l.info("register_pricing_policy %s", register_pricing_policy)

            valuation_currency = register_currency or ecosystem_default.currency
            valuation_pricing_policy = register_pricing_policy or ecosystem_default.pricing_policy

            PortfolioRegister.objects.create(
                master_user=master_user,
                owner=instance.owner,
                valuation_pricing_policy=valuation_pricing_policy,
                valuation_currency=valuation_currency,
                portfolio=instance,
                user_code=instance.user_code,
                linked_instrument=new_instrument,
                default_price=1,
                name=instance.name,
                short_name=instance.short_name,
                public_name=instance.public_name,
            )

    def create(self, validated_data):
        # take them out so Django won’t try to set them on the model
        register_currency = validated_data.get("register_currency", None)
        register_pricing_policy = validated_data.get("register_pricing_policy", None)
        register_instrument_type = validated_data.get("register_instrument_type", None)

        with transaction.atomic():
            instance = super().create(validated_data)

            try:
                self.create_register_if_not_exists(
                    instance, register_currency, register_pricing_policy, register_instrument_type
                )
            except Exception as e:
                _l.error(f"Failed to create register: {e}")
                raise

            return instance

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)

        # 2025-06-07 SZ do not create registers for existing portfolios
        # self.create_register_if_not_exists(instance)

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
            "first_transaction",
            "first_transaction_date",
            "first_cash_flow_date",
        ]

    def get_first_transaction(self, instance: Portfolio) -> dict:
        return {
            "date_field": "accounting_date",
            "date": instance.first_transaction_date,
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
    ModelWithObjectStateSerializer,
):
    master_user = MasterUserField()

    valuation_currency = CurrencyField(default=CurrencyDefault())
    valuation_pricing_policy = PricingPolicyField()

    valuation_currency_object = serializers.PrimaryKeyRelatedField(source="valuation_currency", read_only=True)
    portfolio_object = serializers.PrimaryKeyRelatedField(source="portfolio", read_only=True)
    linked_instrument_object = serializers.PrimaryKeyRelatedField(source="linked_instrument", read_only=True)
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

        self.fields["valuation_currency_object"] = CurrencyViewSerializer(source="valuation_currency", read_only=True)
        self.fields["portfolio_object"] = PortfolioViewSerializer(source="portfolio", read_only=True)
        self.fields["linked_instrument_object"] = InstrumentViewSerializer(source="linked_instrument", read_only=True)
        self.fields["valuation_pricing_policy_object"] = PricingPolicySerializer(
            source="valuation_pricing_policy", read_only=True
        )

    @transaction.atomic
    def create(self, validated_data):
        instance = super().create(validated_data)

        new_linked_instrument = self.context["request"].data.get("new_linked_instrument")
        if new_linked_instrument and ("name" in new_linked_instrument):
            _l.info(f"{self.__class__.__name__}.create new_linked_instrument={new_linked_instrument}")
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
        instrument_object["identifier"] = new_linked_instrument.get("identifier", {})
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
        from poms.transactions.serializers import TransactionClassSerializer

        super().__init__(*args, **kwargs)

        self.fields["cash_currency_object"] = CurrencyViewSerializer(source="cash_currency", read_only=True)
        self.fields["valuation_currency_object"] = CurrencyViewSerializer(source="valuation_currency", read_only=True)
        self.fields["transaction_class_object"] = TransactionClassSerializer(
            source="transaction_class", read_only=True
        )
        self.fields["portfolio_object"] = PortfolioViewSerializer(source="portfolio", read_only=True)
        # self.fields["complex_transaction_object"] = ComplexTransactionViewSerializer(
        #     source="complex_transaction", read_only=True
        # )
        self.fields["portfolio_register_object"] = PortfolioRegisterViewSerializer(
            source="portfolio_register", read_only=True
        )
        self.fields["instrument_object"] = InstrumentViewSerializer(source="instrument", read_only=True)
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


class PortfolioBundleSerializer(
    ModelWithUserCodeSerializer,
    ModelWithTimeStampSerializer,
    ModelWithObjectStateSerializer,
):
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


class PortfolioEvalSerializer(ModelWithUserCodeSerializer, ModelWithTimeStampSerializer):
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


def belongs_to_model(field: str, model: type[models.Model]) -> bool:
    model_fields = model._meta.get_fields()
    field_names = [field.name for field in model_fields if field.is_relation is False]  # Exclude relation fields
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
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)

    portfolio_registers = serializers.ListField(child=serializers.CharField(), required=False)

    def validate(self, attrs: dict) -> dict:
        date_to = attrs.get("date_to") or timezone_today() - timedelta(days=1)
        attrs["date_to"] = date_to

        date_from = attrs.get("date_from")
        if date_from and date_to and (date_from > date_to):
            raise ValidationError("date_from must be <= date_to")

        return attrs


class PrCalculatePriceHistoryRequestSerializer(serializers.Serializer):
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    portfolio_registers = serializers.ListField(child=serializers.CharField(), required=False)

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
            "gav",
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
            "created_at",
            "modified_at",
            "is_enabled",
            "error_message",
            "status",
        ]

    def __init__(self, *args, **kwargs):
        from poms.currencies.serializers import CurrencyViewSerializer

        super().__init__(*args, **kwargs)

        self.fields["currency_object"] = CurrencyViewSerializer(source="currency", read_only=True)
        self.fields["portfolio_object"] = PortfolioViewSerializer(source="portfolio", read_only=True)
        self.fields["pricing_policy_object"] = PricingPolicySerializer(source="pricing_policy", read_only=True)


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

    segmentation_type = serializers.ChoiceField(
        required=False,
        initial=SEGMENTATION_TYPE_BUSINESS_DAYS_END_OF_MONTHS,
        default=SEGMENTATION_TYPE_BUSINESS_DAYS_END_OF_MONTHS,
        choices=SEGMENTATION_TYPE_CHOICES,
    )
    period_type = serializers.ChoiceField(
        required=False,
        default=PortfolioHistory.PERIOD_YTD,
        choices=PortfolioHistory.PERIOD_CHOICES,
    )
    cost_method = CostMethodField(
        required=False,
        default=CostMethod.AVCO,
        initial=CostMethod.AVCO,
    )
    performance_method = serializers.ChoiceField(
        required=False,
        default=PortfolioHistory.PERFORMANCE_METHOD_MODIFIED_DIETZ,
        choices=PortfolioHistory.PERFORMANCE_METHOD_CHOICES,
    )
    benchmark = serializers.CharField(required=False, default="sp_500", initial="sp_500")

    def validate(self, attrs: dict) -> dict:
        date = attrs.get("date") or timezone_today() - timedelta(days=1)
        attrs["date"] = date

        calculation_period_date_from = attrs.get("calculation_period_date_from")
        if calculation_period_date_from and date and (calculation_period_date_from > date):
            raise ValidationError("calculation_period_date_from must be <= date")

        return attrs


class ParamsSerializer(serializers.Serializer):
    only_errors = serializers.BooleanField(required=False, default=False)
    round_digits = serializers.IntegerField(required=False, min_value=0, default=2)
    report_ttl = serializers.IntegerField(required=False, min_value=1, default=90)
    precision = serializers.FloatField(
        required=False,
        default=1.0,
        validators=[MinValueValidator(0.00)],
    )
    notifications = serializers.DictField(required=False, default={})


GROUP_FIELDS = [
    "id",
    "master_user",
    "name",
    "short_name",
    "user_code",
    "public_name",
    "notes",
    "portfolios",
    "params",
    "last_calculated_at",
]


class ReconcilePortfolioField(PortfolioField):
    def to_representation(self, obj):
        return obj.user_code


class PortfolioReconcileGroupSerializer(ModelWithUserCodeSerializer, ModelWithTimeStampSerializer):
    master_user = MasterUserField()
    params = ParamsSerializer()
    portfolios = serializers.ListSerializer(child=ReconcilePortfolioField(required=True))
    user_code = UserCodeField()

    class Meta:
        model = PortfolioReconcileGroup
        fields = GROUP_FIELDS

    def validate(self, attrs):
        portfolios = attrs.get("portfolios")
        if not portfolios:
            return attrs

        view = self.context.get("view")
        if view and view.action in ("update", "partial_update"):
            raise ValidationError({"portfolios": "You can't update list of portfolios"})

        if len(portfolios) != len(set(portfolios)):
            raise serializers.ValidationError({"portfolios": "Duplicated portfolios"})

        if len(portfolios) != 2:
            raise serializers.ValidationError({"portfolios": "Must me exactly 2 portfolios"})

        portfolio_classes = [p.portfolio_type.portfolio_class_id for p in portfolios if p.portfolio_type]
        if len(set(portfolio_classes)) < 2:
            raise serializers.ValidationError({"portfolios": "Portfolios must be of different classes"})

        return attrs

    def create(self, validated_data):
        portfolios = validated_data.pop("portfolios")
        group = super().create(validated_data)
        group.portfolios.set(portfolios)

        return group


class SimplePortfolioReconcileGroupSerializer(serializers.ModelSerializer):
    # Simple model serializer (doesn't use request, user, master_user & owner fields)
    portfolios = serializers.ListSerializer(child=PortfolioField(required=True))

    class Meta:
        model = PortfolioReconcileGroup
        fields = GROUP_FIELDS
        read_only_fields = fields


HISTORY_FIELDS = [
    "id",
    "user_code",
    "master_user",
    "portfolio_reconcile_group",
    "portfolio_reconcile_group_object",
    "date",
    "verbose_result",
    "error_message",
    "status",
    "file_report",
    "report_ttl",
    "created_at",
    "modified_at",
]


class PortfolioReconcileHistorySerializer(ModelWithUserCodeSerializer, ModelWithTimeStampSerializer):
    master_user = MasterUserField()
    portfolio_reconcile_group = serializers.CharField(source="portfolio_reconcile_group.user_code")
    portfolio_reconcile_group_object = PortfolioReconcileGroupSerializer(
        source="portfolio_reconcile_group", read_only=True
    )
    file_report = FileReportSerializer(read_only=True)
    user_code = UserCodeField()

    class Meta:
        model = PortfolioReconcileHistory
        fields = HISTORY_FIELDS


class SimpleReconcileHistorySerializer(serializers.ModelSerializer):
    # Simple model serializer (do not use request, user, master_user & owner fields)
    portfolio_reconcile_group = serializers.CharField(source="portfolio_reconcile_group.user_code")
    portfolio_reconcile_group_object = SimplePortfolioReconcileGroupSerializer(source="portfolio_reconcile_group")
    file_report = FileReportSerializer()

    class Meta:
        model = PortfolioReconcileHistory
        fields = HISTORY_FIELDS
        read_only_fields = fields


class CalculateReconcileHistorySerializer(serializers.Serializer):
    master_user = MasterUserField()
    member = HiddenMemberField()
    portfolio_reconcile_group = PortfolioReconcileGroupField(required=True)
    dates = serializers.ListField(child=serializers.DateField(), required=True)

    @staticmethod
    def validate_dates(dates: list) -> list:
        if not dates:
            raise serializers.ValidationError("'dates' can't be empty")

        return dates


class BulkCalculateReconcileHistorySerializer(serializers.Serializer):
    master_user = MasterUserField()
    member = HiddenMemberField()
    reconcile_groups = serializers.ListField(child=PortfolioReconcileGroupField(), required=True)
    dates = serializers.ListField(child=serializers.DateField(), required=True)

    @staticmethod
    def validate_dates(dates: list) -> list:
        if not dates:
            raise serializers.ValidationError("'dates' can't be empty")

        return dates

    @staticmethod
    def validate_reconcile_groups(groups: list) -> list:
        if not groups:
            raise serializers.ValidationError("'reconcile_groups' can't be empty")

        return groups


class PortfolioReconcileStatusSerializer(serializers.Serializer):
    master_user = MasterUserField()
    member = HiddenMemberField()
    portfolios = serializers.ListField(child=PortfolioField(), required=True)
    date = serializers.DateField(required=True)

    def validate(self, attrs: dict) -> dict:
        if not attrs["portfolios"]:
            raise serializers.ValidationError({"portfolios": "Can't be empty"})

        return attrs

    @staticmethod
    def reconcile_status(history: dict) -> ReconcileStatus:
        return (
            ReconcileStatus.OK.value
            if history["status"] == PortfolioReconcileHistory.STATUS_OK
            else ReconcileStatus.ERROR.value
        )

    @staticmethod
    def final_status(statuses) -> str:
        strings = list(statuses)
        if not strings:
            return ReconcileStatus.ERROR.value

        first_string = strings[0]
        return first_string if all(s == first_string for s in strings) else ReconcileStatus.ERROR.value

    def check_reconciliation_date(self, validated_data: dict) -> dict:
        result = {}
        day = validated_data["date"]
        portfolios = validated_data.pop("portfolios")

        for portfolio in portfolios:
            portfolio_result = {
                "final_status": "unknown",  # to be replaced by real status value
                "all_statuses": {},
                "history_objects": [],
            }
            groups = PortfolioReconcileGroup.objects.filter(portfolios=portfolio)
            if not groups:
                portfolio_result["final_status"] = ReconcileStatus.NO_GROUP.value
                result[portfolio.user_code] = portfolio_result
                continue

            histories = PortfolioReconcileHistory.objects.filter(
                portfolio_reconcile_group__in=groups,
                date=day,
            )
            if not histories:
                portfolio_result["final_status"] = ReconcileStatus.NOT_RUN_YET.value
                result[portfolio.user_code] = portfolio_result
                continue

            history_objects = SimpleReconcileHistorySerializer(histories, many=True).data
            all_statuses = {history["user_code"]: self.reconcile_status(history) for history in history_objects}
            final_status = self.final_status(all_statuses.values())
            result[portfolio.user_code] = {
                "final_status": final_status,
                "history_objects": history_objects,
            }

        return result
