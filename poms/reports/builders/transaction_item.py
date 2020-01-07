import sys

from datetime import date
from django.utils.translation import ugettext

from poms.common import formula
from poms.reports.builders.base_item import BaseReport

empty = object()


def check_int_min(val):
    return val if val is not None else sys.maxsize


def check_int_max(val):
    return val if val is not None else -sys.maxsize


def check_date_min(val):
    return val if val is not None else date.min


def check_date_max(val):
    return val if val is not None else date.max


def check_val(obj, val, attr, default=None):
    if val is empty:
        if callable(attr):
            val = attr()
        else:
            val = getattr(obj, attr, None)
    if val is None:
        return default
    return val


class TransactionReportItem:
    def __init__(self,
                 report,
                 trn=None,
                 id=empty,
                 complex_transaction=empty,
                 complex_transaction_order=empty,
                 transaction_code=empty,
                 transaction_class=empty,
                 instrument=empty,
                 transaction_currency=empty,
                 position_size_with_sign=empty,
                 settlement_currency=empty,
                 cash_consideration=empty,
                 principal_with_sign=empty,
                 carry_with_sign=empty,
                 overheads_with_sign=empty,
                 transaction_date=empty,
                 accounting_date=empty,
                 cash_date=empty,
                 portfolio=empty,
                 account_position=empty,
                 account_cash=empty,
                 account_interim=empty,
                 strategy1_position=empty,
                 strategy1_cash=empty,
                 strategy2_position=empty,
                 strategy2_cash=empty,
                 strategy3_position=empty,
                 strategy3_cash=empty,
                 responsible=empty,
                 counterparty=empty,
                 linked_instrument=empty,
                 allocation_balance=empty,
                 allocation_pl=empty,
                 reference_fx_rate=empty,

                 factor=empty,
                 trade_price=empty,
                 position_amount=empty,
                 principal_amount=empty,
                 carry_amount=empty,
                 overheads=empty,
                 notes=empty,

                 attributes=empty):
        self.report = report

        self.id = check_val(trn, id, 'id')
        self.complex_transaction = check_val(trn, complex_transaction, 'complex_transaction')
        self.complex_transaction_order = check_val(trn, complex_transaction_order, 'complex_transaction_order')
        self.transaction_code = check_val(trn, transaction_code, 'transaction_code')
        self.transaction_class = check_val(trn, transaction_class, 'transaction_class')

        self.instrument = check_val(trn, instrument, 'instrument')
        self.transaction_currency = check_val(trn, transaction_currency, 'transaction_currency')
        self.position_size_with_sign = check_val(trn, position_size_with_sign, 'position_size_with_sign')
        self.settlement_currency = check_val(trn, settlement_currency, 'settlement_currency')
        self.cash_consideration = check_val(trn, cash_consideration, 'cash_consideration')
        self.principal_with_sign = check_val(trn, principal_with_sign, 'principal_with_sign')
        self.carry_with_sign = check_val(trn, carry_with_sign, 'carry_with_sign')
        self.overheads_with_sign = check_val(trn, overheads_with_sign, 'overheads_with_sign')

        self.transaction_date = check_val(trn, transaction_date, 'transaction_date')
        self.accounting_date = check_val(trn, accounting_date, 'accounting_date')
        self.cash_date = check_val(trn, cash_date, 'cash_date')

        self.portfolio = check_val(trn, portfolio, 'portfolio')
        self.account_position = check_val(trn, account_position, 'account_position')
        self.account_cash = check_val(trn, account_cash, 'account_cash')
        self.account_interim = check_val(trn, account_interim, 'account_interim')

        self.strategy1_position = check_val(trn, strategy1_position, 'strategy1_position')
        self.strategy1_cash = check_val(trn, strategy1_cash, 'strategy1_cash')
        self.strategy2_position = check_val(trn, strategy2_position, 'strategy2_position')
        self.strategy2_cash = check_val(trn, strategy2_cash, 'strategy2_cash')
        self.strategy3_position = check_val(trn, strategy3_position, 'strategy3_position')
        self.strategy3_cash = check_val(trn, strategy3_cash, 'strategy3_cash')

        self.responsible = check_val(trn, responsible, 'responsible')
        self.counterparty = check_val(trn, counterparty, 'counterparty')

        self.linked_instrument = check_val(trn, linked_instrument, 'linked_instrument')
        self.allocation_balance = check_val(trn, allocation_balance, 'allocation_balance')
        self.allocation_pl = check_val(trn, allocation_pl, 'allocation_pl')

        self.reference_fx_rate = check_val(trn, reference_fx_rate, 'reference_fx_rate')
        self.factor = check_val(trn, factor, 'factor')
        self.trade_price = check_val(trn, trade_price, 'trade_price')
        self.position_amount = check_val(trn, position_amount, 'position_amount')
        self.principal_amount = check_val(trn, principal_amount, 'principal_amount')
        self.carry_amount = check_val(trn, carry_amount, 'carry_amount')
        self.overheads = check_val(trn, overheads, 'overheads')
        self.notes = check_val(trn, notes, 'notes')

        # if self.id is None or self.id < 0:
        #     self.attributes = []
        # else:
        #     self.attributes = check_val(trn, attributes, lambda: list(trn.attributes.all()))
        #     # self.attributes = attributes if attributes is not empty else \
        #     #     list(getattr(trn, 'attributes', None).all())

        self.custom_fields = []

    def __str__(self):
        return 'TransactionReportItem:%s' % self.id

    def eval_custom_fields(self):
        # use optimization inside serialization
        res = []
        # for cf in self.report.custom_fields:
        #     if cf.expr and self.report.member:
        #         try:
        #             names = {
        #                 'item': self
        #             }
        #             value = formula.safe_eval(cf.expr, names=names, context=self.report.context)
        #         except formula.InvalidExpression:
        #             value = ugettext('Invalid expression')
        #     else:
        #         value = None
        #     res.append({
        #         'custom_field': cf,
        #         'value': value
        #     })
        self.custom_fields = res


