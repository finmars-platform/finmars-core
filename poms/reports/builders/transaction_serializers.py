from __future__ import unicode_literals

from django.utils.translation import ugettext
from rest_framework import serializers

from poms.accounts.fields import AccountField
from poms.accounts.serializers import AccountViewSerializer
from poms.common import formula
from poms.portfolios.fields import PortfolioField
from poms.portfolios.serializers import PortfolioViewSerializer
from poms.reports.builders.base_serializers import ReportPortfolioSerializer, \
    ReportAccountSerializer, ReportStrategy1Serializer, ReportStrategy2Serializer, ReportStrategy3Serializer, \
    ReportInstrumentSerializer, ReportCurrencySerializer, ReportGenericAttributeSerializer, \
    ReportComplexTransactionSerializer, ReportResponsibleSerializer, ReportCounterpartySerializer, \
    ReportItemTransactionReportCustomFieldSerializer, ReportSerializerWithLogs
from poms.reports.builders.transaction_item import TransactionReport
from poms.reports.fields import TransactionReportCustomFieldField
from poms.reports.serializers import TransactionReportCustomFieldSerializer
from poms.strategies.fields import Strategy1Field, Strategy2Field, Strategy3Field
from poms.strategies.serializers import Strategy1ViewSerializer, Strategy2ViewSerializer, Strategy3ViewSerializer
from poms.transactions.serializers import TransactionClassSerializer, ComplexTransactionSerializer
from poms.users.fields import MasterUserField, HiddenMemberField

import time
import logging

_l = logging.getLogger('poms.reports')


class TransactionReportItemSerializer(serializers.Serializer):
    id = serializers.ReadOnlyField()
    # complex_transaction = ReportComplexTransactionSerializer(read_only=True)
    complex_transaction = serializers.PrimaryKeyRelatedField(read_only=True)
    transaction_code = serializers.ReadOnlyField()
    transaction_class = serializers.PrimaryKeyRelatedField(read_only=True)
    instrument = serializers.PrimaryKeyRelatedField(read_only=True)
    transaction_currency = serializers.PrimaryKeyRelatedField(read_only=True)
    position_size_with_sign = serializers.ReadOnlyField()
    settlement_currency = serializers.PrimaryKeyRelatedField(read_only=True)
    cash_consideration = serializers.ReadOnlyField()
    principal_with_sign = serializers.ReadOnlyField()
    carry_with_sign = serializers.ReadOnlyField()
    overheads_with_sign = serializers.ReadOnlyField()
    accounting_date = serializers.DateField(read_only=True)
    cash_date = serializers.DateField(read_only=True)
    transaction_date = serializers.DateField(read_only=True)
    portfolio = serializers.PrimaryKeyRelatedField(read_only=True)
    account_cash = serializers.PrimaryKeyRelatedField(read_only=True)
    account_position = serializers.PrimaryKeyRelatedField(read_only=True)
    account_interim = serializers.PrimaryKeyRelatedField(read_only=True)
    strategy1_position = serializers.PrimaryKeyRelatedField(read_only=True)
    strategy1_cash = serializers.PrimaryKeyRelatedField(read_only=True)
    strategy2_position = serializers.PrimaryKeyRelatedField(read_only=True)
    strategy2_cash = serializers.PrimaryKeyRelatedField(read_only=True)
    strategy3_position = serializers.PrimaryKeyRelatedField(read_only=True)
    strategy3_cash = serializers.PrimaryKeyRelatedField(read_only=True)
    responsible = serializers.PrimaryKeyRelatedField(read_only=True)
    counterparty = serializers.PrimaryKeyRelatedField(read_only=True)
    linked_instrument = serializers.PrimaryKeyRelatedField(read_only=True)
    allocation_balance = serializers.PrimaryKeyRelatedField(read_only=True)
    allocation_pl = serializers.PrimaryKeyRelatedField(read_only=True)
    reference_fx_rate = serializers.ReadOnlyField()
    factor = serializers.ReadOnlyField()
    trade_price = serializers.ReadOnlyField()
    position_amount = serializers.ReadOnlyField()
    principal_amount = serializers.ReadOnlyField()
    carry_amount = serializers.ReadOnlyField()
    overheads = serializers.ReadOnlyField()
    notes = serializers.ReadOnlyField()
    attributes = ReportGenericAttributeSerializer(many=True, read_only=True)

    custom_fields = ReportItemTransactionReportCustomFieldSerializer(many=True, read_only=True)

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('read_only', True)

        super(TransactionReportItemSerializer, self).__init__(*args, **kwargs)


