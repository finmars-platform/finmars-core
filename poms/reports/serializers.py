from __future__ import unicode_literals

import logging
import time
import uuid
from datetime import timedelta, date

from django.db.models import ForeignKey
from django.utils.translation import gettext_lazy
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.fields import SkipField
from rest_framework.relations import PKOnlyObject
from simplejson import OrderedDict

from poms.accounts.fields import AccountField
from poms.accounts.serializers import AccountViewSerializer
from poms.common import formula
from poms.common.fields import ExpressionField
from poms.common.models import EXPRESSION_FIELD_LENGTH
from poms.common.utils import date_now
from poms.currencies.fields import CurrencyField, SystemCurrencyDefault
from poms.currencies.serializers import CurrencyViewSerializer
from poms.instruments.fields import PricingPolicyField, RegisterField, BundleField
from poms.instruments.models import CostMethod
from poms.instruments.serializers import PricingPolicyViewSerializer, CostMethodSerializer
from poms.portfolios.fields import PortfolioField
from poms.portfolios.serializers import PortfolioViewSerializer
from poms.reports.base_serializers import ReportInstrumentSerializer, ReportInstrumentTypeSerializer, \
    ReportCurrencySerializer, ReportPortfolioSerializer, ReportAccountSerializer, ReportAccountTypeSerializer, \
    ReportStrategy1Serializer, ReportStrategy2Serializer, ReportStrategy3Serializer, ReportCurrencyHistorySerializer, \
    ReportPriceHistorySerializer, ReportAccrualCalculationScheduleSerializer, ReportResponsibleSerializer, \
    ReportCounterpartySerializer, ReportComplexTransactionSerializer
from poms.reports.common import Report, PerformanceReport, TransactionReport
from poms.reports.fields import BalanceReportCustomFieldField, PLReportCustomFieldField, \
    TransactionReportCustomFieldField
from poms.reports.models import BalanceReportCustomField, PLReportCustomField, TransactionReportCustomField, \
    PLReportInstance, BalanceReportInstance, BalanceReportInstanceItem, PLReportInstanceItem, PerformanceReportInstance, \
    PerformanceReportInstanceItem
from poms.reports.serializers_helpers import serialize_price_checker_item, serialize_price_checker_item_instrument, \
    serialize_transaction_report_item, serialize_pl_report_item, serialize_report_item_instrument, \
    serialize_balance_report_item
from poms.strategies.fields import Strategy1Field, Strategy2Field, Strategy3Field
from poms.strategies.serializers import Strategy1ViewSerializer, Strategy2ViewSerializer, Strategy3ViewSerializer
from poms.transactions.models import TransactionClass
from poms.transactions.serializers import TransactionClassSerializer, ComplexTransactionStatusSerializer
from poms.users.fields import MasterUserField, HiddenMemberField
from poms_app import settings

_l = logging.getLogger('poms.reports')


class BalanceReportCustomFieldSerializer(serializers.ModelSerializer):
    master_user = MasterUserField()
    expr = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, allow_blank=True, default='""')

    class Meta:
        model = BalanceReportCustomField
        fields = [
            'id', 'master_user', 'name', 'user_code', 'expr', 'value_type', 'notes'
        ]


class PLReportCustomFieldSerializer(serializers.ModelSerializer):
    master_user = MasterUserField()
    expr = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, allow_blank=True, default='""')

    class Meta:
        model = PLReportCustomField
        fields = [
            'id', 'master_user', 'name', 'user_code', 'expr', 'value_type', 'notes'
        ]


class TransactionReportCustomFieldSerializer(serializers.ModelSerializer):
    master_user = MasterUserField()
    expr = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH, required=False, allow_blank=True, default='""')

    class Meta:
        model = TransactionReportCustomField
        fields = [
            'id', 'master_user', 'name', 'user_code', 'expr', 'value_type', 'notes'
        ]


