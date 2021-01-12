from __future__ import unicode_literals

from datetime import timedelta, date

import time
from django.conf import settings
from django.utils.translation import ugettext_lazy, ugettext
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from poms.accounts.fields import AccountField
from poms.accounts.serializers import AccountViewSerializer
from poms.common import formula
from poms.common.utils import date_now
from poms.currencies.fields import CurrencyField, SystemCurrencyDefault
from poms.currencies.serializers import CurrencyViewSerializer
from poms.instruments.fields import PricingPolicyField
from poms.instruments.models import CostMethod
from poms.instruments.serializers import PricingPolicyViewSerializer, CostMethodSerializer
from poms.portfolios.fields import PortfolioField
from poms.portfolios.serializers import PortfolioViewSerializer
from poms.reports.builders.balance_item import ReportItem, Report
from poms.reports.builders.base_serializers import ReportPortfolioSerializer, \
    ReportAccountSerializer, ReportStrategy1Serializer, ReportStrategy2Serializer, ReportStrategy3Serializer, \
    ReportInstrumentSerializer, ReportCurrencySerializer, ReportCurrencyHistorySerializer, ReportPriceHistorySerializer, \
    ReportAccrualCalculationScheduleSerializer, ReportItemBalanceReportCustomFieldSerializer, \
    ReportInstrumentTypeSerializer, ReportAccountTypeSerializer, ReportGenericAttributeSerializer, \
    ReportSerializerWithLogs
# from poms.reports.fields import CustomFieldField
from poms.reports.fields import BalanceReportCustomFieldField
from poms.reports.serializers import BalanceReportCustomFieldSerializer
from poms.strategies.fields import Strategy1Field, Strategy2Field, Strategy3Field
from poms.strategies.serializers import Strategy1ViewSerializer, Strategy2ViewSerializer, Strategy3ViewSerializer
from poms.transactions.models import TransactionClass
from poms.transactions.serializers import TransactionClassSerializer
from poms.users.fields import MasterUserField, HiddenMemberField

import logging

_l = logging.getLogger('poms.reports')


