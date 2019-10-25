from __future__ import unicode_literals

import time

from django.utils.functional import cached_property
from rest_framework import serializers

from poms.accounts.models import Account, AccountType
from poms.accounts.serializers import AccountSerializer
from poms.common.fields import ExpressionField
from poms.common.models import EXPRESSION_FIELD_LENGTH
from poms.common.serializers import ModelWithUserCodeSerializer
from poms.counterparties.serializers import ResponsibleSerializer, \
    CounterpartySerializer
from poms.currencies.models import CurrencyHistory, Currency
from poms.currencies.serializers import CurrencySerializer, CurrencyHistorySerializer
from poms.instruments.models import Instrument, InstrumentType, PriceHistory
from poms.instruments.serializers import InstrumentSerializer, PriceHistorySerializer, \
    AccrualCalculationScheduleSerializer, InstrumentTypeViewSerializer, PaymentSizeDetailSerializer, \
    DailyPricingModelSerializer, InstrumentClassSerializer
from poms.integrations.fields import PriceDownloadSchemeField
from poms.obj_attrs.fields import GenericClassifierField
from poms.obj_attrs.models import GenericAttribute, GenericAttributeType
from poms.obj_attrs.serializers import GenericAttributeTypeSerializer, GenericAttributeSerializer, \
    ModelWithAttributesSerializer, GenericClassifierSerializer, GenericClassifierWithoutChildrenSerializer, \
    GenericClassifierViewSerializer
from poms.portfolios.models import Portfolio
from poms.portfolios.serializers import PortfolioSerializer
from poms.reports.serializers import BalanceReportCustomFieldSerializer, TransactionReportCustomFieldSerializer
from poms.strategies.models import Strategy1, Strategy2, Strategy3
from poms.strategies.serializers import Strategy1Serializer, Strategy2Serializer, Strategy3Serializer, \
    Strategy2SubgroupViewSerializer, Strategy1SubgroupViewSerializer, Strategy3SubgroupViewSerializer
from poms.transactions.serializers import ComplexTransactionSerializer, TransactionTypeViewSerializer
from poms.users.fields import MasterUserField


# class CustomFieldViewSerializer(serializers.ModelSerializer):
#     master_user = MasterUserField()
#
#     class Meta:
#         model = CustomField
#         fields = [
#             'id', 'master_user', 'name', 'expr'
#         ]


# TODO IMPORTANT
# TODO HERE WE HAVE ONLY OBJECTS THAT ALREADY PASSED PERMISSIONS CHEC
# TODO SO, WE DEFINE HERE OWN SERIALIZERS WITHOUT ModelWithObjectPermissionSerializer

class ReportGenericAttributeTypeSerializer(ModelWithUserCodeSerializer):

    classifiers = GenericClassifierSerializer(required=False, allow_null=True, many=True)
    classifiers_flat = GenericClassifierWithoutChildrenSerializer(source='classifiers', read_only=True, many=True)

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('read_only', True)
        super(ReportGenericAttributeTypeSerializer, self).__init__(*args, **kwargs)

    class Meta:
        model = GenericAttributeType
        fields = ['id', 'user_code', 'name', 'short_name', 'public_name', 'notes',
                  'value_type', 'order', 'classifiers', 'classifiers_flat']

        read_only_fields = fields


class ReportGenericAttributeSerializer(serializers.ModelSerializer):

    attribute_type_object = ReportGenericAttributeTypeSerializer(source='attribute_type', read_only=True)
    classifier_object = GenericClassifierViewSerializer(source='classifier', read_only=True)

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('read_only', True)

        super(ReportGenericAttributeSerializer, self).__init__(*args, **kwargs)



    class Meta:
        model = GenericAttribute
        fields = [
            'id',  'value_string', 'value_float', 'value_date',
            'classifier', 'classifier_object',
            'attribute_type', 'attribute_type_object',
        ]

        read_only_fields = fields


class ReportAccrualCalculationScheduleSerializer(AccrualCalculationScheduleSerializer):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('read_only', True)

        super(AccrualCalculationScheduleSerializer, self).__init__(*args, **kwargs)


class ReportPriceHistorySerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('read_only', True)

        super(ReportPriceHistorySerializer, self).__init__(*args, **kwargs)

    class Meta:
        model = PriceHistory
        fields = [
            'id', 'instrument', 'pricing_policy',
            'date', 'principal_price', 'accrued_price'
        ],
        read_only_fields = fields


