from __future__ import unicode_literals

import datetime

from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.fields import empty

from poms.accounts.fields import AccountField, AccountDefault
from poms.accounts.models import Account
from poms.common import formula
from poms.common.fields import ExpressionField
from poms.common.models import EXPRESSION_FIELD_LENGTH
from poms.common.serializers import PomsClassSerializer, ModelWithUserCodeSerializer
from poms.counterparties.fields import ResponsibleField, CounterpartyField, ResponsibleDefault, CounterpartyDefault
from poms.counterparties.models import Counterparty, Responsible
from poms.currencies.fields import CurrencyField, CurrencyDefault, SystemCurrencyDefault
from poms.currencies.models import Currency
from poms.instruments.fields import InstrumentField, InstrumentTypeField, InstrumentDefault, PricingPolicyField, \
    AccrualCalculationModelField, PeriodicityField, NotificationClassField, EventClassField, EventScheduleField
from poms.instruments.models import Instrument, InstrumentType, DailyPricingModel, PaymentSizeDetail, PricingPolicy, \
    Periodicity, AccrualCalculationModel, EventSchedule
from poms.instruments.serializers import PeriodicitySerializer, \
    AccrualCalculationModelSerializer
from poms.integrations.fields import PriceDownloadSchemeField
from poms.integrations.models import PriceDownloadScheme
from poms.obj_attrs.serializers import ModelWithAttributesSerializer
from poms.obj_perms.serializers import ModelWithObjectPermissionSerializer
from poms.portfolios.fields import PortfolioField, PortfolioDefault
from poms.portfolios.models import Portfolio
from poms.strategies.fields import Strategy1Field, Strategy2Field, Strategy3Field, Strategy1Default, Strategy2Default, \
    Strategy3Default
from poms.strategies.models import Strategy1, Strategy2, Strategy3
from poms.tags.serializers import ModelWithTagSerializer
from poms.transactions.fields import TransactionTypeInputContentTypeField, \
    TransactionTypeGroupField, ReadOnlyContentTypeField, TransactionTypeField
from poms.transactions.handlers import TransactionTypeProcess
from poms.transactions.models import TransactionClass, Transaction, TransactionType, TransactionTypeAction, \
    TransactionTypeActionTransaction, TransactionTypeActionInstrument, TransactionTypeInput, TransactionTypeGroup, \
    ComplexTransaction, EventClass, NotificationClass, ComplexTransactionInput, \
    TransactionTypeActionInstrumentFactorSchedule, TransactionTypeActionInstrumentManualPricingFormula, \
    TransactionTypeActionInstrumentAccrualCalculationSchedules, TransactionTypeActionInstrumentEventSchedule, \
    TransactionTypeActionInstrumentEventScheduleAction
from poms.users.fields import MasterUserField


class EventClassSerializer(PomsClassSerializer):
    class Meta(PomsClassSerializer.Meta):
        model = EventClass


class NotificationClassSerializer(PomsClassSerializer):
    class Meta(PomsClassSerializer.Meta):
        model = NotificationClass


class TransactionClassSerializer(PomsClassSerializer):
    class Meta(PomsClassSerializer.Meta):
        model = TransactionClass


class TransactionTypeGroupSerializer(ModelWithObjectPermissionSerializer, ModelWithUserCodeSerializer,
                                     ModelWithTagSerializer):
    master_user = MasterUserField()

    # tags = TagField(many=True, required=False, allow_null=True)
    # tags_object = TagViewSerializer(source='tags', many=True, read_only=True)

    class Meta:
        model = TransactionTypeGroup
        fields = [
            'id', 'master_user', 'user_code', 'name', 'short_name', 'public_name', 'notes', 'is_deleted',
            # 'tags', 'tags_object',
        ]


class TransactionTypeGroupViewSerializer(ModelWithObjectPermissionSerializer):
    class Meta(ModelWithObjectPermissionSerializer.Meta):
        model = TransactionTypeGroup
        fields = [
            'id', 'user_code', 'name', 'short_name', 'public_name', 'notes', 'is_deleted',
        ]


# class TransactionTypeGroupBulkObjectPermissionSerializer(AbstractBulkObjectPermissionSerializer):
#     content_objects = TransactionTypeGroupField(many=True, allow_null=False, allow_empty=False)
#
#     class Meta:
#         model = TransactionTypeGroup


class TransactionInputField(serializers.CharField):
    def __init__(self, **kwargs):
        super(TransactionInputField, self).__init__(**kwargs)

    def to_representation(self, value):
        return value.name if value else None


class TransactionTypeActionInstrumentPhantomField(serializers.IntegerField):
    def to_representation(self, value):
        return value.order if value else None


class TransactionTypeActionInstrumentEventSchedulePhantomField(serializers.IntegerField):
    def to_representation(self, value):
        return value.order if value else None


class TransactionTypeInputSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=False, required=False, allow_null=True)
    name = serializers.CharField(max_length=255, allow_null=False, allow_blank=False,
                                 validators=[
                                     serializers.RegexValidator(regex='\A[a-zA-Z_][a-zA-Z0-9_]*\Z'),
                                 ])
    content_type = TransactionTypeInputContentTypeField(required=False, allow_null=True, allow_empty=True)
    can_recalculate = serializers.BooleanField(read_only=True)
    value_expr = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, allow_null=True, allow_blank=True,
                                 default='')
    is_fill_from_context = serializers.BooleanField(default=False, initial=False, required=False)
    value = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, allow_null=True, allow_blank=True,
                            default='')
    account = AccountField(required=False, allow_null=True)
    instrument_type = InstrumentTypeField(required=False, allow_null=True)
    instrument = InstrumentField(required=False, allow_null=True)
    currency = CurrencyField(required=False, allow_null=True)
    counterparty = CounterpartyField(required=False, allow_null=True)
    responsible = ResponsibleField(required=False, allow_null=True)
    portfolio = PortfolioField(required=False, allow_null=True)
    strategy1 = Strategy1Field(required=False, allow_null=True)
    strategy2 = Strategy2Field(required=False, allow_null=True)
    strategy3 = Strategy3Field(required=False, allow_null=True)
    price_download_scheme = PriceDownloadSchemeField(required=False, allow_null=True)
    pricing_policy = PricingPolicyField(required=False, allow_null=True)

    periodicity = PeriodicityField(required=False, allow_null=True)
    accrual_calculation_model = AccrualCalculationModelField(required=False, allow_null=True)

    # account_object = serializers.PrimaryKeyRelatedField(source='account', read_only=True)
    # instrument_type_object = serializers.PrimaryKeyRelatedField(source='instrument_type', read_only=True)
    # instrument_object = serializers.PrimaryKeyRelatedField(source='instrument', read_only=True)
    # currency_object = serializers.PrimaryKeyRelatedField(source='currency', read_only=True)
    # counterparty_object = serializers.PrimaryKeyRelatedField(source='counterparty', read_only=True)
    # responsible_object = serializers.PrimaryKeyRelatedField(source='responsible', read_only=True)
    # portfolio_object = serializers.PrimaryKeyRelatedField(source='portfolio', read_only=True)
    # strategy1_object = serializers.PrimaryKeyRelatedField(source='strategy1', read_only=True)
    # strategy2_object = serializers.PrimaryKeyRelatedField(source='strategy2', read_only=True)
    # strategy3_object = serializers.PrimaryKeyRelatedField(source='strategy3', read_only=True)
    # daily_pricing_model_object = serializers.PrimaryKeyRelatedField(source='daily_pricing_model', read_only=True)
    # payment_size_detail_object = serializers.PrimaryKeyRelatedField(source='daily_pricing_model', read_only=True)
    # price_download_scheme_object = serializers.PrimaryKeyRelatedField(source='price_download_scheme', read_only=True)

    class Meta:
        model = TransactionTypeInput
        fields = [
            'id', 'name', 'verbose_name', 'value_type', 'content_type', 'order', 'can_recalculate', 'value_expr',
            'is_fill_from_context', 'value', 'account', 'instrument_type', 'instrument', 'currency', 'counterparty',
            'responsible', 'portfolio', 'strategy1', 'strategy2', 'strategy3', 'daily_pricing_model',
            'payment_size_detail', 'price_download_scheme', 'pricing_policy', 'periodicity', 'accrual_calculation_model'
            # 'account_object',
            # 'instrument_type_object',
            # 'instrument_object',
            # 'currency_object',
            # 'counterparty_object',
            # 'responsible_object',
            # 'portfolio_object',
            # 'strategy1_object',
            # 'strategy2_object',
            # 'strategy3_object',
            # 'daily_pricing_model_object',
            # 'payment_size_detail_object',
            # 'price_download_scheme_object',
        ]
        read_only_fields = ['order']

    def __init__(self, *args, **kwargs):
        super(TransactionTypeInputSerializer, self).__init__(*args, **kwargs)

        from poms.accounts.serializers import AccountViewSerializer
        from poms.instruments.serializers import InstrumentTypeViewSerializer, DailyPricingModelSerializer, \
            PaymentSizeDetailSerializer, PricingPolicySerializer
        from poms.currencies.serializers import CurrencyViewSerializer
        from poms.counterparties.serializers import CounterpartyViewSerializer, ResponsibleViewSerializer
        from poms.portfolios.serializers import PortfolioViewSerializer
        from poms.strategies.serializers import Strategy1ViewSerializer, Strategy2ViewSerializer, \
            Strategy3ViewSerializer
        from poms.integrations.serializers import PriceDownloadSchemeViewSerializer

        self.fields['account_object'] = AccountViewSerializer(source='account', read_only=True)

        self.fields['instrument_type_object'] = InstrumentTypeViewSerializer(source='instrument_type', read_only=True)
        self.fields['daily_pricing_model_object'] = DailyPricingModelSerializer(source='daily_pricing_model',
                                                                                read_only=True)
        self.fields['payment_size_detail_object'] = PaymentSizeDetailSerializer(source='payment_size_detail',
                                                                                read_only=True)

        self.fields['currency_object'] = CurrencyViewSerializer(source='currency', read_only=True)

        self.fields['counterparty_object'] = CounterpartyViewSerializer(source='counterparty', read_only=True)
        self.fields['responsible_object'] = ResponsibleViewSerializer(source='counterpresponsible', read_only=True)

        self.fields['portfolio_object'] = PortfolioViewSerializer(source='portfolio', read_only=True)

        self.fields['strategy1_object'] = Strategy1ViewSerializer(source='strategy1', read_only=True)
        self.fields['strategy2_object'] = Strategy2ViewSerializer(source='strategy2', read_only=True)
        self.fields['strategy3_object'] = Strategy3ViewSerializer(source='strategy3', read_only=True)

        self.fields['price_download_scheme_object'] = PriceDownloadSchemeViewSerializer(source='price_download_scheme',
                                                                                        read_only=True)
        self.fields['pricing_policy_object'] = PricingPolicySerializer(source="pricing_policy", read_only=True)

        self.fields['periodicity_object'] = PeriodicitySerializer(source="periodicity", read_only=True)
        self.fields['accrual_calculation_model_object'] = AccrualCalculationModelSerializer(
            source="accrual_calculation_model",
            read_only=True)

    def validate(self, data):
        value_type = data['value_type']
        if value_type == TransactionTypeInput.RELATION:
            content_type = data.get('content_type', None)
            if content_type is None:
                self.content_type.fail('required')
            else:
                model_class = content_type.model_class()
                if issubclass(model_class, Account):
                    target_attr = 'account'
                elif issubclass(model_class, Currency):
                    target_attr = 'currency'
                elif issubclass(model_class, Instrument):
                    target_attr = 'instrument'
                elif issubclass(model_class, InstrumentType):
                    target_attr = 'instrument_type'
                elif issubclass(model_class, Counterparty):
                    target_attr = 'counterparty'
                elif issubclass(model_class, Responsible):
                    target_attr = 'responsible'
                elif issubclass(model_class, Strategy1):
                    target_attr = 'strategy1'
                elif issubclass(model_class, Strategy2):
                    target_attr = 'strategy2'
                elif issubclass(model_class, Strategy3):
                    target_attr = 'strategy3'
                elif issubclass(model_class, DailyPricingModel):
                    target_attr = 'daily_pricing_model'
                elif issubclass(model_class, PaymentSizeDetail):
                    target_attr = 'payment_size_detail'
                elif issubclass(model_class, Portfolio):
                    target_attr = 'portfolio'
                elif issubclass(model_class, PriceDownloadScheme):
                    target_attr = 'price_download_scheme'
                elif issubclass(model_class, PricingPolicy):
                    target_attr = 'pricing_policy'
                elif issubclass(model_class, Periodicity):
                    target_attr = 'periodicity'
                elif issubclass(model_class, AccrualCalculationModel):
                    target_attr = 'accrual_calculation_model'
                elif issubclass(model_class, EventClass):
                    target_attr = 'event_class'
                elif issubclass(model_class, NotificationClass):
                    target_attr = 'notification_class'
                else:
                    raise ValidationError('Unknown content_type')

                attrs = ['account', 'instrument_type', 'instrument', 'currency', 'counterparty', 'responsible',
                         'portfolio', 'strategy1', 'strategy2', 'strategy3', 'daily_pricing_model',
                         'payment_size_detail', 'price_download_scheme', 'pricing_policy', 'periodicity',
                         'accrual_calculation_model']

                for attr in attrs:
                    if attr != target_attr:
                        data[attr] = None
        return data