class ReportSerializerWithLogs(serializers.Serializer):

    pass
    # def to_representation(self, instance):
    #     """
    #     Object instance -> Dict of primitive datatypes.
    #     """
    #     ret = OrderedDict()
    #     fields = self._readable_fields
    #
    #     st = time.perf_counter()
    #
    #     for field in fields:
    #         try:
    #             attribute = field.get_attribute(instance)
    #         except SkipField:
    #             continue
    #
    #         field_st = time.perf_counter()
    #
    #         # We skip `to_representation` for `None` values so that fields do
    #         # not have to explicitly deal with that case.
    #         #
    #         # For related fields with `use_pk_only_optimization` we need to
    #         # resolve the pk value.
    #         check_for_none = attribute.pk if isinstance(attribute, PKOnlyObject) else attribute
    #         if check_for_none is None:
    #             ret[field.field_name] = None
    #         else:
    #             ret[field.field_name] = field.to_representation(attribute)
    #
    #         if 'item_' in field.field_name:
    #             if hasattr(instance, 'is_report'):
    #                 result_time = "{:3.3f}".format(time.perf_counter() - field_st)
    #
    #                 _l.debug('field %s to representation done %s' % (field.field_name, result_time))
    #
    #     if hasattr(instance, 'is_report'):
    #         _l.debug('report to representation done %s' % "{:3.3f}".format(time.perf_counter() - st))
    #
    #     return ret


class ReportSerializer(ReportSerializerWithLogs):
    task_id = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    task_status = serializers.ReadOnlyField()

    master_user = MasterUserField()
    member = HiddenMemberField()

    save_report = serializers.BooleanField(default=False)

    pl_first_date = serializers.DateField(required=False, allow_null=True,
                                          help_text=gettext_lazy('First date for pl report'))
    report_type = serializers.ChoiceField(read_only=True, choices=Report.TYPE_CHOICES)
    report_date = serializers.DateField(required=False, allow_null=True, default=date_now,
                                        help_text=gettext_lazy('Report date or second date for pl report'))
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

    allocation_mode = serializers.ChoiceField(default=Report.MODE_INDEPENDENT,
                                              initial=Report.MODE_INDEPENDENT,
                                              choices=Report.MODE_CHOICES,
                                              required=False,
                                              help_text='Allocation consolidation')

    show_transaction_details = serializers.BooleanField(default=False, initial=False)
    show_balance_exposure_details = serializers.BooleanField(default=False, initial=False)
    approach_multiplier = serializers.FloatField(default=0.5, initial=0.5, min_value=0.0, max_value=1.0, required=False)
    allocation_detailing = serializers.BooleanField(default=True, initial=True)
    pl_include_zero = serializers.BooleanField(default=False, initial=False)
    custom_fields_to_calculate = serializers.CharField(allow_null=True, allow_blank=True, required=False)

    custom_fields = BalanceReportCustomFieldField(many=True, allow_empty=True, allow_null=True, required=False)


    execution_time = serializers.FloatField(allow_null=True, required=False, read_only=True)
    relation_prefetch_time = serializers.FloatField(allow_null=True, required=False, read_only=True)
    serialization_time = serializers.FloatField(allow_null=True, required=False, read_only=True)
    auth_time = serializers.FloatField(allow_null=True, required=False, read_only=True)

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
                                             ('transaction_date', gettext_lazy('Transaction date')),
                                             ('accounting_date', gettext_lazy('Accounting date')),
                                             ('date', gettext_lazy('Date')),
                                             ('cash_date', gettext_lazy('Cash date')),
                                             ('user_date_1', gettext_lazy('User Date 1')),
                                             ('user_date_2', gettext_lazy('User Date 2')),
                                             ('user_date_3', gettext_lazy('User Date 3')),
                                             ('user_date_4', gettext_lazy('User Date 4')),
                                             ('user_date_5', gettext_lazy('User Date 5')),
                                             ('user_date_6', gettext_lazy('User Date 6')),
                                             ('user_date_7', gettext_lazy('User Date 7')),
                                             ('user_date_8', gettext_lazy('User Date 8')),
                                             ('user_date_9', gettext_lazy('User Date 9')),
                                             ('user_date_10', gettext_lazy('User Date 10')),
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
    # items = ReportItemSerializer(many=True, read_only=True)

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

    def validate(self, attrs):

        _l.info("Report Serializer validate start")

        if not attrs.get('report_date', None):
            if settings.DEBUG:
                attrs['report_date'] = date(2017, 2, 12)
            else:
                attrs['report_date'] = date_now() - timedelta(days=1)

        pl_first_date = attrs.get('pl_first_date', None)
        if pl_first_date and pl_first_date >= attrs['report_date']:
            raise ValidationError(gettext_lazy('"pl_first_date" must be lesser than "report_date"'))

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

        # _l.debug('data["custom_fields_to_calculate"] %s' % data["custom_fields_to_calculate"])

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

                for item in items:

                    names = {}

                    for key, value in item.items():
                        names[key] = value

                    names['report_currency'] = data['report_currency']
                    # _set_object(names, 'report_currency', item_currencies)
                    names['report_date'] = data['report_date']
                    names['pl_first_date'] = data['pl_first_date']
                    names['cost_method'] = data['cost_method']
                    names['pricing_policy'] = data['pricing_policy']
                    names['portfolio_mode'] = data['portfolio_mode']
                    names['account_mode'] = data['account_mode']

                    _set_object(names, 'portfolio', item_portfolios)
                    _set_object(names, 'account', item_accounts)
                    _set_object(names, 'strategy1', item_strategies1)
                    _set_object(names, 'strategy2', item_strategies2)
                    _set_object(names, 'strategy3', item_strategies3)
                    _set_object(names, 'instrument', item_instruments)
                    _set_object(names, 'currency', item_currencies)
                    _set_object(names, 'pricing_currency', item_currencies)
                    _set_object(names, 'exposure_currency', item_currencies)
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
                                        # _l.debug('error %s %s' % (cf["name"], e))
                                        value = gettext_lazy('Invalid expression')
                                else:
                                    value = None

                                if not cf['user_code'] in custom_fields_names:
                                    custom_fields_names[cf['user_code']] = value
                                else:
                                    if custom_fields_names[cf['user_code']] == None or custom_fields_names[
                                        cf['user_code']] == gettext_lazy('Invalid expression'):
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
                                            value = gettext_lazy('Invalid expression (Type conversion error)')
                                    else:
                                        value = None

                                elif cf['value_type'] == 20:

                                    if expr:
                                        try:
                                            value = formula.safe_eval('float(item)', names={'item': value},
                                                                      context=self.context)
                                        except formula.InvalidExpression:
                                            value = gettext_lazy('Invalid expression (Type conversion error)')
                                    else:
                                        value = None
                                elif cf['value_type'] == 40:

                                    if expr:
                                        try:
                                            value = formula.safe_eval("parse_date(item, '%d/%m/%Y')",
                                                                      names={'item': value},
                                                                      context=self.context)
                                        except formula.InvalidExpression:
                                            value = gettext_lazy('Invalid expression (Type conversion error)')
                                    else:
                                        value = None

                                cfv.append({
                                    'custom_field': cf['id'],
                                    'user_code': cf['user_code'],
                                    'value': value,
                                })

                    item['custom_fields'] = cfv

        data['serialization_time'] = float("{:3.3f}".format(time.perf_counter() - to_representation_st))

        return data