class TransactionReportSerializer(serializers.Serializer):
    task_id = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    task_status = serializers.ReadOnlyField()

    master_user = MasterUserField()
    member = HiddenMemberField()

    date_field = serializers.ChoiceField(required=False, allow_null=True,
                                         choices=(
                                             ('transaction_date', ugettext('Transaction date')),
                                             ('accounting_date', ugettext('Accounting date')),
                                             ('cash_date', ugettext('Cash date')),
                                             ('date', ugettext('Date')),
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

    begin_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)
    portfolios = PortfolioField(many=True, required=False, allow_null=True, allow_empty=True)
    accounts = AccountField(many=True, required=False, allow_null=True, allow_empty=True)
    accounts_position = AccountField(many=True, required=False, allow_null=True, allow_empty=True)
    accounts_cash = AccountField(many=True, required=False, allow_null=True, allow_empty=True)
    strategies1 = Strategy1Field(many=True, required=False, allow_null=True, allow_empty=True)
    strategies2 = Strategy2Field(many=True, required=False, allow_null=True, allow_empty=True)
    strategies3 = Strategy3Field(many=True, required=False, allow_null=True, allow_empty=True)
    # custom_fields = CustomFieldField(many=True, allow_empty=True, allow_null=True, required=False)

    custom_fields = TransactionReportCustomFieldField(many=True, allow_empty=True, allow_null=True, required=False)

    portfolios_object = PortfolioViewSerializer(source='portfolios', read_only=True, many=True)
    accounts_object = AccountViewSerializer(source='accounts', read_only=True, many=True)
    accounts_position_object = AccountViewSerializer(source='accounts_position', read_only=True, many=True)
    accounts_cash_object = AccountViewSerializer(source='accounts_cash', read_only=True, many=True)
    strategies1_object = Strategy1ViewSerializer(source='strategies1', read_only=True, many=True)
    strategies2_object = Strategy2ViewSerializer(source='strategies2', read_only=True, many=True)
    strategies3_object = Strategy3ViewSerializer(source='strategies3', read_only=True, many=True)

    custom_fields_object = TransactionReportCustomFieldSerializer(source='custom_fields', read_only=True, many=True)

    items = TransactionReportItemSerializer(many=True, read_only=True)
    item_transaction_classes = TransactionClassSerializer(many=True, read_only=True)
    item_complex_transactions = ReportComplexTransactionSerializer(many=True, read_only=True)
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

    def to_representation(self, instance):
        data = super(TransactionReportSerializer, self).to_representation(instance)

        items = data['items']
        custom_fields = data['custom_fields_object']

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

                for i in range(5):

                    for cf in custom_fields:
                        expr = cf['expr']

                        if expr:
                            try:
                                value = formula.safe_eval(expr, names=names, context=self.context)
                            except formula.InvalidExpression:
                                value = ugettext('Invalid expression')
                        else:
                            value = None

                        if not cf['user_code'] in custom_fields_names:
                            custom_fields_names[cf['user_code']] = value
                        else:
                            if custom_fields_names[cf['user_code']] == None or custom_fields_names[cf['user_code']] == ugettext('Invalid expression'):
                                custom_fields_names[cf['user_code']] = value

                    names['custom_fields'] = custom_fields_names

                for key, value in custom_fields_names.items():

                    for cf in custom_fields:

                        if cf['user_code'] == key:

                            expr = cf['expr']

                            if cf['value_type'] == 10:

                                if expr:
                                    try:
                                        value = formula.safe_eval('str(item)', names={'item': value}, context=self.context)
                                    except formula.InvalidExpression:
                                        value = ugettext('Invalid expression')
                                else:
                                    value = None

                            elif cf['value_type'] == 20:

                                if expr:
                                    try:
                                        value = formula.safe_eval('float(item)', names={'item': value}, context=self.context)
                                    except formula.InvalidExpression:
                                        value = ugettext('Invalid expression')
                                else:
                                    value = None
                            elif cf['value_type'] == 40:

                                if expr:
                                    try:
                                        value = formula.safe_eval("parse_date(item, '%d/%m/%Y')", names={'item': value}, context=self.context)
                                    except formula.InvalidExpression:
                                        value = ugettext('Invalid expression')
                                else:
                                    value = None

                            cfv.append({
                                'custom_field': cf['id'],
                                'user_code': cf['user_code'],
                                'value': value,
                            })

                item['custom_fields'] = cfv

        return data

def serialize_transaction_report_item(item):
    result = {
        "id": item["id"],

        "transaction_code": item["transaction_code"],
        "transaction_class": item["transaction_class_id"],
        "complex_transaction": item["complex_transaction_id"],

        "portfolio": item["portfolio_id"],
        "counterparty": item["counterparty_id"],
        "responsible": item["responsible_id"],
        "settlement_currency": item["settlement_currency_id"],
        "transaction_currency": item["transaction_currency_id"],

        "account_cash": item["account_cash_id"],
        "account_interim": item["account_interim_id"],
        "account_position": item["account_position_id"],

        "allocation_balance": item["allocation_balance_id"],
        "allocation_pl": item["allocation_pl_id"],
        "instrument": item["instrument_id"],
        "linked_instrument": item["linked_instrument_id"],

        "cash_consideration": item["cash_consideration"],
        "carry_amount": item["carry_amount"],
        "carry_with_sign": item["carry_with_sign"],
        "factor": item["factor"],
        "position_amount": item["position_amount"],
        "position_size_with_sign": item["position_size_with_sign"],
        "principal_amount": item["principal_amount"],
        "principal_with_sign": item["principal_with_sign"],
        "reference_fx_rate": item["reference_fx_rate"],
        "trade_price": item["trade_price"],

        "cash_date": item["cash_date"],
        "accounting_date": item["accounting_date"],
        "transaction_date": item["transaction_date"],

        "strategy1_cash": item["strategy1_cash_id"],
        "strategy1_position": item["strategy1_position_id"],

        "strategy2_cash": item["strategy2_cash_id"],
        "strategy2_position": item["strategy2_position_id"],

        "strategy3_cash": item["strategy3_cash_id"],
        "strategy3_position": item["strategy3_position_id"],

    }


    return result


class TransactionReportSqlSerializer(ReportSerializerWithLogs):
    task_id = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    task_status = serializers.ReadOnlyField()

    master_user = MasterUserField()
    member = HiddenMemberField()

    date_field = serializers.ChoiceField(required=False, allow_null=True,
                                         choices=(
                                             ('transaction_date', ugettext('Transaction date')),
                                             ('accounting_date', ugettext('Accounting date')),
                                             ('cash_date', ugettext('Cash date')),
                                             ('date', ugettext('Date')),
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

    begin_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)
    portfolios = PortfolioField(many=True, required=False, allow_null=True, allow_empty=True)
    accounts = AccountField(many=True, required=False, allow_null=True, allow_empty=True)
    accounts_position = AccountField(many=True, required=False, allow_null=True, allow_empty=True)
    accounts_cash = AccountField(many=True, required=False, allow_null=True, allow_empty=True)
    strategies1 = Strategy1Field(many=True, required=False, allow_null=True, allow_empty=True)
    strategies2 = Strategy2Field(many=True, required=False, allow_null=True, allow_empty=True)
    strategies3 = Strategy3Field(many=True, required=False, allow_null=True, allow_empty=True)
    # custom_fields = CustomFieldField(many=True, allow_empty=True, allow_null=True, required=False)

    custom_fields = TransactionReportCustomFieldField(many=True, allow_empty=True, allow_null=True, required=False)

    portfolios_object = PortfolioViewSerializer(source='portfolios', read_only=True, many=True)
    accounts_object = AccountViewSerializer(source='accounts', read_only=True, many=True)
    accounts_position_object = AccountViewSerializer(source='accounts_position', read_only=True, many=True)
    accounts_cash_object = AccountViewSerializer(source='accounts_cash', read_only=True, many=True)
    strategies1_object = Strategy1ViewSerializer(source='strategies1', read_only=True, many=True)
    strategies2_object = Strategy2ViewSerializer(source='strategies2', read_only=True, many=True)
    strategies3_object = Strategy3ViewSerializer(source='strategies3', read_only=True, many=True)

    custom_fields_object = TransactionReportCustomFieldSerializer(source='custom_fields', read_only=True, many=True)

    items = serializers.SerializerMethodField()
    item_transaction_classes = TransactionClassSerializer(many=True, read_only=True)
    item_complex_transactions = ReportComplexTransactionSerializer(many=True, read_only=True)
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
        super(TransactionReportSqlSerializer, self).__init__(*args, **kwargs)

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

        data = super(TransactionReportSqlSerializer, self).to_representation(instance)

        _l.info('TransactionReportSerializer to_representation_st done: %s' % "{:3.3f}".format(
            time.perf_counter() - to_representation_st))

        st = time.perf_counter()

        items = data['items']
        custom_fields = data['custom_fields_object']

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

                for i in range(5):

                    for cf in custom_fields:
                        expr = cf['expr']

                        if expr:
                            try:
                                value = formula.safe_eval(expr, names=names, context=self.context)
                            except formula.InvalidExpression:
                                value = ugettext('Invalid expression')
                        else:
                            value = None

                        if not cf['user_code'] in custom_fields_names:
                            custom_fields_names[cf['user_code']] = value
                        else:
                            if custom_fields_names[cf['user_code']] == None or custom_fields_names[cf['user_code']] == ugettext('Invalid expression'):
                                custom_fields_names[cf['user_code']] = value

                    names['custom_fields'] = custom_fields_names

                for key, value in custom_fields_names.items():

                    for cf in custom_fields:

                        if cf['user_code'] == key:

                            expr = cf['expr']

                            if cf['value_type'] == 10:

                                if expr:
                                    try:
                                        value = formula.safe_eval('str(item)', names={'item': value}, context=self.context)
                                    except formula.InvalidExpression:
                                        value = ugettext('Invalid expression')
                                else:
                                    value = None

                            elif cf['value_type'] == 20:

                                if expr:
                                    try:
                                        value = formula.safe_eval('float(item)', names={'item': value}, context=self.context)
                                    except formula.InvalidExpression:
                                        value = ugettext('Invalid expression')
                                else:
                                    value = None
                            elif cf['value_type'] == 40:

                                if expr:
                                    try:
                                        value = formula.safe_eval("parse_date(item, '%d/%m/%Y')", names={'item': value}, context=self.context)
                                    except formula.InvalidExpression:
                                        value = ugettext('Invalid expression')
                                else:
                                    value = None

                            cfv.append({
                                'custom_field': cf['id'],
                                'user_code': cf['user_code'],
                                'value': value,
                            })

                item['custom_fields'] = cfv

        _l.info('TransactionReportSerializer custom fields execution done: %s' % "{:3.3f}".format(time.perf_counter() - st))

        return data