class TransactionTypeInputViewSerializer(serializers.ModelSerializer):
    content_type = ReadOnlyContentTypeField()

    class Meta:
        model = TransactionTypeInput
        fields = [
            'id', 'name', 'verbose_name', 'value_type', 'content_type', 'order',
        ]
        read_only_fields = fields


class TransactionTypeActionInstrumentSerializer(serializers.ModelSerializer):
    user_code = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, allow_blank=True, default='')
    name = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, allow_blank=True, default='')
    public_name = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, allow_blank=True, default='')
    short_name = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, allow_blank=True, default='')
    notes = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, allow_blank=True, default='')

    instrument_type = InstrumentTypeField(required=False, allow_null=True)
    instrument_type_input = TransactionInputField(required=False, allow_null=True)
    pricing_currency = CurrencyField(required=False, allow_null=True)
    pricing_currency_input = TransactionInputField(required=False, allow_null=True)
    price_multiplier = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, default="1.0")
    accrued_currency = CurrencyField(required=False, allow_null=True)
    accrued_currency_input = TransactionInputField(required=False, allow_null=True)
    accrued_multiplier = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, default="1.0")
    default_price = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, default="0.0")
    default_accrued = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, default="0.0")
    user_text_1 = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, allow_blank=True, default='')
    user_text_2 = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, allow_blank=True, default='')
    user_text_3 = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, allow_blank=True, default='')

    reference_for_pricing = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, allow_blank=True,
                                            default='')
    daily_pricing_model_input = TransactionInputField(required=False, allow_null=True)
    payment_size_detail_input = TransactionInputField(required=False, allow_null=True)
    price_download_scheme = PriceDownloadSchemeField(required=False, allow_null=True)
    price_download_scheme_input = TransactionInputField(required=False, allow_null=True)

    maturity_date = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, allow_blank=True)
    maturity_price = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, default="0.0")

    # instrument_type_object = serializers.PrimaryKeyRelatedField(source='instrument_type', read_only=True)
    # pricing_currency_object = serializers.PrimaryKeyRelatedField(source='pricing_currency', read_only=True)
    # accrued_currency_object = serializers.PrimaryKeyRelatedField(source='accrued_currency', read_only=True)
    # daily_pricing_model_object = serializers.PrimaryKeyRelatedField(source='daily_pricing_model', read_only=True)
    # payment_size_detail_object = serializers.PrimaryKeyRelatedField(source='daily_pricing_model', read_only=True)
    # price_download_scheme_object = serializers.PrimaryKeyRelatedField(source='price_download_scheme', read_only=True)

    class Meta:
        model = TransactionTypeActionInstrument
        fields = [
            'user_code', 'name', 'public_name', 'short_name', 'notes',
            'instrument_type',
            'instrument_type_input',
            'pricing_currency',
            'pricing_currency_input',
            'price_multiplier',
            'accrued_currency',
            'accrued_currency_input',
            'accrued_multiplier',
            'payment_size_detail',
            'payment_size_detail_input',
            'default_price',
            'default_accrued',
            'user_text_1',
            'user_text_2',
            'user_text_3',
            'reference_for_pricing',
            'price_download_scheme',
            'price_download_scheme_input',
            'daily_pricing_model',
            'daily_pricing_model_input',
            'maturity_date',
            'maturity_price',

            'action_notes'

            # 'instrument_type_object',
            # 'pricing_currency_object',
            # 'accrued_currency_object',
            # 'payment_size_detail_object',
            # 'price_download_scheme_object',
            # 'daily_pricing_model_object',
        ]

    def __init__(self, *args, **kwargs):
        super(TransactionTypeActionInstrumentSerializer, self).__init__(*args, **kwargs)

        from poms.instruments.serializers import InstrumentTypeViewSerializer, DailyPricingModelSerializer, \
            PaymentSizeDetailSerializer
        from poms.currencies.serializers import CurrencyViewSerializer
        from poms.integrations.serializers import PriceDownloadSchemeViewSerializer

        self.fields['instrument_type_object'] = InstrumentTypeViewSerializer(source='instrument_type', read_only=True)
        self.fields['daily_pricing_model_object'] = DailyPricingModelSerializer(source='daily_pricing_model',
                                                                                read_only=True)
        self.fields['payment_size_detail_object'] = PaymentSizeDetailSerializer(source='payment_size_detail',
                                                                                read_only=True)

        self.fields['pricing_currency_object'] = CurrencyViewSerializer(source='pricing_currency', read_only=True)
        self.fields['accrued_currency_object'] = CurrencyViewSerializer(source='accrued_currency', read_only=True)

        self.fields['price_download_scheme_object'] = PriceDownloadSchemeViewSerializer(source='price_download_scheme',
                                                                                        read_only=True)