class BalanceReportSerializer(ReportSerializer):
    calculate_pl = serializers.BooleanField(default=True, initial=True)

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

    def to_representation(self, instance):

        to_representation_st = time.perf_counter()

        data = super(BalanceReportSerializer, self).to_representation(instance)

        report_uuid = str(uuid.uuid4())

        if instance.save_report:

            report_instance_name = ''
            if self.instance.report_instance_name:
                report_instance_name = self.instance.report_instance_name
            else:
                report_instance_name = report_uuid

            try:

                report_instance = BalanceReportInstance.objects.get(
                    master_user=instance.master_user,
                    member=instance.member,
                    user_code=report_instance_name,
                )
            except Exception as e:
                report_instance = BalanceReportInstance.objects.create(
                    master_user=instance.master_user,
                    member=instance.member,
                    user_code=report_instance_name,
                    name=report_instance_name,
                    short_name=report_instance_name,
                    report_date=instance.report_date,
                    report_currency=instance.report_currency,
                    pricing_policy=instance.pricing_policy,
                    cost_method=instance.cost_method,
                )

            report_instance.report_date = instance.report_date
            report_instance.report_currency = instance.report_currency
            report_instance.pricing_policy = instance.pricing_policy
            report_instance.cost_method = instance.cost_method

            report_instance.report_uuid = report_uuid
            report_instance.save()

            BalanceReportInstanceItem.objects.filter(report_instance=report_instance).delete()

            custom_fields_map = {}

            for custom_field in instance.custom_fields:
                custom_fields_map[custom_field.id] = custom_field

            for item in data['items']:

                instance_item = BalanceReportInstanceItem(report_instance=report_instance,
                                                          master_user=instance.master_user,
                                                          member=instance.member,
                                                          report_date=instance.report_date,
                                                          report_currency=instance.report_currency,
                                                          pricing_policy=instance.pricing_policy,
                                                          cost_method=instance.cost_method)

                instance_item.item_id = item['id']

                for field in BalanceReportInstanceItem._meta.fields:

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

                index_text = 1
                index_number = 1
                index_date = 1

                if 'custom_fields' in item:
                    for custom_field_item in item['custom_fields']:

                        cc = custom_fields_map[custom_field_item['custom_field']]

                        try:

                            if cc.value_type == 10:
                                setattr(instance_item, 'custom_field_text_' + str(index_text),
                                        custom_field_item['value'])

                                index_text = index_text + 1

                            if cc.value_type == 20:
                                setattr(instance_item, 'custom_field_number_' + str(index_number),
                                        float(custom_field_item['value']))

                                index_number = index_number + 1

                            if cc.value_type == 40:
                                setattr(instance_item, 'custom_field_date_' + str(index_date),
                                        custom_field_item['value'])

                                index_date = index_date + 1

                        except Exception as e:
                            print("Custom field save error %s" % e)

                            if cc.value_type == 10:
                                index_text = index_text + 1
                            if cc.value_type == 20:
                                index_number = index_number + 1
                            if cc.value_type == 40:
                                index_date = index_date + 1

                instance_item.save()

        data['report_uuid'] = report_uuid

        data['serialization_time'] = float("{:3.3f}".format(time.perf_counter() - to_representation_st))

        return data


