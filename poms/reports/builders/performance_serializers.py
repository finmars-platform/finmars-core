from __future__ import unicode_literals

import uuid
from datetime import date

from django.db.models import ForeignKey
from django.utils.translation import gettext_lazy
from rest_framework import serializers

from poms.accounts.fields import AccountField
from poms.accounts.serializers import AccountViewSerializer
from poms.common import formula
from poms.common.fields import ExpressionField
from poms.common.utils import date_now
from poms.currencies.fields import CurrencyField, SystemCurrencyDefault
from poms.instruments.fields import PricingPolicyField, InstrumentField, RegisterField, BundleField
from poms.instruments.models import CostMethod
from poms.portfolios.fields import PortfolioField
from poms.portfolios.serializers import PortfolioViewSerializer
from poms.reports.builders.base_serializers import ReportPortfolioSerializer, ReportAccountSerializer, \
    ReportStrategy1Serializer, ReportStrategy2Serializer, ReportStrategy3Serializer
from poms.reports.builders.performance_item import PerformanceReport
from poms.reports.models import BalanceReportInstance, BalanceReportInstanceItem, PerformanceReportInstance, \
    PerformanceReportInstanceItem
from poms.strategies.fields import Strategy1Field, Strategy2Field, Strategy3Field
from poms.strategies.serializers import Strategy1ViewSerializer, Strategy2ViewSerializer, Strategy3ViewSerializer
from poms.users.fields import MasterUserField, HiddenMemberField


class PerformanceReportItemSerializer(serializers.Serializer):
    id = serializers.ReadOnlyField()

    date_from = serializers.CharField(read_only=True)
    date_to = serializers.CharField(read_only=True)

    begin_nav = serializers.FloatField(read_only=True)
    end_nav = serializers.FloatField(read_only=True)

    cash_flow = serializers.FloatField(read_only=True)
    cash_inflow = serializers.FloatField(read_only=True)
    cash_outflow = serializers.FloatField(read_only=True)
    nav = serializers.FloatField(read_only=True)
    instrument_return = serializers.FloatField(read_only=True)
    cumulative_return = serializers.FloatField(read_only=True)

    # period_name = serializers.CharField(read_only=True)
    # period_begin = serializers.DateField(read_only=True)
    # period_end = serializers.DateField(read_only=True)
    #
    # portfolio = serializers.PrimaryKeyRelatedField(read_only=True)
    # account = serializers.PrimaryKeyRelatedField(read_only=True)
    # strategy1 = serializers.PrimaryKeyRelatedField(read_only=True)
    # strategy2 = serializers.PrimaryKeyRelatedField(read_only=True)
    # strategy3 = serializers.PrimaryKeyRelatedField(read_only=True)
    # source_transactions = serializers.ListField(source='src_trns_id', child=serializers.IntegerField(), read_only=True)
    #
    # return_pl = serializers.FloatField(read_only=True)
    # return_nav = serializers.FloatField(read_only=True)
    # pl_in_period = serializers.FloatField(read_only=True)
    # nav_change = serializers.FloatField(read_only=True)
    # nav_period_start = serializers.FloatField(read_only=True)
    # nav_period_end = serializers.FloatField(read_only=True)
    # cash_inflows = serializers.FloatField(read_only=True)
    # cash_outflows = serializers.FloatField(read_only=True)
    # time_weighted_cash_inflows = serializers.FloatField(read_only=True)
    # time_weighted_cash_outflows = serializers.FloatField(read_only=True)
    # avg_nav_in_period = serializers.FloatField(read_only=True)
    # cumulative_return_pl = serializers.FloatField(read_only=True)
    # cumulative_return_nav = serializers.FloatField(read_only=True)

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('read_only', True)

        super(PerformanceReportItemSerializer, self).__init__(*args, **kwargs)