class ReportItemSerializer(serializers.Serializer):
    id = serializers.SerializerMethodField()

    item_type = serializers.ChoiceField(source='type', choices=ReportItem.TYPE_CHOICES, read_only=True)
    item_type_code = serializers.CharField(source='type_code', read_only=True)
    item_type_name = serializers.CharField(source='type_name', read_only=True)

    item_subtype = serializers.ChoiceField(source='subtype', choices=ReportItem.SUBTYPE_CHOICES, read_only=True)
    item_subtype_code = serializers.CharField(source='subtype_code', read_only=True)
    item_subtype_name = serializers.CharField(source='subtype_name', read_only=True)

    item_group = serializers.ChoiceField(source='group', choices=ReportItem.GROUP_CHOICES, read_only=True)
    item_group_code = serializers.CharField(source='group_code', read_only=True)
    item_group_name = serializers.CharField(source='group_name', read_only=True)

    user_code = serializers.CharField(read_only=True)
    name = serializers.CharField(read_only=True)
    short_name = serializers.CharField(read_only=True)
    # detail = serializers.CharField(read_only=True)
    detail = serializers.SerializerMethodField()

    instrument = serializers.PrimaryKeyRelatedField(source='instr', read_only=True)
    currency = serializers.PrimaryKeyRelatedField(source='ccy', read_only=True)
    # transaction_currency = serializers.PrimaryKeyRelatedField(source='trn_ccy', read_only=True)
    portfolio = serializers.PrimaryKeyRelatedField(source='prtfl', read_only=True)
    account = serializers.PrimaryKeyRelatedField(source='acc', read_only=True)
    strategy1 = serializers.PrimaryKeyRelatedField(source='str1', read_only=True)
    strategy2 = serializers.PrimaryKeyRelatedField(source='str2', read_only=True)
    strategy3 = serializers.PrimaryKeyRelatedField(source='str3', read_only=True)
    notes = serializers.CharField(read_only=True)
    source_transactions = serializers.ListField(source='src_trns_id', child=serializers.IntegerField(), read_only=True)

    custom_fields = ReportItemBalanceReportCustomFieldSerializer(many=True, read_only=True)
    is_empty = serializers.BooleanField(read_only=True)

    pricing_currency = serializers.PrimaryKeyRelatedField(source='pricing_ccy', read_only=True)

    last_notes = serializers.CharField(read_only=True)

    # allocations ----------------------------------------------------

    allocation = serializers.PrimaryKeyRelatedField(source='alloc', read_only=True)
    # allocation_balance = serializers.PrimaryKeyRelatedField(source='alloc_bl', read_only=True)
    # allocation_pl = serializers.PrimaryKeyRelatedField(source='alloc_pl', read_only=True)

    # mismatches ----------------------------------------------------

    mismatch = serializers.FloatField(read_only=True)
    mismatch_portfolio = serializers.PrimaryKeyRelatedField(source='mismatch_prtfl', read_only=True)
    mismatch_account = serializers.PrimaryKeyRelatedField(source='mismatch_acc', read_only=True)
    # mismatch_currency = serializers.PrimaryKeyRelatedField(source='mismatch_ccy', read_only=True)

    # ----------------------------------------------------

    instr_principal = serializers.FloatField(source='instr_principal_res', read_only=True)
    instrument_principal = serializers.FloatField(source='instr_principal_res', read_only=True)
    instr_accrued = serializers.FloatField(source='instr_accrued_res', read_only=True)
    instrument_accrued = serializers.FloatField(source='instr_accrued_res', read_only=True)

    exposure = serializers.FloatField(source='exposure_res', read_only=True)
    exposure_loc = serializers.FloatField(read_only=True)

    instrument_principal_price = serializers.FloatField(source='instr_price_cur_principal_price', read_only=True)
    instrument_accrued_price = serializers.FloatField(source='instr_price_cur_accrued_price', read_only=True)

    report_currency_fx_rate = serializers.FloatField(source='report_ccy_cur_fx', read_only=True)
    instrument_price_history_principal_price = serializers.FloatField(source='instr_price_cur_principal_price',
                                                                      read_only=True)
    instrument_price_history_accrued_price = serializers.FloatField(source='instr_price_cur_accrued_price',
                                                                    read_only=True)
    instrument_pricing_currency_fx_rate = serializers.FloatField(source='instr_pricing_ccy_cur_fx', read_only=True)
    instrument_accrued_currency_fx_rate = serializers.FloatField(source='instr_accrued_ccy_cur_fx', read_only=True)
    currency_fx_rate = serializers.FloatField(source='ccy_cur_fx', read_only=True)
    pricing_currency_fx_rate = serializers.FloatField(source='pricing_ccy_cur_fx', read_only=True)

    # ----------------------------------------------------

    position_size = serializers.FloatField(source='pos_size', read_only=True)
    market_value = serializers.FloatField(source='market_value_res', read_only=True)
    market_value_loc = serializers.FloatField(read_only=True)
    cost = serializers.FloatField(source='cost_res', read_only=True)
    ytm = serializers.FloatField(read_only=True)
    modified_duration = serializers.FloatField(read_only=True)
    ytm_at_cost = serializers.FloatField(read_only=True)
    time_invested = serializers.FloatField(read_only=True)
    gross_cost_price = serializers.FloatField(source='gross_cost_res', read_only=True)
    gross_cost_price_loc = serializers.FloatField(source='gross_cost_loc', read_only=True)
    net_cost_price = serializers.FloatField(source='net_cost_res', read_only=True)
    net_cost_price_loc = serializers.FloatField(source='net_cost_loc', read_only=True)
    principal_invested = serializers.FloatField(source='principal_invested_res', read_only=True)
    principal_invested_loc = serializers.FloatField(read_only=True)
    amount_invested = serializers.FloatField(source='amount_invested_res', read_only=True)
    amount_invested_loc = serializers.FloatField(read_only=True)
    position_return = serializers.FloatField(source='pos_return_res', read_only=True)
    position_return_loc = serializers.FloatField(source='pos_return_loc', read_only=True)
    net_position_return = serializers.FloatField(source='net_pos_return_res', read_only=True)
    net_position_return_loc = serializers.FloatField(source='net_pos_return_loc', read_only=True)
    daily_price_change = serializers.FloatField(read_only=True)
    mtd_price_change = serializers.FloatField(read_only=True)

    # P&L ----------------------------------------------------

    # full ----------------------------------------------------
    principal = serializers.FloatField(source='principal_res', read_only=True)
    carry = serializers.FloatField(source='carry_res', read_only=True)
    overheads = serializers.FloatField(source='overheads_res', read_only=True)
    total = serializers.FloatField(source='total_res', read_only=True)

    principal_loc = serializers.FloatField(read_only=True)
    carry_loc = serializers.FloatField(read_only=True)
    overheads_loc = serializers.FloatField(read_only=True)
    total_loc = serializers.FloatField(read_only=True)

    # full / closed ----------------------------------------------------
    principal_closed = serializers.FloatField(source='principal_closed_res', read_only=True)
    carry_closed = serializers.FloatField(source='carry_closed_res', read_only=True)
    overheads_closed = serializers.FloatField(source='overheads_closed_res', read_only=True)
    total_closed = serializers.FloatField(source='total_closed_res', read_only=True)

    principal_closed_loc = serializers.FloatField(read_only=True)
    carry_closed_loc = serializers.FloatField(read_only=True)
    overheads_closed_loc = serializers.FloatField(read_only=True)
    total_closed_loc = serializers.FloatField(read_only=True)

    # full / opened ----------------------------------------------------
    principal_opened = serializers.FloatField(source='principal_opened_res', read_only=True)
    carry_opened = serializers.FloatField(source='carry_opened_res', read_only=True)
    overheads_opened = serializers.FloatField(source='overheads_opened_res', read_only=True)
    total_opened = serializers.FloatField(source='total_opened_res', read_only=True)

    principal_opened_loc = serializers.FloatField(read_only=True)
    carry_opened_loc = serializers.FloatField(read_only=True)
    overheads_opened_loc = serializers.FloatField(read_only=True)
    total_opened_loc = serializers.FloatField(read_only=True)

    # fx ----------------------------------------------------
    principal_fx = serializers.FloatField(source='principal_fx_res', read_only=True)
    carry_fx = serializers.FloatField(source='carry_fx_res', read_only=True)
    overheads_fx = serializers.FloatField(source='overheads_fx_res', read_only=True)
    total_fx = serializers.FloatField(source='total_fx_res', read_only=True)

    principal_fx_loc = serializers.FloatField(read_only=True)
    carry_fx_loc = serializers.FloatField(read_only=True)
    overheads_fx_loc = serializers.FloatField(read_only=True)
    total_fx_loc = serializers.FloatField(read_only=True)

    # fx / closed ----------------------------------------------------
    principal_fx_closed = serializers.FloatField(source='principal_fx_closed_res', read_only=True)
    carry_fx_closed = serializers.FloatField(source='carry_fx_closed_res', read_only=True)
    overheads_fx_closed = serializers.FloatField(source='overheads_fx_closed_res', read_only=True)
    total_fx_closed = serializers.FloatField(source='total_fx_closed_res', read_only=True)

    principal_fx_closed_loc = serializers.FloatField(read_only=True)
    carry_fx_closed_loc = serializers.FloatField(read_only=True)
    overheads_fx_closed_loc = serializers.FloatField(read_only=True)
    total_fx_closed_loc = serializers.FloatField(read_only=True)

    # fx / opened ----------------------------------------------------
    principal_fx_opened = serializers.FloatField(source='principal_fx_opened_res', read_only=True)
    carry_fx_opened = serializers.FloatField(source='carry_fx_opened_res', read_only=True)
    overheads_fx_opened = serializers.FloatField(source='overheads_fx_opened_res', read_only=True)
    total_fx_opened = serializers.FloatField(source='total_fx_opened_res', read_only=True)

    principal_fx_opened_loc = serializers.FloatField(read_only=True)
    carry_fx_opened_loc = serializers.FloatField(read_only=True)
    overheads_fx_opened_loc = serializers.FloatField(read_only=True)
    total_fx_opened_loc = serializers.FloatField(read_only=True)

    # fixed ----------------------------------------------------
    principal_fixed = serializers.FloatField(source='principal_fixed_res', read_only=True)
    carry_fixed = serializers.FloatField(source='carry_fixed_res', read_only=True)
    overheads_fixed = serializers.FloatField(source='overheads_fixed_res', read_only=True)
    total_fixed = serializers.FloatField(source='total_fixed_res', read_only=True)

    principal_fixed_loc = serializers.FloatField(read_only=True)
    carry_fixed_loc = serializers.FloatField(read_only=True)
    overheads_fixed_loc = serializers.FloatField(read_only=True)
    total_fixed_loc = serializers.FloatField(read_only=True)

    # fixed / closed ----------------------------------------------------
    principal_fixed_closed = serializers.FloatField(source='principal_fixed_closed_res', read_only=True)
    carry_fixed_closed = serializers.FloatField(source='carry_fixed_closed_res', read_only=True)
    overheads_fixed_closed = serializers.FloatField(source='overheads_fixed_closed_res', read_only=True)
    total_fixed_closed = serializers.FloatField(source='total_fixed_closed_res', read_only=True)

    principal_fixed_closed_loc = serializers.FloatField(read_only=True)
    carry_fixed_closed_loc = serializers.FloatField(read_only=True)
    overheads_fixed_closed_loc = serializers.FloatField(read_only=True)
    total_fixed_closed_loc = serializers.FloatField(read_only=True)

    # fixed / opened ----------------------------------------------------
    principal_fixed_opened = serializers.FloatField(source='principal_fixed_opened_res', read_only=True)
    carry_fixed_opened = serializers.FloatField(source='carry_fixed_opened_res', read_only=True)
    overheads_fixed_opened = serializers.FloatField(source='overheads_fixed_opened_res', read_only=True)
    total_fixed_opened = serializers.FloatField(source='total_fixed_opened_res', read_only=True)

    principal_fixed_opened_loc = serializers.FloatField(read_only=True)
    carry_fixed_opened_loc = serializers.FloatField(read_only=True)
    overheads_fixed_opened_loc = serializers.FloatField(read_only=True)
    total_fixed_opened_loc = serializers.FloatField(read_only=True)

    # objects and data ----------------------------------------------------

    report_currency_history = serializers.PrimaryKeyRelatedField(source='report_ccy_cur', read_only=True)
    instrument_price_history = serializers.PrimaryKeyRelatedField(source='instr_price_cur', read_only=True)
    instrument_pricing_currency_history = serializers.PrimaryKeyRelatedField(source='instr_pricing_ccy_cur',
                                                                             read_only=True)
    instrument_accrued_currency_history = serializers.PrimaryKeyRelatedField(source='instr_accrued_ccy_cur',
                                                                             read_only=True)
    currency_history = serializers.PrimaryKeyRelatedField(source='ccy_cur', read_only=True)
    pricing_currency_history = serializers.PrimaryKeyRelatedField(source='ccy_cur', read_only=True)

    instrument_accrual = serializers.PrimaryKeyRelatedField(source='instr_accrual', read_only=True)
    instrument_accrual_accrued_price = serializers.FloatField(source='instr_accrual_accrued_price', read_only=True)

    # TODO: deprecated all *_object values
    # portfolio_object = ReportPortfolioSerializer(source='prtfl', read_only=True)
    # account_object = ReportAccountSerializer(source='acc', read_only=True)
    # strategy1_object = ReportStrategy1Serializer(source='str1', read_only=True)
    # strategy2_object = ReportStrategy2Serializer(source='str2', read_only=True)
    # strategy3_object = ReportStrategy3Serializer(source='str3', read_only=True)
    # instrument_object = ReportInstrumentSerializer(source='instr', read_only=True)
    # currency_object = ReportCurrencySerializer(source='ccy', read_only=True)
    # # transaction_currency_object = ReportCurrencySerializer(source='trn_ccy', read_only=True)
    # pricing_currency_object = ReportCurrencySerializer(source='pricing_ccy', read_only=True)
    #
    # allocation_object = ReportInstrumentSerializer(source='alloc', read_only=True)
    # # allocation_balance_object = ReportInstrumentSerializer(source='alloc_bl', read_only=True)
    # # allocation_pl_object = ReportInstrumentSerializer(source='alloc_pl', read_only=True)
    # 
    # mismatch_portfolio_object = ReportPortfolioSerializer(source='mismatch_prtfl', read_only=True)
    # mismatch_account_object = ReportAccountSerializer(source='mismatch_acc', read_only=True)
    #
    # report_currency_history_object = ReportCurrencyHistorySerializer(source='report_ccy_cur', read_only=True)
    # instrument_price_history_object = ReportPriceHistorySerializer(source='instr_price_cur', read_only=True)
    # instrument_pricing_currency_history_object = ReportCurrencyHistorySerializer(source='instr_pricing_ccy_cur',
    #                                                                              read_only=True)
    # instrument_accrued_currency_history_object = ReportCurrencyHistorySerializer(source='instr_accrued_ccy_cur',
    #                                                                              read_only=True)
    # currency_history_object = ReportCurrencyHistorySerializer(source='ccy_cur', read_only=True)
    # pricing_currency_history_object = ReportCurrencyHistorySerializer(source='pricing_ccy_cur', read_only=True)
    #
    # instrument_accrual_object = ReportAccrualCalculationScheduleSerializer(source='instr_accrual')

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('read_only', True)

        super(ReportItemSerializer, self).__init__(*args, **kwargs)

        # from poms.currencies.serializers import CurrencySerializer
        # from poms.instruments.serializers import InstrumentSerializer
        # from poms.portfolios.serializers import PortfolioViewSerializer
        # from poms.accounts.serializers import AccountViewSerializer
        # from poms.strategies.serializers import Strategy1ViewSerializer, Strategy2ViewSerializer, \
        #     Strategy3ViewSerializer

        # self.fields['portfolio_object'] = ReportPortfolioSerializer(source='prtfl', read_only=True)
        # self.fields['account_object'] = ReportAccountSerializer(source='acc', read_only=True)
        # self.fields['strategy1_object'] = ReportStrategy1Serializer(source='str1', read_only=True)
        # self.fields['strategy2_object'] = ReportStrategy2Serializer(source='str2', read_only=True)
        # self.fields['strategy3_object'] = ReportStrategy3Serializer(source='str3', read_only=True)
        # self.fields['instrument_object'] = ReportInstrumentSerializer(source='instr', read_only=True)
        # self.fields['currency_object'] = ReportCurrencySerializer(source='ccy', read_only=True)
        # self.fields['transaction_currency_object'] = ReportCurrencySerializer(source='trn_ccy', read_only=True)
        #
        # self.fields['allocation_balance_object'] = ReportInstrumentSerializer(source='alloc_bl', read_only=True)
        # self.fields['allocation_pl_object'] = ReportInstrumentSerializer(source='alloc_pl', read_only=True)
        #
        # self.fields['mismatch_portfolio_object'] = ReportPortfolioSerializer(source='mismatch_prtfl', read_only=True)
        # self.fields['mismatch_account_object'] = ReportAccountSerializer(source='mismatch_acc', read_only=True)
        # # self.fields['mismatch_currency_object'] = ReportCurrencySerializer(source='mismatch_ccy', read_only=True)
        #
        # self.fields['report_currency_history_object'] = ReportCurrencyHistorySerializer(
        #     source='report_currency_history', read_only=True)
        # self.fields['instrument_price_history_object'] = ReportPriceHistorySerializer(source='instr_price_cur',
        #                                                                               read_only=True)
        # self.fields['instrument_pricing_currency_history_object'] = ReportCurrencyHistorySerializer(
        #     source='instr_pricing_ccy_cur', read_only=True)
        # self.fields['instrument_accrued_currency_history_object'] = ReportCurrencyHistorySerializer(
        #     source='instr_accrued_ccy_cur', read_only=True)
        # self.fields['currency_history_object'] = ReportCurrencyHistorySerializer(source='ccy_cur', read_only=True)

    def get_id(self, obj):
        return ','.join(str(x) for x in obj.pk)

    def get_detail(self, obj):
        # obj_data = formula.get_model_data(obj, ReportItemDetailRendererSerializer, context=self.context)
        # try:
        #     return formula.safe_eval('item.instrument.user_code', names={'item': obj_data})
        # except formula.InvalidExpression:
        #     return 'OLALALALALALA'
        if obj.detail_trn:
            expr = obj.acc.type.transaction_details_expr
            if expr:
                names = {
                    # 'item': formula.get_model_data(obj, ReportItemDetailRendererSerializer, context=self.context),
                    'item': obj,
                }
                try:
                    value = formula.safe_eval(expr, names=names, context=self.context)
                except formula.InvalidExpression:
                    value = ugettext('Invalid expression')
                return value
        return None


