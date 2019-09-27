import uuid

import time
import logging

from poms.common.utils import format_float
from poms.reports.builders.balance_item import Report
from poms.reports.builders.base_item import BaseReportItem, YTMMixin
from poms.transactions.models import TransactionClass

_l = logging.getLogger('poms.reports')


class VirtualTransaction(YTMMixin, BaseReportItem):
    trn = None
    lid = None
    key = None
    pk = None
    is_hidden = False  # if True it is not involved in the calculations
    is_mismatch = True
    trn_code = None
    trn_cls = None
    # case = 0
    avco_multiplier = 0.0
    avco_closed_by = None
    avco_rolling_pos_size = 0.0
    fifo_multiplier = 0.0
    fifo_closed_by = None
    fifo_rolling_pos_size = 0.0
    multiplier = 0.0
    closed_by = None
    rolling_pos_size = 0.0

    # Position related
    instr = None
    trn_ccy = None
    pos_size = 0.0

    # Cash related
    pricing_ccy = None
    stl_ccy = None
    cash = 0.0

    # P&L related
    principal = 0.0
    carry = 0.0
    overheads = 0.0

    ref_fx = 0.0

    # accounting dates
    trn_date = None
    acc_date = None
    cash_date = None

    # portfolio
    prtfl = None

    # accounts
    acc_pos = None
    acc_cash = None
    acc_interim = None

    # strategies
    str1_pos = None
    str1_cash = None
    str2_pos = None
    str2_cash = None
    str3_pos = None
    str3_cash = None

    # linked instrument
    link_instr = None

    # allocations
    alloc = None
    alloc_bl = None
    alloc_pl = None

    trade_price = 0.0

    # total_real_res = 0.0
    # total_unreal_res = 0.0
    notes = None

    # calculated
    case = 0

    # report ccy
    report_ccy_cur = None
    report_ccy_cur_fx = 0.0
    report_ccy_cash_hist = None
    report_ccy_cash_hist_fx = 0.0
    report_ccy_acc_hist = None
    report_ccy_acc_hist_fx = 0.0

    # report ccy
    pricing_ccy_cur = None
    pricing_ccy_cur_fx = 0.0
    pricing_ccy_cash_hist = None
    pricing_ccy_cash_hist_fx = 0.0
    pricing_ccy_acc_hist = None
    pricing_ccy_acc_hist_fx = 0.0

    # instr
    instr_price_cur = None
    instr_price_cur_principal_price = 0.0
    instr_price_cur_accrued_price = 0.0
    instr_pricing_ccy_cur = None
    instr_pricing_ccy_cur_fx = 0.0
    instr_accrued_ccy_cur = None
    instr_accrued_ccy_cur_fx = 0.0

    # trn ccy
    trn_ccy_cash_hist = None
    trn_ccy_cash_hist_fx = 0.0
    trn_ccy_cash_hist_fx_loc = 0.0
    trn_ccy_acc_hist = None
    trn_ccy_acc_hist_fx = 0.0
    trn_ccy_acc_hist_fx_loc = 0.0
    trn_ccy_cur = None
    trn_ccy_cur_fx = 0.0
    trn_ccy_cur_fx_loc = 0.0

    # stl ccy
    stl_ccy_cash_hist = None
    stl_ccy_cash_hist_fx = 0.0
    stl_ccy_cash_hist_fx_loc = 0.0
    stl_ccy_acc_hist = None
    stl_ccy_acc_hist_fx = 0.0
    stl_ccy_acc_hist_fx_loc = 0.0
    stl_ccy_cur = None
    stl_ccy_cur_fx = 0.0
    stl_ccy_cur_fx_loc = 0.0

    # general

    mismatch = 0.0

    instr_principal = 0.0
    instr_principal_res = 0.0
    instr_accrued = 0.0
    instr_accrued_res = 0.0

    cost_res = 0.0
    gross_cost_res = 0.0
    gross_cost_loc = 0.0
    net_cost_res = 0.0
    net_cost_loc = 0.0
    principal_invested_res = 0.0
    principal_invested_loc = 0.0
    amount_invested_res = 0.0
    amount_invested_loc = 0.0

    balance_pos_size = 0.0
    sum_remaining_pos_size = 0.0  # sum of remaining_pos_size by trns before current
    remaining_pos_size = 0.0
    remaining_pos_size_percent = 0.0  # calculated in second pass
    ytm = 0.0
    time_invested_days = 0.0
    time_invested = 0.0
    weighted_ytm = 0.0  # calculated in second pass
    weighted_time_invested_days = 0.0  # calculated in second pass
    weighted_time_invested = 0.0  # calculated in second pass

    # Cash related

    cash_res = 0.0

    # full P&L related
    total = 0.0

    principal_res = 0.0
    carry_res = 0.0
    overheads_res = 0.0
    total_res = 0.0

    principal_loc = 0.0
    carry_loc = 0.0
    overheads_loc = 0.0
    total_loc = 0.0

    # full / closed
    principal_closed_res = 0.0
    carry_closed_res = 0.0
    overheads_closed_res = 0.0
    total_closed_res = 0.0

    principal_closed_loc = 0.0
    carry_closed_loc = 0.0
    overheads_closed_loc = 0.0
    total_closed_loc = 0.0

    # full / opened
    principal_opened_res = 0.0
    carry_opened_res = 0.0
    overheads_opened_res = 0.0
    total_opened_res = 0.0

    principal_opened_loc = 0.0
    carry_opened_loc = 0.0
    overheads_opened_loc = 0.0
    total_opened_loc = 0.0

    # fx
    pl_fx_mul = 0.0
    principal_fx_res = 0.0
    carry_fx_res = 0.0
    overheads_fx_res = 0.0
    total_fx_res = 0.0

    pl_fx_mul_loc = 0.0
    principal_fx_loc = 0.0
    carry_fx_loc = 0.0
    overheads_fx_loc = 0.0
    total_fx_loc = 0.0

    # fx / closed
    principal_fx_closed_res = 0.0
    carry_fx_closed_res = 0.0
    overheads_fx_closed_res = 0.0
    total_fx_closed_res = 0.0

    principal_fx_closed_loc = 0.0
    carry_fx_closed_loc = 0.0
    overheads_fx_closed_loc = 0.0
    total_fx_closed_loc = 0.0

    # fx / opened
    principal_fx_opened_res = 0.0
    carry_fx_opened_res = 0.0
    overheads_fx_opened_res = 0.0
    total_fx_opened_res = 0.0

    principal_fx_opened_loc = 0.0
    carry_fx_opened_loc = 0.0
    overheads_fx_opened_loc = 0.0
    total_fx_opened_loc = 0.0

    # fixed
    pl_fixed_mul = 0.0
    principal_fixed_res = 0.0
    carry_fixed_res = 0.0
    overheads_fixed_res = 0.0
    total_fixed_res = 0.0

    pl_fixed_mul_loc = 0.0
    principal_fixed_loc = 0.0
    carry_fixed_loc = 0.0
    overheads_fixed_loc = 0.0
    total_fixed_loc = 0.0

    # fixed / closed
    principal_fixed_closed_res = 0.0
    carry_fixed_closed_res = 0.0
    overheads_fixed_closed_res = 0.0
    total_fixed_closed_res = 0.0

    principal_fixed_closed_loc = 0.0
    carry_fixed_closed_loc = 0.0
    overheads_fixed_closed_loc = 0.0
    total_fixed_closed_loc = 0.0

    # fixed / opened
    principal_fixed_opened_res = 0.0
    carry_fixed_opened_res = 0.0
    overheads_fixed_opened_res = 0.0
    total_fixed_opened_res = 0.0

    principal_fixed_opened_loc = 0.0
    carry_fixed_opened_loc = 0.0
    overheads_fixed_opened_loc = 0.0
    total_fixed_opened_loc = 0.0

    dump_columns = [
        'is_cloned',
        # 'lid',
        'pk',
        # 'is_hidden',
        # 'is_mismatch',
        # 'trn_code',
        'trn_cls',
        # 'avco_multiplier',
        # 'avco_closed_by',
        # 'fifo_multiplier',
        # 'fifo_closed_by',
        'multiplier',
        'closed_by',
        'instr',
        'trn_ccy',
        'pos_size',
        'stl_ccy',
        'cash',
        'principal',
        'carry',
        'overheads',
        'ref_fx',
        'trn_date',
        'acc_date',
        'cash_date',
        'prtfl',
        'acc_pos',
        'acc_cash',
        'acc_interim',
        'str1_pos',
        'str1_cash',
        'str2_pos',
        'str2_cash',
        'str3_pos',
        'str3_cash',
        'link_instr',
        'alloc_bl',
        'alloc_pl',
        'trade_price',
        'notes',
        'case',
        'report_ccy_cur',
        'report_ccy_cur_fx',
        'report_ccy_cash_hist',
        'report_ccy_cash_hist_fx',
        'report_ccy_acc_hist',
        'report_ccy_acc_hist_fx',
        'instr_price_cur',
        'instr_price_cur_principal_price',
        'instr_price_cur_accrued_price',
        'instr_pricing_ccy_cur',
        'instr_pricing_ccy_cur_fx',
        'instr_accrued_ccy_cur',
        'instr_accrued_ccy_cur_fx',
        'trn_ccy_cash_hist',
        'trn_ccy_cash_hist_fx',
        'trn_ccy_acc_hist',
        'trn_ccy_acc_hist_fx',
        'trn_ccy_cur',
        'trn_ccy_cur_fx',
        'stl_ccy_cash_hist',
        'stl_ccy_cash_hist_fx',
        'stl_ccy_acc_hist',
        'stl_ccy_acc_hist_fx',
        'stl_ccy_cur',
        'stl_ccy_cur_fx',
        'mismatch',
        'instr_principal',
        'instr_principal_res',
        'instr_accrued',
        'instr_accrued_res',
        'gross_cost_res',
        'net_cost_res',
        'principal_invested_res',
        'amount_invested_res',
        'remaining_pos_size',
        'remaining_pos_size_percent',
        'ytm',
        'time_invested_days',
        'time_invested',
        'weighted_ytm',
        'weighted_time_invested_days',
        'weighted_time_invested',
        'cash_res',
        'total',
        'principal_res',
        'carry_res',
        'overheads_res',
        'total_res',
        'principal_closed_res',
        'carry_closed_res',
        'overheads_closed_res',
        'total_closed_res',
        'principal_opened_res',
        'carry_opened_res',
        'overheads_opened_res',
        'total_opened_res',
        'pl_fx_mul',
        'principal_fx_res',
        'carry_fx_res',
        'overheads_fx_res',
        'total_fx_res',
        'principal_fx_closed_res',
        'carry_fx_closed_res',
        'overheads_fx_closed_res',
        'total_fx_closed_res',
        'principal_fx_opened_res',
        'carry_fx_opened_res',
        'overheads_fx_opened_res',
        'total_fx_opened_res',
        'pl_fixed_mul',
        'principal_fixed_res',
        'carry_fixed_res',
        'overheads_fixed_res',
        'total_fixed_res',
        'principal_fixed_closed_res',
        'carry_fixed_closed_res',
        'overheads_fixed_closed_res',
        'total_fixed_closed_res',
        'principal_fixed_opened_res',
        'carry_fixed_opened_res',
        'overheads_fixed_opened_res',
        'total_fixed_opened_res',
    ]

    def __init__(self, report, pricing_provider, fx_rate_provider, trn, overrides=None):

        create_virtual_transaction_st = time.perf_counter()

        super(VirtualTransaction, self).__init__(report, pricing_provider, fx_rate_provider)
        overrides = overrides or {}

        # _l.debug(len(self.__class__.__dict__))

        self.lid = uuid.uuid1()

        self.trn = trn

        self.pk = trn.pk
        self.trn_code = trn.transaction_code
        self.trn_cls = trn.transaction_class

        self.instr = trn.instrument
        self.trn_ccy = trn.transaction_currency
        self.pos_size = trn.position_size_with_sign

        self.stl_ccy = trn.settlement_currency
        self.cash = trn.cash_consideration

        self.principal = trn.principal_with_sign
        self.carry = trn.carry_with_sign
        self.overheads = trn.overheads_with_sign

        self.ref_fx = trn.reference_fx_rate

        self.trn_date = trn.transaction_date
        self.acc_date = trn.accounting_date
        self.cash_date = trn.cash_date

        self.link_instr = trn.linked_instrument

        self.prtfl = trn.portfolio

        self.acc_pos = trn.account_position
        self.acc_cash = trn.account_cash
        self.acc_interim = trn.account_interim

        self.str1_pos = trn.strategy1_position
        self.str1_cash = trn.strategy1_cash

        self.str2_pos = trn.strategy2_position
        self.str2_cash = trn.strategy2_cash

        self.str3_pos = trn.strategy3_position
        self.str3_cash = trn.strategy3_cash

        self.alloc_bl = trn.allocation_balance
        self.alloc_pl = trn.allocation_pl

        self.trade_price = trn.trade_price
        self.notes = trn.notes

        # _l.debug(overrides)
        if len(overrides):
            self.override(overrides)

        if report.report_type == Report.TYPE_BALANCE:
            self.alloc = self.alloc_bl
        elif report.report_type == Report.TYPE_PL:
            self.alloc = self.alloc_pl
        else:
            # raise RuntimeError('Bad report type: %s' % (report.report_type,))
            pass

        self.set_case()

        res = time.perf_counter() - create_virtual_transaction_st

        # if res > 0.03:
        #     _l.debug('create virtual transaction done: %s', res)

    def set_case(self):
        if self.acc_date <= self.report.report_date < self.cash_date:
            self.case = 1
        elif self.cash_date <= self.report.report_date < self.acc_date:
            self.case = 2
        else:
            self.case = 0

    def __str__(self):
        return str(self.trn_code)

    def __repr__(self):
        return 'VT(%s)' % self.pk

    # def clone(self):
    #     ret = super(VirtualTransaction, self).clone()
    #     ret.lid = uuid.uuid1()
    #     return ret

    def override(self, overrides):

        if 'portfolio' in overrides:
            self.prtfl = overrides['portfolio']

        if 'account_position' in overrides:
            self.acc_pos = overrides['account_position']
        if 'account_cash' in overrides:
            self.acc_cash = overrides['account_cash']
        if 'account_interim' in overrides:
            self.acc_interim = overrides['account_interim']

        if 'strategy1_position' in overrides:
            self.str1_pos = overrides['strategy1_position']
        if 'strategy1_cash' in overrides:
            self.str1_cash = overrides['strategy1_cash']

        if 'strategy2_position' in overrides:
            self.str2_pos = overrides['strategy2_position']
        if 'strategy2_cash' in overrides:
            self.str2_cash = overrides['strategy2_cash']

        if 'strategy3_position' in overrides:
            self.str3_pos = overrides['strategy3_position']
        if 'strategy3_cash' in overrides:
            self.str3_cash = overrides['strategy3_cash']

        if 'allocation_balance' in overrides:
            self.alloc_bl = overrides['allocation_balance']
        if 'allocation_pl' in overrides:
            self.alloc_pl = overrides['allocation_pl']

    @property
    def is_buy(self):
        return self.trn_cls.id == TransactionClass.BUY

    @property
    def is_sell(self):
        return self.trn_cls.id == TransactionClass.SELL

    @property
    def is_fx_trade(self):
        return self.trn_cls.id == TransactionClass.FX_TRADE

    @property
    def is_instrument_pl(self):
        return self.trn_cls.id == TransactionClass.INSTRUMENT_PL

    @property
    def is_transaction_pl(self):
        return self.trn_cls.id == TransactionClass.TRANSACTION_PL

    @property
    def is_transfer(self):
        return self.trn_cls.id == TransactionClass.TRANSFER

    @property
    def is_fx_transfer(self):
        return self.trn_cls.id == TransactionClass.FX_TRANSFER

    @property
    def is_cash_inflow(self):
        return self.trn_cls.id == TransactionClass.CASH_INFLOW

    @property
    def is_cash_outflow(self):
        return self.trn_cls.id == TransactionClass.CASH_OUTFLOW

    def pricing(self):
        # report ccy
        self.report_ccy_cur = self.fx_rate_provider[self.report.report_currency]
        self.report_ccy_cur_fx = self.report_ccy_cur.fx_rate

        self.report_ccy_cash_hist = self.fx_rate_provider[self.report.report_currency, self.cash_date]
        self.report_ccy_cash_hist_fx = self.report_ccy_cash_hist.fx_rate

        self.report_ccy_acc_hist = self.fx_rate_provider[self.report.report_currency, self.acc_date]
        self.report_ccy_acc_hist_fx = self.report_ccy_acc_hist.fx_rate

        try:
            report_ccy_cur_fx = 1.0 / self.report_ccy_cur_fx
        except ArithmeticError:
            report_ccy_cur_fx = 0.0
        try:
            report_ccy_cash_hist_fx = 1.0 / self.report_ccy_cash_hist_fx
        except ArithmeticError:
            report_ccy_cash_hist_fx = 0.0
        try:
            report_ccy_acc_hist_fx = 1.0 / self.report_ccy_acc_hist_fx
        except ArithmeticError:
            report_ccy_acc_hist_fx = 0.0

        # pricing ccy
        if self.trn_cls.id in [TransactionClass.BUY, TransactionClass.SELL, TransactionClass.INSTRUMENT_PL]:
            self.pricing_ccy = getattr(self.instr, 'pricing_currency', None)
            if self.pricing_ccy is None:
                self.pricing_ccy = self.report.master_user.currency

        elif self.trn_cls.id in [TransactionClass.FX_TRADE, TransactionClass.TRANSACTION_PL,
                                 TransactionClass.CASH_INFLOW, TransactionClass.CASH_INFLOW]:
            self.pricing_ccy = self.report.report_currency
        else:
            self.pricing_ccy = self.report.report_currency

        if self.pricing_ccy.id == self.report.report_currency.id:
            self.pricing_ccy_cur = self.report_ccy_cur
            self.pricing_ccy_cur_fx = self.report_ccy_cur_fx

            self.pricing_ccy_cash_hist = self.report_ccy_cash_hist
            self.pricing_ccy_cash_hist_fx = self.report_ccy_cash_hist_fx

            self.pricing_ccy_acc_hist = self.report_ccy_acc_hist
            self.pricing_ccy_acc_hist_fx = self.report_ccy_acc_hist_fx

            pricing_ccy_cur_fx = report_ccy_cur_fx
            pricing_ccy_cash_hist_fx = report_ccy_cash_hist_fx
            pricing_ccy_acc_hist_fx = report_ccy_acc_hist_fx

        else:
            self.pricing_ccy_cur = self.fx_rate_provider[self.pricing_ccy]
            self.pricing_ccy_cur_fx = self.pricing_ccy_cur.fx_rate

            self.pricing_ccy_cash_hist = self.fx_rate_provider[self.pricing_ccy, self.cash_date]
            self.pricing_ccy_cash_hist_fx = self.pricing_ccy_cash_hist.fx_rate

            self.pricing_ccy_acc_hist = self.fx_rate_provider[self.pricing_ccy, self.acc_date]
            self.pricing_ccy_acc_hist_fx = self.pricing_ccy_acc_hist.fx_rate

            try:
                pricing_ccy_cur_fx = 1.0 / self.pricing_ccy_cur_fx
            except ArithmeticError:
                pricing_ccy_cur_fx = 0.0
            try:
                pricing_ccy_cash_hist_fx = 1.0 / self.pricing_ccy_cash_hist_fx
            except ArithmeticError:
                pricing_ccy_cash_hist_fx = 0.0
            try:
                pricing_ccy_acc_hist_fx = 1.0 / self.pricing_ccy_acc_hist_fx
            except ArithmeticError:
                pricing_ccy_acc_hist_fx = 0.0

        # instr
        if self.instr:
            self.instr_price_cur = self.pricing_provider[self.instr]
            self.instr_price_cur_principal_price = self.instr_price_cur.principal_price
            self.instr_price_cur_accrued_price = self.instr_price_cur.accrued_price

            self.instr_pricing_ccy_cur = self.fx_rate_provider[self.instr.pricing_currency]
            self.instr_pricing_ccy_cur_fx = self.instr_pricing_ccy_cur.fx_rate * report_ccy_cur_fx

            self.instr_accrued_ccy_cur = self.fx_rate_provider[self.instr.accrued_currency]
            self.instr_accrued_ccy_cur_fx = self.instr_accrued_ccy_cur.fx_rate * report_ccy_cur_fx

        # trn ccy
        if self.trn_ccy:
            self.trn_ccy_cash_hist = self.fx_rate_provider[self.trn_ccy, self.cash_date]
            self.trn_ccy_cash_hist_fx = self.trn_ccy_cash_hist.fx_rate * report_ccy_cash_hist_fx
            self.trn_ccy_cash_hist_fx_loc = self.trn_ccy_cash_hist.fx_rate * pricing_ccy_cash_hist_fx

            self.trn_ccy_acc_hist = self.fx_rate_provider[self.trn_ccy, self.acc_date]
            self.trn_ccy_acc_hist_fx = self.trn_ccy_acc_hist.fx_rate * report_ccy_acc_hist_fx
            self.trn_ccy_acc_hist_fx_loc = self.trn_ccy_acc_hist.fx_rate * pricing_ccy_acc_hist_fx

            self.trn_ccy_cur = self.fx_rate_provider[self.trn_ccy]
            self.trn_ccy_cur_fx = self.trn_ccy_cur.fx_rate * report_ccy_cur_fx
            self.trn_ccy_cur_fx_loc = self.trn_ccy_cur.fx_rate * pricing_ccy_cur_fx

        # stl ccy
        if self.stl_ccy:
            self.stl_ccy_cash_hist = self.fx_rate_provider[self.stl_ccy, self.cash_date]
            self.stl_ccy_cash_hist_fx = self.stl_ccy_cash_hist.fx_rate * report_ccy_cash_hist_fx
            self.stl_ccy_cash_hist_fx_loc = self.stl_ccy_cash_hist.fx_rate * pricing_ccy_cash_hist_fx

            self.stl_ccy_acc_hist = self.fx_rate_provider[self.stl_ccy, self.acc_date]
            self.stl_ccy_acc_hist_fx = self.stl_ccy_acc_hist.fx_rate * report_ccy_acc_hist_fx
            self.stl_ccy_acc_hist_fx_loc = self.stl_ccy_acc_hist.fx_rate * pricing_ccy_acc_hist_fx

            self.stl_ccy_cur = self.fx_rate_provider[self.stl_ccy]
            self.stl_ccy_cur_fx = self.stl_ccy_cur.fx_rate * report_ccy_cur_fx
            self.stl_ccy_cur_fx_loc = self.stl_ccy_cur.fx_rate * pricing_ccy_cur_fx

    def get_instr_ytm_data_d0_v0(self, dt):
        # return self.acc_date, -(
        #         self.trade_price * self.instr.price_multiplier * self.instr.get_factor(self.report.report_date))
        return dt, -(
                self.trade_price * self.instr.price_multiplier * self.instr.get_factor(dt))

    def get_instr_ytm_x0(self, dt):
        try:
            accrual_size = self.instr.get_accrual_size(dt)
            return (accrual_size * self.instr.accrued_multiplier) * \
                   (self.instr_accrued_ccy_cur_fx / self.instr_pricing_ccy_cur_fx) / \
                   (self.instr_price_cur_principal_price * self.instr.price_multiplier)
        except ArithmeticError:
            return 0


    def round_after_calc(self):
        self.avco_multiplier = format_float(self.avco_multiplier)
        self.avco_rolling_pos_size = format_float(self.avco_rolling_pos_size)
        self.fifo_multiplier = format_float(self.fifo_multiplier)
        self.fifo_rolling_pos_size = format_float(self.fifo_rolling_pos_size)
        self.multiplier = format_float(self.multiplier)
        self.rolling_pos_size = format_float(self.rolling_pos_size)

        self.pos_size = format_float(self.pos_size)

        self.cash = format_float(self.cash)

        # P&L related
        self.principal = format_float(self.principal)
        self.carry = format_float(self.carry)
        self.overheads = format_float(self.overheads)

        self.ref_fx = format_float(self.ref_fx)
        self.trade_price = format_float(self.trade_price)

        self.report_ccy_cur_fx = format_float(self.report_ccy_cur_fx)
        self.report_ccy_cash_hist_fx = format_float(self.report_ccy_cash_hist_fx)
        self.report_ccy_acc_hist_fx = format_float(self.report_ccy_acc_hist_fx)

        # report ccy

        self.pricing_ccy_cur_fx = format_float(self.pricing_ccy_cur_fx)
        self.pricing_ccy_cash_hist_fx = format_float(self.pricing_ccy_cash_hist_fx)
        self.pricing_ccy_acc_hist_fx = format_float(self.pricing_ccy_acc_hist_fx)

        # instr

        self.instr_price_cur_principal_price = format_float(self.instr_price_cur_principal_price)
        self.instr_price_cur_accrued_price = format_float(self.instr_price_cur_accrued_price)
        self.instr_pricing_ccy_cur_fx = format_float(self.instr_pricing_ccy_cur_fx)
        self.instr_accrued_ccy_cur_fx = format_float(self.instr_accrued_ccy_cur_fx)

        # trn ccy

        self.trn_ccy_cash_hist_fx = format_float(self.trn_ccy_cash_hist_fx)
        self.trn_ccy_cash_hist_fx_loc = format_float(self.trn_ccy_cash_hist_fx_loc)

        self.trn_ccy_acc_hist_fx = format_float(self.trn_ccy_acc_hist_fx)
        self.trn_ccy_acc_hist_fx_loc = format_float(self.trn_ccy_acc_hist_fx_loc)

        self.trn_ccy_cur_fx = format_float(self.trn_ccy_cur_fx)
        self.trn_ccy_cur_fx_loc = format_float(self.trn_ccy_cur_fx_loc)

        # stl ccy
        self.stl_ccy_cash_hist_fx = format_float(self.stl_ccy_cash_hist_fx)
        self.stl_ccy_cash_hist_fx_loc = format_float(self.stl_ccy_cash_hist_fx_loc)
        self.stl_ccy_acc_hist_fx = format_float(self.stl_ccy_acc_hist_fx)
        self.stl_ccy_acc_hist_fx_loc = format_float(self.stl_ccy_acc_hist_fx_loc)
        self.stl_ccy_cur_fx = format_float(self.stl_ccy_cur_fx)
        self.stl_ccy_cur_fx_loc = format_float(self.stl_ccy_cur_fx_loc)

        # general

        self.mismatch = format_float(self.mismatch)

        self.instr_principal = format_float(self.instr_principal)
        self.instr_principal_res = format_float(self.instr_principal_res)
        self.instr_accrued = format_float(self.instr_accrued)
        self.instr_accrued_res = format_float(self.instr_accrued_res)

        self.cost_res = format_float(self.cost_res)
        self.gross_cost_res = format_float(self.gross_cost_res)
        self.gross_cost_loc = format_float(self.gross_cost_loc)
        self.net_cost_res = format_float(self.net_cost_res)
        self.net_cost_loc = format_float(self.net_cost_loc)
        self.principal_invested_res = format_float(self.principal_invested_res)
        self.principal_invested_loc = format_float(self.principal_invested_loc)
        self.amount_invested_res = format_float(self.amount_invested_res)
        self.amount_invested_loc = format_float(self.amount_invested_loc)

        self.balance_pos_size = format_float(self.balance_pos_size)
        self.sum_remaining_pos_size = format_float(self.sum_remaining_pos_size)   # sum of remaining_pos_size by trns before current
        self.remaining_pos_size = format_float(self.remaining_pos_size)
        self.remaining_pos_size_percent = format_float(self.remaining_pos_size_percent)   # calculated in second pass
        self.ytm = format_float(self.ytm)
        self.time_invested_days = format_float(self.time_invested_days)
        self.time_invested = format_float(self.time_invested)
        self.weighted_ytm = format_float(self.weighted_ytm)   # calculated in second pass
        self.weighted_time_invested_days = format_float(self.weighted_time_invested_days)   # calculated in second pass
        self.weighted_time_invested = format_float(self.weighted_time_invested)   # calculated in second pass

        # Cash related

        self.cash_res = format_float(self.cash_res)

        # full P&L related
        self.total = format_float(self.total)

        self.principal_res = format_float(self.principal_res)
        self.carry_res = format_float(self.carry_res)
        self.overheads_res = format_float(self.overheads_res)
        self.total_res = format_float(self.total_res)

        self.principal_loc = format_float(self.principal_loc)
        self.carry_loc = format_float(self.carry_loc)
        self.overheads_loc = format_float(self.overheads_loc)
        self.total_loc = format_float(self.total_loc)

        # full / closed
        self.principal_closed_res = format_float(self.principal_closed_res)
        self.carry_closed_res = format_float(self.carry_closed_res)
        self.overheads_closed_res = format_float(self.overheads_closed_res)
        self.total_closed_res = format_float(self.total_closed_res)

        self.principal_closed_loc = format_float(self.principal_closed_loc)
        self.carry_closed_loc = format_float(self.carry_closed_loc)
        self.overheads_closed_loc = format_float(self.overheads_closed_loc)
        self.total_closed_loc = format_float(self.total_closed_loc)

        # full / opened
        self.principal_opened_res = format_float(self.principal_opened_res)
        self.carry_opened_res = format_float(self.carry_opened_res)
        self.overheads_opened_res = format_float(self.overheads_opened_res)
        self.total_opened_res = format_float(self.total_opened_res)

        self.principal_opened_loc = format_float(self.principal_opened_loc)
        self.carry_opened_loc = format_float(self.carry_opened_loc)
        self.overheads_opened_loc = format_float(self.overheads_opened_loc)
        self.total_opened_loc = format_float(self.total_opened_loc)

        # fx
        self.pl_fx_mul = format_float(self.pl_fx_mul)
        self.principal_fx_res = format_float(self.principal_fx_res)
        self.carry_fx_res = format_float(self.carry_fx_res)
        self.overheads_fx_res = format_float(self.overheads_fx_res)
        self.total_fx_res = format_float(self.total_fx_res)

        self.pl_fx_mul_loc = format_float(self.pl_fx_mul_loc)
        self.principal_fx_loc = format_float(self.principal_fx_loc)
        self.carry_fx_loc = format_float(self.carry_fx_loc)
        self.overheads_fx_loc = format_float(self.overheads_fx_loc)
        self.total_fx_loc = format_float(self.total_fx_loc)

        # fx / closed
        self.principal_fx_closed_res = format_float(self.principal_fx_closed_res)
        self.carry_fx_closed_res = format_float(self.carry_fx_closed_res)
        self.overheads_fx_closed_res = format_float(self.overheads_fx_closed_res)
        self.total_fx_closed_res = format_float(self.total_fx_closed_res)

        self.principal_fx_closed_loc = format_float(self.principal_fx_closed_loc)
        self.carry_fx_closed_loc = format_float(self.carry_fx_closed_loc)
        self.overheads_fx_closed_loc = format_float(self.overheads_fx_closed_loc)
        self.total_fx_closed_loc = format_float(self.total_fx_closed_loc)

        # fx / opened
        self.principal_fx_opened_res = format_float(self.principal_fx_opened_res)
        self.carry_fx_opened_res = format_float(self.carry_fx_opened_res)
        self.overheads_fx_opened_res = format_float(self.overheads_fx_opened_res)
        self.total_fx_opened_res = format_float(self.total_fx_opened_res)

        self.principal_fx_opened_loc = format_float(self.principal_fx_opened_loc)
        self.carry_fx_opened_loc = format_float(self.carry_fx_opened_loc)
        self.overheads_fx_opened_loc = format_float(self.overheads_fx_opened_loc)
        self.total_fx_opened_loc = format_float(self.total_fx_opened_loc)

        # fixed
        self.pl_fixed_mul = format_float(self.pl_fixed_mul)
        self.principal_fixed_res = format_float(self.principal_fixed_res)
        self.carry_fixed_res = format_float(self.carry_fixed_res)
        self.overheads_fixed_res = format_float(self.overheads_fixed_res)
        self.total_fixed_res = format_float(self.total_fixed_res)

        self.pl_fixed_mul_loc = format_float(self.pl_fixed_mul_loc)
        self.principal_fixed_loc = format_float(self.principal_fixed_loc)
        self.carry_fixed_loc = format_float(self.carry_fixed_loc)
        self.overheads_fixed_loc = format_float(self.overheads_fixed_loc)
        self.total_fixed_loc = format_float(self.total_fixed_loc)

        # fixed / closed
        self.principal_fixed_closed_res = format_float(self.principal_fixed_closed_res)
        self.carry_fixed_closed_res = format_float(self.carry_fixed_closed_res)
        self.overheads_fixed_closed_res = format_float(self.overheads_fixed_closed_res)
        self.total_fixed_closed_res = format_float(self.total_fixed_closed_res)

        self.principal_fixed_closed_loc = format_float(self.principal_fixed_closed_loc)
        self.carry_fixed_closed_loc = format_float(self.carry_fixed_closed_loc)
        self.overheads_fixed_closed_loc = format_float(self.overheads_fixed_closed_loc)
        self.total_fixed_closed_loc = format_float(self.total_fixed_closed_loc)

        # fixed / opened
        self.principal_fixed_opened_res = format_float(self.principal_fixed_opened_res)
        self.carry_fixed_opened_res = format_float(self.carry_fixed_opened_res)
        self.overheads_fixed_opened_res = format_float(self.overheads_fixed_opened_res)
        self.total_fixed_opened_res = format_float(self.total_fixed_opened_res)

        self.principal_fixed_opened_loc = format_float(self.principal_fixed_opened_loc)
        self.carry_fixed_opened_loc = format_float(self.carry_fixed_opened_loc)
        self.overheads_fixed_opened_loc = format_float(self.overheads_fixed_opened_loc)
        self.total_fixed_opened_loc = format_float(self.total_fixed_opened_loc)

    def calc(self):
            # if not self.is_hidden:
            #     print(1)
            if self.trn_cls.id in [TransactionClass.BUY, TransactionClass.SELL, TransactionClass.TRANSACTION_PL,
                                   TransactionClass.INSTRUMENT_PL, TransactionClass.FX_TRADE]:
                if self.instr:
                    self.instr_principal = self.pos_size * self.instr.price_multiplier * self.instr_price_cur_principal_price
                    self.instr_principal_res = self.instr_principal * self.instr_pricing_ccy_cur_fx

                    self.instr_accrued = self.pos_size * self.instr.accrued_multiplier * self.instr_price_cur_accrued_price
                    self.instr_accrued_res = self.instr_accrued * self.instr_accrued_ccy_cur_fx

                # Cash related

                self.cash_res = self.cash * self.stl_ccy_cur_fx

                # ------------------
                # P&L in report ccy
                # ------------------
                self.total = self.principal + self.carry + self.overheads

                self.pl_fx_mul = self.stl_ccy_cur_fx - self.ref_fx * self.trn_ccy_acc_hist_fx
                self.pl_fixed_mul = self.ref_fx * self.trn_ccy_acc_hist_fx

                self.principal_res = self.principal * self.stl_ccy_cur_fx
                self.carry_res = self.carry * self.stl_ccy_cur_fx
                self.overheads_res = self.overheads * self.stl_ccy_cur_fx
                self.total_res = self.total * self.stl_ccy_cur_fx

                # full / closed
                self.principal_closed_res = self.principal_res * self.multiplier
                self.carry_closed_res = self.carry_res * self.multiplier
                self.overheads_closed_res = self.overheads_res * self.multiplier
                self.total_closed_res = self.total_res * self.multiplier

                # full / opened
                self.principal_opened_res = self.principal_res * (1.0 - self.multiplier)
                self.carry_opened_res = self.carry_res * (1.0 - self.multiplier)
                self.overheads_opened_res = self.overheads_res * (1.0 - self.multiplier)
                self.total_opened_res = self.total_res * (1.0 - self.multiplier)

                # fx
                self.principal_fx_res = self.principal * self.pl_fx_mul
                self.carry_fx_res = self.carry * self.pl_fx_mul
                self.overheads_fx_res = self.overheads * self.pl_fx_mul
                self.total_fx_res = self.total * self.pl_fx_mul

                # fx / closed
                self.principal_fx_closed_res = self.principal_fx_res * self.multiplier
                self.carry_fx_closed_res = self.carry_fx_res * self.multiplier
                self.overheads_fx_closed_res = self.overheads_fx_res * self.multiplier
                self.total_fx_closed_res = self.total_fx_res * self.multiplier

                # fx / opened
                self.principal_fx_opened_res = self.principal_fx_res * (1.0 - self.multiplier)
                self.carry_fx_opened_res = self.carry_fx_res * (1.0 - self.multiplier)
                self.overheads_fx_opened_res = self.overheads_fx_res * (1.0 - self.multiplier)
                self.total_fx_opened_res = self.total_fx_res * (1.0 - self.multiplier)

                if self.trn_cls.id in [TransactionClass.FX_TRADE]:
                    pass
                else:
                    # fixed
                    self.principal_fixed_res = self.principal * self.pl_fixed_mul
                    self.carry_fixed_res = self.carry * self.pl_fixed_mul
                    self.overheads_fixed_res = self.overheads * self.pl_fixed_mul
                    self.total_fixed_res = self.total * self.pl_fixed_mul

                    # fixed / closed
                    self.principal_fixed_closed_res = self.principal_fixed_res * self.multiplier
                    self.carry_fixed_closed_res = self.carry_fixed_res * self.multiplier
                    self.overheads_fixed_closed_res = self.overheads_fixed_res * self.multiplier
                    self.total_fixed_closed_res = self.total_fixed_res * self.multiplier

                    # fixed / opened
                    self.principal_fixed_opened_res = self.principal_fixed_res * (1.0 - self.multiplier)
                    self.carry_fixed_opened_res = self.carry_fixed_res * (1.0 - self.multiplier)
                    self.overheads_fixed_opened_res = self.overheads_fixed_res * (1.0 - self.multiplier)
                    self.total_fixed_opened_res = self.total_fixed_res * (1.0 - self.multiplier)

                # ------------------
                # P&L in pricing ccy
                # ------------------
                self.pl_fx_mul_loc = self.stl_ccy_cur_fx_loc - self.ref_fx * self.trn_ccy_acc_hist_fx_loc
                self.pl_fixed_mul_loc = self.ref_fx * self.trn_ccy_acc_hist_fx_loc

                self.principal_loc = self.principal * self.stl_ccy_cur_fx_loc
                self.carry_loc = self.carry * self.stl_ccy_cur_fx_loc
                self.overheads_loc = self.overheads * self.stl_ccy_cur_fx_loc
                self.total_loc = self.total * self.stl_ccy_cur_fx_loc

                # full / closed
                self.principal_closed_loc = self.principal_loc * self.multiplier
                self.carry_closed_loc = self.carry_loc * self.multiplier
                self.overheads_closed_loc = self.overheads_loc * self.multiplier
                self.total_closed_loc = self.total_loc * self.multiplier

                # full / opened
                self.principal_opened_loc = self.principal_loc * (1.0 - self.multiplier)
                self.carry_opened_loc = self.carry_loc * (1.0 - self.multiplier)
                self.overheads_opened_loc = self.overheads_loc * (1.0 - self.multiplier)
                self.total_opened_loc = self.total_loc * (1.0 - self.multiplier)

                # fx
                self.principal_fx_loc = self.principal * self.pl_fx_mul_loc
                self.carry_fx_loc = self.carry * self.pl_fx_mul_loc
                self.overheads_fx_loc = self.overheads * self.pl_fx_mul_loc
                self.total_fx_loc = self.total * self.pl_fx_mul_loc

                # fx / closed
                self.principal_fx_closed_loc = self.principal_fx_loc * self.multiplier
                self.carry_fx_closed_loc = self.carry_fx_loc * self.multiplier
                self.overheads_fx_closed_loc = self.overheads_fx_loc * self.multiplier
                self.total_fx_closed_loc = self.total_fx_loc * self.multiplier

                # fx / opened
                self.principal_fx_opened_loc = self.principal_fx_loc * (1.0 - self.multiplier)
                self.carry_fx_opened_loc = self.carry_fx_loc * (1.0 - self.multiplier)
                self.overheads_fx_opened_loc = self.overheads_fx_loc * (1.0 - self.multiplier)
                self.total_fx_opened_loc = self.total_fx_loc * (1.0 - self.multiplier)

                if self.trn_cls.id in [TransactionClass.FX_TRADE]:
                    pass
                else:
                    # fixed
                    self.principal_fixed_loc = self.principal * self.pl_fixed_mul_loc
                    self.carry_fixed_loc = self.carry * self.pl_fixed_mul_loc
                    self.overheads_fixed_loc = self.overheads * self.pl_fixed_mul_loc
                    self.total_fixed_loc = self.total * self.pl_fixed_mul_loc

                    # fixed / closed
                    self.principal_fixed_closed_loc = self.principal_fixed_loc * self.multiplier
                    self.carry_fixed_closed_loc = self.carry_fixed_loc * self.multiplier
                    self.overheads_fixed_closed_loc = self.overheads_fixed_loc * self.multiplier
                    self.total_fixed_closed_loc = self.total_fixed_loc * self.multiplier

                    # fixed / opened
                    self.principal_fixed_opened_loc = self.principal_fixed_loc * (1.0 - self.multiplier)
                    self.carry_fixed_opened_loc = self.carry_fixed_loc * (1.0 - self.multiplier)
                    self.overheads_fixed_opened_loc = self.overheads_fixed_loc * (1.0 - self.multiplier)
                    self.total_fixed_opened_loc = self.total_fixed_loc * (1.0 - self.multiplier)

                #
                if not self.is_cloned and self.instr:

                    if self.trn_cls.id in [TransactionClass.BUY, TransactionClass.SELL]:
                        try:
                            self.cost_res = self.principal * (self.stl_ccy_cur.fx_rate / self.report_ccy_cur.fx_rate) * \
                                            (1.0 - self.multiplier)
                        except ArithmeticError:
                            self.cost_res = 0.0

                        # gross_cost

                        try:
                            self.gross_cost_res = self.principal * self.ref_fx * \
                                                  (self.trn_ccy_acc_hist.fx_rate / self.report_ccy_acc_hist.fx_rate) * \
                                                  (1.0 - self.multiplier) / self.pos_size / self.instr.price_multiplier
                        except ArithmeticError:
                            self.gross_cost_res = 0.0

                        try:
                            self.gross_cost_loc = self.principal * self.ref_fx * \
                                                  (self.trn_ccy_acc_hist.fx_rate / self.pricing_ccy_acc_hist.fx_rate) * \
                                                  (1.0 - self.multiplier) / self.pos_size / self.instr.price_multiplier
                        except ArithmeticError:
                            self.gross_cost_loc = 0.0

                        # net_cost

                        try:
                            self.net_cost_res = (self.principal + self.overheads) * self.ref_fx * \
                                                (self.trn_ccy_acc_hist.fx_rate / self.report_ccy_acc_hist.fx_rate) * \
                                                (1.0 - self.multiplier) / self.pos_size / self.instr.price_multiplier
                        except ArithmeticError:
                            self.net_cost_res = 0.0

                        try:
                            self.net_cost_loc = (self.principal + self.overheads) * self.ref_fx * \
                                                (self.trn_ccy_acc_hist.fx_rate / self.pricing_ccy_acc_hist.fx_rate) * \
                                                (1.0 - self.multiplier) / self.pos_size / self.instr.price_multiplier
                        except ArithmeticError:
                            self.net_cost_loc = 0.0

                        # principal_invested

                        try:
                            self.principal_invested_res = self.principal * self.ref_fx * \
                                                          (
                                                                  self.trn_ccy_acc_hist.fx_rate / self.report_ccy_acc_hist.fx_rate) * \
                                                          (1.0 - self.multiplier)
                        except ArithmeticError:
                            self.principal_invested_res = 0.0

                        try:
                            self.principal_invested_loc = self.principal * self.ref_fx * \
                                                          (
                                                                  self.trn_ccy_acc_hist.fx_rate / self.pricing_ccy_acc_hist.fx_rate) * \
                                                          (1.0 - self.multiplier)
                        except ArithmeticError:
                            self.principal_invested_loc = 0.0

                        # amount_invested

                        try:
                            self.amount_invested_res = self.total_res * self.ref_fx * \
                                                       (self.trn_ccy_acc_hist.fx_rate / self.report_ccy_acc_hist.fx_rate) * \
                                                       (1.0 - self.multiplier)
                        except ArithmeticError:
                            self.amount_invested_res = 0.0

                        try:
                            self.amount_invested_loc = self.total_res * self.ref_fx * \
                                                       (self.trn_ccy_acc_hist.fx_rate / self.pricing_ccy_acc_hist.fx_rate) * \
                                                       (1.0 - self.multiplier)
                        except ArithmeticError:
                            self.amount_invested_loc = 0.0

                        # ytm_data = ReportBuilder.instr_ytm_data(
                        #     instr=self.instr,
                        #     d0=self.acc_date,
                        #     v0=self.trade_price,
                        #     pricing_ccy_fx=self.instr_pricing_ccy_cur_fx,
                        #     accrued_ccy_fx=self.instr_accrued_ccy_cur_fx,
                        # )
                        # self.ytm = ReportBuilder.instr_ytm(
                        #     instr=self.instr,
                        #     data=ytm_data,
                        #     x0=self.trade_price * self.instr.price_multiplier
                        # )
                        self.ytm = self.get_instr_ytm(self.acc_date)

                        self.time_invested_days = (self.report.report_date - self.acc_date).days
                        self.time_invested = self.time_invested_days / 365.0

                        try:
                            self.remaining_pos_size_percent = self.remaining_pos_size / self.balance_pos_size
                        except ArithmeticError:
                            self.remaining_pos_size_percent = 0.0

                        self.weighted_ytm = self.ytm * self.remaining_pos_size_percent
                        self.weighted_time_invested_days = self.time_invested_days * self.remaining_pos_size_percent
                        self.weighted_time_invested = self.time_invested * self.remaining_pos_size_percent

            elif self.trn_cls.id in [TransactionClass.CASH_INFLOW, TransactionClass.CASH_OUTFLOW]:
                self.pl_fx_mul = self.stl_ccy_cur_fx - self.ref_fx * self.trn_ccy_acc_hist_fx
                self.pl_fixed_mul = self.ref_fx * self.trn_ccy_acc_hist_fx

                self.principal_res = self.cash * self.pl_fx_mul
                self.principal_closed_res = self.principal_res
                self.principal_fx_res = self.principal_res
                self.principal_fx_closed_res = self.principal_res

                self.mismatch = 0.0

            else:
                self.mismatch = self.cash - self.total


            self.round_after_calc()

        # def calc_pass2(self, balance_pos_size):
        #     # called after "balance"
        #     if not self.is_cloned and self.trn_cls.id in [TransactionClass.BUY, TransactionClass.SELL] and self.instr:
        #         # try:
        #         #     future_accrual_payments = self.instr.get_future_accrual_payments(
        #         #         d0=self.acc_date,
        #         #         v0=self.trade_price,
        #         #         principal_ccy_fx=self.instr_pricing_ccy_cur_fx,
        #         #         accrual_ccy_fx=self.instr_accrued_ccy_cur_fx
        #         #     )
        #         # except (ValueError, TypeError):
        #         #     future_accrual_payments = False
        #         # self.ytm = f_xirr(future_accrual_payments)
        #         #
        #         # self.time_invested_days = (self.report.report_date - self.acc_date).days
        #         # self.time_invested = self.time_invested_days / 365.0
        #
        #         try:
        #             self.remaining_pos_size_percent = self.remaining_pos_size / balance_pos_size
        #         except ArithmeticError:
        #             self.remaining_pos_size_percent = 0.0
        #
        #         self.weighted_ytm = self.ytm * self.remaining_pos_size_percent
        #         self.weighted_time_invested_days = self.time_invested_days * self.remaining_pos_size_percent
        #         self.weighted_time_invested = self.time_invested * self.remaining_pos_size_percent

    @staticmethod
    def approach_clone(cur, closed, mul_delta):
        def _clean(t):
            t.is_mismatch = False

            t.report_ccy_cur = None
            t.report_ccy_cur_fx = 0.0  # float('nan')
            t.report_ccy_cash_hist = None
            t.report_ccy_cash_hist_fx = 0.0  # float('nan')
            t.report_ccy_acc_hist = None
            t.report_ccy_acc_hist_fx = 0.0  # float('nan')

            t.pricing_ccy_cur = None
            t.pricing_ccy_cur_fx = 0.0  # float('nan')
            t.pricing_ccy_cash_hist = None
            t.pricing_ccy_cash_hist_fx = 0.0  # float('nan')
            t.pricing_ccy_acc_hist = None
            t.pricing_ccy_acc_hist_fx = 0.0  # float('nan')

            t.instr_price_cur = None
            t.instr_price_cur_principal_price = 0.0  # float('nan')
            t.instr_price_cur_accrued_price = 0.0  # float('nan')
            t.instr_pricing_ccy_cur = None
            t.instr_pricing_ccy_cur_fx = 0.0  # float('nan')
            t.instr_accrued_ccy_cur = None
            t.instr_accrued_ccy_cur_fx = 0.0  # float('nan')

            t.trn_ccy_cash_hist = None
            t.trn_ccy_cash_hist_fx = 0.0  # float('nan')
            t.trn_ccy_acc_hist = None
            t.trn_ccy_acc_hist_fx = 0.0  # float('nan')
            t.trn_ccy_cur = None
            t.trn_ccy_cur_fx = 0.0  # float('nan')

            t.stl_ccy_cash_hist = None
            t.stl_ccy_cash_hist_fx = 0.0  # float('nan')
            t.stl_ccy_acc_hist = None
            t.stl_ccy_acc_hist_fx = 0.0  # float('nan')
            t.stl_ccy_cur = None
            t.stl_ccy_cur_fx = 0.0  # float('nan')

            t.mismatch = 0.0
            t.avco_multiplier = 0.0
            t.avco_closed_by = []
            t.fifo_multiplier = 0.0
            t.fifo_closed_by = []
            t.multiplier = 1.0
            t.closed_by = []
            t.cash = 0.0
            t.cash_res = 0.0

            t.instr_principal = 0.0  # float('nan')
            t.instr_principal_res = 0.0
            t.instr_accrued = 0.0  # float('nan')
            t.instr_accrued_res = 0.0

            t.principal = 0.0  # float('nan')
            t.carry = 0.0  # float('nan')
            t.overheads = 0.0  # float('nan')
            t.total = 0.0  # float('nan')

            t.pl_fx_mul = 0.0  # float('nan')
            t.pl_fixed_mul = 0.0  # float('nan')

        pos_size = abs(closed.pos_size * mul_delta)

        try:
            abm = closed.report.approach_begin_multiplier * abs(pos_size / closed.pos_size)
        except ArithmeticError:
            abm = 0.0
        try:
            aem = closed.report.approach_end_multiplier * abs(pos_size / cur.pos_size)
        except ArithmeticError:
            aem = 0.0

        # abm = closed.report.approach_begin_multiplier * closed1.multiplier
        # aem = closed.report.approach_end_multiplier * cur1.multiplier
        # abm = closed.report.approach_begin_multiplier
        # aem = closed.report.approach_end_multiplier

        closed1 = closed
        # closed1 = closed.clone()
        # closed1.multiplier = abs(pos_size / closed.pos_size)
        # closed1.principal_res = closed.principal_res * closed1.multiplier
        # closed1.carry_res = closed.principal_res * closed1.multiplier
        # closed1.overheads_res = closed.principal_res * closed1.multiplier
        # closed1.total_res = closed.principal_res * closed1.multiplier
        # closed1.calc()

        cur1 = cur
        # cur1 = cur.clone()
        # cur1.multiplier = abs(pos_size / cur.pos_size)
        # cur1.principal_res = cur.principal_res * cur1.multiplier
        # cur1.carry_res = cur.principal_res * cur1.multiplier
        # cur1.overheads_res = cur.principal_res * cur1.multiplier
        # cur1.total_res = cur.principal_res * cur1.multiplier
        # cur1.calc()

        # ------------
        # t1
        # ------------
        t1 = closed1.clone()
        t1.trn_cls = cur1.trn_cls
        t1.pk = 'a1,%s,%s,%s' % (closed1.pk, cur1.pk, t1.trn_cls)

        _clean(t1)

        t1.pos_size = -pos_size

        # P&L in report ccy
        t1.principal_res = -(closed1.principal_res * abm + cur1.principal_res * aem)
        t1.carry_res = -(closed1.carry_res * abm + cur1.carry_res * aem)
        t1.overheads_res = -(closed1.overheads_res * abm + cur1.overheads_res * aem)
        t1.total_res = t1.principal_res + t1.carry_res + t1.overheads_res

        # t1.principal_closed_res = -(closed1.principal_closed_res * abm + cur1.principal_closed_res * aem)
        # t1.carry_closed_res = -(closed1.carry_closed_res * abm + cur1.carry_closed_res * aem)
        # t1.overheads_closed_res = -(closed1.overheads_closed_res * abm + cur1.overheads_closed_res * aem)
        # t1.total_closed_res = t1.principal_closed_res + t1.carry_closed_res + t1.overheads_closed_res
        t1.principal_closed_res = t1.principal_res
        t1.carry_closed_res = t1.carry_res
        t1.overheads_closed_res = t1.overheads_res
        t1.total_closed_res = t1.total_res

        # t1.principal_opened_res = -(closed1.principal_opened_res * abm + cur1.principal_opened_res * aem)
        # t1.carry_opened_res = -(closed1.carry_opened_res * abm + cur1.carry_opened_res * aem)
        # t1.overheads_opened_res = -(closed1.overheads_opened_res * abm + cur1.overheads_opened_res * aem)
        # t1.total_opened_res = t1.principal_opened_res + t1.carry_opened_res + t1.overheads_opened_res
        t1.principal_opened_res = 0.0
        t1.carry_opened_res = 0.0
        t1.overheads_opened_res = 0.0
        t1.total_opened_res = 0.0

        t1.principal_fx_res = -(closed1.principal_fx_res * abm + cur1.principal_fx_res * aem)
        t1.carry_fx_res = -(closed1.carry_fx_res * abm + cur1.carry_fx_res * aem)
        t1.overheads_fx_res = -(closed1.overheads_fx_res * abm + cur1.overheads_fx_res * aem)
        t1.total_fx_res = t1.principal_fx_res + t1.carry_fx_res + t1.overheads_fx_res

        # t1.principal_fx_closed_res = -(closed1.principal_fx_closed_res * abm + cur1.principal_fx_closed_res * aem)
        # t1.carry_fx_closed_res = -(closed1.carry_fx_closed_res * abm + cur1.carry_fx_closed_res * aem)
        # t1.overheads_fx_closed_res = -(closed1.overheads_fx_closed_res * abm + cur1.overheads_fx_closed_res * aem)
        # t1.total_fx_closed_res = t1.principal_fx_closed_res + t1.carry_fx_closed_res + t1.overheads_fx_closed_res
        t1.principal_fx_closed_res = t1.principal_fx_res
        t1.carry_fx_closed_res = t1.carry_fx_res
        t1.overheads_fx_closed_res = t1.overheads_fx_res
        t1.total_fx_closed_res = t1.total_fx_res

        # t1.principal_fx_opened_res = -(closed1.principal_fx_opened_res * abm + cur1.principal_fx_opened_res * aem)
        # t1.carry_fx_opened_res = -(closed1.carry_fx_opened_res * abm + cur1.carry_fx_opened_res * aem)
        # t1.overheads_fx_opened_res = -(closed1.overheads_fx_opened_res * abm + cur1.overheads_fx_opened_res * aem)
        # t1.total_fx_opened_res = t1.principal_fx_opened_res + t1.carry_fx_opened_res + t1.overheads_fx_opened_res
        t1.principal_fx_opened_res = 0.0
        t1.carry_fx_opened_res = 0.0
        t1.overheads_fx_opened_res = 0.0
        t1.total_fx_opened_res = 0.0

        t1.principal_fixed_res = -(closed1.principal_fixed_res * abm + cur1.principal_fixed_res * aem)
        t1.carry_fixed_res = -(closed1.carry_fixed_res * abm + cur1.carry_fixed_res * aem)
        t1.overheads_fixed_res = -(closed1.overheads_fixed_res * abm + cur1.overheads_fixed_res * aem)
        t1.total_fixed_res = t1.principal_fixed_res + t1.carry_fixed_res + t1.overheads_fixed_res

        # t1.principal_fixed_closed_res = -(
        #     closed1.principal_fixed_closed_res * abm + cur1.principal_fixed_closed_res * aem)
        # t1.carry_fixed_closed_res = -(closed1.carry_fixed_closed_res * abm + cur1.carry_fixed_closed_res * aem)
        # t1.overheads_fixed_closed_res = -(
        #     closed1.overheads_fixed_closed_res * abm + cur1.overheads_fixed_closed_res * aem)
        # t1.total_fixed_closed_res = t1.principal_fixed_closed_res + t1.carry_fixed_closed_res + t1.overheads_fixed_closed_res
        t1.principal_fixed_closed_res = t1.principal_fixed_res
        t1.carry_fixed_closed_res = t1.carry_fixed_res
        t1.overheads_fixed_closed_res = t1.overheads_fixed_res
        t1.total_fixed_closed_res = t1.total_fixed_res

        # t1.principal_fixed_opened_res = -(
        #     closed1.principal_fixed_opened_res * abm + cur1.principal_fixed_opened_res * aem)
        # t1.carry_fixed_opened_res = -(closed1.carry_fixed_opened_res * abm + cur1.carry_fixed_opened_res * aem)
        # t1.overheads_fixed_opened_res = -(
        #     closed1.overheads_fixed_opened_res * abm + cur1.overheads_fixed_opened_res * aem)
        # t1.total_fixed_opened_res = t1.principal_fixed_opened_res + t1.carry_fixed_opened_res + t1.overheads_fixed_opened_res
        t1.principal_fixed_opened_res = 0.0
        t1.carry_fixed_opened_res = 0.0
        t1.overheads_fixed_opened_res = 0.0
        t1.total_fixed_opened_res = 0.0

        # P&L in pricing ccy
        t1.principal_loc = -(closed1.principal_loc * abm + cur1.principal_loc * aem)
        t1.carry_loc = -(closed1.carry_loc * abm + cur1.carry_loc * aem)
        t1.overheads_loc = -(closed1.overheads_loc * abm + cur1.overheads_loc * aem)
        t1.total_loc = t1.principal_loc + t1.carry_loc + t1.overheads_loc

        # t1.principal_closed_loc = -(closed1.principal_closed_loc * abm + cur1.principal_closed_loc * aem)
        # t1.carry_closed_loc = -(closed1.carry_closed_loc * abm + cur1.carry_closed_loc * aem)
        # t1.overheads_closed_loc = -(closed1.overheads_closed_loc * abm + cur1.overheads_closed_loc * aem)
        # t1.total_closed_loc = t1.principal_closed_loc + t1.carry_closed_loc + t1.overheads_closed_loc
        t1.principal_closed_loc = t1.principal_loc
        t1.carry_closed_loc = t1.carry_loc
        t1.overheads_closed_loc = t1.overheads_loc
        t1.total_closed_loc = t1.total_loc

        # t1.principal_opened_loc = -(closed1.principal_opened_loc * abm + cur1.principal_opened_loc * aem)
        # t1.carry_opened_loc = -(closed1.carry_opened_loc * abm + cur1.carry_opened_loc * aem)
        # t1.overheads_opened_loc = -(closed1.overheads_opened_loc * abm + cur1.overheads_opened_loc * aem)
        # t1.total_opened_loc = t1.principal_opened_loc + t1.carry_opened_loc + t1.overheads_opened_loc
        t1.principal_opened_loc = 0.0
        t1.carry_opened_loc = 0.0
        t1.overheads_opened_loc = 0.0
        t1.total_opened_loc = 0.0

        t1.principal_fx_loc = -(closed1.principal_fx_loc * abm + cur1.principal_fx_loc * aem)
        t1.carry_fx_loc = -(closed1.carry_fx_loc * abm + cur1.carry_fx_loc * aem)
        t1.overheads_fx_loc = -(closed1.overheads_fx_loc * abm + cur1.overheads_fx_loc * aem)
        t1.total_fx_loc = t1.principal_fx_loc + t1.carry_fx_loc + t1.overheads_fx_loc

        # t1.principal_fx_closed_loc = -(closed1.principal_fx_closed_loc * abm + cur1.principal_fx_closed_loc * aem)
        # t1.carry_fx_closed_loc = -(closed1.carry_fx_closed_loc * abm + cur1.carry_fx_closed_loc * aem)
        # t1.overheads_fx_closed_loc = -(closed1.overheads_fx_closed_loc * abm + cur1.overheads_fx_closed_loc * aem)
        # t1.total_fx_closed_loc = t1.principal_fx_closed_loc + t1.carry_fx_closed_loc + t1.overheads_fx_closed_loc
        t1.principal_fx_closed_loc = t1.principal_fx_loc
        t1.carry_fx_closed_loc = t1.carry_fx_loc
        t1.overheads_fx_closed_loc = t1.overheads_fx_loc
        t1.total_fx_closed_loc = t1.total_fx_loc

        # t1.principal_fx_opened_loc = -(closed1.principal_fx_opened_loc * abm + cur1.principal_fx_opened_loc * aem)
        # t1.carry_fx_opened_loc = -(closed1.carry_fx_opened_loc * abm + cur1.carry_fx_opened_loc * aem)
        # t1.overheads_fx_opened_loc = -(closed1.overheads_fx_opened_loc * abm + cur1.overheads_fx_opened_loc * aem)
        # t1.total_fx_opened_loc = t1.principal_fx_opened_loc + t1.carry_fx_opened_loc + t1.overheads_fx_opened_loc
        t1.principal_fx_opened_loc = 0.0
        t1.carry_fx_opened_loc = 0.0
        t1.overheads_fx_opened_loc = 0.0
        t1.total_fx_opened_loc = 0.0

        t1.principal_fixed_loc = -(closed1.principal_fixed_loc * abm + cur1.principal_fixed_loc * aem)
        t1.carry_fixed_loc = -(closed1.carry_fixed_loc * abm + cur1.carry_fixed_loc * aem)
        t1.overheads_fixed_loc = -(closed1.overheads_fixed_loc * abm + cur1.overheads_fixed_loc * aem)
        t1.total_fixed_loc = t1.principal_fixed_loc + t1.carry_fixed_loc + t1.overheads_fixed_loc

        # t1.principal_fixed_closed_loc = -(
        #     closed1.principal_fixed_closed_loc * abm + cur1.principal_fixed_closed_loc * aem)
        # t1.carry_fixed_closed_loc = -(closed1.carry_fixed_closed_loc * abm + cur1.carry_fixed_closed_loc * aem)
        # t1.overheads_fixed_closed_loc = -(
        #     closed1.overheads_fixed_closed_loc * abm + cur1.overheads_fixed_closed_loc * aem)
        # t1.total_fixed_closed_loc = t1.principal_fixed_closed_loc + t1.carry_fixed_closed_loc + t1.overheads_fixed_closed_loc
        t1.principal_fixed_closed_loc = t1.principal_fixed_loc
        t1.carry_fixed_closed_loc = t1.carry_fixed_loc
        t1.overheads_fixed_closed_loc = t1.overheads_fixed_loc
        t1.total_fixed_closed_loc = t1.total_fixed_loc

        # t1.principal_fixed_opened_loc = -(
        #     closed1.principal_fixed_opened_loc * abm + cur1.principal_fixed_opened_loc * aem)
        # t1.carry_fixed_opened_loc = -(closed1.carry_fixed_opened_loc * abm + cur1.carry_fixed_opened_loc * aem)
        # t1.overheads_fixed_opened_loc = -(
        #     closed1.overheads_fixed_opened_loc * abm + cur1.overheads_fixed_opened_loc * aem)
        # t1.total_fixed_opened_loc = t1.principal_fixed_opened_loc + t1.carry_fixed_opened_loc + t1.overheads_fixed_opened_loc
        t1.principal_fixed_opened_loc = 0.0
        t1.carry_fixed_opened_loc = 0.0
        t1.overheads_fixed_opened_loc = 0.0
        t1.total_fixed_opened_loc = 0.0

        # ------------
        # t2
        # ------------
        t2 = cur1.clone()
        t2.trn_cls = closed1.trn_cls
        t2.pk = 'a2,%s,%s,%s' % (closed1.pk, cur1.pk, t2.trn_cls)

        _clean(t2)

        t2.pos_size = -t1.pos_size

        # P&L in report ccy
        t2.principal_res = -t1.principal_res
        t2.carry_res = -t1.carry_res
        t2.overheads_res = -t1.overheads_res
        t2.total_res = -t1.total_res

        t2.principal_closed_res = -t1.principal_closed_res
        t2.carry_closed_res = -t1.carry_closed_res
        t2.overheads_closed_res = -t1.overheads_closed_res
        t2.total_closed_res = -t1.total_closed_res

        t2.principal_opened_res = -t1.principal_opened_res
        t2.carry_opened_res = -t1.carry_opened_res
        t2.overheads_opened_res = -t1.overheads_opened_res
        t2.total_opened_res = -t1.total_opened_res

        t2.principal_fx_res = -t1.principal_fx_res
        t2.carry_fx_res = -t1.carry_fx_res
        t2.overheads_fx_res = -t1.overheads_fx_res
        t2.total_fx_res = -t1.total_fx_res

        t2.principal_fx_closed_res = -t1.principal_fx_closed_res
        t2.carry_fx_closed_res = -t1.carry_fx_closed_res
        t2.overheads_fx_closed_res = -t1.overheads_fx_closed_res
        t2.total_fx_closed_res = -t1.total_fx_closed_res

        t2.principal_fx_opened_res = -t1.principal_fx_opened_res
        t2.carry_fx_opened_res = -t1.carry_fx_opened_res
        t2.overheads_fx_opened_res = -t1.overheads_fx_opened_res
        t2.total_fx_opened_res = -t1.total_fx_opened_res

        t2.principal_fixed_res = -t1.principal_fixed_res
        t2.carry_fixed_res = -t1.carry_fixed_res
        t2.overheads_fixed_res = -t1.overheads_fixed_res
        t2.total_fixed_res = -t1.total_fixed_res

        t2.principal_fixed_closed_res = -t1.principal_fixed_closed_res
        t2.carry_fixed_closed_res = -t1.carry_fixed_closed_res
        t2.overheads_fixed_closed_res = -t1.overheads_fixed_closed_res
        t2.total_fixed_closed_res = -t1.total_fixed_closed_res

        t2.principal_fixed_opened_res = -t1.principal_fixed_opened_res
        t2.carry_fixed_opened_res = -t1.carry_fixed_opened_res
        t2.overheads_fixed_opened_res = -t1.overheads_fixed_opened_res
        t2.total_fixed_opened_res = -t1.total_fixed_opened_res

        # P&L in pricing ccy
        t2.principal_loc = -t1.principal_loc
        t2.carry_loc = -t1.carry_loc
        t2.overheads_loc = -t1.overheads_loc
        t2.total_loc = -t1.total_loc

        t2.principal_closed_loc = -t1.principal_closed_loc
        t2.carry_closed_loc = -t1.carry_closed_loc
        t2.overheads_closed_loc = -t1.overheads_closed_loc
        t2.total_closed_loc = -t1.total_closed_loc

        t2.principal_opened_loc = -t1.principal_opened_loc
        t2.carry_opened_loc = -t1.carry_opened_loc
        t2.overheads_opened_loc = -t1.overheads_opened_loc
        t2.total_opened_loc = -t1.total_opened_loc

        t2.principal_fx_loc = -t1.principal_fx_loc
        t2.carry_fx_loc = -t1.carry_fx_loc
        t2.overheads_fx_loc = -t1.overheads_fx_loc
        t2.total_fx_loc = -t1.total_fx_loc

        t2.principal_fx_closed_loc = -t1.principal_fx_closed_loc
        t2.carry_fx_closed_loc = -t1.carry_fx_closed_loc
        t2.overheads_fx_closed_loc = -t1.overheads_fx_closed_loc
        t2.total_fx_closed_loc = -t1.total_fx_closed_loc

        t2.principal_fx_opened_loc = -t1.principal_fx_opened_loc
        t2.carry_fx_opened_loc = -t1.carry_fx_opened_loc
        t2.overheads_fx_opened_loc = -t1.overheads_fx_opened_loc
        t2.total_fx_opened_loc = -t1.total_fx_opened_loc

        t2.principal_fixed_loc = -t1.principal_fixed_loc
        t2.carry_fixed_loc = -t1.carry_fixed_loc
        t2.overheads_fixed_loc = -t1.overheads_fixed_loc
        t2.total_fixed_loc = -t1.total_fixed_loc

        t2.principal_fixed_closed_loc = -t1.principal_fixed_closed_loc
        t2.carry_fixed_closed_loc = -t1.carry_fixed_closed_loc
        t2.overheads_fixed_closed_loc = -t1.overheads_fixed_closed_loc
        t2.total_fixed_closed_loc = -t1.total_fixed_closed_loc

        t2.principal_fixed_opened_loc = -t1.principal_fixed_opened_loc
        t2.carry_fixed_opened_loc = -t1.carry_fixed_opened_loc
        t2.overheads_fixed_opened_loc = -t1.overheads_fixed_opened_loc
        t2.total_fixed_opened_loc = -t1.total_fixed_opened_loc

        return t1, t2

    def fx_trade_clone(self):
        # always used *_cash for groupping!
        # t1
        t1 = self.clone()
        t1.is_hidden = False
        t1.is_mismatch = False
        t1.trn_ccy = self.trn_ccy
        t1.stl_ccy = self.trn_ccy
        # t1.pos_size = self.pos_size
        t1.cash = self.pos_size
        t1.principal = self.pos_size
        t1.carry = 0.0
        t1.overheads = 0.0
        t1.ref_fx = 1.0
        # t1.cash_date = self.acc_date
        t1.acc_cash = self.acc_pos
        t1.str1_cash = self.str1_pos
        t1.str2_cash = self.str2_pos
        t1.str3_cash = self.str3_pos
        t1.set_case()
        t1.pricing()
        t1.calc()

        # t2
        t2 = self.clone()
        t2.is_hidden = False
        t2.is_mismatch = False
        t2.trn_ccy = self.trn_ccy
        t2.stl_ccy = self.stl_ccy
        t2.pos_size = self.principal
        # t2.cash = self.cash
        # t2.principal = self.principal
        # t2.carry = self.carry
        # t2.overheads = self.overheads
        try:
            t2.ref_fx = abs(self.pos_size / self.principal)
        except ArithmeticError:
            t2.ref_fx = 0.0
        t2.pricing()
        t2.calc()

        return t1, t2

    def transfer_clone(self, t1_cls, t2_cls, t1_pos_sign=-1.0, t1_cash_sign=1.0):
        # t1
        t1 = self.clone()
        t1.is_mismatch = False
        t1.is_hidden = False
        t1.trn_cls = t1_cls
        t1.acc_pos = self.acc_cash
        t1.acc_cash = self.acc_cash
        t1.str1_pos = self.str1_cash
        t1.str1_cash = self.str1_cash
        t1.str2_pos = self.str2_cash
        t1.str2_cash = self.str2_cash
        t1.str3_pos = self.str3_cash
        t1.str3_cash = self.str3_cash
        t1.pos_size = abs(self.pos_size) * t1_pos_sign
        t1.cash = abs(self.cash) * t1_cash_sign
        t1.principal = abs(self.principal) * t1_cash_sign
        t1.carry = abs(self.carry) * t1_cash_sign
        t1.overheads = abs(self.overheads) * t1_cash_sign
        t1.calc()

        # t2
        t2 = self.clone()
        t2.is_mismatch = False
        t2.is_hidden = False
        t2.trn_cls = t2_cls
        t2.acc_pos = self.acc_pos
        t2.acc_cash = self.acc_pos
        t2.str1_pos = self.str1_pos
        t2.str1_cash = self.str1_pos
        t2.str2_pos = self.str2_pos
        t2.str2_cash = self.str2_pos
        t2.str3_pos = self.str3_pos
        t2.str3_cash = self.str3_pos

        t2.pos_size = -t1.pos_size
        t2.cash = -t1.cash
        t2.principal = -t1.principal
        t2.carry = -t1.carry
        t2.overheads = -t1.overheads
        t2.calc()
        return t1, t2

    def fx_transfer_clone(self, trn_cls_in, trn_cls_out):
        # t1
        t1 = self.clone()
        t1.is_mismatch = False
        t1.is_hidden = False
        t1.trn_cls = trn_cls_out
        t1.acc_pos = self.acc_cash
        t1.acc_cash = self.acc_cash
        t1.str1_pos = self.str1_cash
        t1.str1_cash = self.str1_cash
        t1.str2_pos = self.str2_cash
        t1.str2_cash = self.str2_cash
        t1.str3_pos = self.str3_cash
        t1.str3_cash = self.str3_cash
        t1.pos_size = -self.pos_size
        t1.cash = -self.cash
        t1.principal = -self.principal
        t1.carry = -self.carry
        t1.overheads = -self.overheads
        t1.calc()

        # t2
        t2 = self.clone()
        t2.is_mismatch = False
        t2.is_hidden = False
        t2.trn_cls = trn_cls_in
        t2.acc_pos = self.acc_pos
        t2.acc_cash = self.acc_pos
        t2.str1_pos = self.str1_pos
        t2.str1_cash = self.str1_pos
        t2.str2_pos = self.str2_pos
        t2.str2_cash = self.str2_pos
        t2.str3_pos = self.str3_pos
        t2.str3_cash = self.str3_pos
        t2.pos_size = -self.pos_size
        t2.cash = self.cash
        t2.principal = self.principal
        t2.carry = self.carry
        t2.overheads = self.overheads
        t2.calc()
        return t1, t2

    def is_show_details(self, acc):
        if self.case in [1, 2] and self.report.show_transaction_details:
            return acc and acc.type and acc.type.show_transaction_details
        return False