class TransactionTypeActionTransactionSerializer(serializers.ModelSerializer):
    instrument = InstrumentField(required=False, allow_null=True)
    instrument_input = TransactionInputField(required=False, allow_null=True)
    instrument_phantom = TransactionTypeActionInstrumentPhantomField(required=False, allow_null=True)
    transaction_currency = CurrencyField(required=False, allow_null=True)
    transaction_currency_input = TransactionInputField(required=False, allow_null=True)
    position_size_with_sign = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, default="0.0")
    settlement_currency = CurrencyField(required=False, allow_null=True)
    settlement_currency_input = TransactionInputField(required=False, allow_null=True)
    cash_consideration = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, default="0.0")
    principal_with_sign = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, default="0.0")
    carry_with_sign = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, default="0.0")
    overheads_with_sign = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, default="0.0")
    portfolio = PortfolioField(required=False, allow_null=True)
    portfolio_input = TransactionInputField(required=False, allow_null=True)
    account_position = AccountField(required=False, allow_null=True)
    account_position_input = TransactionInputField(required=False, allow_null=True)
    account_cash = AccountField(required=False, allow_null=True)
    account_cash_input = TransactionInputField(required=False, allow_null=True)
    account_interim = AccountField(required=False, allow_null=True)
    account_interim_input = TransactionInputField(required=False, allow_null=True)
    accounting_date = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, default="now()")
    cash_date = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, default="now()")
    strategy1_position = Strategy1Field(required=False, allow_null=True)
    strategy1_position_input = TransactionInputField(required=False, allow_null=True)
    strategy1_cash = Strategy1Field(required=False, allow_null=True)
    strategy1_cash_input = TransactionInputField(required=False, allow_null=True)
    strategy2_position = Strategy2Field(required=False, allow_null=True)
    strategy2_position_input = TransactionInputField(required=False, allow_null=True)
    strategy2_cash = Strategy2Field(required=False, allow_null=True)
    strategy2_cash_input = TransactionInputField(required=False, allow_null=True)
    strategy3_position = Strategy3Field(required=False, allow_null=True)
    strategy3_position_input = TransactionInputField(required=False, allow_null=True)
    strategy3_cash = Strategy3Field(required=False, allow_null=True)
    strategy3_cash_input = TransactionInputField(required=False, allow_null=True)
    responsible = ResponsibleField(required=False, allow_null=True)
    responsible_input = TransactionInputField(required=False, allow_null=True)
    counterparty = CounterpartyField(required=False, allow_null=True)
    counterparty_input = TransactionInputField(required=False, allow_null=True)
    linked_instrument = InstrumentField(required=False, allow_null=True)
    linked_instrument_input = TransactionInputField(required=False, allow_null=True)
    linked_instrument_phantom = TransactionTypeActionInstrumentPhantomField(required=False, allow_null=True)
    allocation_balance = InstrumentField(required=False, allow_null=True)
    allocation_balance_input = TransactionInputField(required=False, allow_null=True)
    allocation_balance_phantom = TransactionTypeActionInstrumentPhantomField(required=False, allow_null=True)
    allocation_pl = InstrumentField(required=False, allow_null=True)
    allocation_pl_input = TransactionInputField(required=False, allow_null=True)
    allocation_pl_phantom = TransactionTypeActionInstrumentPhantomField(required=False, allow_null=True)

    reference_fx_rate = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, default="0.0")
    factor = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, default="0.0")
    trade_price = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, default="0.0")
    position_amount = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, default="0.0")
    principal_amount = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, default="0.0")
    carry_amount = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, default="0.0")
    overheads = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, default="0.0")

    notes = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, allow_blank=True, default='')

    # transaction_class_object = TransactionClassSerializer(source='transaction_class', read_only=True)
    # instrument_object = serializers.PrimaryKeyRelatedField(source='instrument', read_only=True)
    # transaction_currency_object = serializers.PrimaryKeyRelatedField(source='transaction_currency', read_only=True)
    # settlement_currency_object = serializers.PrimaryKeyRelatedField(source='settlement_currency', read_only=True)
    # portfolio_object = serializers.PrimaryKeyRelatedField(source='portfolio', read_only=True)
    # account_position_object = serializers.PrimaryKeyRelatedField(source='account_position', read_only=True)
    # account_cash_object = serializers.PrimaryKeyRelatedField(source='account_cash', read_only=True)
    # account_interim_object = serializers.PrimaryKeyRelatedField(source='account_interim', read_only=True)
    # strategy1_position_object = serializers.PrimaryKeyRelatedField(source='strategy1_position', read_only=True)
    # strategy1_cash_object = serializers.PrimaryKeyRelatedField(source='strategy1_cash', read_only=True)
    # strategy2_position_object = serializers.PrimaryKeyRelatedField(source='strategy2_position', read_only=True)
    # strategy2_cash_object = serializers.PrimaryKeyRelatedField(source='strategy2_cash', read_only=True)
    # strategy3_position_object = serializers.PrimaryKeyRelatedField(source='strategy3_position', read_only=True)
    # strategy3_cash_object = serializers.PrimaryKeyRelatedField(source='strategy3_cash', read_only=True)
    # responsible_object = serializers.PrimaryKeyRelatedField(source='responsible', read_only=True)
    # counterparty_object = serializers.PrimaryKeyRelatedField(source='counterparty', read_only=True)

    class Meta:
        model = TransactionTypeActionTransaction
        fields = [
            'transaction_class',
            'instrument',
            'instrument_input',
            'instrument_phantom',
            'transaction_currency',
            'transaction_currency_input',
            'position_size_with_sign',
            'settlement_currency',
            'settlement_currency_input',
            'cash_consideration',
            'principal_with_sign',
            'carry_with_sign',
            'overheads_with_sign',
            'reference_fx_rate',
            'portfolio',
            'portfolio_input',
            'account_position',
            'account_position_input',
            'account_cash',
            'account_cash_input',
            'account_interim',
            'account_interim_input',
            'accounting_date',
            'cash_date',
            'strategy1_position',
            'strategy1_position_input',
            'strategy1_cash',
            'strategy1_cash_input',
            'strategy2_position',
            'strategy2_position_input',
            'strategy2_cash',
            'strategy2_cash_input',
            'strategy3_position',
            'strategy3_position_input',
            'strategy3_cash',
            'strategy3_cash_input',
            'linked_instrument',
            'linked_instrument_input',
            'linked_instrument_phantom',
            'allocation_balance',
            'allocation_balance_input',
            'allocation_balance_phantom',
            'allocation_pl',
            'allocation_pl_input',
            'allocation_pl_phantom',
            'responsible',
            'responsible_input',
            'counterparty',
            'counterparty_input',
            'factor',
            'trade_price',
            'position_amount',
            'principal_amount',
            'carry_amount',
            'overheads',
            'notes',

            'action_notes'

            # 'transaction_class_object',
            # 'portfolio_object',
            # 'instrument_object',
            # 'transaction_currency_object',
            # 'settlement_currency_object',
            # 'account_position_object',
            # 'account_cash_object',
            # 'account_interim_object',
            # 'strategy1_position_object',
            # 'strategy1_cash_object',
            # 'strategy2_position_object',
            # 'strategy2_cash_object',
            # 'strategy3_position_object',
            # 'strategy3_cash_object',
            # 'responsible_object',
            # 'counterparty_object',
        ]

    def __init__(self, *args, **kwargs):
        super(TransactionTypeActionTransactionSerializer, self).__init__(*args, **kwargs)

        from poms.portfolios.serializers import PortfolioViewSerializer
        from poms.instruments.serializers import InstrumentViewSerializer
        from poms.currencies.serializers import CurrencyViewSerializer
        from poms.accounts.serializers import AccountViewSerializer
        from poms.strategies.serializers import Strategy1ViewSerializer, Strategy2ViewSerializer, \
            Strategy3ViewSerializer
        from poms.counterparties.serializers import ResponsibleViewSerializer, CounterpartyViewSerializer

        self.fields['transaction_class_object'] = TransactionClassSerializer(source='transaction_class', read_only=True)

        self.fields['instrument_object'] = InstrumentViewSerializer(source='instrument', read_only=True)
        self.fields['transaction_currency_object'] = CurrencyViewSerializer(source='transaction_currency',
                                                                            read_only=True)
        self.fields['settlement_currency_object'] = CurrencyViewSerializer(source='settlement_currency', read_only=True)

        self.fields['portfolio_object'] = PortfolioViewSerializer(source='portfolio', read_only=True)

        self.fields['account_position_object'] = AccountViewSerializer(source='account_position', read_only=True)
        self.fields['account_cash_object'] = AccountViewSerializer(source='account_cash', read_only=True)
        self.fields['account_interim_object'] = AccountViewSerializer(source='account_interim', read_only=True)

        self.fields['strategy1_position_object'] = Strategy1ViewSerializer(source='strategy1_position', read_only=True)
        self.fields['strategy1_cash_object'] = Strategy1ViewSerializer(source='strategy1_cash', read_only=True)
        self.fields['strategy2_position_object'] = Strategy2ViewSerializer(source='strategy2_position', read_only=True)
        self.fields['strategy2_cash_object'] = Strategy2ViewSerializer(source='strategy2_cash', read_only=True)
        self.fields['strategy3_position_object'] = Strategy3ViewSerializer(source='strategy3_position', read_only=True)
        self.fields['strategy3_cash_object'] = Strategy3ViewSerializer(source='strategy3_cash', read_only=True)

        self.fields['responsible_object'] = ResponsibleViewSerializer(source='responsible', read_only=True)
        self.fields['counterparty_object'] = CounterpartyViewSerializer(source='counterparty', read_only=True)

        self.fields['linked_instrument_object'] = InstrumentViewSerializer(source='linked_instrument', read_only=True)
        self.fields['allocation_balance_object'] = InstrumentViewSerializer(source='allocation_balance', read_only=True)
        self.fields['allocation_pl_object'] = InstrumentViewSerializer(source='allocation_pl', read_only=True)


class TransactionTypeActionInstrumentFactorScheduleSerializer(serializers.ModelSerializer):
    instrument = InstrumentField(required=False, allow_null=True)
    instrument_input = TransactionInputField(required=False, allow_null=True)
    instrument_phantom = TransactionTypeActionInstrumentPhantomField(required=False, allow_null=True)

    effective_date = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, allow_blank=True)
    factor_value = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, default="0.0")

    class Meta:
        model = TransactionTypeActionInstrumentFactorSchedule
        fields = [
            'instrument',
            'instrument_input',
            'instrument_phantom',

            'effective_date',
            'factor_value'
        ]

    def __init__(self, *args, **kwargs):
        super(TransactionTypeActionInstrumentFactorScheduleSerializer, self).__init__(*args, **kwargs)

        from poms.instruments.serializers import InstrumentViewSerializer

        self.fields['instrument_object'] = InstrumentViewSerializer(source='instrument', read_only=True)


class TransactionTypeActionInstrumentManualPricingFormulaSerializer(serializers.ModelSerializer):
    instrument = InstrumentField(required=False, allow_null=True)
    instrument_input = TransactionInputField(required=False, allow_null=True)
    instrument_phantom = TransactionTypeActionInstrumentPhantomField(required=False, allow_null=True)

    pricing_policy = PricingPolicyField(required=False, allow_null=True)
    pricing_policy_input = TransactionInputField(required=False, allow_null=True)

    expr = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False)
    notes = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, default="")

    class Meta:
        model = TransactionTypeActionInstrumentFactorSchedule
        fields = [
            'instrument',
            'instrument_input',
            'instrument_phantom',

            'pricing_policy',
            'pricing_policy_input',

            'expr',
            'notes'
        ]

    def __init__(self, *args, **kwargs):
        super(TransactionTypeActionInstrumentManualPricingFormulaSerializer, self).__init__(*args, **kwargs)

        from poms.instruments.serializers import InstrumentViewSerializer, PricingPolicySerializer

        self.fields['instrument_object'] = InstrumentViewSerializer(source='instrument', read_only=True)
        self.fields['pricing_policy_object'] = PricingPolicySerializer(source='pricing_policy', read_only=True)


class TransactionTypeActionInstrumentAccrualCalculationSchedulesSerializer(serializers.ModelSerializer):
    instrument = InstrumentField(required=False, allow_null=True)
    instrument_input = TransactionInputField(required=False, allow_null=True)
    instrument_phantom = TransactionTypeActionInstrumentPhantomField(required=False, allow_null=True)

    accrual_calculation_model = AccrualCalculationModelField(required=False, allow_null=True)
    accrual_calculation_model_input = TransactionInputField(required=False, allow_null=True)

    periodicity = PeriodicityField(required=False, allow_null=True)
    periodicity_input = TransactionInputField(required=False, allow_null=True)

    accrual_start_date = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, allow_blank=True)
    first_payment_date = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, allow_blank=True)
    accrual_size = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, default="0.0")
    periodicity_n = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, allow_blank=True)
    notes = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, allow_blank=True)

    class Meta:
        model = TransactionTypeActionInstrumentFactorSchedule
        fields = [
            'instrument',
            'instrument_input',
            'instrument_phantom',

            'accrual_calculation_model',
            'accrual_calculation_model_input',

            'periodicity',
            'periodicity_input',

            'accrual_start_date',
            'first_payment_date',
            'accrual_size',
            'periodicity_n',
            'notes'
        ]

    def __init__(self, *args, **kwargs):
        super(TransactionTypeActionInstrumentAccrualCalculationSchedulesSerializer, self).__init__(*args, **kwargs)

        from poms.instruments.serializers import InstrumentViewSerializer

        self.fields['instrument_object'] = InstrumentViewSerializer(source='instrument', read_only=True)

        self.fields['periodicity_object'] = PeriodicitySerializer(source='periodicity', read_only=True)
        self.fields['accrual_calculation_model_object'] = AccrualCalculationModelSerializer(
            source='accrual_calculation_model', read_only=True)