class ReportItemEvalSerializer(ReportItemSerializer):
    def __init__(self, *args, **kwargs):
        # kwargs.setdefault('read_only', True)

        super(ReportItemEvalSerializer, self).__init__(*args, **kwargs)
        self.fields.pop('detail')




# class ReportSerializer(serializers.Serializer):
class ReportSerializer(ReportSerializerWithLogs):
    task_id = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    task_status = serializers.ReadOnlyField()

    master_user = MasterUserField()
    member = HiddenMemberField()
    pl_first_date = serializers.DateField(required=False, allow_null=True,
                                          help_text=ugettext_lazy('First date for pl report'))
    report_type = serializers.ChoiceField(read_only=True, choices=Report.TYPE_CHOICES)
    report_date = serializers.DateField(required=False, allow_null=True, default=date_now,
                                        help_text=ugettext_lazy('Report date or second date for pl report'))
    report_currency = CurrencyField(required=False, allow_null=True, default=SystemCurrencyDefault())
    pricing_policy = PricingPolicyField()
    cost_method = serializers.PrimaryKeyRelatedField(queryset=CostMethod.objects, allow_null=True, allow_empty=True)

    portfolio_mode = serializers.ChoiceField(default=Report.MODE_INDEPENDENT,
                                             initial=Report.MODE_INDEPENDENT,
                                             choices=Report.MODE_CHOICES,
                                             required=False,
                                             help_text='Portfolio consolidation')
    account_mode = serializers.ChoiceField(default=Report.MODE_INDEPENDENT,
                                           initial=Report.MODE_INDEPENDENT,
                                           choices=Report.MODE_CHOICES,
                                           required=False,
                                           help_text='Account consolidation')
    strategy1_mode = serializers.ChoiceField(default=Report.MODE_INDEPENDENT,
                                             initial=Report.MODE_INDEPENDENT,
                                             choices=Report.MODE_CHOICES,
                                             required=False,
                                             help_text='Strategy1 consolidation')
    strategy2_mode = serializers.ChoiceField(default=Report.MODE_INDEPENDENT,
                                             initial=Report.MODE_INDEPENDENT,
                                             choices=Report.MODE_CHOICES,
                                             required=False,
                                             help_text='Strategy2 consolidation')
    strategy3_mode = serializers.ChoiceField(default=Report.MODE_INDEPENDENT,
                                             initial=Report.MODE_INDEPENDENT,
                                             choices=Report.MODE_CHOICES,
                                             required=False,
                                             help_text='Strategy3 consolidation')

    show_transaction_details = serializers.BooleanField(default=False, initial=False)
    show_balance_exposure_details = serializers.BooleanField(default=False, initial=False)
    approach_multiplier = serializers.FloatField(default=0.5, initial=0.5, min_value=0.0, max_value=1.0, required=False)
    allocation_detailing = serializers.BooleanField(default=True, initial=True)
    pl_include_zero = serializers.BooleanField(default=False, initial=False)

    custom_fields = BalanceReportCustomFieldField(many=True, allow_empty=True, allow_null=True, required=False)

    custom_fields_to_calculate = serializers.CharField( allow_null=True, allow_blank=True, required=False)

    portfolios = PortfolioField(many=True, required=False, allow_null=True, allow_empty=True)
    accounts = AccountField(many=True, required=False, allow_null=True, allow_empty=True)
    accounts_position = AccountField(many=True, required=False, allow_null=True, allow_empty=True)
    accounts_cash = AccountField(many=True, required=False, allow_null=True, allow_empty=True)
    strategies1 = Strategy1Field(many=True, required=False, allow_null=True, allow_empty=True)
    strategies2 = Strategy2Field(many=True, required=False, allow_null=True, allow_empty=True)
    strategies3 = Strategy3Field(many=True, required=False, allow_null=True, allow_empty=True)
    transaction_classes = serializers.PrimaryKeyRelatedField(queryset=TransactionClass.objects.all(),
                                                             many=True, required=False, allow_null=True,
                                                             allow_empty=True)
    date_field = serializers.ChoiceField(required=False, allow_null=True,
                                         choices=(
                                             ('transaction_date', ugettext('Transaction date')),
                                             ('accounting_date', ugettext('Accounting date')),
                                             ('date', ugettext('Date')),
                                             ('cash_date', ugettext('Cash date')),
                                             ('user_date_1', ugettext('User Date 1')),
                                             ('user_date_2', ugettext('User Date 2')),
                                             ('user_date_3', ugettext('User Date 3')),
                                             ('user_date_4', ugettext('User Date 4')),
                                             ('user_date_5', ugettext('User Date 5')),
                                             ('user_date_6', ugettext('User Date 6')),
                                             ('user_date_7', ugettext('User Date 7')),
                                             ('user_date_8', ugettext('User Date 8')),
                                             ('user_date_9', ugettext('User Date 9')),
                                             ('user_date_10', ugettext('User Date 10')),
                                         ))

    pricing_policy_object = PricingPolicyViewSerializer(source='pricing_policy', read_only=True)
    report_currency_object = CurrencyViewSerializer(source='report_currency', read_only=True)
    cost_method_object = CostMethodSerializer(source='cost_method', read_only=True)
    portfolios_object = PortfolioViewSerializer(source='portfolios', read_only=True, many=True)
    accounts_object = AccountViewSerializer(source='accounts', read_only=True, many=True)
    accounts_position_object = AccountViewSerializer(source='accounts_position', read_only=True, many=True)
    accounts_cash_object = AccountViewSerializer(source='accounts_cash', read_only=True, many=True)
    strategies1_object = Strategy1ViewSerializer(source='strategies1', read_only=True, many=True)
    strategies2_object = Strategy2ViewSerializer(source='strategies2', read_only=True, many=True)
    strategies3_object = Strategy3ViewSerializer(source='strategies3', read_only=True, many=True)
    custom_fields_object = BalanceReportCustomFieldSerializer(source='custom_fields', read_only=True, many=True)
    transaction_classes_object = TransactionClassSerializer(source='transaction_classes',
                                                            read_only=True, many=True)

    # transactions = ReportTransactionSerializer(many=True, read_only=True)
    items = ReportItemSerializer(many=True, read_only=True)

    item_instruments = ReportInstrumentSerializer(many=True, read_only=True)
    item_instrument_types = ReportInstrumentTypeSerializer(many=True, read_only=True)
    item_currencies = ReportCurrencySerializer(many=True, read_only=True)
    item_portfolios = ReportPortfolioSerializer(many=True, read_only=True)
    item_accounts = ReportAccountSerializer(many=True, read_only=True)
    item_account_types = ReportAccountTypeSerializer(many=True, read_only=True)
    item_strategies1 = ReportStrategy1Serializer(many=True, read_only=True)
    item_strategies2 = ReportStrategy2Serializer(many=True, read_only=True)
    item_strategies3 = ReportStrategy3Serializer(many=True, read_only=True)
    item_currency_fx_rates = ReportCurrencyHistorySerializer(many=True, read_only=True)
    item_instrument_pricings = ReportPriceHistorySerializer(many=True, read_only=True)
    item_instrument_accruals = ReportAccrualCalculationScheduleSerializer(many=True, read_only=True)

    def __init__(self, *args, **kwargs):
        super(ReportSerializer, self).__init__(*args, **kwargs)

        # self.fields['pricing_policy_object'] = PricingPolicyViewSerializer(source='pricing_policy', read_only=True)
        # self.fields['report_currency_object'] = CurrencyViewSerializer(source='report_currency', read_only=True)
        # self.fields['cost_method_object'] = CostMethodSerializer(source='cost_method', read_only=True)
        # self.fields['portfolios_object'] = PortfolioViewSerializer(source='portfolios', read_only=True, many=True)
        # self.fields['accounts_object'] = AccountViewSerializer(source='accounts', read_only=True, many=True)
        # self.fields['strategies1_object'] = Strategy1ViewSerializer(source='strategies1', read_only=True, many=True)
        # self.fields['strategies2_object'] = Strategy2ViewSerializer(source='strategies2', read_only=True, many=True)
        # self.fields['strategies3_object'] = Strategy3ViewSerializer(source='strategies3', read_only=True, many=True)
        # self.fields['custom_fields_object'] = BalanceReportCustomFieldSerializer(source='custom_fields', read_only=True,
        #                                                                          many=True)
        # self.fields['transaction_classes_object'] = TransactionClassSerializer(source='transaction_classes',
        #                                                                        read_only=True, many=True)

    def validate(self, attrs):
        if not attrs.get('report_date', None):
            if settings.DEBUG:
                attrs['report_date'] = date(2017, 2, 12)
            else:
                attrs['report_date'] = date_now() - timedelta(days=1)

        pl_first_date = attrs.get('pl_first_date', None)
        if pl_first_date and pl_first_date >= attrs['report_date']:
            raise ValidationError(ugettext('"pl_first_date" must be lesser than "report_date"'))

        # if settings.DEBUG:
        #     if not attrs.get('pl_first_date', None):
        #         attrs['pl_first_date'] = date(2017, 2, 10)

        if not attrs.get('report_currency', None):
            attrs['report_currency'] = attrs['master_user'].system_currency

        if not attrs.get('cost_method', None):
            attrs['cost_method'] = CostMethod.objects.get(pk=CostMethod.AVCO)

        return attrs

    def create(self, validated_data):
        return Report(**validated_data)

    def to_representation(self, instance):

        to_representation_st = time.perf_counter()

        instance.is_report = True

        data = super(ReportSerializer, self).to_representation(instance)

        _l.debug('ReportSerializer to_representation_st done: %s' % "{:3.3f}".format(
            time.perf_counter() - to_representation_st))

        _l.debug('data["custom_fields_to_calculate"] %s' % data["custom_fields_to_calculate"])

        st = time.perf_counter()

        custom_fields = data['custom_fields_object']

        if len(data["custom_fields_to_calculate"]):
            if custom_fields:
                items = data['items']

                item_instruments = {o['id']: o for o in data['item_instruments']}
                item_currencies = {o['id']: o for o in data['item_currencies']}
                item_portfolios = {o['id']: o for o in data['item_portfolios']}
                item_accounts = {o['id']: o for o in data['item_accounts']}
                item_strategies1 = {o['id']: o for o in data['item_strategies1']}
                item_strategies2 = {o['id']: o for o in data['item_strategies2']}
                item_strategies3 = {o['id']: o for o in data['item_strategies3']}
                item_currency_fx_rates = {o['id']: o for o in data['item_currency_fx_rates']}
                item_instrument_pricings = {o['id']: o for o in data['item_instrument_pricings']}
                item_instrument_accruals = {o['id']: o for o in data['item_instrument_accruals']}

                def _set_object(names, pk_attr, objs):

                    if pk_attr in names:
                        pk = names[pk_attr]
                        if pk is not None:

                            try:
                                names['%s_object' % pk_attr] = objs[pk]
                            except KeyError:
                                pass
                                # _l.debug('pk %s' % pk)
                                # _l.debug('pk_attr %s' % pk_attr)
                            # names[pk_attr] = objs[pk]

                for item in items:

                    names = {}

                    for key, value in item.items():
                        names[key] = value

                    _set_object(names, 'portfolio', item_portfolios)
                    _set_object(names, 'account', item_accounts)
                    _set_object(names, 'strategy1', item_strategies1)
                    _set_object(names, 'strategy2', item_strategies2)
                    _set_object(names, 'strategy3', item_strategies3)
                    _set_object(names, 'instrument', item_instruments)
                    _set_object(names, 'currency', item_currencies)
                    _set_object(names, 'pricing_currency', item_currencies)
                    _set_object(names, 'allocation', item_instruments)
                    _set_object(names, 'mismatch_portfolio', item_portfolios)
                    _set_object(names, 'mismatch_account', item_accounts)
                    _set_object(names, 'report_currency_history', item_currency_fx_rates)

                    _set_object(names, 'instrument_price_history', item_instrument_pricings)
                    _set_object(names, 'instrument_pricing_currency_history', item_currency_fx_rates)
                    _set_object(names, 'instrument_accrued_currency_history', item_currency_fx_rates)

                    _set_object(names, 'currency_history', item_currency_fx_rates)
                    _set_object(names, 'pricing_currency_history', item_currency_fx_rates)
                    _set_object(names, 'instrument_accrual', item_instrument_accruals)

                    names = formula.value_prepare(names)

                    # _l.debug('names %s' % names['market_value'])

                    cfv = []

                    custom_fields_names = {}

                    # data["custom_fields_to_calculate"] = 'custom_fields.Currency_asset'

                    # for i in range(5):
                    for i in range(2):

                        for cf in custom_fields:

                            if cf["name"] in data["custom_fields_to_calculate"]:

                                expr = cf['expr']

                                if expr:

                                    try:
                                        value = formula.safe_eval(expr, names=names, context=self.context)
                                    except formula.InvalidExpression as e:
                                        # _l.debug('error %s' % e)
                                        value = ugettext('Invalid expression')
                                else:
                                    value = None

                                if not cf['user_code'] in custom_fields_names:
                                    custom_fields_names[cf['user_code']] = value
                                else:
                                    if custom_fields_names[cf['user_code']] == None or custom_fields_names[
                                        cf['user_code']] == ugettext('Invalid expression'):
                                        custom_fields_names[cf['user_code']] = value

                        names['custom_fields'] = custom_fields_names

                    for key, value in custom_fields_names.items():

                        for cf in custom_fields:

                            if cf['user_code'] == key:

                                expr = cf['expr']

                                if cf['value_type'] == 10:

                                    if expr:
                                        try:
                                            value = formula.safe_eval('str(item)', names={'item': value},
                                                                      context=self.context)
                                        except formula.InvalidExpression:
                                            value = ugettext('Invalid expression (Type conversion error)')
                                    else:
                                        value = None

                                elif cf['value_type'] == 20:

                                    if expr:
                                        try:
                                            value = formula.safe_eval('float(item)', names={'item': value},
                                                                      context=self.context)
                                        except formula.InvalidExpression:
                                            value = ugettext('Invalid expression (Type conversion error)')
                                    else:
                                        value = None
                                elif cf['value_type'] == 40:

                                    if expr:
                                        try:
                                            value = formula.safe_eval("parse_date(item, '%d/%m/%Y')", names={'item': value},
                                                                      context=self.context)
                                        except formula.InvalidExpression:
                                            value = ugettext('Invalid expression (Type conversion error)')
                                    else:
                                        value = None

                                cfv.append({
                                    'custom_field': cf['id'],
                                    'user_code': cf['user_code'],
                                    'value': value,
                                })

                    item['custom_fields'] = cfv

        _l.debug('ReportSerializer custom fields execution done: %s' % "{:3.3f}".format(time.perf_counter() - st))

        return data


