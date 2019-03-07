from __future__ import unicode_literals

from django.utils.translation import ugettext
from rest_framework import serializers

from poms.accounts.fields import AccountField
from poms.accounts.serializers import AccountViewSerializer
from poms.common import formula
from poms.portfolios.fields import PortfolioField
from poms.portfolios.serializers import PortfolioViewSerializer
from poms.reports.builders.base_serializers import ReportItemCustomFieldSerializer, ReportPortfolioSerializer, \
    ReportAccountSerializer, ReportStrategy1Serializer, ReportStrategy2Serializer, ReportStrategy3Serializer, \
    ReportInstrumentSerializer, ReportCurrencySerializer, CustomFieldViewSerializer, ReportGenericAttributeSerializer, \
    ReportComplexTransactionSerializer, ReportResponsibleSerializer, ReportCounterpartySerializer
from poms.reports.builders.transaction_item import TransactionReport
from poms.reports.fields import CustomFieldField
from poms.strategies.fields import Strategy1Field, Strategy2Field, Strategy3Field
from poms.strategies.serializers import Strategy1ViewSerializer, Strategy2ViewSerializer, Strategy3ViewSerializer
from poms.transactions.serializers import TransactionClassSerializer, ComplexTransactionSerializer
from poms.users.fields import MasterUserField, HiddenMemberField


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

    custom_fields = ReportItemCustomFieldSerializer(many=True, read_only=True)

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('read_only', True)

        super(TransactionReportItemSerializer, self).__init__(*args, **kwargs)


class TransactionReportSerializer(serializers.Serializer):
    task_id = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    task_status = serializers.ReadOnlyField()

    master_user = MasterUserField()
    member = HiddenMemberField()
    begin_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)
    portfolios = PortfolioField(many=True, required=False, allow_null=True, allow_empty=True)
    accounts = AccountField(many=True, required=False, allow_null=True, allow_empty=True)
    accounts_position = AccountField(many=True, required=False, allow_null=True, allow_empty=True)
    accounts_cash = AccountField(many=True, required=False, allow_null=True, allow_empty=True)
    strategies1 = Strategy1Field(many=True, required=False, allow_null=True, allow_empty=True)
    strategies2 = Strategy2Field(many=True, required=False, allow_null=True, allow_empty=True)
    strategies3 = Strategy3Field(many=True, required=False, allow_null=True, allow_empty=True)
    custom_fields = CustomFieldField(many=True, allow_empty=True, allow_null=True, required=False)

    portfolios_object = PortfolioViewSerializer(source='portfolios', read_only=True, many=True)
    accounts_object = AccountViewSerializer(source='accounts', read_only=True, many=True)
    accounts_position_object = AccountViewSerializer(source='accounts_position', read_only=True, many=True)
    accounts_cash_object = AccountViewSerializer(source='accounts_cash', read_only=True, many=True)
    strategies1_object = Strategy1ViewSerializer(source='strategies1', read_only=True, many=True)
    strategies2_object = Strategy2ViewSerializer(source='strategies2', read_only=True, many=True)
    strategies3_object = Strategy3ViewSerializer(source='strategies3', read_only=True, many=True)
    custom_fields_object = CustomFieldViewSerializer(source='custom_fields', read_only=True, many=True)

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

    # item_complex_transaction_attribute_types = ReportGenericAttributeTypeSerializer(source='complex_transaction_attribute_types', many=True, read_only=True, show_classifiers=True)
    # item_transaction_attribute_types = ReportGenericAttributeTypeSerializer(source='transaction_attribute_types', many=True, read_only=True, show_classifiers=True)
    # item_instrument_attribute_types = ReportGenericAttributeTypeSerializer(source='instrument_attribute_types', many=True, read_only=True, show_classifiers=True)
    # item_currency_attribute_types = ReportGenericAttributeTypeSerializer(source='currency_attribute_types', many=True, read_only=True, show_classifiers=True)
    # item_portfolio_attribute_types = ReportGenericAttributeTypeSerializer(source='portfolio_attribute_types', many=True, read_only=True, show_classifiers=True)
    # item_account_attribute_types = ReportGenericAttributeTypeSerializer(source='account_attribute_types', many=True, read_only=True, show_classifiers=True)
    # item_responsible_attribute_types = ReportGenericAttributeTypeSerializer(source='responsible_attribute_types', many=True, read_only=True, show_classifiers=True)
    # item_counterparty_attribute_types = ReportGenericAttributeTypeSerializer(source='counterparty_attribute_types', many=True, read_only=True, show_classifiers=True)

    # TODO: deprecated names
    # complex_transactions = ReportComplexTransactionSerializer(many=True, read_only=True)
    # transaction_types = TransactionTypeViewSerializer(many=True, read_only=True)
    # instruments = ReportInstrumentSerializer(many=True, read_only=True)
    # currencies = ReportCurrencySerializer(many=True, read_only=True)
    # portfolios = ReportPortfolioSerializer(many=True, read_only=True)
    # accounts = ReportAccountSerializer(many=True, read_only=True)
    # strategies1 = ReportStrategy1Serializer(many=True, read_only=True)
    # strategies2 = ReportStrategy2Serializer(many=True, read_only=True)
    # strategies3 = ReportStrategy3Serializer(many=True, read_only=True)
    # responsibles = ReportResponsibleSerializer(many=True, read_only=True)
    # counterparties = ReportCounterpartySerializer(many=True, read_only=True)
    # complex_transaction_attribute_types = ReportGenericAttributeTypeSerializer(many=True, read_only=True,  show_classifiers=True)
    # transaction_attribute_types = ReportGenericAttributeTypeSerializer(many=True, read_only=True, show_classifiers=True)
    # instrument_attribute_types = ReportGenericAttributeTypeSerializer(many=True, read_only=True, show_classifiers=True)
    # currency_attribute_types = ReportGenericAttributeTypeSerializer(many=True, read_only=True, show_classifiers=True)
    # portfolio_attribute_types = ReportGenericAttributeTypeSerializer(many=True, read_only=True, show_classifiers=True)
    # account_attribute_types = ReportGenericAttributeTypeSerializer(many=True, read_only=True, show_classifiers=True)
    # responsible_attribute_types = ReportGenericAttributeTypeSerializer(many=True, read_only=True, show_classifiers=True)
    # counterparty_attribute_types = ReportGenericAttributeTypeSerializer(many=True, read_only=True, show_classifiers=True)

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
                    names['%s_object' % pk_attr] = objs[pk]

            for item in items:
                names = {n: v for n, v in item.items()}

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
                for cf in custom_fields:
                    expr = cf['expr']

                    if expr:
                        try:
                            value = formula.safe_eval(expr, names={'item': names}, context=self.context)
                        except formula.InvalidExpression:
                            value = ugettext('Invalid expression')
                    else:
                        value = None
                    cfv.append({
                        'custom_field': cf['id'],
                        'value': value,
                    })

                item['custom_fields'] = cfv

        return data