class ReportCurrencySerializer(ModelWithUserCodeSerializer, ModelWithAttributesSerializer):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('read_only', True)

        super(ReportCurrencySerializer, self).__init__(*args, **kwargs)

        self.fields['attributes'] = ReportGenericAttributeSerializer(many=True, required=False, allow_null=True)


    class Meta:
        model = Currency
        fields = [
            'id', 'user_code', 'name', 'short_name', 'notes',
            'reference_for_pricing', 'daily_pricing_model',
            'price_download_scheme', 'default_fx_rate',
        ]
        read_only_fields = fields


class ReportInstrumentTypeSerializer(ModelWithUserCodeSerializer):

    instrument_class_object = InstrumentClassSerializer(source='instrument_class', read_only=True)

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('read_only', True)

        super(ReportInstrumentTypeSerializer, self).__init__(*args, **kwargs)

    class Meta:
        model = InstrumentType
        fields = [
            'id', 'instrument_class', 'instrument_class_object',
            'user_code', 'name', 'short_name', 'public_name',
            'notes',
        ]
        read_only_fields = fields


class ReportInstrumentSerializer(ModelWithAttributesSerializer, ModelWithUserCodeSerializer):

    # instrument_type_object = ReportInstrumentTypeSerializer(source='instrument_type', read_only=True) # TODO Improve later, create separte Serializer without permission check

    # payment_size_detail_object = PaymentSizeDetailSerializer(source='payment_size_detail', read_only=True)
    # daily_pricing_model_object = DailyPricingModelSerializer(source='daily_pricing_model', read_only=True)

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('read_only', True)

        super(ReportInstrumentSerializer, self).__init__(*args, **kwargs)

        self.fields['attributes'] = ReportGenericAttributeSerializer(many=True, required=False, allow_null=True)


    class Meta:
        model = Instrument
        fields = [
            'id', 'instrument_type',  'user_code', 'name', 'short_name',
            'public_name', 'notes',
            'pricing_currency', 'price_multiplier',
            'accrued_currency',  'accrued_multiplier',
            'default_price', 'default_accrued',
            'user_text_1', 'user_text_2', 'user_text_3',
            'reference_for_pricing',
            'payment_size_detail',
            'daily_pricing_model',
            'maturity_date', 'maturity_price'

        ]
        read_only_fields = fields


class ReportCurrencyHistorySerializer(serializers.ModelSerializer):

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('read_only', True)

        super(ReportCurrencyHistorySerializer, self).__init__(*args, **kwargs)

    class Meta:
        model = CurrencyHistory
        fields = [
            'id', 'currency', 'pricing_policy', 'date', 'fx_rate'
        ]
        read_only_fields = fields


class ReportPortfolioSerializer(ModelWithAttributesSerializer, ModelWithUserCodeSerializer):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('read_only', True)

        super(ReportPortfolioSerializer, self).__init__(*args, **kwargs)

        self.fields['attributes'] = ReportGenericAttributeSerializer(many=True, required=False, allow_null=True)

    class Meta:
        model = Portfolio
        fields = [
            'id', 'user_code', 'name', 'short_name', 'public_name', 'notes',

        ]
        read_only_fields = fields


class ReportAccountTypeSerializer(ModelWithUserCodeSerializer):

    transaction_details_expr = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, allow_blank=True,
                                               allow_null=True, default='""')

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('read_only', True)

        super(ReportAccountTypeSerializer, self).__init__(*args, **kwargs)

    class Meta:
        model = AccountType
        fields = [
            'id', 'user_code', 'name', 'short_name', 'public_name', 'notes',
            'show_transaction_details', 'transaction_details_expr',
        ]
        read_only_fields = fields


class ReportAccountSerializer(ModelWithAttributesSerializer, ModelWithUserCodeSerializer):

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('read_only', True)

        super(ReportAccountSerializer, self).__init__(*args, **kwargs)

        self.fields['attributes'] = ReportGenericAttributeSerializer(many=True, required=False, allow_null=True)

    class Meta:
        model = Account
        fields = [
            'id', 'type', 'user_code', 'name', 'short_name', 'public_name',
            'notes',
        ]
        read_only_fields = fields


class ReportStrategy1Serializer(ModelWithUserCodeSerializer):

    # subgroup_object = Strategy1SubgroupViewSerializer(source='subgroup', read_only=True)

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('read_only', True)

        super(ReportStrategy1Serializer, self).__init__(*args, **kwargs)

    class Meta:
        model = Strategy1
        fields = [
            'id',  'subgroup', 'user_code', 'name', 'short_name', 'public_name', 'notes',
            # 'subgroup_object',
        ]
        read_only_fields = fields