class BalanceReportSerializer(ReportSerializer):
    pass


class PLReportSerializer(ReportSerializer):
    pass


def serialize_balance_report_item(item):

    result = {
        # "id": ','.join(str(x) for x in item['pk']),
        "id": '-',
        "name": item["name"],
        "short_name": item["short_name"],
        "user_code": item["user_code"],
        "portfolio": item["portfolio_id"],
        "item_type": item["item_type"],
        "item_type_name": item["item_type_name"],
    }

    if item["instrument_id"] == -1:
        result["instrument"] = None
    else:
        result["instrument"] = item["instrument_id"]

    if item["currency_id"] == -1:
        result["currency"] = None
    else:
        result["currency"] = item["currency_id"]

    if item["pricing_currency_id"] == -1:
        result["pricing_currency"] = None
    else:
        result["pricing_currency"] = item["pricing_currency_id"]

    if item["exposure_currency_id"] == -1:
        result["exposure_currency"] = None
    else:
        result["exposure_currency"] = item["exposure_currency_id"]


    # Check if logic is right
    result["instrument_pricing_currency_fx_rate"] = item["instrument_pricing_currency_fx_rate"]
    result["instrument_accrued_currency_fx_rate"] = item["instrument_accrued_currency_fx_rate"]
    result["instrument_principal_price"] = item["instrument_principal_price"]
    result["instrument_accrued_price"] = item["instrument_accrued_price"]


    result["account"] = item["account_position_id"]

    result["strategy1"] = item["strategy1_position_id"]
    result["strategy2"] = item["strategy2_position_id"]
    result["strategy3"] = item["strategy3_position_id"]

    ids = []
    ids.append(str(result["item_type"]))

    if item['item_type'] == 1:
        ids.append(str(result["instrument"]))

    if item['item_type'] == 2:
        ids.append(str(result["currency"]))

    ids.append(str(result["account"]))
    ids.append(str(result["strategy1"]))
    ids.append(str(result["strategy2"]))
    ids.append(str(result["strategy3"]))

    result['id'] = ','.join(ids)

    # result["pricing_currency"] = item["pricing_currency_id"]
    result["currency"] = None


    result["position_size"] = item["position_size"]
    result["market_value"] = item["market_value"]
    result["market_value_loc"] = item["market_value_loc"]
    result["exposure"] = item["exposure"]
    result["exposure_loc"] = item["exposure_loc"]


    result["ytm"] = item["ytm"]
    result["ytm_at_cost"] = item["ytm_at_cost"]
    result["modified_duration"] = item["modified_duration"]
    result["return_annually"] = item["return_annually"]

    result["position_return"] = item["position_return"]
    result["net_position_return"] = item["net_position_return"]

    result["net_cost_price"] = item["net_cost_price"]
    result["net_cost_price_loc"] = item["net_cost_price_loc"]
    result["gross_cost_price"] = item["gross_cost_price"]
    result["gross_cost_price_loc"] = item["gross_cost_price_loc"]

    result["principal_invested"] = item["principal_invested"]
    result["principal_invested_loc"] = item["principal_invested_loc"]

    result["amount_invested"] = item["amount_invested"]
    result["amount_invested_loc"] = item["amount_invested_loc"]

    result["time_invested"] = item["time_invested"]
    result["return_annually"] = item["return_annually"]

    # performance

    result["principal_opened"] = item["principal_opened"]
    result["carry_opened"] = item["carry_opened"]
    result["overheads_opened"] = item["overheads_opened"]
    result["total_opened"] = item["total_opened"]

    result["principal_fx_opened"] = item["principal_fx_opened"]
    result["carry_fx_opened"] = item["carry_fx_opened"]
    result["overheads_fx_opened"] = item["overheads_fx_opened"]
    result["total_fx_opened"] = item["total_fx_opened"]

    result["principal_fixed_opened"] = item["principal_fixed_opened"]
    result["carry_fixed_opened"] = item["carry_fixed_opened"]
    result["overheads_fixed_opened"] = item["overheads_fixed_opened"]
    result["total_fixed_opened"] = item["total_fixed_opened"]

    # loc started

    result["principal_opened_loc"] = item["principal_opened_loc"]
    result["carry_opened_loc"] = item["carry_opened_loc"]
    result["overheads_opened_loc"] = item["overheads_opened_loc"]
    result["total_opened_loc"] = item["total_opened_loc"]

    result["principal_fx_opened_loc"] = item["principal_fx_opened_loc"]
    result["carry_fx_opened_loc"] = item["carry_fx_opened_loc"]
    result["overheads_fx_opened_loc"] = item["overheads_fx_opened_loc"]
    result["total_fx_opened_loc"] = item["total_fx_opened_loc"]

    result["principal_fixed_opened_loc"] = item["principal_fixed_opened_loc"]
    result["carry_fixed_opened_loc"] = item["carry_fixed_opened_loc"]
    result["overheads_fixed_opened_loc"] = item["overheads_fixed_opened_loc"]
    result["total_fixed_opened_loc"] = item["total_fixed_opened_loc"]

    result["principal_closed"] = item["principal_closed"]
    result["carry_closed"] = item["carry_closed"]
    result["overheads_closed"] = item["overheads_closed"]
    result["total_closed"] = item["total_closed"]

    result["principal_fx_closed"] = item["principal_fx_closed"]
    result["carry_fx_closed"] = item["carry_fx_closed"]
    result["overheads_fx_closed"] = item["overheads_fx_closed"]
    result["total_fx_closed"] = item["total_fx_closed"]

    result["principal_fixed_closed"] = item["principal_fixed_closed"]
    result["carry_fixed_closed"] = item["carry_fixed_closed"]
    result["overheads_fixed_closed"] = item["overheads_fixed_closed"]
    result["total_fixed_closed"] = item["total_fixed_closed"]

    # loc started

    result["principal_closed_loc"] = item["principal_closed_loc"]
    result["carry_closed_loc"] = item["carry_closed_loc"]
    result["overheads_closed_loc"] = item["overheads_closed_loc"]
    result["total_closed_loc"] = item["total_closed_loc"]

    result["principal_fx_closed_loc"] = item["principal_fx_closed_loc"]
    result["carry_fx_closed_loc"] = item["carry_fx_closed_loc"]
    result["overheads_fx_closed_loc"] = item["overheads_fx_closed_loc"]
    result["total_fx_closed_loc"] = item["total_fx_closed_loc"]

    result["principal_fixed_closed_loc"] = item["principal_fixed_closed_loc"]
    result["carry_fixed_closed_loc"] = item["carry_fixed_closed_loc"]
    result["overheads_fixed_closed_loc"] = item["overheads_fixed_closed_loc"]
    result["total_fixed_closed_loc"] = item["total_fixed_closed_loc"]

    return result