class TransactionTypeActionInstrumentEventScheduleSerializer(serializers.ModelSerializer):
    instrument = InstrumentField(required=False, allow_null=True)
    instrument_input = TransactionInputField(required=False, allow_null=True)
    instrument_phantom = TransactionTypeActionInstrumentPhantomField(required=False, allow_null=True)

    periodicity = PeriodicityField(required=False, allow_null=True)
    periodicity_input = TransactionInputField(required=False, allow_null=True)

    notification_class = NotificationClassField(required=False, allow_null=True)
    notification_class_input = TransactionInputField(required=False, allow_null=True)

    event_class = EventClassField(required=False, allow_null=True)
    event_class_input = TransactionInputField(required=False, allow_null=True)

    effective_date = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, allow_blank=True)
    final_date = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, allow_blank=True)
    notify_in_n_days = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, allow_blank=True)
    periodicity_n = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, allow_blank=True)
    name = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, allow_blank=True)
    description = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, allow_blank=True)

    class Meta:
        model = TransactionTypeActionInstrumentEventSchedule
        fields = [
            'instrument',
            'instrument_input',
            'instrument_phantom',

            'periodicity',
            'periodicity_input',

            'notification_class',
            'notification_class_input',

            'event_class',
            'event_class_input',

            'effective_date',
            'final_date',
            'notify_in_n_days',
            'periodicity_n',
            'name',
            'description'
        ]

    def __init__(self, *args, **kwargs):
        super(TransactionTypeActionInstrumentEventScheduleSerializer, self).__init__(*args, **kwargs)

        from poms.instruments.serializers import InstrumentViewSerializer

        self.fields['instrument_object'] = InstrumentViewSerializer(source='instrument', read_only=True)
        self.fields['periodicity_object'] = PeriodicitySerializer(source='periodicity', read_only=True)
        self.fields['notification_class_object'] = NotificationClassSerializer(source='notification_class',
                                                                               read_only=True)
        self.fields['event_class_object'] = EventClassSerializer(source='event_class', read_only=True)


class TransactionTypeActionInstrumentEventScheduleActionSerializer(serializers.ModelSerializer):
    event_schedule = EventScheduleField(required=False, allow_null=True)
    event_schedule_input = TransactionInputField(required=False, allow_null=True)
    event_schedule_phantom = TransactionTypeActionInstrumentEventSchedulePhantomField(required=False, allow_null=True)

    transaction_type_from_instrument_type = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False,
                                                            allow_blank=True)

    is_book_automatic = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, allow_blank=True)
    is_sent_to_pending = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, allow_blank=True)

    button_position = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, allow_blank=True)

    text = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, allow_blank=True)

    class Meta:
        model = TransactionTypeActionInstrumentEventScheduleAction
        fields = [
            'event_schedule',
            'event_schedule_input',
            'event_schedule_phantom',

            'transaction_type_from_instrument_type',

            'is_book_automatic',
            'is_sent_to_pending',

            'button_position',

            'text'
        ]

    def __init__(self, *args, **kwargs):
        super(TransactionTypeActionInstrumentEventScheduleActionSerializer, self).__init__(*args, **kwargs)


class TransactionTypeActionSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False, allow_null=True)

    rebook_reaction = serializers.IntegerField(required=False, allow_null=True)

    transaction = TransactionTypeActionTransactionSerializer(source='transactiontypeactiontransaction', required=False,
                                                             allow_null=True)
    instrument = TransactionTypeActionInstrumentSerializer(source='transactiontypeactioninstrument', required=False,
                                                           allow_null=True)
    instrument_factor_schedule = TransactionTypeActionInstrumentFactorScheduleSerializer(
        source='transactiontypeactioninstrumentfactorschedule', required=False,
        allow_null=True)

    instrument_manual_pricing_formula = TransactionTypeActionInstrumentManualPricingFormulaSerializer(
        source='transactiontypeactioninstrumentmanualpricingformula', required=False,
        allow_null=True)

    instrument_accrual_calculation_schedules = TransactionTypeActionInstrumentAccrualCalculationSchedulesSerializer(
        source='transactiontypeactioninstrumentaccrualcalculationschedules', required=False, allow_null=True
    )

    instrument_event_schedule = TransactionTypeActionInstrumentEventScheduleSerializer(
        source='transactiontypeactioninstrumenteventschedule', required=False, allow_null=True
    )

    instrument_event_schedule_action = TransactionTypeActionInstrumentEventScheduleActionSerializer(
        source='transactiontypeactioninstrumenteventscheduleaction', required=False, allow_null=True
    )

    class Meta:
        model = TransactionTypeAction
        fields = ['id', 'order', 'rebook_reaction', 'action_notes', 'transaction', 'instrument',
                  'instrument_factor_schedule',
                  'instrument_manual_pricing_formula', 'instrument_accrual_calculation_schedules',
                  'instrument_event_schedule', 'instrument_event_schedule_action']

    def validate(self, attrs):
        # TODO: transaction or instrument present
        return attrs