class ReportStrategy2Serializer(ModelWithUserCodeSerializer):

    # subgroup_object = Strategy2SubgroupViewSerializer(source='subgroup', read_only=True)

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('read_only', True)

        super(ReportStrategy2Serializer, self).__init__(*args, **kwargs)

    class Meta:
        model = Strategy2
        fields = [
            'id',  'subgroup', 'user_code', 'name', 'short_name', 'public_name', 'notes',
            # 'subgroup_object',
        ]
        read_only_fields = fields


class ReportStrategy3Serializer(ModelWithUserCodeSerializer):

    # subgroup_object = Strategy3SubgroupViewSerializer(source='subgroup', read_only=True)

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('read_only', True)

        super(ReportStrategy3Serializer, self).__init__(*args, **kwargs)

    class Meta:
        model = Strategy3
        fields = [
            'id',  'subgroup', 'user_code', 'name', 'short_name', 'public_name', 'notes',
            # 'subgroup_object',
        ]
        read_only_fields = fields


class ReportResponsibleSerializer(ResponsibleSerializer):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('read_only', True)

        super(ReportResponsibleSerializer, self).__init__(*args, **kwargs)

        self.fields['attributes'] = ReportGenericAttributeSerializer(many=True, required=False, allow_null=True)

        self.fields.pop('portfolios')
        self.fields.pop('portfolios_object')

        # self.fields.pop('user_object_permissions')
        # self.fields.pop('group_object_permissions')
        # self.fields.pop('object_permissions')

        self.fields.pop('tags')
        self.fields.pop('tags_object')

        self.fields.pop('is_default')


class ReportCounterpartySerializer(CounterpartySerializer):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('read_only', True)

        super(ReportCounterpartySerializer, self).__init__(*args, **kwargs)

        self.fields['attributes'] = ReportGenericAttributeSerializer(many=True, required=False, allow_null=True)

        self.fields.pop('portfolios')
        self.fields.pop('portfolios_object')

        # self.fields.pop('user_object_permissions')
        # self.fields.pop('group_object_permissions')
        # self.fields.pop('object_permissions')

        self.fields.pop('tags')
        self.fields.pop('tags_object')

        self.fields.pop('is_default')


class ReportComplexTransactionSerializer(ComplexTransactionSerializer):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('read_only', True)

        super(ReportComplexTransactionSerializer, self).__init__(*args, **kwargs)

        # self.fields.pop('text')
        self.fields.pop('transactions')
        self.fields.pop('transactions_object')
        # self.fields.pop('transaction_type_object')
        # self.fields['transaction_type_object'] = TransactionTypeViewSerializer(source='transaction_type', read_only=True)

        self.fields['attributes'] = ReportGenericAttributeSerializer(many=True, required=False, allow_null=True)

        for k in list(self.fields.keys()):
            if str(k).endswith('_object'):
                self.fields.pop(k)

        self.fields['transaction_type_object'] = TransactionTypeViewSerializer(source='transaction_type', read_only=True)


class ReportItemBalanceReportCustomFieldSerializer(serializers.Serializer):
    custom_field = serializers.PrimaryKeyRelatedField(read_only=True)
    user_code = serializers.ReadOnlyField()
    value = serializers.ReadOnlyField()

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('read_only', True)

        super(ReportItemBalanceReportCustomFieldSerializer, self).__init__(*args, **kwargs)

        self.fields['custom_field_object'] = BalanceReportCustomFieldSerializer(source='custom_field', read_only=True)

    @cached_property
    def _readable_fields(self):
        custom_fields_hide_objects = self.context.get('custom_fields_hide_objects', False)
        return [
            field for field in self.fields.values()
            if not field.write_only and (
                not custom_fields_hide_objects or field.field_name not in ('custom_field_object',))
            ]


class ReportItemTransactionReportCustomFieldSerializer(serializers.Serializer):
    custom_field = serializers.PrimaryKeyRelatedField(read_only=True)
    user_code = serializers.ReadOnlyField()
    value = serializers.ReadOnlyField()

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('read_only', True)

        super(ReportItemTransactionReportCustomFieldSerializer, self).__init__(*args, **kwargs)

        self.fields['custom_field_object'] = TransactionReportCustomFieldSerializer(source='custom_field', read_only=True)

    @cached_property
    def _readable_fields(self):
        custom_fields_hide_objects = self.context.get('custom_fields_hide_objects', False)
        return [
            field for field in self.fields.values()
            if not field.write_only and (
                    not custom_fields_hide_objects or field.field_name not in ('custom_field_object',))
        ]

