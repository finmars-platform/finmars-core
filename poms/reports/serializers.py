from __future__ import unicode_literals

from rest_framework import serializers

from poms.common.fields import ExpressionField
from poms.common.models import EXPRESSION_FIELD_LENGTH
from poms.reports.models import BalanceReportCustomField, PLReportCustomField, TransactionReportCustomField

from poms.users.fields import MasterUserField


class BalanceReportCustomFieldSerializer(serializers.ModelSerializer):
    master_user = MasterUserField()
    expr = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, allow_blank=True, default='""')

    class Meta:
        model = BalanceReportCustomField
        fields = [
            'id', 'master_user', 'name', 'user_code', 'expr', 'value_type'
        ]


class PLReportCustomFieldSerializer(serializers.ModelSerializer):
    master_user = MasterUserField()
    expr = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, allow_blank=True, default='""')

    class Meta:
        model = PLReportCustomField
        fields = [
            'id', 'master_user', 'name', 'user_code', 'expr', 'value_type'
        ]


class TransactionReportCustomFieldSerializer(serializers.ModelSerializer):
    master_user = MasterUserField()
    expr = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, allow_blank=True, default='""')

    class Meta:
        model = TransactionReportCustomField
        fields = [
            'id', 'master_user', 'name', 'user_code', 'expr', 'value_type'
        ]

