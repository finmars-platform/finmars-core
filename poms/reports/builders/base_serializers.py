from __future__ import unicode_literals

from django.utils.functional import cached_property
from rest_framework import serializers

from poms.accounts.serializers import AccountSerializer
from poms.counterparties.serializers import ResponsibleSerializer, \
    CounterpartySerializer
from poms.currencies.serializers import CurrencySerializer, CurrencyHistorySerializer
from poms.instruments.serializers import InstrumentSerializer, PriceHistorySerializer, \
    AccrualCalculationScheduleSerializer
from poms.obj_attrs.serializers import GenericAttributeTypeSerializer, GenericAttributeSerializer
from poms.portfolios.serializers import PortfolioSerializer
from poms.reports.serializers import BalanceReportCustomFieldSerializer, TransactionReportCustomFieldSerializer
from poms.strategies.serializers import Strategy1Serializer, Strategy2Serializer, Strategy3Serializer
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


class ReportGenericAttributeTypeSerializer(GenericAttributeTypeSerializer):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('read_only', True)

        super(ReportGenericAttributeTypeSerializer, self).__init__(*args, **kwargs)
        # self.fields.pop('user_object_permissions')
        # self.fields.pop('group_object_permissions')
        # self.fields.pop('object_permissions')


class ReportGenericAttributeSerializer(GenericAttributeSerializer):
    attribute_type_object = ReportGenericAttributeTypeSerializer(source='attribute_type', read_only=True)

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('read_only', True)

        super(ReportGenericAttributeSerializer, self).__init__(*args, **kwargs)

        # if self.context.get('attributes_hide_objects', False):
        #     self.fields.pop('attribute_type_object')
        #     self.fields.pop('classifier_object')

    # @cached_property
    # def _readable_fields(self):
    #     attributes_hide_objects = self.context.get('attributes_hide_objects', False)
    #     return [
    #         field for field in self.fields.values()
    #         if not field.write_only and (
    #             not attributes_hide_objects or field.field_name not in ('attribute_type_object', 'classifier_object'))
    #         ]


class ReportInstrumentSerializer(InstrumentSerializer):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('read_only', True)

        super(ReportInstrumentSerializer, self).__init__(*args, **kwargs)

        self.fields['attributes'] = ReportGenericAttributeSerializer(many=True, required=False, allow_null=True)

        self.fields.pop('manual_pricing_formulas')
        self.fields.pop('accrual_calculation_schedules')
        self.fields.pop('factor_schedules')
        self.fields.pop('event_schedules')

        # self.fields.pop('user_object_permissions')
        # self.fields.pop('group_object_permissions')
        # self.fields.pop('object _permissions')

        self.fields.pop('tags')
        self.fields.pop('tags_object')

        # self.fields.pop('payment_size_detail')
        # self.fields.pop('payment_size_detail_object')
        self.fields.pop('price_download_scheme')
        self.fields.pop('price_download_scheme_object')
        # self.fields.pop('daily_pricing_model')
        # self.fields.pop('daily_pricing_model_object')


class ReportAccrualCalculationScheduleSerializer(AccrualCalculationScheduleSerializer):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('read_only', True)

        super(AccrualCalculationScheduleSerializer, self).__init__(*args, **kwargs)


class ReportPriceHistorySerializer(PriceHistorySerializer):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('read_only', True)

        super(ReportPriceHistorySerializer, self).__init__(*args, **kwargs)

        self.fields.pop('instrument')
        self.fields.pop('instrument_object')

        self.fields.pop('pricing_policy')
        self.fields.pop('pricing_policy_object')


class ReportCurrencySerializer(CurrencySerializer):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('read_only', True)

        super(ReportCurrencySerializer, self).__init__(*args, **kwargs)

        # self.fields['attributes'] = ReportGenericAttributeSerializer(many=True, required=False, allow_null=True)
        self.fields.pop('attributes')

        self.fields.pop('tags')
        self.fields.pop('tags_object')

        self.fields.pop('price_download_scheme')
        self.fields.pop('price_download_scheme_object')
        self.fields.pop('daily_pricing_model')
        self.fields.pop('daily_pricing_model_object')

        self.fields.pop('is_default')


class ReportCurrencyHistorySerializer(CurrencyHistorySerializer):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('read_only', True)

        super(ReportCurrencyHistorySerializer, self).__init__(*args, **kwargs)

        self.fields.pop('currency')
        self.fields.pop('currency_object')

        self.fields.pop('pricing_policy')
        self.fields.pop('pricing_policy_object')


class ReportPortfolioSerializer(PortfolioSerializer):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('read_only', True)

        super(ReportPortfolioSerializer, self).__init__(*args, **kwargs)

        self.fields['attributes'] = ReportGenericAttributeSerializer(many=True, required=False, allow_null=True)

        self.fields.pop('accounts')
        self.fields.pop('accounts_object')
        self.fields.pop('responsibles')
        self.fields.pop('responsibles_object')
        self.fields.pop('counterparties')
        self.fields.pop('counterparties_object')
        self.fields.pop('transaction_types')
        self.fields.pop('transaction_types_object')

        # self.fields.pop('user_object_permissions')
        # self.fields.pop('group_object_permissions')
        # self.fields.pop('object_permissions')

        self.fields.pop('tags')
        self.fields.pop('tags_object')

        self.fields.pop('is_default')


class ReportAccountSerializer(AccountSerializer):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('read_only', True)

        super(ReportAccountSerializer, self).__init__(*args, **kwargs)

        self.fields['attributes'] = ReportGenericAttributeSerializer(many=True, required=False, allow_null=True)

        self.fields.pop('portfolios')
        self.fields.pop('portfolios_object')

        # self.fields.pop('user_object_permissions')
        # self.fields.pop('group_object_permissions')
        # self.fields.pop('object_permissions')

        self.fields.pop('tags')
        self.fields.pop('tags_object')

        self.fields.pop('is_default')


class ReportStrategy1Serializer(Strategy1Serializer):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('read_only', True)

        super(ReportStrategy1Serializer, self).__init__(*args, **kwargs)

        # self.fields.pop('user_object_permissions')
        # self.fields.pop('group_object_permissions')
        # self.fields.pop('object_permissions')

        self.fields.pop('tags')
        self.fields.pop('tags_object')

        # self.fields.pop('is_default')


class ReportStrategy2Serializer(Strategy2Serializer):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('read_only', True)

        super(ReportStrategy2Serializer, self).__init__(*args, **kwargs)

        # self.fields.pop('user_object_permissions')
        # self.fields.pop('group_object_permissions')
        # self.fields.pop('object_permissions')

        self.fields.pop('tags')
        self.fields.pop('tags_object')

        # self.fields.pop('is_default')


class ReportStrategy3Serializer(Strategy3Serializer):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('read_only', True)

        super(ReportStrategy3Serializer, self).__init__(*args, **kwargs)

        # self.fields.pop('user_object_permissions')
        # self.fields.pop('group_object_permissions')
        # self.fields.pop('object_permissions')

        self.fields.pop('tags')
        self.fields.pop('tags_object')

        # self.fields.pop('is_default')


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