def serialize_pl_report_item(item):
    result = {
        # "id": ','.join(str(x) for x in item['pk']),
        "id": '-',
        "name": item["name"],
        "short_name": item["short_name"],
        "user_code": item["user_code"],
        "portfolio": item["portfolio_id"],
        "item_type": item["item_type"],
        "item_type_name": item["item_type_name"],

        "item_group": item["item_group"],
        "item_group_code": item["item_group_code"],
        "item_group_name": item["item_group_name"]
    }

    # if item["item_type"] == 1:  # instrument
    if item["instrument_id"] == -1:
        result["instrument"] = None
    else:
        result["instrument"] = item["instrument_id"]

    if item["pricing_currency_id"] == -1:
            result["pricing_currency"] = None
    else:
        result["pricing_currency"] = item["pricing_currency_id"]

    result["account"] = item["account_position_id"]

    result["strategy1"] = item["strategy1_position_id"]
    result["strategy2"] = item["strategy2_position_id"]
    result["strategy3"] = item["strategy3_position_id"]

    # result["pricing_currency"] = item["pricing_currency_id"]
    # result["currency"] = None

    ids = []
    ids.append(str(result["item_type"]))
    ids.append(str(result["item_group"]))

    if item['item_type'] == 1: # instrument
        ids.append(str(result["instrument"]))

    if item['item_type'] == 3: # FX Variations
        ids.append(str(result["name"]))

    if item['item_type'] == 4: # FX Trades
        ids.append(str(result["name"]))

    if item['item_type'] == 5:
        ids.append(str(result["name"]))

    if item['item_type'] == 6: # mismatch
        ids.append(str(result["instrument"]))


    ids.append(str(result["account"]))
    ids.append(str(result["strategy1"]))
    ids.append(str(result["strategy2"]))
    ids.append(str(result["strategy3"]))

    result['id'] = ','.join(ids)


    result["instrument_pricing_currency_fx_rate"] = item["instrument_pricing_currency_fx_rate"]
    result["instrument_accrued_currency_fx_rate"] = item["instrument_accrued_currency_fx_rate"]
    result["instrument_principal_price"] = item["instrument_principal_price"]
    result["instrument_accrued_price"] = item["instrument_accrued_price"]

    #
    result["position_size"] = item["position_size"]

    result["position_return"] = item["position_return"]
    result["net_position_return"] = item["net_position_return"]

    result["net_cost_price"] = item["net_cost_price"]
    result["net_cost_price_loc"] = item["net_cost_price_loc"]
    result["gross_cost_price"] = item["gross_cost_price"]
    result["gross_cost_price_loc"] = item["gross_cost_price_loc"]

    result["principal_invested"] = item["principal_invested"]
    result["principal_invested_loc"] = item["principal_invested_loc"]

    result["amount_invested"] = item["amount_invested"]
    result["amount_invested_loc"] = item["amount_invested_loc"]

    result["time_invested"] = item["time_invested"]

    result["mismatch"] = item["mismatch"]

    result["ytm"] = item["ytm"]

    result["market_value"] = item["market_value"]
    result["market_value_loc"] = item["market_value_loc"]
    result["exposure"] = item["exposure"]
    result["exposure_loc"] = item["exposure_loc"]

    result["principal"] = item["principal"]
    result["carry"] = item["carry"]
    result["overheads"] = item["overheads"]
    result["total"] = item["total"]

    result["principal_fx"] = item["principal_fx"]
    result["carry_fx"] = item["carry_fx"]
    result["overheads_fx"] = item["overheads_fx"]
    result["total_fx"] = item["total_fx"]

    result["principal_fixed"] = item["principal_fixed"]
    result["carry_fixed"] = item["carry_fixed"]
    result["overheads_fixed"] = item["overheads_fixed"]
    result["total_fixed"] = item["total_fixed"]

    # loc started

    result["principal_loc"] = item["principal_loc"]
    result["carry_loc"] = item["carry_loc"]
    result["overheads_loc"] = item["overheads_loc"]
    result["total_loc"] = item["total_loc"]

    result["principal_fx_loc"] = item["principal_fx_loc"]
    result["carry_fx_loc"] = item["carry_fx_loc"]
    result["overheads_fx_loc"] = item["overheads_fx_loc"]
    result["total_fx_loc"] = item["total_fx_loc"]

    result["principal_fixed_loc"] = item["principal_fixed_loc"]
    result["carry_fixed_loc"] = item["carry_fixed_loc"]
    result["overheads_fixed_loc"] = item["overheads_fixed_loc"]
    result["total_fixed_loc"] = item["total_fixed_loc"]

    return result