class TransactionTypeSerializer(ModelWithObjectPermissionSerializer, ModelWithUserCodeSerializer,
                                ModelWithTagSerializer):
    master_user = MasterUserField()
    group = TransactionTypeGroupField(required=False, allow_null=False)
    date_expr = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, allow_blank=True,
                                allow_null=True, default='now()')
    display_expr = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, allow_blank=True,
                                   allow_null=True, default='')
    instrument_types = InstrumentTypeField(required=False, allow_null=True, many=True)
    portfolios = PortfolioField(required=False, allow_null=True, many=True)
    # tags = TagField(required=False, many=True, allow_null=True)
    # tags_object = TagViewSerializer(source='tags', many=True, read_only=True)
    inputs = TransactionTypeInputSerializer(required=False, many=True)
    actions = TransactionTypeActionSerializer(required=False, many=True, read_only=False)
    book_transaction_layout = serializers.JSONField(required=False, allow_null=True)

    group_object = TransactionTypeGroupViewSerializer(source='group', read_only=True)

    # instrument_types_object = serializers.PrimaryKeyRelatedField(source='instrument_types', many=True, read_only=True)
    # portfolios_object = serializers.PrimaryKeyRelatedField(source='portfolios', many=True, read_only=True)

    def __init__(self, *args, **kwargs):
        super(TransactionTypeSerializer, self).__init__(*args, **kwargs)

        from poms.instruments.serializers import InstrumentTypeViewSerializer
        from poms.portfolios.serializers import PortfolioViewSerializer

        self.fields['instrument_types_object'] = InstrumentTypeViewSerializer(source='instrument_types', many=True,
                                                                              read_only=True)
        self.fields['portfolios_object'] = PortfolioViewSerializer(source='portfolios', many=True, read_only=True)

    class Meta:
        model = TransactionType
        fields = [
            'id', 'master_user', 'group',
            'user_code', 'name', 'short_name', 'public_name', 'notes',
            'date_expr', 'display_expr',
            'is_valid_for_all_portfolios', 'is_valid_for_all_instruments', 'is_deleted',
            'book_transaction_layout',
            'instrument_types', 'portfolios',
            'inputs', 'actions',
            'group_object',
        ]

    def validate(self, attrs):
        # TODO: validate *_input...
        return attrs

    def create(self, validated_data):
        inputs = validated_data.pop('inputs', None)
        actions = validated_data.pop('actions', None)
        instance = super(TransactionTypeSerializer, self).create(validated_data)
        inputs = self.save_inputs(instance, inputs)
        self.save_actions(instance, actions, inputs)
        return instance

    def update(self, instance, validated_data):
        inputs = validated_data.pop('inputs', empty)
        actions = validated_data.pop('actions', empty)
        instance = super(TransactionTypeSerializer, self).update(instance, validated_data)
        if inputs is not empty:
            inputs = self.save_inputs(instance, inputs)
        if actions is not empty:
            actions = self.save_actions(instance, actions, inputs)
        if inputs is not empty:
            instance.inputs.exclude(id__in=[i.id for i in inputs]).delete()
        if actions is not empty:
            instance.actions.exclude(id__in=[a.id for a in actions]).delete()
        return instance

    def save_inputs(self, instance, inputs_data):
        cur_inputs = {i.id: i for i in instance.inputs.all()}
        new_inputs = []

        print('instance %s' % instance)

        for order, inp_data in enumerate(inputs_data):
            # name = inp_data['name']
            pk = inp_data.pop('id', None)
            inp = cur_inputs.pop(pk, None)
            if inp is None:
                inp = TransactionTypeInput(transaction_type=instance)
            inp.order = order
            for attr, value in inp_data.items():
                setattr(inp, attr, value)
            inp.save()
            new_inputs.append(inp)
        return new_inputs

    def save_actions_instrument(self, instance, inputs, actions, existed_actions, actions_data):

        for order, action_data in enumerate(actions_data):
            pk = action_data.pop('id', None)
            action = existed_actions.get(pk, None)

            action_instrument_data = action_data.get('instrument', action_data.get('transactiontypeactioninstrument'))
            if action_instrument_data:
                for attr, value in action_instrument_data.items():
                    if attr.endswith('_input') and value:
                        try:
                            action_instrument_data[attr] = inputs[value]
                        except KeyError:
                            raise ValidationError('Invalid input "%s"' % value)

                action_instrument = None
                if action:
                    try:
                        action_instrument = action.transactiontypeactioninstrument
                    except ObjectDoesNotExist:
                        pass
                if action_instrument is None:
                    action_instrument = TransactionTypeActionInstrument(transaction_type=instance)

                action_instrument.order = order
                action_instrument.rebook_reaction = action_data.get('rebook_reaction',
                                                                    action_instrument.rebook_reaction)
                action_instrument.action_notes = action_data.get('action_notes', action_instrument.action_notes)
                for attr, value in action_instrument_data.items():
                    setattr(action_instrument, attr, value)

                action_instrument.save()
                actions[order] = action_instrument

    def save_actions_transaction(self, instance, inputs, actions, existed_actions, actions_data):

        for order, action_data in enumerate(actions_data):
            pk = action_data.pop('id', None)
            action = existed_actions.get(pk, None)
            action_transaction_data = action_data.get('transaction',
                                                      action_data.get('transactiontypeactiontransaction'))

            if action_transaction_data:
                for attr, value in action_transaction_data.items():
                    if attr.endswith('_input') and value:
                        try:
                            action_transaction_data[attr] = inputs[value]
                        except KeyError:
                            raise ValidationError('Invalid input "%s"' % value)
                    if attr == 'instrument_phantom' and value is not None:
                        try:
                            action_transaction_data[attr] = actions[value]
                        except IndexError:
                            raise ValidationError('Invalid action order "%s"' % value)

                    if attr == 'linked_instrument_phantom' and value is not None:
                        try:
                            action_transaction_data[attr] = actions[value]
                        except IndexError:
                            raise ValidationError('Invalid action order "%s"' % value)

                    if attr == 'allocation_balance_phantom' and value is not None:
                        try:
                            action_transaction_data[attr] = actions[value]
                        except IndexError:
                            raise ValidationError('Invalid action order "%s"' % value)

                    if attr == 'allocation_pl_phantom' and value is not None:
                        try:
                            action_transaction_data[attr] = actions[value]
                        except IndexError:
                            raise ValidationError('Invalid action order "%s"' % value)

                action_transaction = None
                if action:
                    try:
                        action_transaction = action.transactiontypeactiontransaction
                    except ObjectDoesNotExist:
                        pass
                if action_transaction is None:
                    action_transaction = TransactionTypeActionTransaction(transaction_type=instance)

                action_transaction.order = order
                action_transaction.rebook_reaction = action_data.get('rebook_reaction',
                                                                     action_transaction.rebook_reaction)
                action_transaction.action_notes = action_data.get('action_notes', action_transaction.action_notes)
                for attr, value in action_transaction_data.items():
                    setattr(action_transaction, attr, value)

                action_transaction.save()
                actions[order] = action_transaction

    def save_actions_instrument_factor_schedule(self, instance, inputs, actions, existed_actions, actions_data):

        for order, action_data in enumerate(actions_data):
            pk = action_data.pop('id', None)
            action = existed_actions.get(pk, None)

            item_data = action_data.get('instrument_factor_schedule', action_data.get(
                'transactiontypeactioninstrumentfactorschedule'))
            if item_data:
                for attr, value in item_data.items():
                    if attr.endswith('_input') and value:
                        try:
                            item_data[attr] = inputs[value]
                        except KeyError:
                            raise ValidationError('Invalid input "%s"' % value)

                    if attr == 'instrument_phantom' and value is not None:
                        try:
                            item_data[attr] = actions[value]
                        except IndexError:
                            raise ValidationError('Invalid action order "%s"' % value)

                item = None
                if action:
                    try:
                        item = action.transactiontypeactioninstrumentfactorschedule
                    except ObjectDoesNotExist:
                        pass
                if item is None:
                    item = TransactionTypeActionInstrumentFactorSchedule(
                        transaction_type=instance)

                item.order = order
                item.rebook_reaction = action_data.get('rebook_reaction', item.rebook_reaction)
                item.action_notes = action_data.get('action_notes',
                                                    item.action_notes)
                for attr, value in item_data.items():
                    setattr(item, attr, value)

                item.save()
                actions[order] = item

    def save_actions_instrument_manual_pricing_formula(self, instance, inputs, actions, existed_actions, actions_data):

        for order, action_data in enumerate(actions_data):
            pk = action_data.pop('id', None)
            action = existed_actions.get(pk, None)

            item_data = action_data.get('instrument_manual_pricing_formula',
                                        action_data.get(
                                            'transactiontypeactioninstrumentmanualpricingformula'))
            if item_data:
                for attr, value in item_data.items():
                    if attr.endswith('_input') and value:
                        try:
                            item_data[attr] = inputs[value]
                        except KeyError:
                            raise ValidationError('Invalid input "%s"' % value)

                    if attr == 'instrument_phantom' and value is not None:
                        try:
                            item_data[attr] = actions[value]
                        except IndexError:
                            raise ValidationError('Invalid action order "%s"' % value)

                item = None
                if action:
                    try:
                        item = action.transactiontypeactioninstrumentmanualpricingformula
                    except ObjectDoesNotExist:
                        pass
                if item is None:
                    item = TransactionTypeActionInstrumentManualPricingFormula(
                        transaction_type=instance)

                item.order = order
                item.rebook_reaction = action_data.get('rebook_reaction', item.rebook_reaction)
                item.action_notes = action_data.get('action_notes',
                                                    item.action_notes)
                for attr, value in item_data.items():
                    setattr(item, attr, value)

                item.save()
                actions[order] = item

    def save_actions_instrument_accrual_calculation_schedule(self, instance, inputs, actions, existed_actions,
                                                             actions_data):

        for order, action_data in enumerate(actions_data):
            pk = action_data.pop('id', None)
            action = existed_actions.get(pk, None)

            item_data = action_data.get('instrument_accrual_calculation_schedules',
                                        action_data.get(
                                            'transactiontypeactioninstrumentaccrualcalculationschedules'))
            if item_data:
                for attr, value in item_data.items():
                    if attr.endswith('_input') and value:
                        try:
                            item_data[attr] = inputs[value]
                        except KeyError:
                            raise ValidationError('Invalid input "%s"' % value)

                    if attr == 'instrument_phantom' and value is not None:
                        try:
                            item_data[attr] = actions[value]
                        except IndexError:
                            raise ValidationError('Invalid action order "%s"' % value)

                item = None
                if action:
                    try:
                        item = action.transactiontypeactioninstrumentaccrualcalculationschedules
                    except ObjectDoesNotExist:
                        pass
                if item is None:
                    item = TransactionTypeActionInstrumentAccrualCalculationSchedules(
                        transaction_type=instance)

                item.order = order
                item.rebook_reaction = action_data.get('rebook_reaction', item.rebook_reaction)
                item.action_notes = action_data.get('action_notes',
                                                    item.action_notes)
                for attr, value in item_data.items():
                    setattr(item, attr, value)

                item.save()
                actions[order] = item

    def save_actions_instrument_event_schedule(self, instance, inputs, actions, existed_actions,
                                               actions_data):

        for order, action_data in enumerate(actions_data):
            pk = action_data.pop('id', None)
            action = existed_actions.get(pk, None)

            item_data = action_data.get('instrument_event_schedule',
                                        action_data.get(
                                            'transactiontypeactioninstrumenteventschedule'))
            if item_data:
                for attr, value in item_data.items():
                    if attr.endswith('_input') and value:
                        try:
                            item_data[attr] = inputs[value]
                        except KeyError:
                            raise ValidationError('Invalid input "%s"' % value)

                    if attr == 'instrument_phantom' and value is not None:
                        try:
                            item_data[attr] = actions[value]
                        except IndexError:
                            raise ValidationError('Invalid action order "%s"' % value)

                item = None
                if action:
                    try:
                        item = action.transactiontypeactioninstrumenteventschedule
                    except ObjectDoesNotExist:
                        pass
                if item is None:
                    item = TransactionTypeActionInstrumentEventSchedule(
                        transaction_type=instance)

                item.order = order
                item.rebook_reaction = action_data.get('rebook_reaction', item.rebook_reaction)
                item.action_notes = action_data.get('action_notes', item.action_notes)
                for attr, value in item_data.items():
                    setattr(item, attr, value)

                item.save()
                actions[order] = item

    def save_actions_instrument_event_schedule_action(self, instance, inputs, actions, existed_actions,
                                                      actions_data):

        for order, action_data in enumerate(actions_data):
            pk = action_data.pop('id', None)
            action = existed_actions.get(pk, None)

            item_data = action_data.get('instrument_event_schedule_action',
                                        action_data.get(
                                            'transactiontypeactioninstrumenteventscheduleaction'))
            if item_data:
                for attr, value in item_data.items():
                    if attr.endswith('_input') and value:
                        try:
                            item_data[attr] = inputs[value]
                        except KeyError:
                            raise ValidationError('Invalid input "%s"' % value)

                    if attr == 'event_schedule_phantom' and value is not None:
                        try:
                            item_data[attr] = actions[value]
                        except IndexError:
                            raise ValidationError('Invalid action order "%s"' % value)

                item = None
                if action:
                    try:
                        item = action.transactiontypeactioninstrumenteventscheduleaction
                    except ObjectDoesNotExist:
                        pass
                if item is None:
                    item = TransactionTypeActionInstrumentEventScheduleAction(
                        transaction_type=instance)

                item.order = order
                item.rebook_reaction = action_data.get('rebook_reaction', item.rebook_reaction)
                item.action_notes = action_data.get('action_notes', item.action_notes)
                for attr, value in item_data.items():
                    setattr(item, attr, value)

                item.save()
                actions[order] = item

    def save_actions(self, instance, actions_data, inputs):
        actions_qs = instance.actions.select_related(
            'transactiontypeactioninstrument',
            'transactiontypeactiontransaction',
            'transactiontypeactioninstrumentfactorschedule',
            'transactiontypeactioninstrumentmanualpricingformula',
            'transactiontypeactioninstrumentaccrualcalculationschedules',
            'transactiontypeactioninstrumenteventschedule',
            'transactiontypeactioninstrumenteventscheduleaction').order_by('order', 'id')
        existed_actions = {a.id: a for a in actions_qs}

        if inputs is None or inputs is empty:
            inputs = {i.name: i for i in instance.inputs.all()}
        else:
            inputs = {i.name: i for i in inputs}

        actions = [None for a in actions_data]

        self.save_actions_instrument(instance, inputs, actions, existed_actions, actions_data)

        self.save_actions_transaction(instance, inputs, actions, existed_actions, actions_data)

        self.save_actions_instrument_factor_schedule(instance, inputs, actions, existed_actions, actions_data)

        self.save_actions_instrument_manual_pricing_formula(instance, inputs, actions, existed_actions, actions_data)

        self.save_actions_instrument_accrual_calculation_schedule(instance, inputs, actions, existed_actions,
                                                                  actions_data)

        self.save_actions_instrument_event_schedule(instance, inputs, actions, existed_actions, actions_data)

        self.save_actions_instrument_event_schedule_action(instance, inputs, actions, existed_actions, actions_data)

        return actions


class TransactionTypeViewSerializer(ModelWithObjectPermissionSerializer):
    group = TransactionTypeGroupField(required=False, allow_null=False)
    group_object = TransactionTypeGroupViewSerializer(source='group', read_only=True)

    class Meta(ModelWithObjectPermissionSerializer.Meta):
        model = TransactionType
        fields = [
            'id', 'group', 'user_code', 'name', 'short_name', 'public_name', 'notes',
            'is_valid_for_all_portfolios', 'is_valid_for_all_instruments', 'is_deleted',
            'group_object',
        ]