class PLReportSerializer(ReportSerializer):
    custom_fields = PLReportCustomFieldField(many=True, allow_empty=True, allow_null=True, required=False)

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

    def to_representation(self, instance):

        to_representation_st = time.perf_counter()

        data = super(PLReportSerializer, self).to_representation(instance)

        report_uuid = str(uuid.uuid4())

        if instance.save_report:

            report_instance_name = ''
            if self.instance.report_instance_name:
                report_instance_name = self.instance.report_instance_name
            else:
                report_instance_name = report_uuid

            try:
                report_instance = PLReportInstance.objects.get(
                    master_user=instance.master_user,
                    member=instance.member,
                    name=report_instance_name,
                )

            except Exception as e:

                report_instance = PLReportInstance.objects.create(
                    master_user=instance.master_user,
                    member=instance.member,
                    user_code=report_instance_name,
                    name=report_instance_name,
                    short_name=report_instance_name,
                    report_date=instance.report_date,
                    pl_first_date=instance.pl_first_date,
                    report_currency=instance.report_currency,
                    pricing_policy=instance.pricing_policy,
                    cost_method=instance.cost_method,
                )

            report_instance.report_uuid = report_uuid
            report_instance.report_date = instance.report_date
            report_instance.pl_first_date = instance.pl_first_date
            report_instance.report_currency = instance.report_currency
            report_instance.pricing_policy = instance.pricing_policy
            report_instance.cost_method = instance.cost_method

            report_instance.save()

            PLReportInstanceItem.objects.filter(report_instance=report_instance).delete()

            custom_fields_map = {}

            for custom_field in instance.custom_fields:
                custom_fields_map[custom_field.id] = custom_field

            for item in data['items']:

                instance_item = PLReportInstanceItem(report_instance=report_instance,
                                                     master_user=instance.master_user,
                                                     member=instance.member,
                                                     report_date=instance.report_date,
                                                     pl_first_date=instance.pl_first_date,
                                                     report_currency=instance.report_currency,
                                                     pricing_policy=instance.pricing_policy,
                                                     cost_method=instance.cost_method)

                instance_item.item_id = item['id']

                for field in PLReportInstanceItem._meta.fields:

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

                index_text = 1
                index_number = 1
                index_date = 1

                if 'custom_fields' in item:
                    for custom_field_item in item['custom_fields']:

                        cc = custom_fields_map[custom_field_item['custom_field']]

                        try:

                            if cc.value_type == 10:
                                setattr(instance_item, 'custom_field_text_' + str(index_text),
                                        custom_field_item['value'])

                                index_text = index_text + 1

                            if cc.value_type == 20:
                                setattr(instance_item, 'custom_field_number_' + str(index_number),
                                        float(custom_field_item['value']))

                                index_number = index_number + 1

                            if cc.value_type == 40:
                                setattr(instance_item, 'custom_field_date_' + str(index_date),
                                        custom_field_item['value'])

                                index_date = index_date + 1

                        except Exception as e:
                            print("Custom field save error %s" % e)

                            if cc.value_type == 10:
                                index_text = index_text + 1
                            if cc.value_type == 20:
                                index_number = index_number + 1
                            if cc.value_type == 40:
                                index_date = index_date + 1

                instance_item.save()

            _l.debug('PLReportSqlSerializer.to_representation done: %s' % "{:3.3f}".format(
                time.perf_counter() - to_representation_st))

        data['report_uuid'] = report_uuid

        return data