def serialize_report_item_instrument(item):

    attributes = []

    for attribute in item.attributes.all():

        attr_result = {
            "id": attribute.id,
            "attribute_type": attribute.attribute_type_id,
            "attribute_type_object": {
                "id": attribute.attribute_type.id,
                "user_code": attribute.attribute_type.user_code,
                "name": attribute.attribute_type.name,
                "short_name": attribute.attribute_type.short_name,
                "value_type": attribute.attribute_type.value_type
            },
            "value_string": attribute.value_string,
            "value_float": attribute.value_float,
            "value_date": attribute.value_date,
            "classifier": attribute.classifier_id
        }

        if attribute.classifier_id:
            attr_result["classifier_object"] = {
                "id": attribute.classifier.id,
                "name": attribute.classifier.name
            }

        attributes.append(attr_result)

    instrument_type = {
        "id": item.instrument_type.id,
        "name": item.instrument_type.name,
        "user_code": item.instrument_type.user_code,
        "short_name": item.instrument_type.short_name
    }


    result = {
        "id": item.id,
        "name": item.name,
        "short_name": item.short_name,
        "user_code": item.user_code,
        "public_name": item.public_name,
        "pricing_currency": item.pricing_currency_id,
        "price_multiplier": item.price_multiplier,
        "accrued_currency": item.accrued_currency_id,
        "accrued_multiplier": item.accrued_multiplier,
        "default_accrued": item.default_accrued,
        "default_price": item.price_multiplier,
        "user_text_1": item.user_text_1,
        "user_text_2": item.user_text_2,
        "user_text_3": item.user_text_3,
        "reference_for_pricing": item.reference_for_pricing,
        "payment_size_detail": item.payment_size_detail_id,
        "maturity_date": item.maturity_date,
        "attributes": attributes,
        "instrument_type": item.instrument_type.id,
        "instrument_type_object": instrument_type
    }

    return result


