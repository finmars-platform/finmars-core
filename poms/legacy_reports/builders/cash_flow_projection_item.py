import logging

from django.utils.translation import gettext_lazy
from poms.reports.builders.transaction_item import TransactionReportItem, TransactionReport

_l = logging.getLogger('poms.reports')


class CashFlowProjectionReportItem(TransactionReportItem):
    DEFAULT = 1
    BALANCE = 2
    ROLLING = 3
    TYPE_CHOICES = (
        (DEFAULT, gettext_lazy('Default')),
        (BALANCE, gettext_lazy('Balance')),
        (ROLLING, gettext_lazy('Rolling')),
    )

    def __init__(self, report, type=DEFAULT, trn=None, cash_consideration_before=0.0, cash_consideration_after=0.0,
                 **kwargs):
        super(CashFlowProjectionReportItem, self).__init__(report, trn, **kwargs)
        self.type = type
        # self.position_size_with_sign_before = position_size_with_sign_before
        # self.position_size_with_sign_after = position_size_with_sign_after
        self.cash_consideration_before = cash_consideration_before
        self.cash_consideration_after = cash_consideration_after

    def add_balance(self, trn_or_item, sign=1):
        self.position_size_with_sign += sign * trn_or_item.position_size_with_sign
        self.cash_consideration += sign * trn_or_item.cash_consideration
        self.principal_with_sign += sign * trn_or_item.principal_with_sign
        self.carry_with_sign += sign * trn_or_item.carry_with_sign
        self.overheads_with_sign += sign * trn_or_item.overheads_with_sign

    def __str__(self):
        return 'CashFlowProjectionReportItem:%s' % self.id

    @property
    def type_name(self):
        for i, n in CashFlowProjectionReportItem.TYPE_CHOICES:
            if i == self.type:
                return n
        return 'ERR'

    @property
    def type_code(self):
        if self.type == CashFlowProjectionReportItem.DEFAULT:
            return 'DEFAULT'

        elif self.type == CashFlowProjectionReportItem.BALANCE:
            return 'BALANCE'

        elif self.type == CashFlowProjectionReportItem.ROLLING:
            return 'ROLLING'

        return 'ERR'


class CashFlowProjectionReport(TransactionReport):
    def __init__(self, balance_date=None, report_date=None, **kwargs):
        super(CashFlowProjectionReport, self).__init__(**kwargs)
        self.balance_date = balance_date
        self.report_date = report_date

    def __str__(self):
        return 'CashFlowProjectionReport:%s' % self.id