class TransactionReportSerializer(ReportSerializerWithLogs):
    task_id = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    task_status = serializers.ReadOnlyField()

    master_user = MasterUserField()
    member = HiddenMemberField()

    date_field = serializers.ChoiceField(required=False, allow_null=True,
                                         choices=(
                                             ('transaction_date', gettext_lazy('Transaction date')),
                                             ('accounting_date', gettext_lazy('Accounting date')),
                                             ('cash_date', gettext_lazy('Cash date')),
                                             ('date', gettext_lazy('Date')),
                                             ('user_date_1', gettext_lazy('User Date 1')),
                                             ('user_date_2', gettext_lazy('User Date 2')),
                                             ('user_date_3', gettext_lazy('User Date 3')),
                                             ('user_date_4', gettext_lazy('User Date 4')),
                                             ('user_date_5', gettext_lazy('User Date 5')),
                                             # ('user_date_6', gettext_lazy('User Date 6')),
                                             # ('user_date_7', gettext_lazy('User Date 7')),
                                             # ('user_date_8', gettext_lazy('User Date 8')),
                                             # ('user_date_9', gettext_lazy('User Date 9')),
                                             # ('user_date_10', gettext_lazy('User Date 10')),
                                         ))

    begin_date = serializers.DateField(required=False, allow_null=True, initial=date_now() - timedelta(days=365),
                                       default=date_now() - timedelta(days=365))
    end_date = serializers.DateField(required=False, allow_null=True, initial=date_now, default=date_now)
    portfolios = PortfolioField(many=True, required=False, allow_null=True, allow_empty=True)
    accounts = AccountField(many=True, required=False, allow_null=True, allow_empty=True)
    accounts_position = AccountField(many=True, required=False, allow_null=True, allow_empty=True)
    accounts_cash = AccountField(many=True, required=False, allow_null=True, allow_empty=True)
    strategies1 = Strategy1Field(many=True, required=False, allow_null=True, allow_empty=True)
    strategies2 = Strategy2Field(many=True, required=False, allow_null=True, allow_empty=True)
    strategies3 = Strategy3Field(many=True, required=False, allow_null=True, allow_empty=True)
    # custom_fields = CustomFieldField(many=True, allow_empty=True, allow_null=True, required=False)

    custom_fields = TransactionReportCustomFieldField(many=True, allow_empty=True, allow_null=True, required=False)
    custom_fields_to_calculate = serializers.CharField(default='', allow_null=True, allow_blank=True, required=False)
    custom_fields_object = TransactionReportCustomFieldSerializer(source='custom_fields', read_only=True, many=True)

    complex_transaction_statuses_filter = serializers.CharField(default='', allow_null=True, allow_blank=True,
                                                                required=False)

    portfolios_object = PortfolioViewSerializer(source='portfolios', read_only=True, many=True)
    accounts_object = AccountViewSerializer(source='accounts', read_only=True, many=True)
    accounts_position_object = AccountViewSerializer(source='accounts_position', read_only=True, many=True)
    accounts_cash_object = AccountViewSerializer(source='accounts_cash', read_only=True, many=True)
    strategies1_object = Strategy1ViewSerializer(source='strategies1', read_only=True, many=True)
    strategies2_object = Strategy2ViewSerializer(source='strategies2', read_only=True, many=True)
    strategies3_object = Strategy3ViewSerializer(source='strategies3', read_only=True, many=True)

    items = serializers.SerializerMethodField()
    item_transaction_classes = TransactionClassSerializer(many=True, read_only=True)
    item_complex_transactions = ReportComplexTransactionSerializer(many=True, read_only=True)
    item_complex_transaction_status = ComplexTransactionStatusSerializer(many=True, read_only=True)
    # item_complex_transactions = ComplexTransactionSerializer(many=True, read_only=True)
    # item_transaction_types = TransactionTypeViewSerializer(source='transaction_types', many=True, read_only=True)
    item_instruments = ReportInstrumentSerializer(many=True, read_only=True)
    item_currencies = ReportCurrencySerializer(many=True, read_only=True)
    item_portfolios = ReportPortfolioSerializer(many=True, read_only=True)
    item_accounts = ReportAccountSerializer(many=True, read_only=True)
    item_strategies1 = ReportStrategy1Serializer(many=True, read_only=True)
    item_strategies2 = ReportStrategy2Serializer(many=True, read_only=True)
    item_strategies3 = ReportStrategy3Serializer(many=True, read_only=True)
    item_responsibles = ReportResponsibleSerializer(many=True, read_only=True)
    item_counterparties = ReportCounterpartySerializer(many=True, read_only=True)

    def __init__(self, *args, **kwargs):
        super(TransactionReportSerializer, self).__init__(*args, **kwargs)

        # self.fields['custom_fields_object'] = CustomFieldViewSerializer(source='custom_fields', read_only=True,
        #                                                                 many=True)

    def create(self, validated_data):
        return TransactionReport(**validated_data)

    def get_items(self, obj):

        result = []

        for item in obj.items:
            result.append(serialize_transaction_report_item(item))

        return result

    def to_representation(self, instance):

        to_representation_st = time.perf_counter()

        instance.is_report = True

        data = super(TransactionReportSerializer, self).to_representation(instance)

        _l.debug('TransactionReportSerializer to_representation_st done: %s' % "{:3.3f}".format(
            time.perf_counter() - to_representation_st))

        st = time.perf_counter()

        items = data['items']
        custom_fields = data['custom_fields_object']

        # _l.info('custom_fields_to_calculate %s' % data["custom_fields_to_calculate"])
        # _l.info('custom_fields %s' % data["custom_fields_object"])

        if len(data["custom_fields_to_calculate"]):

            if custom_fields and items:
                item_transaction_classes = {o['id']: o for o in data['item_transaction_classes']}
                item_complex_transactions = {o['id']: o for o in data['item_complex_transactions']}
                item_instruments = {o['id']: o for o in data['item_instruments']}
                item_currencies = {o['id']: o for o in data['item_currencies']}
                item_portfolios = {o['id']: o for o in data['item_portfolios']}
                item_accounts = {o['id']: o for o in data['item_accounts']}
                item_strategies1 = {o['id']: o for o in data['item_strategies1']}
                item_strategies2 = {o['id']: o for o in data['item_strategies2']}
                item_strategies3 = {o['id']: o for o in data['item_strategies3']}
                item_responsibles = {o['id']: o for o in data['item_responsibles']}
                item_counterparties = {o['id']: o for o in data['item_counterparties']}

                def _set_object(names, pk_attr, objs):
                    pk = names[pk_attr]
                    if pk is not None:

                        try:
                            names['%s_object' % pk_attr] = objs[pk]
                        except KeyError:
                            pass
                            # print('pk %s' % pk)
                            # print('pk_attr %s' % pk_attr)
                        # names[pk_attr] = objs[pk]

                for item in items:

                    names = {}

                    for key, value in item.items():
                        names[key] = value

                    _set_object(names, 'complex_transaction', item_complex_transactions)
                    _set_object(names, 'transaction_class', item_transaction_classes)
                    _set_object(names, 'instrument', item_instruments)
                    _set_object(names, 'transaction_currency', item_currencies)
                    _set_object(names, 'settlement_currency', item_currencies)
                    _set_object(names, 'portfolio', item_portfolios)
                    _set_object(names, 'account_cash', item_accounts)
                    _set_object(names, 'account_position', item_accounts)
                    _set_object(names, 'account_interim', item_accounts)
                    _set_object(names, 'strategy1_position', item_strategies1)
                    _set_object(names, 'strategy1_cash', item_strategies1)
                    _set_object(names, 'strategy2_position', item_strategies2)
                    _set_object(names, 'strategy2_cash', item_strategies2)
                    _set_object(names, 'strategy3_position', item_strategies3)
                    _set_object(names, 'strategy3_cash', item_strategies3)
                    _set_object(names, 'responsible', item_responsibles)
                    _set_object(names, 'counterparty', item_counterparties)
                    _set_object(names, 'linked_instrument', item_instruments)
                    _set_object(names, 'allocation_balance', item_instruments)
                    _set_object(names, 'allocation_pl', item_instruments)

                    names = formula.value_prepare(names)

                    cfv = []

                    custom_fields_names = {}

                    # for i in range(5):
                    for i in range(2):

                        for cf in custom_fields:

                            if cf["name"] in data["custom_fields_to_calculate"]:

                                expr = cf['expr']

                                if expr:
                                    try:
                                        value = formula.safe_eval(expr, names=names, context=self.context)
                                    except formula.InvalidExpression:
                                        value = gettext_lazy('Invalid expression')
                                else:
                                    value = None

                                if not cf['user_code'] in custom_fields_names:
                                    custom_fields_names[cf['user_code']] = value
                                else:
                                    if custom_fields_names[cf['user_code']] == None or custom_fields_names[
                                        cf['user_code']] == gettext_lazy('Invalid expression'):
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
                                            value = gettext_lazy('Invalid expression')
                                    else:
                                        value = None

                                elif cf['value_type'] == 20:

                                    if expr:
                                        try:
                                            value = formula.safe_eval('float(item)', names={'item': value},
                                                                      context=self.context)
                                        except formula.InvalidExpression:
                                            value = gettext_lazy('Invalid expression')
                                    else:
                                        value = None
                                elif cf['value_type'] == 40:

                                    if expr:
                                        try:
                                            value = formula.safe_eval("parse_date(item, '%d/%m/%Y')",
                                                                      names={'item': value}, context=self.context)
                                        except formula.InvalidExpression:
                                            value = gettext_lazy('Invalid expression')
                                    else:
                                        value = None

                                cfv.append({
                                    'custom_field': cf['id'],
                                    'user_code': cf['user_code'],
                                    'value': value,
                                })

                    item['custom_fields'] = cfv

        # _l.debug(
        #     'TransactionReportSerializer custom fields execution done: %s' % "{:3.3f}".format(time.perf_counter() - st))

        data['serialization_time'] = float("{:3.3f}".format(time.perf_counter() - to_representation_st))

        return data


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

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('read_only', True)

        super(PerformanceReportItemSerializer, self).__init__(*args, **kwargs)


class PerformanceReportSerializer(serializers.Serializer):
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
    report_currency = CurrencyField(required=False, allow_null=True, default=SystemCurrencyDefault())
    report_currency_object = CurrencyViewSerializer(source='report_currency', read_only=True)

    items = PerformanceReportItemSerializer(many=True, read_only=True)
    raw_items = serializers.JSONField(allow_null=True, required=False, read_only=True)
    begin_nav = serializers.ReadOnlyField()
    end_nav = serializers.ReadOnlyField()
    grand_return = serializers.ReadOnlyField()
    grand_cash_flow = serializers.ReadOnlyField()
    grand_cash_inflow = serializers.ReadOnlyField()
    grand_cash_outflow = serializers.ReadOnlyField()
    grand_nav = serializers.ReadOnlyField()

    def __init__(self, *args, **kwargs):
        super(PerformanceReportSerializer, self).__init__(*args, **kwargs)

    def create(self, validated_data):
        return PerformanceReport(**validated_data)

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

        data['serialization_time'] = float("{:3.3f}".format(time.perf_counter() - to_representation_st))

        return data


class PriceHistoryCheckSerializer(ReportSerializer):
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