class BalanceReportSqlSerializer(ReportSerializer):
    items = serializers.SerializerMethodField()

    item_instruments = serializers.SerializerMethodField()

    def get_items(self, obj):

        result = []

        for item in obj.items:
            result.append(serialize_balance_report_item(item))

        return result

    def get_item_instruments(self, obj):

        result = []

        for item in obj.item_instruments:
            result.append(serialize_report_item_instrument(item))

        return result


class PLReportSqlSerializer(ReportSerializer):
    items = serializers.SerializerMethodField()

    item_instruments = serializers.SerializerMethodField()

    def get_items(self, obj):

        result = []

        for item in obj.items:
            result.append(serialize_pl_report_item(item))

        return result

    def get_item_instruments(self, obj):

        _l.debug('get item instruments here')

        result = []

        for item in obj.item_instruments:
            result.append(serialize_report_item_instrument(item))

        return result


def serialize_price_checker_item(item):

    result = {
        "type": item["type"]
    }

    if "name" in item:
        result["name"] = item["name"]

    if "user_code" in item:
        result["user_code"] = item["user_code"]

    if "id" in item:
        result["id"] = item["id"]

    if "accounting_date" in item:
        result["accounting_date"] = item["accounting_date"]

    if "transaction_currency_id" in item:
        result["transaction_currency_id"] = item["transaction_currency_id"]

    if "transaction_currency_name" in item:
        result["transaction_currency_name"] = item["transaction_currency_name"]

    if "transaction_currency_user_code" in item:
        result["transaction_currency_user_code"] = item["transaction_currency_user_code"]

    if "settlement_currency_name" in item:
        result["settlement_currency_name"] = item["settlement_currency_name"]

    if "settlement_currency_user_code" in item:
        result["settlement_currency_user_code"] = item["settlement_currency_user_code"]

    return result