class TransactionReport(BaseReport):
    def __init__(self,
                 id=None,
                 task_id=None,
                 task_status=None,
                 master_user=None,
                 member=None,
                 begin_date=None,
                 end_date=None,
                 portfolios=None,
                 accounts=None,
                 accounts_position=None,
                 accounts_cash=None,
                 strategies1=None,
                 strategies2=None,
                 strategies3=None,
                 custom_fields=None,
                 items=None,
                 date_field=None):
        super(TransactionReport, self).__init__(id=id, master_user=master_user, member=member,
                                                task_id=task_id, task_status=task_status)

        self.has_errors = False

        # self.id = id
        # self.task_id = task_id
        # self.task_status = task_status
        # self.master_user = master_user
        # self.member = member

        self.begin_date = begin_date
        self.end_date = end_date
        self.portfolios = portfolios or []
        self.accounts = accounts or []
        self.accounts_position = accounts_position or []
        self.accounts_cash = accounts_cash or []
        self.strategies1 = strategies1 or []
        self.strategies2 = strategies2 or []
        self.strategies3 = strategies3 or []
        self.custom_fields = custom_fields or []

        # self.context = {
        #     'master_user': self.master_user,
        #     'member': self.member,
        # }

        self.items = items

        self.item_transaction_classes = []
        self.item_complex_transactions = []
        self.item_transaction_types = []
        self.item_instruments = []
        self.item_currencies = []
        self.item_portfolios = []
        self.item_accounts = []
        self.item_strategies1 = []
        self.item_strategies2 = []
        self.item_strategies3 = []
        self.item_responsibles = []
        self.item_counterparties = []

        if date_field:
            self.date_field = date_field
        else:
            self.date_field = 'date'

    def __str__(self):
        return 'TransactionReport:%s' % self.id

    def close(self):
        for item in self.items:
            item.eval_custom_fields()