# class CustomFieldViewSerializer(serializers.ModelSerializer):
#     master_user = MasterUserField()
#
#     class Meta:
#         model = CustomField
#         fields = [
#             'id', 'master_user', 'name'
#         ]
#
#
# # Report --------
#
#
# class ReportGenericAttributeTypeSerializer(GenericAttributeTypeSerializer):
#     def __init__(self, *args, **kwargs):
#         kwargs.setdefault('read_only', True)
#
#         super(ReportGenericAttributeTypeSerializer, self).__init__(*args, **kwargs)
#         # self.fields.pop('user_object_permissions')
#         # self.fields.pop('group_object_permissions')
#         # self.fields.pop('object_permissions')
#
#
# class ReportGenericAttributeSerializer(GenericAttributeSerializer):
#     attribute_type_object = ReportGenericAttributeTypeSerializer(source='attribute_type', read_only=True)
#
#     def __init__(self, *args, **kwargs):
#         kwargs.setdefault('read_only', True)
#
#         super(ReportGenericAttributeSerializer, self).__init__(*args, **kwargs)
#
#         # if self.context.get('attributes_hide_objects', False):
#         #     self.fields.pop('attribute_type_object')
#         #     self.fields.pop('classifier_object')
#
#     @cached_property
#     def _readable_fields(self):
#         attributes_hide_objects = self.context.get('attributes_hide_objects', False)
#         return [
#             field for field in self.fields.values()
#             if not field.write_only and (
#                 not attributes_hide_objects or field.field_name not in ('attribute_type_object', 'classifier_object'))
#             ]
#
#
# class ReportInstrumentSerializer(InstrumentSerializer):
#     def __init__(self, *args, **kwargs):
#         kwargs.setdefault('read_only', True)
#
#         super(ReportInstrumentSerializer, self).__init__(*args, **kwargs)
#
#         self.fields['attributes'] = ReportGenericAttributeSerializer(many=True, required=False, allow_null=True)
#
#         self.fields.pop('manual_pricing_formulas')
#         self.fields.pop('accrual_calculation_schedules')
#         self.fields.pop('factor_schedules')
#         self.fields.pop('event_schedules')
#
#         # self.fields.pop('user_object_permissions')
#         # self.fields.pop('group_object_permissions')
#         # self.fields.pop('object _permissions')
#
#         self.fields.pop('tags')
#         self.fields.pop('tags_object')
#
#         self.fields.pop('payment_size_detail')
#         self.fields.pop('payment_size_detail_object')
#         self.fields.pop('price_download_scheme')
#         self.fields.pop('price_download_scheme_object')
#         self.fields.pop('daily_pricing_model')
#         self.fields.pop('daily_pricing_model_object')
#
#
# class ReportAccrualCalculationScheduleSerializer(AccrualCalculationScheduleSerializer):
#     def __init__(self, *args, **kwargs):
#         kwargs.setdefault('read_only', True)
#
#         super(AccrualCalculationScheduleSerializer, self).__init__(*args, **kwargs)
#
#
# class ReportPriceHistorySerializer(PriceHistorySerializer):
#     def __init__(self, *args, **kwargs):
#         kwargs.setdefault('read_only', True)
#
#         super(ReportPriceHistorySerializer, self).__init__(*args, **kwargs)
#
#         self.fields.pop('instrument')
#         self.fields.pop('instrument_object')
#
#         self.fields.pop('pricing_policy')
#         self.fields.pop('pricing_policy_object')
#
#
# class ReportCurrencySerializer(CurrencySerializer):
#     def __init__(self, *args, **kwargs):
#         kwargs.setdefault('read_only', True)
#
#         super(ReportCurrencySerializer, self).__init__(*args, **kwargs)
#
#         self.fields['attributes'] = ReportGenericAttributeSerializer(many=True, required=False, allow_null=True)
#
#         self.fields.pop('tags')
#         self.fields.pop('tags_object')
#
#         self.fields.pop('price_download_scheme')
#         self.fields.pop('price_download_scheme_object')
#         self.fields.pop('daily_pricing_model')
#         self.fields.pop('daily_pricing_model_object')
#
#         self.fields.pop('is_default')
#
#
# class ReportCurrencyHistorySerializer(CurrencyHistorySerializer):
#     def __init__(self, *args, **kwargs):
#         kwargs.setdefault('read_only', True)
#
#         super(ReportCurrencyHistorySerializer, self).__init__(*args, **kwargs)
#
#         self.fields.pop('currency')
#         self.fields.pop('currency_object')
#
#         self.fields.pop('pricing_policy')
#         self.fields.pop('pricing_policy_object')
#
#
# class ReportPortfolioSerializer(PortfolioSerializer):
#     def __init__(self, *args, **kwargs):
#         kwargs.setdefault('read_only', True)
#
#         super(ReportPortfolioSerializer, self).__init__(*args, **kwargs)
#
#         self.fields['attributes'] = ReportGenericAttributeSerializer(many=True, required=False, allow_null=True)
#
#         self.fields.pop('accounts')
#         self.fields.pop('accounts_object')
#         self.fields.pop('responsibles')
#         self.fields.pop('responsibles_object')
#         self.fields.pop('counterparties')
#         self.fields.pop('counterparties_object')
#         self.fields.pop('transaction_types')
#         self.fields.pop('transaction_types_object')
#
#         # self.fields.pop('user_object_permissions')
#         # self.fields.pop('group_object_permissions')
#         # self.fields.pop('object_permissions')
#
#         self.fields.pop('tags')
#         self.fields.pop('tags_object')
#
#         self.fields.pop('is_default')
#
#
# class ReportAccountSerializer(AccountSerializer):
#     def __init__(self, *args, **kwargs):
#         kwargs.setdefault('read_only', True)
#
#         super(ReportAccountSerializer, self).__init__(*args, **kwargs)
#
#         self.fields['attributes'] = ReportGenericAttributeSerializer(many=True, required=False, allow_null=True)
#
#         self.fields.pop('portfolios')
#         self.fields.pop('portfolios_object')
#
#         # self.fields.pop('user_object_permissions')
#         # self.fields.pop('group_object_permissions')
#         # self.fields.pop('object_permissions')
#
#         self.fields.pop('tags')
#         self.fields.pop('tags_object')
#
#         self.fields.pop('is_default')
#
#
# class ReportStrategy1Serializer(Strategy1Serializer):
#     def __init__(self, *args, **kwargs):
#         kwargs.setdefault('read_only', True)
#
#         super(ReportStrategy1Serializer, self).__init__(*args, **kwargs)
#
#         # self.fields.pop('user_object_permissions')
#         # self.fields.pop('group_object_permissions')
#         # self.fields.pop('object_permissions')
#
#         self.fields.pop('tags')
#         self.fields.pop('tags_object')
#
#         # self.fields.pop('is_default')
#
#
# class ReportStrategy2Serializer(Strategy2Serializer):
#     def __init__(self, *args, **kwargs):
#         kwargs.setdefault('read_only', True)
#
#         super(ReportStrategy2Serializer, self).__init__(*args, **kwargs)
#
#         # self.fields.pop('user_object_permissions')
#         # self.fields.pop('group_object_permissions')
#         # self.fields.pop('object_permissions')
#
#         self.fields.pop('tags')
#         self.fields.pop('tags_object')
#
#         # self.fields.pop('is_default')
#
#
# class ReportStrategy3Serializer(Strategy3Serializer):
#     def __init__(self, *args, **kwargs):
#         kwargs.setdefault('read_only', True)
#
#         super(ReportStrategy3Serializer, self).__init__(*args, **kwargs)
#
#         # self.fields.pop('user_object_permissions')
#         # self.fields.pop('group_object_permissions')
#         # self.fields.pop('object_permissions')
#
#         self.fields.pop('tags')
#         self.fields.pop('tags_object')
#
#         # self.fields.pop('is_default')
#
#
# class ReportResponsibleSerializer(ResponsibleSerializer):
#     def __init__(self, *args, **kwargs):
#         kwargs.setdefault('read_only', True)
#
#         super(ReportResponsibleSerializer, self).__init__(*args, **kwargs)
#
#         self.fields['attributes'] = ReportGenericAttributeSerializer(many=True, required=False, allow_null=True)
#
#         self.fields.pop('portfolios')
#         self.fields.pop('portfolios_object')
#
#         # self.fields.pop('user_object_permissions')
#         # self.fields.pop('group_object_permissions')
#         # self.fields.pop('object_permissions')
#
#         self.fields.pop('tags')
#         self.fields.pop('tags_object')
#
#         self.fields.pop('is_default')
#
#
# class ReportCounterpartySerializer(CounterpartySerializer):
#     def __init__(self, *args, **kwargs):
#         kwargs.setdefault('read_only', True)
#
#         super(ReportCounterpartySerializer, self).__init__(*args, **kwargs)
#
#         self.fields['attributes'] = ReportGenericAttributeSerializer(many=True, required=False, allow_null=True)
#
#         self.fields.pop('portfolios')
#         self.fields.pop('portfolios_object')
#
#         # self.fields.pop('user_object_permissions')
#         # self.fields.pop('group_object_permissions')
#         # self.fields.pop('object_permissions')
#
#         self.fields.pop('tags')
#         self.fields.pop('tags_object')
#
#         self.fields.pop('is_default')
#
#
# class ReportComplexTransactionSerializer(ComplexTransactionSerializer):
#     def __init__(self, *args, **kwargs):
#         kwargs.setdefault('read_only', True)
#
#         super(ReportComplexTransactionSerializer, self).__init__(*args, **kwargs)
#
#         self.fields.pop('text')
#         self.fields.pop('transactions')
#         self.fields.pop('transactions_object')
#         # self.fields.pop('transaction_type_object')
#         # self.fields['transaction_type_object'] = TransactionTypeViewSerializer(source='transaction_type', read_only=True)
#
#         self.fields['attributes'] = ReportGenericAttributeSerializer(many=True, required=False, allow_null=True)
#
#         for k in list(self.fields.keys()):
#             if str(k).endswith('_object'):
#                 self.fields.pop(k)
#
#
# class ReportItemCustomFieldSerializer(serializers.Serializer):
#     custom_field = serializers.PrimaryKeyRelatedField(read_only=True)
#     value = serializers.ReadOnlyField()
#
#     def __init__(self, *args, **kwargs):
#         kwargs.setdefault('read_only', True)
#
#         super(ReportItemCustomFieldSerializer, self).__init__(*args, **kwargs)
#
#         self.fields['custom_field_object'] = CustomFieldViewSerializer(source='custom_field', read_only=True)
#
#     @cached_property
#     def _readable_fields(self):
#         custom_fields_hide_objects = self.context.get('custom_fields_hide_objects', False)
#         return [
#             field for field in self.fields.values()
#             if not field.write_only and (
#                 not custom_fields_hide_objects or field.field_name not in ('custom_field_object',))
#             ]
#
#
# class ReportItemSerializer(serializers.Serializer):
#     id = serializers.SerializerMethodField()
#
#     item_type = serializers.ChoiceField(source='type', choices=ReportItem.TYPE_CHOICES, read_only=True)
#     item_type_code = serializers.CharField(source='type_code', read_only=True)
#     item_type_name = serializers.CharField(source='type_name', read_only=True)
#
#     item_subtype = serializers.ChoiceField(source='subtype', choices=ReportItem.TYPE_CHOICES, read_only=True)
#     item_subtype_code = serializers.CharField(source='subtype_code', read_only=True)
#     item_subtype_name = serializers.CharField(source='subtype_name', read_only=True)
#
#     user_code = serializers.CharField(read_only=True)
#     name = serializers.CharField(read_only=True)
#     short_name = serializers.CharField(read_only=True)
#     # detail = serializers.CharField(read_only=True)
#     detail = serializers.SerializerMethodField()
#
#     instrument = serializers.PrimaryKeyRelatedField(source='instr', read_only=True)
#     currency = serializers.PrimaryKeyRelatedField(source='ccy', read_only=True)
#     transaction_currency = serializers.PrimaryKeyRelatedField(source='trn_ccy', read_only=True)
#     portfolio = serializers.PrimaryKeyRelatedField(source='prtfl', read_only=True)
#     account = serializers.PrimaryKeyRelatedField(source='acc', read_only=True)
#     strategy1 = serializers.PrimaryKeyRelatedField(source='str1', read_only=True)
#     strategy2 = serializers.PrimaryKeyRelatedField(source='str2', read_only=True)
#     strategy3 = serializers.PrimaryKeyRelatedField(source='str3', read_only=True)
#     custom_fields = ReportItemCustomFieldSerializer(many=True, read_only=True)
#     is_empty = serializers.BooleanField(read_only=True)
#     pricing_currency = serializers.PrimaryKeyRelatedField(source='pricing_ccy', read_only=True)
#
#     last_notes = serializers.CharField(read_only=True)
#
#     # allocations ----------------------------------------------------
#
#     allocation_balance = serializers.PrimaryKeyRelatedField(source='alloc_bl', read_only=True)
#     allocation_pl = serializers.PrimaryKeyRelatedField(source='alloc_pl', read_only=True)
#
#     # mismatches ----------------------------------------------------
#
#     mismatch = serializers.FloatField(read_only=True)
#     mismatch_portfolio = serializers.PrimaryKeyRelatedField(source='mismatch_prtfl', read_only=True)
#     mismatch_account = serializers.PrimaryKeyRelatedField(source='mismatch_acc', read_only=True)
#     # mismatch_currency = serializers.PrimaryKeyRelatedField(source='mismatch_ccy', read_only=True)
#
#     # ----------------------------------------------------
#
#     instr_principal = serializers.FloatField(source='instr_principal_res', read_only=True)
#     instrument_principal = serializers.FloatField(source='instr_principal_res', read_only=True)
#     instr_accrued = serializers.FloatField(source='instr_accrued_res', read_only=True)
#     instrument_accrued = serializers.FloatField(source='instr_accrued_res', read_only=True)
#
#     exposure = serializers.FloatField(source='exposure_res', read_only=True)
#     exposure_loc = serializers.FloatField(read_only=True)
#
#     instrument_principal_price = serializers.FloatField(source='instr_price_cur_principal_price', read_only=True)
#     instrument_accrued_price = serializers.FloatField(source='instr_price_cur_accrued_price', read_only=True)
#
#     report_currency_fx_rate = serializers.FloatField(source='report_ccy_cur_fx', read_only=True)
#     instrument_price_history_principal_price = serializers.FloatField(source='instr_price_cur_principal_price',
#                                                                       read_only=True)
#     instrument_price_history_accrued_price = serializers.FloatField(source='instr_price_cur_accrued_price',
#                                                                     read_only=True)
#     instrument_pricing_currency_fx_rate = serializers.FloatField(source='instr_pricing_ccy_cur_fx', read_only=True)
#     instrument_accrued_currency_fx_rate = serializers.FloatField(source='instr_accrued_ccy_cur_fx', read_only=True)
#     currency_fx_rate = serializers.FloatField(source='ccy_cur_fx', read_only=True)
#     pricing_currency_fx_rate = serializers.FloatField(source='pricing_ccy_cur_fx', read_only=True)
#
#     # ----------------------------------------------------
#
#     position_size = serializers.FloatField(source='pos_size', read_only=True)
#     market_value = serializers.FloatField(source='market_value_res', read_only=True)
#     market_value_loc = serializers.FloatField(read_only=True)
#     cost = serializers.FloatField(source='cost_res', read_only=True)
#     ytm = serializers.FloatField(read_only=True)
#     modified_duration = serializers.FloatField(read_only=True)
#     ytm_at_cost = serializers.FloatField(read_only=True)
#     time_invested = serializers.FloatField(read_only=True)
#     gross_cost_price = serializers.FloatField(source='gross_cost_res', read_only=True)
#     gross_cost_price_loc = serializers.FloatField(source='gross_cost_loc', read_only=True)
#     net_cost_price = serializers.FloatField(source='net_cost_res', read_only=True)
#     net_cost_price_loc = serializers.FloatField(source='net_cost_loc', read_only=True)
#     principal_invested = serializers.FloatField(source='principal_invested_res', read_only=True)
#     principal_invested_loc = serializers.FloatField(read_only=True)
#     amount_invested = serializers.FloatField(source='amount_invested_res', read_only=True)
#     amount_invested_loc = serializers.FloatField(read_only=True)
#     position_return = serializers.FloatField(source='pos_return_res', read_only=True)
#     position_return_loc = serializers.FloatField(source='pos_return_loc', read_only=True)
#     net_position_return = serializers.FloatField(source='net_pos_return_res', read_only=True)
#     net_position_return_loc = serializers.FloatField(source='net_pos_return_loc', read_only=True)
#     daily_price_change = serializers.FloatField(read_only=True)
#     mtd_price_change = serializers.FloatField(read_only=True)
#
#     # P&L ----------------------------------------------------
#
#     # full ----------------------------------------------------
#     principal = serializers.FloatField(source='principal_res', read_only=True)
#     carry = serializers.FloatField(source='carry_res', read_only=True)
#     overheads = serializers.FloatField(source='overheads_res', read_only=True)
#     total = serializers.FloatField(source='total_res', read_only=True)
#
#     principal_loc = serializers.FloatField(read_only=True)
#     carry_loc = serializers.FloatField(read_only=True)
#     overheads_loc = serializers.FloatField(read_only=True)
#     total_loc = serializers.FloatField(read_only=True)
#
#     # full / closed ----------------------------------------------------
#     principal_closed = serializers.FloatField(source='principal_closed_res', read_only=True)
#     carry_closed = serializers.FloatField(source='carry_closed_res', read_only=True)
#     overheads_closed = serializers.FloatField(source='overheads_closed_res', read_only=True)
#     total_closed = serializers.FloatField(source='total_closed_res', read_only=True)
#
#     principal_closed_loc = serializers.FloatField(read_only=True)
#     carry_closed_loc = serializers.FloatField(read_only=True)
#     overheads_closed_loc = serializers.FloatField(read_only=True)
#     total_closed_loc = serializers.FloatField(read_only=True)
#
#     # full / opened ----------------------------------------------------
#     principal_opened = serializers.FloatField(source='principal_opened_res', read_only=True)
#     carry_opened = serializers.FloatField(source='carry_opened_res', read_only=True)
#     overheads_opened = serializers.FloatField(source='overheads_opened_res', read_only=True)
#     total_opened = serializers.FloatField(source='total_opened_res', read_only=True)
#
#     principal_opened_loc = serializers.FloatField(read_only=True)
#     carry_opened_loc = serializers.FloatField(read_only=True)
#     overheads_opened_loc = serializers.FloatField(read_only=True)
#     total_opened_loc = serializers.FloatField(read_only=True)
#
#     # fx ----------------------------------------------------
#     principal_fx = serializers.FloatField(source='principal_fx_res', read_only=True)
#     carry_fx = serializers.FloatField(source='carry_fx_res', read_only=True)
#     overheads_fx = serializers.FloatField(source='overheads_fx_res', read_only=True)
#     total_fx = serializers.FloatField(source='total_fx_res', read_only=True)
#
#     principal_fx_loc = serializers.FloatField(read_only=True)
#     carry_fx_loc = serializers.FloatField(read_only=True)
#     overheads_fx_loc = serializers.FloatField(read_only=True)
#     total_fx_loc = serializers.FloatField(read_only=True)
#
#     # fx / closed ----------------------------------------------------
#     principal_fx_closed = serializers.FloatField(source='principal_fx_closed_res', read_only=True)
#     carry_fx_closed = serializers.FloatField(source='carry_fx_closed_res', read_only=True)
#     overheads_fx_closed = serializers.FloatField(source='overheads_fx_closed_res', read_only=True)
#     total_fx_closed = serializers.FloatField(source='total_fx_closed_res', read_only=True)
#
#     principal_fx_closed_loc = serializers.FloatField(read_only=True)
#     carry_fx_closed_loc = serializers.FloatField(read_only=True)
#     overheads_fx_closed_loc = serializers.FloatField(read_only=True)
#     total_fx_closed_loc = serializers.FloatField(read_only=True)
#
#     # fx / opened ----------------------------------------------------
#     principal_fx_opened = serializers.FloatField(source='principal_fx_opened_res', read_only=True)
#     carry_fx_opened = serializers.FloatField(source='carry_fx_opened_res', read_only=True)
#     overheads_fx_opened = serializers.FloatField(source='overheads_fx_opened_res', read_only=True)
#     total_fx_opened = serializers.FloatField(source='total_fx_opened_res', read_only=True)
#
#     principal_fx_opened_loc = serializers.FloatField(read_only=True)
#     carry_fx_opened_loc = serializers.FloatField(read_only=True)
#     overheads_fx_opened_loc = serializers.FloatField(read_only=True)
#     total_fx_opened_loc = serializers.FloatField(read_only=True)
#
#     # fixed ----------------------------------------------------
#     principal_fixed = serializers.FloatField(source='principal_fixed_res', read_only=True)
#     carry_fixed = serializers.FloatField(source='carry_fixed_res', read_only=True)
#     overheads_fixed = serializers.FloatField(source='overheads_fixed_res', read_only=True)
#     total_fixed = serializers.FloatField(source='total_fixed_res', read_only=True)
#
#     principal_fixed_loc = serializers.FloatField(read_only=True)
#     carry_fixed_loc = serializers.FloatField(read_only=True)
#     overheads_fixed_loc = serializers.FloatField(read_only=True)
#     total_fixed_loc = serializers.FloatField(read_only=True)
#
#     # fixed / closed ----------------------------------------------------
#     principal_fixed_closed = serializers.FloatField(source='principal_fixed_closed_res', read_only=True)
#     carry_fixed_closed = serializers.FloatField(source='carry_fixed_closed_res', read_only=True)
#     overheads_fixed_closed = serializers.FloatField(source='overheads_fixed_closed_res', read_only=True)
#     total_fixed_closed = serializers.FloatField(source='total_fixed_closed_res', read_only=True)
#
#     principal_fixed_closed_loc = serializers.FloatField(read_only=True)
#     carry_fixed_closed_loc = serializers.FloatField(read_only=True)
#     overheads_fixed_closed_loc = serializers.FloatField(read_only=True)
#     total_fixed_closed_loc = serializers.FloatField(read_only=True)
#
#     # fixed / opened ----------------------------------------------------
#     principal_fixed_opened = serializers.FloatField(source='principal_fixed_opened_res', read_only=True)
#     carry_fixed_opened = serializers.FloatField(source='carry_fixed_opened_res', read_only=True)
#     overheads_fixed_opened = serializers.FloatField(source='overheads_fixed_opened_res', read_only=True)
#     total_fixed_opened = serializers.FloatField(source='total_fixed_opened_res', read_only=True)
#
#     principal_fixed_opened_loc = serializers.FloatField(read_only=True)
#     carry_fixed_opened_loc = serializers.FloatField(read_only=True)
#     overheads_fixed_opened_loc = serializers.FloatField(read_only=True)
#     total_fixed_opened_loc = serializers.FloatField(read_only=True)
#
#     # objects and data ----------------------------------------------------
#
#     report_currency_history = serializers.PrimaryKeyRelatedField(source='report_ccy_cur', read_only=True)
#     instrument_price_history = serializers.PrimaryKeyRelatedField(source='instr_price_cur', read_only=True)
#     instrument_pricing_currency_history = serializers.PrimaryKeyRelatedField(source='instr_pricing_ccy_cur',
#                                                                              read_only=True)
#     instrument_accrued_currency_history = serializers.PrimaryKeyRelatedField(source='instr_accrued_ccy_cur',
#                                                                              read_only=True)
#     currency_history = serializers.PrimaryKeyRelatedField(source='ccy_cur', read_only=True)
#     pricing_currency_history = serializers.PrimaryKeyRelatedField(source='ccy_cur', read_only=True)
#
#     instrument_accrual = serializers.PrimaryKeyRelatedField(source='instr_accrual', read_only=True)
#     instrument_accrual_accrued_price = serializers.FloatField(source='instr_accrual_accrued_price', read_only=True)
#
#     portfolio_object = ReportPortfolioSerializer(source='prtfl', read_only=True)
#     account_object = ReportAccountSerializer(source='acc', read_only=True)
#     strategy1_object = ReportStrategy1Serializer(source='str1', read_only=True)
#     strategy2_object = ReportStrategy2Serializer(source='str2', read_only=True)
#     strategy3_object = ReportStrategy3Serializer(source='str3', read_only=True)
#     instrument_object = ReportInstrumentSerializer(source='instr', read_only=True)
#     currency_object = ReportCurrencySerializer(source='ccy', read_only=True)
#     transaction_currency_object = ReportCurrencySerializer(source='trn_ccy', read_only=True)
#     pricing_currency_object = ReportCurrencySerializer(source='pricing_ccy', read_only=True)
#
#     allocation_balance_object = ReportInstrumentSerializer(source='alloc_bl', read_only=True)
#     allocation_pl_object = ReportInstrumentSerializer(source='alloc_pl', read_only=True)
#     mismatch_portfolio_object = ReportPortfolioSerializer(source='mismatch_prtfl', read_only=True)
#     mismatch_account_object = ReportAccountSerializer(source='mismatch_acc', read_only=True)
#
#     report_currency_history_object = ReportCurrencyHistorySerializer(source='report_ccy_cur', read_only=True)
#     instrument_price_history_object = ReportPriceHistorySerializer(source='instr_price_cur', read_only=True)
#     instrument_pricing_currency_history_object = ReportCurrencyHistorySerializer(source='instr_pricing_ccy_cur',
#                                                                                  read_only=True)
#     instrument_accrued_currency_history_object = ReportCurrencyHistorySerializer(source='instr_accrued_ccy_cur',
#                                                                                  read_only=True)
#     currency_history_object = ReportCurrencyHistorySerializer(source='ccy_cur', read_only=True)
#     pricing_currency_history_object = ReportCurrencyHistorySerializer(source='pricing_ccy_cur', read_only=True)
#
#     instrument_accrual_object = ReportAccrualCalculationScheduleSerializer(source='instr_accrual')
#
#     def __init__(self, *args, **kwargs):
#         kwargs.setdefault('read_only', True)
#
#         super(ReportItemSerializer, self).__init__(*args, **kwargs)
#
#         # from poms.currencies.serializers import CurrencySerializer
#         # from poms.instruments.serializers import InstrumentSerializer
#         # from poms.portfolios.serializers import PortfolioViewSerializer
#         # from poms.accounts.serializers import AccountViewSerializer
#         # from poms.strategies.serializers import Strategy1ViewSerializer, Strategy2ViewSerializer, \
#         #     Strategy3ViewSerializer
#
#         # self.fields['portfolio_object'] = ReportPortfolioSerializer(source='prtfl', read_only=True)
#         # self.fields['account_object'] = ReportAccountSerializer(source='acc', read_only=True)
#         # self.fields['strategy1_object'] = ReportStrategy1Serializer(source='str1', read_only=True)
#         # self.fields['strategy2_object'] = ReportStrategy2Serializer(source='str2', read_only=True)
#         # self.fields['strategy3_object'] = ReportStrategy3Serializer(source='str3', read_only=True)
#         # self.fields['instrument_object'] = ReportInstrumentSerializer(source='instr', read_only=True)
#         # self.fields['currency_object'] = ReportCurrencySerializer(source='ccy', read_only=True)
#         # self.fields['transaction_currency_object'] = ReportCurrencySerializer(source='trn_ccy', read_only=True)
#         #
#         # self.fields['allocation_balance_object'] = ReportInstrumentSerializer(source='alloc_bl', read_only=True)
#         # self.fields['allocation_pl_object'] = ReportInstrumentSerializer(source='alloc_pl', read_only=True)
#         #
#         # self.fields['mismatch_portfolio_object'] = ReportPortfolioSerializer(source='mismatch_prtfl', read_only=True)
#         # self.fields['mismatch_account_object'] = ReportAccountSerializer(source='mismatch_acc', read_only=True)
#         # # self.fields['mismatch_currency_object'] = ReportCurrencySerializer(source='mismatch_ccy', read_only=True)
#         #
#         # self.fields['report_currency_history_object'] = ReportCurrencyHistorySerializer(
#         #     source='report_currency_history', read_only=True)
#         # self.fields['instrument_price_history_object'] = ReportPriceHistorySerializer(source='instr_price_cur',
#         #                                                                               read_only=True)
#         # self.fields['instrument_pricing_currency_history_object'] = ReportCurrencyHistorySerializer(
#         #     source='instr_pricing_ccy_cur', read_only=True)
#         # self.fields['instrument_accrued_currency_history_object'] = ReportCurrencyHistorySerializer(
#         #     source='instr_accrued_ccy_cur', read_only=True)
#         # self.fields['currency_history_object'] = ReportCurrencyHistorySerializer(source='ccy_cur', read_only=True)
#
#     def get_id(self, obj):
#         return ','.join(str(x) for x in obj.pk)
#
#     def get_detail(self, obj):
#         # obj_data = formula.get_model_data(obj, ReportItemDetailRendererSerializer, context=self.context)
#         # try:
#         #     return formula.safe_eval('item.instrument.user_code', names={'item': obj_data})
#         # except formula.InvalidExpression:
#         #     return 'OLALALALALALA'
#         if obj.detail_trn:
#             expr = obj.acc.type.transaction_details_expr
#             if expr:
#                 names = {
#                     # 'item': formula.get_model_data(obj, ReportItemDetailRendererSerializer, context=self.context),
#                     'item': obj,
#                 }
#                 try:
#                     value = formula.safe_eval(expr, names=names, context=self.context)
#                 except formula.InvalidExpression:
#                     value = ugettext('Invalid expression')
#                 return value
#         return None
#
#
# class ReportItemEvalSerializer(ReportItemSerializer):
#     def __init__(self, *args, **kwargs):
#         # kwargs.setdefault('read_only', True)
#
#         super(ReportItemEvalSerializer, self).__init__(*args, **kwargs)
#         self.fields.pop('detail')
#
#
# class ReportSerializer(serializers.Serializer):
#     task_id = serializers.CharField(allow_null=True, allow_blank=True, required=False)
#     task_status = serializers.ReadOnlyField()
#
#     master_user = MasterUserField()
#     member = HiddenMemberField()
#     pricing_policy = PricingPolicyField()
#     pl_first_date = serializers.DateField(required=False, allow_null=True,
#                                           help_text=ugettext_lazy('First date for pl report'))
#     report_date = serializers.DateField(required=False, allow_null=True, default=date_now,
#                                         help_text=ugettext_lazy('Report date or second date for pl report'))
#     report_currency = CurrencyField(required=False, allow_null=True, default=SystemCurrencyDefault())
#     cost_method = serializers.PrimaryKeyRelatedField(queryset=CostMethod.objects, allow_null=True, allow_empty=True)
#
#     portfolio_mode = serializers.ChoiceField(default=Report.MODE_INDEPENDENT, initial=Report.MODE_INDEPENDENT,
#                                              choices=Report.MODE_CHOICES, required=False)
#     account_mode = serializers.ChoiceField(default=Report.MODE_INDEPENDENT, initial=Report.MODE_INDEPENDENT,
#                                            choices=Report.MODE_CHOICES, required=False)
#     strategy1_mode = serializers.ChoiceField(default=Report.MODE_INDEPENDENT, initial=Report.MODE_INDEPENDENT,
#                                              choices=Report.MODE_CHOICES, required=False)
#     strategy2_mode = serializers.ChoiceField(default=Report.MODE_INDEPENDENT, initial=Report.MODE_INDEPENDENT,
#                                              choices=Report.MODE_CHOICES, required=False)
#     strategy3_mode = serializers.ChoiceField(default=Report.MODE_INDEPENDENT, initial=Report.MODE_INDEPENDENT,
#                                              choices=Report.MODE_CHOICES, required=False)
#     show_transaction_details = serializers.BooleanField(default=False)
#     approach_multiplier = serializers.FloatField(default=0.5, initial=0.5, min_value=0.0, max_value=1.0, required=False)
#
#     custom_fields = CustomFieldField(many=True, allow_empty=True, allow_null=True, required=False)
#
#     portfolios = PortfolioField(many=True, required=False, allow_null=True, allow_empty=True)
#     accounts = AccountField(many=True, required=False, allow_null=True, allow_empty=True)
#     strategies1 = Strategy1Field(many=True, required=False, allow_null=True, allow_empty=True)
#     strategies2 = Strategy2Field(many=True, required=False, allow_null=True, allow_empty=True)
#     strategies3 = Strategy3Field(many=True, required=False, allow_null=True, allow_empty=True)
#     transaction_classes = serializers.PrimaryKeyRelatedField(queryset=TransactionClass.objects.all(),
#                                                              many=True, required=False, allow_null=True,
#                                                              allow_empty=True)
#     date_field = serializers.ChoiceField(required=False, allow_null=True,
#                                          initial='transaction_date', default='transaction_date',
#                                          choices=(
#                                              ('transaction_date', ugettext_lazy('Transaction date')),
#                                              ('accounting_date', ugettext_lazy('Accounting date')),
#                                              ('cash_date', ugettext_lazy('Cash date')),
#                                          ))
#
#     items = ReportItemSerializer(many=True, read_only=True)
#
#     # transactions = ReportTransactionSerializer(many=True, read_only=True)
#
#     def __init__(self, *args, **kwargs):
#         super(ReportSerializer, self).__init__(*args, **kwargs)
#
#         self.fields['pricing_policy_object'] = PricingPolicyViewSerializer(source='pricing_policy', read_only=True)
#         self.fields['report_currency_object'] = CurrencyViewSerializer(source='report_currency', read_only=True)
#         self.fields['cost_method_object'] = CostMethodSerializer(source='cost_method', read_only=True)
#         self.fields['portfolios_object'] = PortfolioViewSerializer(source='portfolios', read_only=True, many=True)
#         self.fields['accounts_object'] = AccountViewSerializer(source='accounts', read_only=True, many=True)
#         self.fields['strategies1_object'] = Strategy1ViewSerializer(source='strategies1', read_only=True, many=True)
#         self.fields['strategies2_object'] = Strategy2ViewSerializer(source='strategies2', read_only=True, many=True)
#         self.fields['strategies3_object'] = Strategy3ViewSerializer(source='strategies3', read_only=True, many=True)
#         self.fields['custom_fields_object'] = CustomFieldViewSerializer(source='custom_fields', read_only=True,
#                                                                         many=True)
#         self.fields['transaction_classes_object'] = TransactionClassSerializer(source='transaction_classes',
#                                                                                read_only=True, many=True)
#
#     def validate(self, attrs):
#         if not attrs.get('report_date', None):
#             if settings.DEBUG:
#                 attrs['report_date'] = date(2017, 2, 12)
#             else:
#                 attrs['report_date'] = date_now() - timedelta(days=1)
#
#         pl_first_date = attrs.get('pl_first_date', None)
#         if pl_first_date and pl_first_date >= attrs['report_date']:
#             raise ValidationError(ugettext('"pl_first_date" must be lesser than "report_date"'))
#
#         # if settings.DEBUG:
#         #     if not attrs.get('pl_first_date', None):
#         #         attrs['pl_first_date'] = date(2017, 2, 10)
#
#         if not attrs.get('report_currency', None):
#             attrs['report_currency'] = attrs['master_user'].system_currency
#
#         if not attrs.get('cost_method', None):
#             attrs['cost_method'] = CostMethod.objects.get(pk=CostMethod.AVCO)
#
#         return attrs
#
#     def create(self, validated_data):
#         return Report(**validated_data)
#
#
# # Transaction Report --------
#
#
# class TransactionReportItemSerializer(serializers.Serializer):
#     id = serializers.ReadOnlyField()
#     # complex_transaction = ReportComplexTransactionSerializer(read_only=True)
#     complex_transaction = serializers.PrimaryKeyRelatedField(read_only=True)
#     transaction_code = serializers.ReadOnlyField()
#     transaction_class = serializers.PrimaryKeyRelatedField(read_only=True)
#     instrument = serializers.PrimaryKeyRelatedField(read_only=True)
#     transaction_currency = serializers.PrimaryKeyRelatedField(read_only=True)
#     position_size_with_sign = serializers.ReadOnlyField()
#     settlement_currency = serializers.PrimaryKeyRelatedField(read_only=True)
#     cash_consideration = serializers.ReadOnlyField()
#     principal_with_sign = serializers.ReadOnlyField()
#     carry_with_sign = serializers.ReadOnlyField()
#     overheads_with_sign = serializers.ReadOnlyField()
#     accounting_date = serializers.DateField(read_only=True)
#     cash_date = serializers.DateField(read_only=True)
#     transaction_date = serializers.DateField(read_only=True)
#     portfolio = serializers.PrimaryKeyRelatedField(read_only=True)
#     account_cash = serializers.PrimaryKeyRelatedField(read_only=True)
#     account_position = serializers.PrimaryKeyRelatedField(read_only=True)
#     account_interim = serializers.PrimaryKeyRelatedField(read_only=True)
#     strategy1_position = serializers.PrimaryKeyRelatedField(read_only=True)
#     strategy1_cash = serializers.PrimaryKeyRelatedField(read_only=True)
#     strategy2_position = serializers.PrimaryKeyRelatedField(read_only=True)
#     strategy2_cash = serializers.PrimaryKeyRelatedField(read_only=True)
#     strategy3_position = serializers.PrimaryKeyRelatedField(read_only=True)
#     strategy3_cash = serializers.PrimaryKeyRelatedField(read_only=True)
#     responsible = serializers.PrimaryKeyRelatedField(read_only=True)
#     counterparty = serializers.PrimaryKeyRelatedField(read_only=True)
#     linked_instrument = serializers.PrimaryKeyRelatedField(read_only=True)
#     allocation_balance = serializers.PrimaryKeyRelatedField(read_only=True)
#     allocation_pl = serializers.PrimaryKeyRelatedField(read_only=True)
#     reference_fx_rate = serializers.ReadOnlyField()
#     factor = serializers.ReadOnlyField()
#     trade_price = serializers.ReadOnlyField()
#     position_amount = serializers.ReadOnlyField()
#     principal_amount = serializers.ReadOnlyField()
#     carry_amount = serializers.ReadOnlyField()
#     overheads = serializers.ReadOnlyField()
#     notes = serializers.ReadOnlyField()
#     attributes = ReportGenericAttributeSerializer(many=True, read_only=True)
#
#     custom_fields = ReportItemCustomFieldSerializer(many=True, read_only=True)
#
#     def __init__(self, *args, **kwargs):
#         kwargs.setdefault('read_only', True)
#
#         super(TransactionReportItemSerializer, self).__init__(*args, **kwargs)
#
#
# class TransactionReportSerializer(serializers.Serializer):
#     task_id = serializers.CharField(allow_null=True, allow_blank=True, required=False)
#     task_status = serializers.ReadOnlyField()
#
#     master_user = MasterUserField()
#     member = HiddenMemberField()
#
#     begin_date = serializers.DateField(required=False, allow_null=True)
#     end_date = serializers.DateField(required=False, allow_null=True)
#
#     custom_fields = CustomFieldField(many=True, allow_empty=True, allow_null=True, required=False)
#
#     items = TransactionReportItemSerializer(many=True, read_only=True)
#     complex_transactions = ReportComplexTransactionSerializer(many=True, read_only=True)
#     transaction_types = TransactionTypeViewSerializer(many=True, read_only=True)
#     instruments = ReportInstrumentSerializer(many=True, read_only=True)
#     currencies = ReportCurrencySerializer(many=True, read_only=True)
#     portfolios = ReportPortfolioSerializer(many=True, read_only=True)
#     accounts = ReportAccountSerializer(many=True, read_only=True)
#     strategies1 = ReportStrategy1Serializer(many=True, read_only=True)
#     strategies2 = ReportStrategy2Serializer(many=True, read_only=True)
#     strategies3 = ReportStrategy3Serializer(many=True, read_only=True)
#     responsibles = ReportResponsibleSerializer(many=True, read_only=True)
#     counterparties = ReportCounterpartySerializer(many=True, read_only=True)
#
#     complex_transaction_attribute_types = ReportGenericAttributeTypeSerializer(many=True, read_only=True,
#                                                                                show_classifiers=True)
#     transaction_attribute_types = ReportGenericAttributeTypeSerializer(many=True, read_only=True, show_classifiers=True)
#     instrument_attribute_types = ReportGenericAttributeTypeSerializer(many=True, read_only=True, show_classifiers=True)
#     currency_attribute_types = ReportGenericAttributeTypeSerializer(many=True, read_only=True, show_classifiers=True)
#     portfolio_attribute_types = ReportGenericAttributeTypeSerializer(many=True, read_only=True, show_classifiers=True)
#     account_attribute_types = ReportGenericAttributeTypeSerializer(many=True, read_only=True, show_classifiers=True)
#     responsible_attribute_types = ReportGenericAttributeTypeSerializer(many=True, read_only=True, show_classifiers=True)
#     counterparty_attribute_types = ReportGenericAttributeTypeSerializer(many=True, read_only=True,
#                                                                         show_classifiers=True)
#
#     def __init__(self, *args, **kwargs):
#         super(TransactionReportSerializer, self).__init__(*args, **kwargs)
#
#         self.fields['custom_fields_object'] = CustomFieldViewSerializer(source='custom_fields', read_only=True,
#                                                                         many=True)
#
#     def create(self, validated_data):
#         return TransactionReport(**validated_data)
#
#
# # CashFlowProjectionReport --------
#
#
# class CashFlowProjectionReportItemSerializer(TransactionReportItemSerializer):
#     item_type = serializers.ChoiceField(source='type', read_only=True, choices=CashFlowProjectionReportItem.TYPE_CHOICE)
#     cash_consideration_before = serializers.ReadOnlyField()
#     cash_consideration_after = serializers.ReadOnlyField()
#
#     def __init__(self, *args, **kwargs):
#         kwargs.setdefault('read_only', True)
#
#         super(CashFlowProjectionReportItemSerializer, self).__init__(*args, **kwargs)
#
#         self.fields.fields.move_to_end('item_type', last=False)
#
#
# class CashFlowProjectionReportSerializer(TransactionReportSerializer):
#     balance_date = serializers.DateField(required=False, allow_null=True)
#     report_date = serializers.DateField(required=False, allow_null=True)
#     has_errors = serializers.ReadOnlyField()
#     items = CashFlowProjectionReportItemSerializer(many=True, read_only=True)
#
#     def __init__(self, *args, **kwargs):
#         # kwargs.setdefault('read_only', True)
#
#         super(CashFlowProjectionReportSerializer, self).__init__(*args, **kwargs)
#
#     def validate(self, attrs):
#         if not attrs.get('balance_date', None):
#             if settings.DEBUG:
#                 attrs['balance_date'] = date(2016, 12, 21)
#             else:
#                 attrs['balance_date'] = date_now()
#
#         if not attrs.get('report_date', None):
#             if settings.DEBUG:
#                 attrs['report_date'] = date(2016, 12, 26)
#             else:
#                 attrs['report_date'] = attrs['balance_date'] + relativedelta(months=1)
#
#         return attrs
#
#     def create(self, validated_data):
#         return CashFlowProjectionReport(**validated_data)