# class TransactionTypeBulkObjectPermissionSerializer(AbstractBulkObjectPermissionSerializer):
#     content_objects = TransactionTypeField(many=True, allow_null=False, allow_empty=False)
#
#     class Meta:
#         model = TransactionType


# class TransactionClassifierSerializer(AbstractClassifierSerializer):
#     class Meta(AbstractClassifierSerializer.Meta):
#         model = TransactionClassifier
#
#
# class TransactionClassifierNodeSerializer(AbstractClassifierNodeSerializer):
#     class Meta(AbstractClassifierNodeSerializer.Meta):
#         model = TransactionClassifier
#
#
# class TransactionAttributeTypeSerializer(AbstractAttributeTypeSerializer):
#     classifiers = TransactionClassifierSerializer(required=False, allow_null=True, many=True)
#
#     class Meta(AbstractAttributeTypeSerializer.Meta):
#         model = TransactionAttributeType
#         fields = AbstractAttributeTypeSerializer.Meta.fields + ['classifiers']
#

# class TransactionAttributeTypeBulkObjectPermissionSerializer(AbstractBulkObjectPermissionSerializer):
#     content_objects = TransactionAttributeTypeField(many=True, allow_null=False, allow_empty=False)
#
#     class Meta:
#         model = TransactionAttributeType


# class TransactionAttributeSerializer(AbstractAttributeSerializer):
#     attribute_type = TransactionAttributeTypeField()
#     classifier = TransactionClassifierField(required=False, allow_null=True)
#
#     class Meta(AbstractAttributeSerializer.Meta):
#         model = TransactionAttribute
#         fields = AbstractAttributeSerializer.Meta.fields + ['attribute_type', 'classifier']


class TransactionSerializer(ModelWithAttributesSerializer):
    master_user = MasterUserField()
    complex_transaction = serializers.PrimaryKeyRelatedField(read_only=True)
    complex_transaction_order = serializers.IntegerField(read_only=True)
    instrument = InstrumentField(required=False, allow_null=True)
    transaction_currency = CurrencyField(default=CurrencyDefault(), required=False, allow_null=True)
    settlement_currency = CurrencyField(default=SystemCurrencyDefault())
    portfolio = PortfolioField(default=PortfolioDefault())
    account_cash = AccountField(default=AccountDefault())
    account_position = AccountField(default=AccountDefault())
    account_interim = AccountField(default=AccountDefault())
    strategy1_position = Strategy1Field(default=Strategy1Default())
    strategy1_cash = Strategy1Field(default=Strategy1Default())
    strategy2_position = Strategy2Field(default=Strategy2Default())
    strategy2_cash = Strategy2Field(default=Strategy2Default())
    strategy3_position = Strategy3Field(default=Strategy3Default())
    strategy3_cash = Strategy3Field(default=Strategy3Default())
    responsible = ResponsibleField(default=ResponsibleDefault())
    counterparty = CounterpartyField(default=CounterpartyDefault())
    linked_instrument = InstrumentField(default=InstrumentDefault())
    allocation_balance = InstrumentField(default=InstrumentDefault())
    allocation_pl = InstrumentField(default=InstrumentDefault())

    # transaction_class_object = TransactionClassSerializer(source='transaction_class', read_only=True)
    # transaction_currency_object = serializers.PrimaryKeyRelatedField(source='transaction_currency', read_only=True)
    # linked_instrument_object = serializers.PrimaryKeyRelatedField(source='instrument', read_only=True)
    # instrument_object = serializers.PrimaryKeyRelatedField(source='instrument', read_only=True)
    # settlement_currency_object = serializers.PrimaryKeyRelatedField(source='settlement_currency', read_only=True)
    # portfolio_object = serializers.PrimaryKeyRelatedField(source='portfolio', read_only=True)
    # account_cash_object = serializers.PrimaryKeyRelatedField(source='account_cash', read_only=True)
    # account_position_object = serializers.PrimaryKeyRelatedField(source='account_position', read_only=True)
    # account_interim_object = serializers.PrimaryKeyRelatedField(source='account_interim', read_only=True)
    # strategy1_position_object = serializers.PrimaryKeyRelatedField(source='strategy1_position', read_only=True)
    # strategy1_cash_object = serializers.PrimaryKeyRelatedField(source='strategy1_cash', read_only=True)
    # strategy2_position_object = serializers.PrimaryKeyRelatedField(source='strategy2_position', read_only=True)
    # strategy2_cash_object = serializers.PrimaryKeyRelatedField(source='strategy2_cash', read_only=True)
    # strategy3_position_object = serializers.PrimaryKeyRelatedField(source='strategy3_position', read_only=True)
    # strategy3_cash_object = serializers.PrimaryKeyRelatedField(source='strategy3_cash', read_only=True)
    # responsible_object = serializers.PrimaryKeyRelatedField(source='responsible', read_only=True)
    # counterparty_object = serializers.PrimaryKeyRelatedField(source='counterparty', read_only=True)

    # attributes = TransactionAttributeSerializer(many=True, required=False, allow_null=True)

    class Meta:
        model = Transaction
        fields = [
            'id',
            'master_user',
            'transaction_code',
            'complex_transaction',
            'complex_transaction_order',
            'transaction_class',
            'instrument',
            'transaction_currency',
            'position_size_with_sign',
            'settlement_currency',
            'cash_consideration',
            'principal_with_sign',
            'carry_with_sign',
            'overheads_with_sign',
            'reference_fx_rate',

            'accounting_date',
            'cash_date',
            'transaction_date',

            'portfolio',
            'account_cash',
            'account_position',
            'account_interim',
            'strategy1_position',
            'strategy1_cash',
            'strategy2_position',
            'strategy2_cash',
            'strategy3_position',
            'strategy3_cash',

            'responsible',
            'counterparty',
            'linked_instrument',
            'allocation_balance',
            'allocation_pl',

            'is_locked',
            'is_deleted',
            'factor',
            'trade_price',
            'position_amount',
            'principal_amount',
            'carry_amount',
            'overheads',
            'notes',

            # 'transaction_class_object',
            # 'transaction_currency_object',
            # 'linked_instrument_object',
            # 'instrument_object',
            # 'settlement_currency_object',
            # 'portfolio_object',
            # 'account_cash_object',
            # 'account_position_object',
            # 'account_interim_object',
            # 'strategy1_position_object',
            # 'strategy1_cash_object',
            # 'strategy2_position_object',
            # 'strategy2_cash_object',
            # 'strategy3_position_object',
            # 'strategy3_cash_object',
            # 'responsible_object',
            # 'counterparty_object',
        ]

    def __init__(self, *args, **kwargs):
        skip_complex_transaction = kwargs.pop('skip_complex_transaction', False)
        super(TransactionSerializer, self).__init__(*args, **kwargs)

        from poms.currencies.serializers import CurrencyViewSerializer
        from poms.instruments.serializers import InstrumentViewSerializer
        from poms.portfolios.serializers import PortfolioViewSerializer
        from poms.accounts.serializers import AccountViewSerializer
        from poms.strategies.serializers import Strategy1ViewSerializer, Strategy2ViewSerializer, \
            Strategy3ViewSerializer
        from poms.counterparties.serializers import ResponsibleViewSerializer, CounterpartyViewSerializer

        self.fields['transaction_class_object'] = TransactionClassSerializer(source='transaction_class', read_only=True)

        if not skip_complex_transaction:
            self.fields['complex_transaction_object'] = ComplexTransactionViewSerializer(source='complex_transaction',
                                                                                         read_only=True)

        self.fields['instrument_object'] = InstrumentViewSerializer(source='instrument', read_only=True)
        self.fields['transaction_currency_object'] = CurrencyViewSerializer(source='transaction_currency',
                                                                            read_only=True)
        self.fields['settlement_currency_object'] = CurrencyViewSerializer(source='settlement_currency', read_only=True)

        self.fields['portfolio_object'] = PortfolioViewSerializer(source='portfolio', read_only=True)

        self.fields['account_position_object'] = AccountViewSerializer(source='account_position', read_only=True)
        self.fields['account_cash_object'] = AccountViewSerializer(source='account_cash', read_only=True)
        self.fields['account_interim_object'] = AccountViewSerializer(source='account_interim', read_only=True)

        self.fields['strategy1_position_object'] = Strategy1ViewSerializer(source='strategy1_position', read_only=True)
        self.fields['strategy1_cash_object'] = Strategy1ViewSerializer(source='strategy1_cash', read_only=True)
        self.fields['strategy2_position_object'] = Strategy2ViewSerializer(source='strategy2_position', read_only=True)
        self.fields['strategy2_cash_object'] = Strategy2ViewSerializer(source='strategy2_cash', read_only=True)
        self.fields['strategy3_position_object'] = Strategy3ViewSerializer(source='strategy3_position', read_only=True)
        self.fields['strategy3_cash_object'] = Strategy3ViewSerializer(source='strategy3_cash', read_only=True)

        self.fields['responsible_object'] = ResponsibleViewSerializer(source='responsible', read_only=True)
        self.fields['counterparty_object'] = CounterpartyViewSerializer(source='counterparty', read_only=True)

        self.fields['linked_instrument_object'] = InstrumentViewSerializer(source='linked_instrument', read_only=True)
        self.fields['allocation_balance_object'] = InstrumentViewSerializer(source='allocation_balance', read_only=True)
        self.fields['allocation_pl_object'] = InstrumentViewSerializer(source='allocation_pl', read_only=True)


class TransactionTextRenderSerializer(TransactionSerializer):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('skip_complex_transaction', True)
        super(TransactionTextRenderSerializer, self).__init__(*args, **kwargs)