class PerformanceReportSerializer(serializers.Serializer):
    # task_id = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    # task_status = serializers.ReadOnlyField()

    master_user = MasterUserField()
    member = HiddenMemberField()

    save_report = serializers.BooleanField(default=False)

    begin_date = serializers.DateField(required=False, allow_null=True, default=date.min)
    end_date = serializers.DateField(required=False, allow_null=True, default=date_now)
    calculation_type = serializers.ChoiceField(allow_null=True,
                                               initial=PerformanceReport.CALCULATION_TYPE_TIME_WEIGHTED,
                                               default=PerformanceReport.CALCULATION_TYPE_TIME_WEIGHTED,
                                               choices=PerformanceReport.CALCULATION_TYPE_CHOICES, allow_blank=True,
                                               required=False)
    segmentation_type = serializers.ChoiceField(allow_null=True, initial=PerformanceReport.SEGMENTATION_TYPE_MONTHS,
                                                default=PerformanceReport.SEGMENTATION_TYPE_MONTHS,
                                                choices=PerformanceReport.SEGMENTATION_TYPE_CHOICES, allow_blank=True,
                                                required=False)
    registers = RegisterField(many=True, required=False, allow_null=True, allow_empty=True)
    bundle = BundleField(required=False, allow_null=True, allow_empty=True)
    # periods = ExpressionField(required=False, allow_blank=True, allow_null=True, default='',
    #                           initial='date_group(transaction.accounting_date, [[None,None,timedelta(months=1),["[","%Y-%m-%d","/","","%Y-%m-%d","]"]]], "Err")')
    report_currency = CurrencyField(required=False, allow_null=True, default=SystemCurrencyDefault())
    # pricing_policy = PricingPolicyField()

    # portfolio_mode = serializers.ChoiceField(default=PerformanceReport.MODE_INDEPENDENT,
    #                                          initial=PerformanceReport.MODE_INDEPENDENT,
    #                                          choices=PerformanceReport.MODE_CHOICES,
    #                                          required=False,
    #                                          help_text='Portfolio consolidation')
    # account_mode = serializers.ChoiceField(default=PerformanceReport.MODE_INDEPENDENT,
    #                                        initial=PerformanceReport.MODE_INDEPENDENT,
    #                                        choices=PerformanceReport.MODE_CHOICES,
    #                                        required=False,
    #                                        help_text='Account consolidation')
    # strategy1_mode = serializers.ChoiceField(default=PerformanceReport.MODE_INDEPENDENT,
    #                                          initial=PerformanceReport.MODE_INDEPENDENT,
    #                                          choices=PerformanceReport.MODE_CHOICES,
    #                                          required=False,
    #                                          help_text='Strategy1 consolidation')
    # strategy2_mode = serializers.ChoiceField(default=PerformanceReport.MODE_INDEPENDENT,
    #                                          initial=PerformanceReport.MODE_INDEPENDENT,
    #                                          choices=PerformanceReport.MODE_CHOICES,
    #                                          required=False,
    #                                          help_text='Strategy2 consolidation')
    # strategy3_mode = serializers.ChoiceField(default=PerformanceReport.MODE_INDEPENDENT,
    #                                          initial=PerformanceReport.MODE_INDEPENDENT,
    #                                          choices=PerformanceReport.MODE_CHOICES,
    #                                          required=False,
    #                                          help_text='Strategy3 consolidation')
    # cost_method = serializers.PrimaryKeyRelatedField(queryset=CostMethod.objects, allow_null=True, allow_empty=True)
    # approach_multiplier = serializers.FloatField(default=0.5, initial=0.5, min_value=0.0, max_value=1.0, required=False)
    #
    # portfolios = PortfolioField(many=True, required=False, allow_null=True, allow_empty=True)
    # accounts = AccountField(many=True, required=False, allow_null=True, allow_empty=True)
    # accounts_position = AccountField(many=True, required=False, allow_null=True, allow_empty=True)
    # accounts_cash = AccountField(many=True, required=False, allow_null=True, allow_empty=True)
    # strategies1 = Strategy1Field(many=True, required=False, allow_null=True, allow_empty=True)
    # strategies2 = Strategy2Field(many=True, required=False, allow_null=True, allow_empty=True)
    # strategies3 = Strategy3Field(many=True, required=False, allow_null=True, allow_empty=True)
    # custom_fields = CustomFieldField(many=True, allow_empty=True, allow_null=True, required=False)

    # portfolios_object = PortfolioViewSerializer(source='portfolios', read_only=True, many=True)
    # accounts_object = AccountViewSerializer(source='accounts', read_only=True, many=True)
    # accounts_position_object = AccountViewSerializer(source='accounts_position', read_only=True, many=True)
    # accounts_cash_object = AccountViewSerializer(source='accounts_cash', read_only=True, many=True)
    # strategies1_object = Strategy1ViewSerializer(source='strategies1', read_only=True, many=True)
    # strategies2_object = Strategy2ViewSerializer(source='strategies2', read_only=True, many=True)
    # strategies3_object = Strategy3ViewSerializer(source='strategies3', read_only=True, many=True)
    # custom_fields_object = CustomFieldViewSerializer(source='custom_fields', read_only=True, many=True)

    # has_errors = serializers.ReadOnlyField()
    items = PerformanceReportItemSerializer(many=True, read_only=True)
    raw_items = serializers.JSONField(allow_null=True, required=False, read_only=True)
    begin_nav = serializers.ReadOnlyField()
    end_nav = serializers.ReadOnlyField()
    grand_return = serializers.ReadOnlyField()
    grand_cash_flow = serializers.ReadOnlyField()
    grand_cash_inflow = serializers.ReadOnlyField()
    grand_cash_outflow = serializers.ReadOnlyField()
    grand_nav = serializers.ReadOnlyField()

    # item_portfolios = ReportPortfolioSerializer(many=True, read_only=True)
    # item_accounts = ReportAccountSerializer(many=True, read_only=True)
    # item_strategies1 = ReportStrategy1Serializer(many=True, read_only=True)
    # item_strategies2 = ReportStrategy2Serializer(many=True, read_only=True)
    # item_strategies3 = ReportStrategy3Serializer(many=True, read_only=True)

    def __init__(self, *args, **kwargs):
        super(PerformanceReportSerializer, self).__init__(*args, **kwargs)

    def create(self, validated_data):
        return PerformanceReport(**validated_data)

    # def validate(self, attrs):
    #     periods = attrs['periods']
    #     if not periods.startswith('date_group('):
    #         raise serializers.ValidationError({'periods': gettext_lazy('function "date_group" not found')})
    #     return attrs

    def to_representation(self, instance):
        data = super(PerformanceReportSerializer, self).to_representation(instance)

        report_uuid = str(uuid.uuid4())

        if instance.save_report:

            register_ids_list = []
            register_names_list = []
            register_ids = ''
            register_names = ''

            for r in instance.registers:
                register_ids_list.append(str(r.id))
                register_names_list.append(str(r.name))

            register_ids = ", ".join(register_ids_list)
            register_names = ", ".join(register_names_list)

            report_instance_name = ''
            if self.instance.report_instance_name:
                report_instance_name = self.instance.report_instance_name
            else:
                report_instance_name = report_uuid

            report_instance = None

            try:

                report_instance = PerformanceReportInstance.objects.get(
                    master_user=instance.master_user,
                    member=instance.member,
                    user_code=report_instance_name,
                )

            except Exception as e:

                report_instance = PerformanceReportInstance.objects.create(
                    master_user=instance.master_user,
                    member=instance.member,
                    user_code=report_instance_name,
                    name=report_instance_name,
                    short_name=report_instance_name,
                    report_currency=instance.report_currency,
                    begin_date=instance.begin_date,
                    end_date=instance.end_date,
                )

            report_instance.report_currency = instance.report_currency
            report_instance.begin_date = instance.begin_date
            report_instance.end_date = instance.end_date
            report_instance.calculation_type = instance.calculation_type
            report_instance.segmentation_type = instance.segmentation_type
            report_instance.registers = register_ids
            report_instance.registers_names = register_names
            report_instance.begin_nav = instance.begin_nav
            report_instance.end_nav = instance.end_nav
            report_instance.grand_return = instance.grand_return
            report_instance.grand_cash_flow = instance.grand_cash_flow
            report_instance.grand_cash_inflow = instance.grand_cash_inflow
            report_instance.grand_cash_outflow = instance.grand_cash_outflow
            report_instance.grand_nav = instance.grand_nav

            report_instance.report_uuid = report_uuid
            report_instance.save()

            PerformanceReportInstanceItem.objects.filter(report_instance=report_instance).delete()

            custom_fields_map = {}

            for custom_field in instance.custom_fields:
                custom_fields_map[custom_field.id] = custom_field

            for item in data['items']:

                instance_item = PerformanceReportInstanceItem(report_instance=report_instance,
                                                              master_user=instance.master_user,
                                                              member=instance.member,
                                                              begin_date=instance.begin_date,
                                                              end_date=instance.end_date,
                                                              calculation_type=instance.calculation_type,
                                                              segmentation_type=instance.segmentation_type,
                                                              registers=register_ids,
                                                              registers_names=register_names,
                                                              report_currency=instance.report_currency,
                                                              )

                for field in PerformanceReportInstanceItem._meta.fields:

                    if field.name not in ['id']:

                        if field.name in item:

                            if isinstance(field, ForeignKey):

                                try:
                                    setattr(instance_item, field.name + '_id', item[field.name])
                                except Exception as e:
                                    print('exception field %s : %s' % (field.name, e))
                                    setattr(instance_item, field.name, None)

                            else:

                                try:
                                    setattr(instance_item, field.name, item[field.name])
                                except Exception as e:
                                    print('exception field %s : %s' % (field.name, e))
                                    setattr(instance_item, field.name, None)

                instance_item.save()

        data['report_uuid'] = report_uuid

        # items = data['items']
        # custom_fields = data['custom_fields_object']
        # if custom_fields and items:
        #     item_portfolios = {o['id']: o for o in data['item_portfolios']}
        #     item_accounts = {o['id']: o for o in data['item_accounts']}
        #     item_strategies1 = {o['id']: o for o in data['item_strategies1']}
        #     item_strategies2 = {o['id']: o for o in data['item_strategies2']}
        #     item_strategies3 = {o['id']: o for o in data['item_strategies3']}
        #
        #     def _set_object(names, pk_attr, objs):
        #         pk = names[pk_attr]
        #         if pk is not None:
        #             names['%s_object' % pk_attr] = objs[pk]
        #
        #     for item in items:
        #         names = {n: v for n, v in item.items()}
        #
        #         _set_object(names, 'portfolio', item_portfolios)
        #         _set_object(names, 'account', item_accounts)
        #         _set_object(names, 'strategy1', item_strategies1)
        #         _set_object(names, 'strategy2', item_strategies2)
        #         _set_object(names, 'strategy3', item_strategies3)
        #
        #         names = formula.value_prepare(names)
        #
        #         cfv = []
        #
        #         custom_fields_names = {}
        #
        #         # for i in range(5):
        #         for i in range(2):
        #
        #             for cf in custom_fields:
        #
        #                 if cf["name"] in data["custom_fields_to_calculate"]:
        #
        #                     expr = cf['expr']
        #
        #                     if expr:
        #                         try:
        #                             value = formula.safe_eval(expr, names=names, context=self.context)
        #                         except formula.InvalidExpression:
        #                             value = gettext_lazy('Invalid expression')
        #                     else:
        #                         value = None
        #
        #                     if not cf['user_code'] in custom_fields_names:
        #                         custom_fields_names[cf['user_code']] = value
        #                     else:
        #                         if custom_fields_names[cf['user_code']] == None or custom_fields_names[cf['user_code']] == gettext_lazy('Invalid expression'):
        #                             custom_fields_names[cf['user_code']] = value
        #
        #             names['custom_fields'] = custom_fields_names
        #
        #         for key, value in custom_fields_names.items():
        #
        #             for cf in custom_fields:
        #
        #                 if cf['user_code'] == key:
        #
        #                     expr = cf['expr']
        #
        #                     if cf['value_type'] == 10:
        #
        #                         if expr:
        #                             try:
        #                                 value = formula.safe_eval('str(item)', names={'item': value}, context=self.context)
        #                             except formula.InvalidExpression:
        #                                 value = gettext_lazy('Invalid expression')
        #                         else:
        #                             value = None
        #
        #                     elif cf['value_type'] == 20:
        #
        #                         if expr:
        #                             try:
        #                                 value = formula.safe_eval('float(item)', names={'item': value}, context=self.context)
        #                             except formula.InvalidExpression:
        #                                 value = gettext_lazy('Invalid expression')
        #                         else:
        #                             value = None
        #                     elif cf['value_type'] == 40:
        #
        #                         if expr:
        #                             try:
        #                                 value = formula.safe_eval("parse_date(item, '%d/%m/%Y')", names={'item': value}, context=self.context)
        #                             except formula.InvalidExpression:
        #                                 value = gettext_lazy('Invalid expression')
        #                         else:
        #                             value = None
        #
        #                     cfv.append({
        #                         'custom_field': cf['id'],
        #                         'user_code': cf['user_code'],
        #                         'value': value,
        #                     })
        #
        #         item['custom_fields'] = cfv

        return data
