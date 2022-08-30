from __future__ import unicode_literals

from rest_framework import serializers

from poms.accounts.fields import AccountField
from poms.common.serializers import ModelWithUserCodeSerializer, ModelWithTimeStampSerializer
from poms.counterparties.fields import ResponsibleField, CounterpartyField
from poms.currencies.serializers import CurrencyViewSerializer
from poms.instruments.serializers import InstrumentViewSerializer, PricingPolicySerializer
from poms.obj_attrs.serializers import ModelWithAttributesSerializer
from poms.obj_perms.serializers import ModelWithObjectPermissionSerializer
from poms.portfolios.models import Portfolio, PortfolioRegister, PortfolioRegisterRecord
from poms.transactions.fields import TransactionTypeField

from poms.users.fields import MasterUserField



class PortfolioPortfolioRegisterSerializer(ModelWithObjectPermissionSerializer, ModelWithAttributesSerializer,
                                  ModelWithUserCodeSerializer, ModelWithTimeStampSerializer):

    master_user = MasterUserField()

    valuation_currency_object = serializers.PrimaryKeyRelatedField(source='valuation_currency', read_only=True)
    linked_instrument_object = serializers.PrimaryKeyRelatedField(source='linked_instrument', read_only=True)
    valuation_pricing_policy_object = serializers.PrimaryKeyRelatedField(source='valuation_pricing_policy', read_only=True)


    class Meta:
        model = PortfolioRegister
        fields = [
            'id', 'master_user', 'user_code', 'name', 'short_name', 'public_name', 'notes',
            'is_deleted',  'is_enabled',
            'linked_instrument', 'linked_instrument_object',
            'valuation_currency',  'valuation_currency_object',
            'valuation_pricing_policy', 'valuation_pricing_policy_object',
            'default_price'
        ]

    def __init__(self, *args, **kwargs):
        super(PortfolioPortfolioRegisterSerializer, self).__init__(*args, **kwargs)

        self.fields['valuation_currency_object'] = CurrencyViewSerializer(source='valuation_currency', read_only=True)

        self.fields['linked_instrument_object'] = InstrumentViewSerializer(source='linked_instrument', read_only=True)
        self.fields['valuation_pricing_policy_object'] = PricingPolicySerializer(source="valuation_pricing_policy", read_only=True)




class PortfolioSerializer(ModelWithObjectPermissionSerializer, ModelWithAttributesSerializer,
                          ModelWithUserCodeSerializer, ModelWithTimeStampSerializer):

    master_user = MasterUserField()
    accounts = AccountField(many=True, allow_null=True, required=False)
    responsibles = ResponsibleField(many=True, allow_null=True, required=False)
    counterparties = CounterpartyField(many=True, allow_null=True, required=False)
    transaction_types = TransactionTypeField(many=True, allow_null=True, required=False)

    portfolio_registers = PortfolioPortfolioRegisterSerializer(many=True, read_only=True)

    class Meta:
        model = Portfolio
        fields = [
            'id', 'master_user', 'user_code', 'name', 'short_name', 'public_name', 'notes', 'is_default',
            'is_deleted', 'accounts', 'responsibles', 'counterparties', 'transaction_types',
            'is_enabled', 'portfolio_registers'

        ]

    def __init__(self, *args, **kwargs):
        super(PortfolioSerializer, self).__init__(*args, **kwargs)

        from poms.accounts.serializers import AccountViewSerializer
        from poms.counterparties.serializers import ResponsibleViewSerializer, CounterpartyViewSerializer
        from poms.transactions.serializers import TransactionTypeViewSerializer

        self.fields['accounts_object'] = AccountViewSerializer(source='accounts', many=True, read_only=True)
        self.fields['responsibles_object'] = ResponsibleViewSerializer(source='responsibles', many=True, read_only=True)
        self.fields['counterparties_object'] = CounterpartyViewSerializer(source='counterparties', many=True,
                                                                          read_only=True)
        self.fields['transaction_types_object'] = TransactionTypeViewSerializer(source='transaction_types', many=True,
                                                                                read_only=True)


class PortfolioEvSerializer(ModelWithObjectPermissionSerializer, ModelWithAttributesSerializer, ModelWithUserCodeSerializer):
    master_user = MasterUserField()

    class Meta:
        model = Portfolio
        fields = [
            'id', 'master_user',
            'user_code', 'name', 'short_name', 'public_name', 'notes',
            'is_default', 'is_deleted', 'is_enabled'
        ]


class PortfolioLightSerializer(ModelWithObjectPermissionSerializer, ModelWithUserCodeSerializer):
    master_user = MasterUserField()

    class Meta:
        model = Portfolio
        fields = [
            'id', 'master_user', 'user_code', 'name', 'short_name', 'public_name',
            'is_default', 'is_deleted', 'is_enabled'
        ]


class PortfolioViewSerializer(ModelWithObjectPermissionSerializer):
    class Meta(ModelWithObjectPermissionSerializer.Meta):
        model = Portfolio
        fields = [
            'id', 'user_code', 'name', 'short_name', 'public_name',
        ]


class PortfolioGroupSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=256)