class ComplexTransactionMixin:
    # def __init__(self, *args, **kwargs):
    #     super(ComplexTransactionMixin, self).__init__(*args, **kwargs)
    #     self.fields['transactions_object2'] = TransactionSerializer(source='transactions', many=True, read_only=True)

    # def get_text(self, obj):
    #     if hasattr(obj, '_fake_transactions'):
    #         transactions = obj._fake_transactions
    #     else:
    #         transactions = obj.transactions.all()
    #
    #     try:
    #         return obj._cached_text
    #     except AttributeError:
    #         if obj.transaction_type_id is None:
    #             obj._cached_text = ''
    #         else:
    #             if obj.transaction_type.display_expr:
    #                 names = {
    #                     'complex_transaction': {
    #                         'code': obj.code,
    #                         'date': obj.date,
    #                     },
    #                     # 'transactions': formula.get_model_data(transactions, TransactionTextRenderSerializer, many=True,
    #                     #                                        context=self.context),
    #                     'transactions': transactions,
    #                 }
    #                 try:
    #                     obj._cached_text = formula.safe_eval(obj.transaction_type.display_expr, names=names,
    #                                                          context=self.context)
    #                 except formula.InvalidExpression:
    #                     obj._cached_text = '<InvalidExpression>'
    #             else:
    #                 obj._cached_text = ''
    #         return obj._cached_text

    def get_text(self, obj):
        return None

    def to_representation(self, instance):
        data = super(ComplexTransactionMixin, self).to_representation(instance)
        if 'text' in self.fields:
            if instance.transaction_type.display_expr:
                ctrn = formula.value_prepare(data)
                trns = ctrn.get('transactions', None)
                names = {
                    'complex_transaction': ctrn,
                    'transactions': trns,
                }
                try:
                    instance._cached_text = formula.safe_eval(instance.transaction_type.display_expr, names=names,
                                                              context=self.context)
                except formula.InvalidExpression:
                    instance._cached_text = '<InvalidExpression>'
            else:
                instance._cached_text = ''
            data['text'] = instance._cached_text
        return data


class ComplexTransactionSerializer(ComplexTransactionMixin, ModelWithAttributesSerializer):
    text = serializers.SerializerMethodField()
    master_user = MasterUserField()
    transaction_type = serializers.PrimaryKeyRelatedField(read_only=True)
    transactions = serializers.PrimaryKeyRelatedField(read_only=True, many=True)

    def __init__(self, *args, **kwargs):
        super(ComplexTransactionSerializer, self).__init__(*args, **kwargs)

        self.fields['transaction_type_object'] = TransactionTypeViewSerializer(
            source='transaction_type', read_only=True)

        self.fields['transactions_object'] = TransactionSerializer(
            source='transactions', many=True, read_only=True)

    class Meta:
        model = ComplexTransaction
        fields = [
            'id', 'date', 'status', 'code', 'text', 'is_deleted', 'transaction_type', 'transactions', 'master_user'
        ]


class ComplexTransactionEvalSerializer(ComplexTransactionSerializer):
    def __init__(self, *args, **kwargs):
        super(ComplexTransactionEvalSerializer, self).__init__(*args, **kwargs)
        self.fields.pop('text', None)


class ComplexTransactionViewSerializer(ComplexTransactionMixin, serializers.ModelSerializer):
    text = serializers.SerializerMethodField()
    transaction_type = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = ComplexTransaction
        fields = [
            'id', 'date', 'status', 'code', 'text', 'transaction_type',
        ]

    def __init__(self, *args, **kwargs):
        super(ComplexTransactionViewSerializer, self).__init__(*args, **kwargs)

        self.fields['transaction_type_object'] = TransactionTypeViewSerializer(
            source='transaction_type', read_only=True)

        self.fields['transactions_object'] = TransactionSerializer(
            source='transactions', many=True, read_only=True, skip_complex_transaction=True)

    def to_representation(self, instance):
        data = super(ComplexTransactionViewSerializer, self).to_representation(instance)
        data.pop('transactions_object', None)
        return data


# TransactionType processing -------------------------------------------------------------------------------------------


class TransactionTypeProcessValuesSerializer(serializers.Serializer):
    def __init__(self, **kwargs):
        super(TransactionTypeProcessValuesSerializer, self).__init__(**kwargs)

        from poms.accounts.serializers import AccountViewSerializer
        from poms.currencies.serializers import CurrencyViewSerializer
        from poms.instruments.serializers import InstrumentViewSerializer
        from poms.instruments.serializers import InstrumentTypeViewSerializer
        from poms.counterparties.serializers import CounterpartyViewSerializer
        from poms.counterparties.serializers import ResponsibleViewSerializer
        from poms.strategies.serializers import Strategy1ViewSerializer
        from poms.strategies.serializers import Strategy2ViewSerializer
        from poms.strategies.serializers import Strategy3ViewSerializer
        from poms.instruments.serializers import DailyPricingModelSerializer
        from poms.instruments.serializers import PaymentSizeDetailSerializer
        from poms.portfolios.serializers import PortfolioViewSerializer
        from poms.integrations.serializers import PriceDownloadSchemeViewSerializer
        from poms.instruments.serializers import PricingPolicyViewSerializer
        from poms.instruments.serializers import EventScheduleSerializer

        # now = timezone.now().date()
        # master_user = get_master_user_from_context(self.context)

        for i in self.instance.inputs:
            name = i.name
            name_object = '%s_object' % name
            field = None
            field_object = None

            if i.value_type == TransactionTypeInput.STRING:
                # field = serializers.CharField(required=True, label=i.name, help_text=i.verbose_name)
                field = serializers.CharField(required=False, allow_blank=True, allow_null=True,
                                              label=i.name, help_text=i.verbose_name)

            elif i.value_type == TransactionTypeInput.NUMBER:
                field = serializers.FloatField(required=False, allow_null=True,
                                               label=i.name, help_text=i.verbose_name)

            elif i.value_type == TransactionTypeInput.DATE:
                field = serializers.DateField(required=False, allow_null=True,
                                              label=i.name, help_text=i.verbose_name)

            elif i.value_type == TransactionTypeInput.RELATION:
                model_class = i.content_type.model_class()

                print('model_class %s' % model_class)

                if issubclass(model_class, Account):
                    field = AccountField(required=False, allow_null=True,
                                         label=i.name, help_text=i.verbose_name)
                    field_object = AccountViewSerializer(source=name, read_only=True)

                elif issubclass(model_class, Currency):
                    field = CurrencyField(required=False, allow_null=True,
                                          label=i.name, help_text=i.verbose_name)
                    field_object = CurrencyViewSerializer(source=name, read_only=True)

                elif issubclass(model_class, Instrument):
                    field = InstrumentField(required=False, allow_null=True,
                                            label=i.name, help_text=i.verbose_name)
                    field_object = InstrumentViewSerializer(source=name, read_only=True)

                elif issubclass(model_class, InstrumentType):
                    field = InstrumentTypeField(required=False, allow_null=True,
                                                label=i.name, help_text=i.verbose_name)
                    field_object = InstrumentTypeViewSerializer(source=name, read_only=True)

                elif issubclass(model_class, Counterparty):
                    field = CounterpartyField(required=False, allow_null=True,
                                              label=i.name, help_text=i.verbose_name)
                    field_object = CounterpartyViewSerializer(source=name, read_only=True)

                elif issubclass(model_class, Responsible):
                    field = ResponsibleField(required=False, allow_null=True,
                                             label=i.name, help_text=i.verbose_name)
                    field_object = ResponsibleViewSerializer(source=name, read_only=True)

                elif issubclass(model_class, Strategy1):
                    field = Strategy1Field(required=False, allow_null=True,
                                           label=i.name, help_text=i.verbose_name)
                    field_object = Strategy1ViewSerializer(source=name, read_only=True)

                elif issubclass(model_class, Strategy2):
                    field = Strategy2Field(required=False, allow_null=True,
                                           label=i.name, help_text=i.verbose_name)
                    field_object = Strategy2ViewSerializer(source=name, read_only=True)

                elif issubclass(model_class, Strategy3):
                    field = Strategy3Field(required=False, allow_null=True,
                                           label=i.name, help_text=i.verbose_name)
                    field_object = Strategy3ViewSerializer(source=name, read_only=True)

                elif issubclass(model_class, DailyPricingModel):
                    field = serializers.PrimaryKeyRelatedField(queryset=DailyPricingModel.objects,
                                                               required=False, allow_null=True,
                                                               label=i.name, help_text=i.verbose_name)
                    field_object = DailyPricingModelSerializer(source=name, read_only=True)

                elif issubclass(model_class, PaymentSizeDetail):
                    field = serializers.PrimaryKeyRelatedField(queryset=PaymentSizeDetail.objects,
                                                               required=False, allow_null=True,
                                                               label=i.name, help_text=i.verbose_name)
                    field_object = PaymentSizeDetailSerializer(source=name, read_only=True)

                elif issubclass(model_class, Portfolio):
                    field = PortfolioField(required=False, allow_null=True,
                                           label=i.name, help_text=i.verbose_name)
                    field_object = PortfolioViewSerializer(source=name, read_only=True)

                elif issubclass(model_class, PriceDownloadScheme):
                    field = PriceDownloadSchemeField(required=False, allow_null=True,
                                                     label=i.name, help_text=i.verbose_name)
                    field_object = PriceDownloadSchemeViewSerializer(source=name, read_only=True)

                elif issubclass(model_class, PricingPolicy):
                    field = PricingPolicyField(required=False, allow_null=True,
                                               label=i.name, help_text=i.verbose_name)
                    field_object = PricingPolicyViewSerializer(source=name, read_only=True)

                elif issubclass(model_class, Periodicity):
                    field = PeriodicityField(required=False, allow_null=True,
                                             label=i.name, help_text=i.verbose_name)
                    field_object = PeriodicitySerializer(source=name, read_only=True)

                elif issubclass(model_class, AccrualCalculationModel):
                    field = AccrualCalculationModelField(required=False, allow_null=True,
                                                         label=i.name, help_text=i.verbose_name)
                    field_object = AccrualCalculationModelSerializer(source=name, read_only=True)

                elif issubclass(model_class, EventClass):
                    field = EventClassField(required=False, allow_null=True,
                                            label=i.name, help_text=i.verbose_name)
                    field_object = EventClassSerializer(source=name, read_only=True)

                elif issubclass(model_class, NotificationClass):
                    field = NotificationClassField(required=False, allow_null=True,
                                                   label=i.name, help_text=i.verbose_name)
                    field_object = NotificationClassSerializer(source=name, read_only=True)

                elif issubclass(model_class, EventSchedule):
                    field = EventScheduleField(required=False, allow_null=True,
                                               label=i.name, help_text=i.verbose_name)
                    field_object = EventScheduleSerializer(source=name, read_only=True)

            if field:
                self.fields[name] = field
                if field_object:
                    self.fields[name_object] = field_object
            else:
                raise RuntimeError('Unknown value type %s' % i.value_type)


class PhantomInstrumentField(InstrumentField):
    def to_internal_value(self, data):
        pk = data
        if self.pk_field is not None:
            pk = self.pk_field.to_internal_value(data)
        if pk and pk < 0:
            return Instrument(id=pk)
        return super(PhantomInstrumentField, self).to_internal_value(data)


class PhantomTransactionSerializer(TransactionSerializer):
    def __init__(self, **kwargs):
        super(PhantomTransactionSerializer, self).__init__(**kwargs)
        self.fields['instrument'] = PhantomInstrumentField(required=False)
        self.fields.pop('attributes')