def serialize_price_checker_item_instrument(item):
    # id', 'instrument_type',  'user_code', 'name', 'short_name',
    # 'public_name', 'notes',
    # 'pricing_currency', 'price_multiplier',
    # 'accrued_currency',  'accrued_multiplier',
    # 'default_price', 'default_accrued',
    # 'user_text_1', 'user_text_2', 'user_text_3',
    # 'reference_for_pricing',
    # 'payment_size_detail',
    # 'daily_pricing_model',
    # 'maturity_date', 'maturity_price'

    attributes = []

    for attribute in item.attributes.all():

        attr_result = {
            "id": attribute.id,
            "attribute_type": attribute.attribute_type_id,
            "attribute_type_object": {
                "id": attribute.attribute_type.id,
                "user_code": attribute.attribute_type.user_code,
                "name": attribute.attribute_type.name,
                "short_name": attribute.attribute_type.short_name,
                "value_type": attribute.attribute_type.value_type
            },
            "value_string": attribute.value_string,
            "value_float": attribute.value_float,
            "value_date": attribute.value_date,
            "classifier": attribute.classifier_id
        }

        if attribute.classifier_id:
            attr_result["classifier_object"] = {
                "id": attribute.classifier.id,
                "name": attribute.classifier.name
            }

        attributes.append(attr_result)

    pricing_policies = []

    for policy in item.pricing_policies.all():

        policy_result = {
            "id": policy.id,
            "pricing_policy": policy.pricing_policy_id
        }

        if policy.pricing_scheme_id:

            policy_result["pricing_scheme"] = policy.pricing_scheme_id,
            policy_result["pricing_scheme_object"] = {
                "id": policy.pricing_scheme.id,
                "user_code": policy.pricing_scheme.user_code,
                "name": policy.pricing_scheme.name,
            }

        pricing_policies.append(policy_result)

    instrument_type = {
        "id": item.instrument_type.id,
        "name": item.instrument_type.name,
        "user_code": item.instrument_type.user_code,
        "short_name": item.instrument_type.short_name
    }

    result = {
        "id": item.id,
        "name": item.name,
        "short_name": item.short_name,
        "user_code": item.user_code,
        "public_name": item.public_name,
        "pricing_currency": item.pricing_currency_id,
        "price_multiplier": item.price_multiplier,
        "accrued_currency": item.accrued_currency_id,
        "accrued_multiplier": item.accrued_multiplier,
        "default_accrued": item.default_accrued,
        "default_price": item.price_multiplier,
        "user_text_1": item.user_text_1,
        "user_text_2": item.user_text_2,
        "user_text_3": item.user_text_3,
        "reference_for_pricing": item.reference_for_pricing,
        "payment_size_detail": item.payment_size_detail_id,
        "maturity_date": item.maturity_date,
        "attributes": attributes,
        "pricing_policies": pricing_policies,
        "instrument_type": item.instrument_type.id,
        "instrument_type_object": instrument_type

    }

    return result


class PriceHistoryCheckSqlSerializer(ReportSerializer):
    items = serializers.SerializerMethodField()

    item_instruments = serializers.SerializerMethodField()

    def get_items(self, obj):

        result = []

        for item in obj.items:
            result.append(serialize_price_checker_item(item))

        return result

    def get_item_instruments(self, obj):

        result = []

        for item in obj.item_instruments:
            result.append(serialize_price_checker_item_instrument(item))

        return result