class PortfolioRegisterSerializer(ModelWithObjectPermissionSerializer, ModelWithAttributesSerializer,
                          ModelWithUserCodeSerializer, ModelWithTimeStampSerializer):

    master_user = MasterUserField()

    valuation_currency_object = serializers.PrimaryKeyRelatedField(source='valuation_currency', read_only=True)
    portfolio_object = serializers.PrimaryKeyRelatedField(source='portfolio', read_only=True)
    linked_instrument_object = serializers.PrimaryKeyRelatedField(source='linked_instrument', read_only=True)
    valuation_pricing_policy_object = serializers.PrimaryKeyRelatedField(source='valuation_pricing_policy', read_only=True)


    class Meta:
        model = PortfolioRegister
        fields = [
            'id', 'master_user', 'user_code', 'name', 'short_name', 'public_name', 'notes',
            'is_deleted',  'is_enabled',
            'portfolio', 'portfolio_object',
            'linked_instrument', 'linked_instrument_object',
            'valuation_currency',  'valuation_currency_object',
            'valuation_pricing_policy', 'valuation_pricing_policy_object',
            'default_price'
        ]

    def __init__(self, *args, **kwargs):
        super(PortfolioRegisterSerializer, self).__init__(*args, **kwargs)

        from poms.portfolios.serializers import PortfolioViewSerializer
        self.fields['valuation_currency_object'] = CurrencyViewSerializer(source='valuation_currency', read_only=True)
        self.fields['portfolio_object'] = PortfolioViewSerializer(source='portfolio', read_only=True)
        self.fields['linked_instrument_object'] = InstrumentViewSerializer(source='linked_instrument', read_only=True)
        self.fields['valuation_pricing_policy_object'] = PricingPolicySerializer(source="valuation_pricing_policy", read_only=True)



class PortfolioRegisterEvSerializer(ModelWithObjectPermissionSerializer, ModelWithAttributesSerializer, ModelWithUserCodeSerializer):
    master_user = MasterUserField()

    valuation_currency_object = serializers.PrimaryKeyRelatedField(source='valuation_currency', read_only=True)
    portfolio_object = serializers.PrimaryKeyRelatedField(source='portfolio', read_only=True)
    linked_instrument_object = serializers.PrimaryKeyRelatedField(source='linked_instrument', read_only=True)
    valuation_pricing_policy_object = serializers.PrimaryKeyRelatedField(source='valuation_pricing_policy', read_only=True)


    class Meta:
        model = PortfolioRegister
        fields = [
            'id', 'master_user',
            'user_code', 'name', 'short_name', 'public_name', 'notes',
            'is_deleted', 'is_enabled',
            'portfolio', 'linked_instrument', 'valuation_pricing_policy', 'valuation_currency',

            'valuation_currency_object', 'portfolio_object', 'linked_instrument_object', 'valuation_pricing_policy_object',
            'default_price'

        ]

    def __init__(self, *args, **kwargs):
        super(PortfolioRegisterEvSerializer, self).__init__(*args, **kwargs)

        from poms.portfolios.serializers import PortfolioViewSerializer
        self.fields['valuation_currency_object'] = CurrencyViewSerializer(source='valuation_currency', read_only=True)
        self.fields['portfolio_object'] = PortfolioViewSerializer(source='portfolio', read_only=True)
        self.fields['linked_instrument_object'] = InstrumentViewSerializer(source='linked_instrument', read_only=True)
        self.fields['valuation_pricing_policy_object'] = PricingPolicySerializer(source="valuation_pricing_policy", read_only=True)



class PortfolioRegisterRecordSerializer(ModelWithObjectPermissionSerializer, ModelWithTimeStampSerializer):

    master_user = MasterUserField()


    class Meta:
        model = PortfolioRegisterRecord
        fields = [
            'id', 'master_user',

            'portfolio', 'instrument', 'transaction_class', 'transaction_code', 'transaction_date', 'cash_amount', 'cash_currency',
            'fx_rate', 'cash_amount_valuation_currency', 'valuation_currency', 'nav_previous_day_valuation_currency',

            'n_shares_previous_day', 'n_shares_added',

            'dealing_price_valuation_currency', 'rolling_shares_of_the_day',
            'transaction', 'complex_transaction', 'portfolio_register'

        ]

    def __init__(self, *args, **kwargs):
        super(PortfolioRegisterRecordSerializer, self).__init__(*args, **kwargs)



class PortfolioRegisterRecordEvSerializer(ModelWithObjectPermissionSerializer, ModelWithTimeStampSerializer):
    master_user = MasterUserField()

    class Meta:
        model = PortfolioRegisterRecord
        fields = [
            'id', 'master_user',

            'portfolio', 'instrument', 'transaction_class', 'transaction_code', 'transaction_date', 'cash_amount', 'cash_currency',
            'fx_rate', 'cash_amount_valuation_currency', 'valuation_currency', 'nav_previous_day_valuation_currency',

            'n_shares_previous_day', 'n_shares_added',

            'dealing_price_valuation_currency', 'rolling_shares_of_the_day',
            'transaction', 'complex_transaction', 'portfolio_register'
        ]

    def __init__(self, *args, **kwargs):
        super(PortfolioRegisterRecordEvSerializer, self).__init__(*args, **kwargs)

        from poms.transactions.serializers import TransactionClassSerializer
        self.fields['transaction_class_object'] = TransactionClassSerializer(
            source='transaction_class', read_only=True)
        self.fields['portfolio_object'] = PortfolioViewSerializer(source='portfolio', read_only=True)
        self.fields['instrument_object'] = InstrumentViewSerializer(source='instrument', read_only=True)
        self.fields['portfolio_register_object'] = PortfolioRegisterSerializer(source='portfolio_register', read_only=True)

        self.fields['cash_currency_object'] = CurrencyViewSerializer(source='cash_currency', read_only=True)
        self.fields['valuation_currency_object'] = CurrencyViewSerializer(source='valuation_currency', read_only=True)

class CalculateRecordsSerializer(serializers.Serializer):

    portfolio_register_ids = serializers.CharField(allow_blank=False)