class TransactionTypeComplexTransactionSerializer(ComplexTransactionSerializer):
    date = serializers.DateField(required=False, allow_null=True)
    code = serializers.IntegerField(default=0, initial=0, min_value=0, required=False)
    status = serializers.ChoiceField(default=ComplexTransaction.PRODUCTION, initial=ComplexTransaction.PRODUCTION,
                                     required=False, choices=ComplexTransaction.STATUS_CHOICES)

    def __init__(self, *args, **kwargs):
        super(TransactionTypeComplexTransactionSerializer, self).__init__(*args, **kwargs)
        self.fields['is_deleted'].read_only = True


class TransactionTypeProcessSerializer(serializers.Serializer):
    def __init__(self, **kwargs):
        from poms.instruments.serializers import InstrumentSerializer

        kwargs['context'] = context = kwargs.get('context', {}) or {}
        super(TransactionTypeProcessSerializer, self).__init__(**kwargs)
        context['instance'] = self.instance

        self.fields['transaction_type'] = serializers.PrimaryKeyRelatedField(read_only=True)
        # self.fields['calculate'] = serializers.BooleanField(default=False, required=False)
        # self.fields['store'] = serializers.BooleanField(default=False, required=False)

        # self.fields['expressions'] = serializers.DictField(
        #     child=serializers.CharField(allow_null=False, allow_blank=False), allow_null=True, required=False)
        # self.fields['expressions_error'] = serializers.ReadOnlyField()
        # self.fields['expressions_result'] = serializers.ReadOnlyField()

        self.fields['process_mode'] = serializers.ChoiceField(
            required=False,
            allow_null=True,
            initial=TransactionTypeProcess.MODE_BOOK,
            default=TransactionTypeProcess.MODE_BOOK,
            choices=(
                (TransactionTypeProcess.MODE_BOOK, 'Book'),
                (TransactionTypeProcess.MODE_RECALCULATE, 'Recalculate fields values'),
            )
        )

        if self.instance:
            self.fields['values'] = TransactionTypeProcessValuesSerializer(instance=self.instance, required=False)

        if self.instance:
            recalculate_inputs = [(i.name, i.verbose_name) for i in self.instance.inputs if i.can_recalculate]
            self.fields['recalculate_inputs'] = serializers.MultipleChoiceField(required=False, allow_null=True,
                                                                                choices=recalculate_inputs)
        else:
            self.fields['recalculate_inputs'] = serializers.MultipleChoiceField(required=False, allow_null=True,
                                                                                choices=[])

        self.fields['has_errors'] = serializers.BooleanField(read_only=True)
        self.fields['value_errors'] = serializers.ReadOnlyField()
        self.fields['instruments_errors'] = serializers.ReadOnlyField()
        self.fields['complex_transaction_errors'] = serializers.ReadOnlyField()
        self.fields['transactions_errors'] = serializers.ReadOnlyField()
        self.fields['instruments'] = InstrumentSerializer(many=True, read_only=True, required=False, allow_null=True)
        self.fields['complex_transaction'] = TransactionTypeComplexTransactionSerializer(
            read_only=False, required=False, allow_null=True)
        # self.fields['transactions'] = PhantomTransactionSerializer(many=True, required=False, allow_null=True)

        self.fields['transaction_type_object'] = TransactionTypeSerializer(source='transaction_type', read_only=True)

        self.fields['book_transaction_layout'] = serializers.SerializerMethodField()

    def validate(self, attrs):
        if attrs['process_mode'] == TransactionTypeProcess.MODE_BOOK:
            values = attrs['values']
            fvalues = self.fields['values']
            errors = {}
            for k, v in values.items():
                if v is None or v == '':
                    try:
                        fvalues.fields[k].fail('required')
                    except ValidationError as e:
                        errors[k] = e.detail
            if errors:
                raise ValidationError({'values': errors})
        return attrs

    def get_book_transaction_layout(self, obj):
        return obj.transaction_type.book_transaction_layout

    def create(self, validated_data):
        return validated_data

    def update(self, instance, validated_data):

        print("Event book here? instance %s" % instance)
        print("Event book here? validated_data %s" % validated_data)

        for key, value in validated_data.items():
            if key not in ['complex_transaction', ]:
                setattr(instance, key, value)
        instance.value_errors = []

        print('instance.is_book %s' % instance.is_book)

        if instance.is_book:
            ctrn_values = validated_data.get('complex_transaction', None)
            if ctrn_values:
                ctrn_ser = ComplexTransactionSerializer(instance=instance.complex_transaction, context=self.context)
                ctrn_values = ctrn_values.copy()

                is_date_was_empty = False
                if not ctrn_values.get('date', None):
                    ctrn_values['date'] = datetime.date.min
                    is_date_was_empty = True

                if instance.complex_transaction:
                    ctrn = ctrn_ser.update(ctrn_ser.instance, ctrn_values)
                else:
                    ctrn = ctrn_ser.create(ctrn_values)

                if is_date_was_empty:
                    ctrn.date = None

                instance.complex_transaction = ctrn

        instance.process()

        if instance.is_book:
            self._save_inputs(instance)

        # if instance.calculate:
        #     instance.process()
        #
        #     if instance.store and not instance.has_errors:
        #         instruments_map = {}
        #         for instrument in instance.instruments:
        #             fake_id = instrument.id
        #             self._save_if_need(instrument)
        #             if fake_id:
        #                 instruments_map[fake_id] = instrument
        #         self._save_inputs(instance)
        #         if instance.transactions:
        #             self._save_if_need(instance.complex_transaction)
        #             for transaction in instance.transactions:
        #                 if transaction.instrument_id in instruments_map:
        #                     transaction.instrument = instruments_map[transaction.instrument_id]
        #                 self._save_if_need(transaction)
        # else:
        #     if instance.store:
        #         instruments_map = {}
        #         instruments_data = validated_data.get('instruments', None)
        #         if instruments_data:
        #             for instrument_data in instruments_data:
        #                 fake_id = instrument_data.pop('id', None)
        #                 instrument = Instrument(master_user=instance.transaction_type.master_user)
        #                 for attr, value in instrument_data.items():
        #                     setattr(instrument, attr, value)
        #                 instrument.save()
        #                 instance.instruments.append(instrument)
        #                 if fake_id:
        #                     instruments_map[fake_id] = instrument
        #
        #         self._save_inputs(instance)
        #         transactions_data = validated_data.get('transactions', None)
        #         if transactions_data:
        #             self._save_if_need(instance.complex_transaction)
        #             for transaction_data in transactions_data:
        #                 transaction = Transaction(master_user=instance.transaction_type.master_user)
        #                 transaction_data.pop('id', None)
        #                 for attr, value in transaction_data.items():
        #                     if attr == 'instrument':
        #                         value = value.id
        #                         if value in instruments_map:
        #                             value = instruments_map[value]
        #                         else:
        #                             value = None
        #                     setattr(transaction, attr, value)
        #                 transaction.complex_transaction = instance.complex_transaction
        #                 transaction.save()
        #                 instance.transactions.append(transaction)
        #
        # instance.complex_transaction._fake_transactions = instance.transactions

        # if not instance.has_errors and instance.transactions:
        #     for trn in instance.transactions:
        #         trn.calc_cash_by_formulas()

        # if not instance.store:
        #     instance.complex_transaction.id = instance.next_fake_id()
        #     instr_map = {}
        #     for instr in instance.instruments:
        #         pk = instance.next_fake_id()
        #         instr_map[instr.pk] = pk
        #         instr.pk = pk
        #     for trn in instance.transactions:
        #         pk = instance.next_fake_id()
        #         trn.pk = pk
        #         if trn.instrument_id in instr_map:
        #             trn.instrument_id = instr_map[trn.instrument_id]
        #         if trn.linked_instrument_id in instr_map:
        #             trn.linked_instrument_id = instr_map[trn.linked_instrument_id]
        #         if trn.allocation_balance_id in instr_map:
        #             trn.allocation_balance_id = instr_map[trn.allocation_balance_id]
        #         if trn.allocation_pl_id in instr_map:
        #             trn.allocation_pl_id = instr_map[trn.allocation_pl_id]

        return instance

    # def _save_if_need(self, obj):
    #     if obj.id is None or obj.id < 0:
    #         obj.id = None
    #         obj.save()

    def _save_inputs(self, instance):

        print('_save_unputs instance.values %s' % instance.values)

        instance.complex_transaction.inputs.all().delete()

        for ti in instance.transaction_type.inputs.all():
            val = instance.values.get(ti.name, None)

            ci = ComplexTransactionInput()
            ci.complex_transaction = instance.complex_transaction
            ci.transaction_type_input = ti

            if ti.value_type == TransactionTypeInput.STRING:
                if val is None:
                    val = ''
                ci.value_string = val
            elif ti.value_type == TransactionTypeInput.NUMBER:
                if val is None:
                    val = 0.0
                ci.value_float = val
            elif ti.value_type == TransactionTypeInput.DATE:
                if val is None:
                    val = datetime.date.min
                ci.value_date = val
            elif ti.value_type == TransactionTypeInput.RELATION:

                model_class = ti.content_type.model_class()

                if issubclass(model_class, Account):
                    ci.account = val
                elif issubclass(model_class, Currency):
                    ci.currency = val
                elif issubclass(model_class, Instrument):
                    ci.instrument = val
                elif issubclass(model_class, InstrumentType):
                    ci.instrument_type = val
                elif issubclass(model_class, Counterparty):
                    ci.counterparty = val
                elif issubclass(model_class, Responsible):
                    ci.responsible = val
                elif issubclass(model_class, Strategy1):
                    ci.strategy1 = val
                elif issubclass(model_class, Strategy2):
                    ci.strategy2 = val
                elif issubclass(model_class, Strategy3):
                    ci.strategy3 = val
                elif issubclass(model_class, DailyPricingModel):
                    ci.daily_pricing_model = val
                elif issubclass(model_class, PaymentSizeDetail):
                    ci.payment_size_detail = val
                elif issubclass(model_class, Portfolio):
                    ci.portfolio = val
                elif issubclass(model_class, PriceDownloadScheme):
                    ci.price_download_scheme = val
                elif issubclass(model_class, PricingPolicy):
                    ci.pricing_policy = val
                elif issubclass(model_class, Periodicity):
                    ci.periodicity = val
                elif issubclass(model_class, AccrualCalculationModel):
                    ci.accrual_calculation_model = val
                elif issubclass(model_class, EventClass):
                    ci.event_class = val
                elif issubclass(model_class, NotificationClass):
                    ci.notification_class = val

            ci.save()
