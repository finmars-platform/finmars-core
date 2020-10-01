# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division

import copy
import csv
import logging
import sys
import uuid
from collections import Counter, defaultdict
from datetime import timedelta, date
from io import StringIO
from itertools import groupby

from django.conf import settings
from django.db.models import Q
from django.utils.functional import cached_property
from django.utils.translation import ugettext, ugettext_lazy

from poms.accounts.models import Account, AccountType
from poms.common import formula
from poms.common.formula_accruals import f_xirr, f_duration
from poms.common.utils import date_now, isclose
from poms.currencies.models import Currency
from poms.instruments.models import Instrument, InstrumentType, CostMethod, InstrumentClass
from poms.obj_attrs.utils import get_attributes_prefetch
from poms.obj_perms.utils import get_permissions_prefetch_lookups
from poms.portfolios.models import Portfolio
from poms.reports.pricing import FakeInstrumentPricingProvider, FakeCurrencyFxRateProvider, CurrencyFxRateProvider
from poms.reports.pricing import InstrumentPricingProvider
from poms.reports.utils import sprint_table
from poms.strategies.models import Strategy1, Strategy2, Strategy3, Strategy1Subgroup, Strategy1Group, \
    Strategy2Subgroup, Strategy2Group, Strategy3Subgroup, Strategy3Group
from poms.tags.utils import get_tag_prefetch
from poms.transactions.models import TransactionClass, Transaction, ComplexTransaction

_l = logging.getLogger('poms.reports')


class _Base:
    is_cloned = False
    report = None
    pricing_provider = None
    fx_rate_provider = None

    dump_columns = []

    def __init__(self, report, pricing_provider, fx_rate_provider):
        self.report = report
        self.pricing_provider = pricing_provider
        self.fx_rate_provider = fx_rate_provider

    def clone(self):
        ret = copy.copy(self)
        ret.is_cloned = True
        return ret

    @classmethod
    def dump_values(cls, obj, columns=None):
        if columns is None:
            columns = cls.dump_columns
        row = []
        for f in columns:
            row.append(getattr(obj, f))
        return row

    @classmethod
    def sdumps(cls, items, columns=None, filter=None, in_csv=False):
        if columns is None:
            columns = cls.dump_columns

        data = []
        for item in items:
            if filter and callable(filter):
                if filter(item):
                    pass
                else:
                    continue
            data.append(cls.dump_values(item, columns=columns))

        if in_csv:
            si = StringIO()
            cw = csv.writer(si)
            cw.writerow(columns)
            for r in data:
                cw.writerow(r)
            return si.getvalue()
        return sprint_table(data, columns)

    @classmethod
    def dumps(cls, items, columns=None, trn_filter=None, in_csv=None):
        _l.debug('\n%s', cls.sdumps(items, columns=columns, filter=filter, in_csv=in_csv))


class VirtualTransaction(_Base):
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
    alloc_bl = None
    alloc_pl = None

    trade_price = 0.0

    # total_real_res = 0.0
    # total_unreal_res = 0.0
    notes = None

    # calculated ----------------------------------------------------
    case = 0

    # report ccy ----------------------------------------------------
    report_ccy_cur = None
    report_ccy_cur_fx = 0.0
    report_ccy_cash_hist = None
    report_ccy_cash_hist_fx = 0.0
    report_ccy_acc_hist = None
    report_ccy_acc_hist_fx = 0.0

    # instr
    instr_price_cur = None
    instr_price_cur_principal_price = 0.0
    instr_price_cur_accrued_price = 0.0
    instr_pricing_ccy_cur = None
    instr_pricing_ccy_cur_fx = 0.0
    instr_accrued_ccy_cur = None
    instr_accrued_ccy_cur_fx = 0.0

    # trn ccy ----------------------------------------------------
    trn_ccy_cash_hist = None
    trn_ccy_cash_hist_fx = 0.0
    trn_ccy_acc_hist = None
    trn_ccy_acc_hist_fx = 0.0
    trn_ccy_cur = None
    trn_ccy_cur_fx = 0.0

    # stl ccy ----------------------------------------------------
    stl_ccy_cash_hist = None
    stl_ccy_cash_hist_fx = 0.0
    stl_ccy_acc_hist = None
    stl_ccy_acc_hist_fx = 0.0
    stl_ccy_cur = None
    stl_ccy_cur_fx = 0.0

    # general ----------------------------------------------------

    mismatch = 0.0

    instr_principal = 0.0
    instr_principal_res = 0.0
    instr_accrued = 0.0
    instr_accrued_res = 0.0

    gross_cost_res = 0.0
    net_cost_res = 0.0
    principal_invested_res = 0.0
    amount_invested_res = 0.0

    balance_pos_size = 0.0
    remaining_pos_size = 0.0
    remaining_pos_size_percent = 0.0  # calculated in second pass
    ytm = 0.0
    time_invested_days = 0.0
    time_invested = 0.0
    weighted_ytm = 0.0  # calculated in second pass
    weighted_time_invested_days = 0.0  # calculated in second pass
    weighted_time_invested = 0.0  # calculated in second pass

    # Cash related ----------------------------------------------------

    cash_res = 0.0

    # full P&L related ----------------------------------------------------
    total = 0.0

    principal_res = 0.0
    carry_res = 0.0
    overheads_res = 0.0
    total_res = 0.0

    # full / closed ----------------------------------------------------
    principal_closed_res = 0.0
    carry_closed_res = 0.0
    overheads_closed_res = 0.0
    total_closed_res = 0.0

    # full / opened ----------------------------------------------------
    principal_opened_res = 0.0
    carry_opened_res = 0.0
    overheads_opened_res = 0.0
    total_opened_res = 0.0

    # fx ----------------------------------------------------
    pl_fx_mul = 0.0
    principal_fx_res = 0.0
    carry_fx_res = 0.0
    overheads_fx_res = 0.0
    total_fx_res = 0.0

    # fx / closed ----------------------------------------------------
    principal_fx_closed_res = 0.0
    carry_fx_closed_res = 0.0
    overheads_fx_closed_res = 0.0
    total_fx_closed_res = 0.0

    # fx / opened ----------------------------------------------------
    principal_fx_opened_res = 0.0
    carry_fx_opened_res = 0.0
    overheads_fx_opened_res = 0.0
    total_fx_opened_res = 0.0

    # fixed ----------------------------------------------------
    pl_fixed_mul = 0.0
    principal_fixed_res = 0.0
    carry_fixed_res = 0.0
    overheads_fixed_res = 0.0
    total_fixed_res = 0.0

    # fixed / closed ----------------------------------------------------
    principal_fixed_closed_res = 0.0
    carry_fixed_closed_res = 0.0
    overheads_fixed_closed_res = 0.0
    total_fixed_closed_res = 0.0

    # fixed / opened ----------------------------------------------------
    principal_fixed_opened_res = 0.0
    carry_fixed_opened_res = 0.0
    overheads_fixed_opened_res = 0.0
    total_fixed_opened_res = 0.0

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
        super(VirtualTransaction, self).__init__(report, pricing_provider, fx_rate_provider)
        overrides = overrides or {}
        self.trn = trn
        self.lid = uuid.uuid1()
        self.pk = overrides.get('pk', trn.pk)
        self.trn_code = overrides.get('transaction_code', trn.transaction_code)
        self.trn_cls = overrides.get('transaction_class', trn.transaction_class)

        self.instr = overrides.get('instrument', trn.instrument)
        self.trn_ccy = overrides.get('transaction_currency', trn.transaction_currency)
        self.pos_size = overrides.get('position_size_with_sign', trn.position_size_with_sign)

        self.stl_ccy = overrides.get('settlement_currency', trn.settlement_currency)
        self.cash = overrides.get('cash_consideration', trn.cash_consideration)

        self.principal = overrides.get('principal_with_sign', trn.principal_with_sign)
        self.carry = overrides.get('carry_with_sign', trn.carry_with_sign)
        self.overheads = overrides.get('overheads_with_sign', trn.overheads_with_sign)

        self.ref_fx = overrides.get('reference_fx_rate', trn.reference_fx_rate)

        self.trn_date = overrides.get('transaction_date', trn.transaction_date)
        self.acc_date = overrides.get('accounting_date', trn.accounting_date)
        self.cash_date = overrides.get('cash_date', trn.cash_date)

        self.prtfl = overrides.get('portfolio', trn.portfolio)

        self.acc_pos = overrides.get('account_position', trn.account_position)
        self.acc_cash = overrides.get('account_cash', trn.account_cash)
        self.acc_interim = overrides.get('account_interim', trn.account_interim)

        self.str1_pos = overrides.get('strategy1_position', trn.strategy1_position)
        self.str1_cash = overrides.get('strategy1_cash', trn.strategy1_cash)
        self.str2_pos = overrides.get('strategy2_position', trn.strategy2_position)
        self.str2_cash = overrides.get('strategy2_cash', trn.strategy2_cash)
        self.str3_pos = overrides.get('strategy3_position', trn.strategy3_position)
        self.str3_cash = overrides.get('strategy3_cash', trn.strategy3_cash)

        self.link_instr = overrides.get('linked_instrument', trn.linked_instrument)

        self.alloc_bl = overrides.get('allocation_balance', trn.allocation_balance)
        self.alloc_pl = overrides.get('allocation_pl', trn.allocation_pl)

        self.trade_price = overrides.get('trade_price', trn.trade_price)

        self.notes = overrides.get('notes', trn.notes)

        self.set_case()

    def set_case(self):
        if self.acc_date <= self.report.report_date < self.cash_date:
            self.case = 1
        elif self.cash_date <= self.report.report_date < self.acc_date:
            self.case = 2
        else:
            self.case = 0

    def __str__(self):
        return str(self.pk)

    def __repr__(self):
        return 'VT(%s)' % self.pk

    def pricing(self):
        # report ccy ----------------------------------------------------
        self.report_ccy_cur = self.fx_rate_provider[self.report.report_currency]
        self.report_ccy_cur_fx = self.report_ccy_cur.fx_rate
        self.report_ccy_cash_hist = self.fx_rate_provider[self.report.report_currency, self.acc_date]
        self.report_ccy_cash_hist_fx = self.report_ccy_cash_hist.fx_rate
        self.report_ccy_acc_hist = self.fx_rate_provider[self.report.report_currency, self.cash_date]
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

        # instr ----------------------------------------------------
        if self.instr:
            self.instr_price_cur = self.pricing_provider[self.instr]
            self.instr_price_cur_principal_price = self.instr_price_cur.principal_price
            self.instr_price_cur_accrued_price = self.instr_price_cur.accrued_price
            self.instr_pricing_ccy_cur = self.fx_rate_provider[self.instr.pricing_currency]
            self.instr_pricing_ccy_cur_fx = self.instr_pricing_ccy_cur.fx_rate * report_ccy_cur_fx
            self.instr_accrued_ccy_cur = self.fx_rate_provider[self.instr.accrued_currency]
            self.instr_accrued_ccy_cur_fx = self.instr_accrued_ccy_cur.fx_rate * report_ccy_cur_fx

        # trn ccy ----------------------------------------------------
        if self.trn_ccy:
            self.trn_ccy_cash_hist = self.fx_rate_provider[self.trn_ccy, self.cash_date]
            self.trn_ccy_cash_hist_fx = self.trn_ccy_cash_hist.fx_rate * report_ccy_cash_hist_fx
            self.trn_ccy_acc_hist = self.fx_rate_provider[self.trn_ccy, self.acc_date]
            self.trn_ccy_acc_hist_fx = self.trn_ccy_acc_hist.fx_rate * report_ccy_acc_hist_fx
            self.trn_ccy_cur = self.fx_rate_provider[self.trn_ccy]
            self.trn_ccy_cur_fx = self.trn_ccy_cur.fx_rate * report_ccy_cur_fx

        # stl ccy ----------------------------------------------------
        if self.stl_ccy:
            self.stl_ccy_cash_hist = self.fx_rate_provider[self.stl_ccy, self.cash_date]
            self.stl_ccy_cash_hist_fx = self.stl_ccy_cash_hist.fx_rate * report_ccy_cash_hist_fx
            self.stl_ccy_acc_hist = self.fx_rate_provider[self.stl_ccy, self.acc_date]
            self.stl_ccy_acc_hist_fx = self.stl_ccy_acc_hist.fx_rate * report_ccy_cash_hist_fx
            self.stl_ccy_cur = self.fx_rate_provider[self.stl_ccy]
            self.stl_ccy_cur_fx = self.stl_ccy_cur.fx_rate * report_ccy_cur_fx

    def calc(self):
        # if not self.is_hidden:
        #     print(1)
        if self.trn_cls.id in [TransactionClass.BUY, TransactionClass.SELL, TransactionClass.TRANSACTION_PL,
                               TransactionClass.INSTRUMENT_PL, TransactionClass.FX_TRADE]:
            if self.instr:
                self.instr_principal = self.pos_size * self.instr.price_multiplier * self.instr_price_cur_principal_price
                self.instr_principal_res = self.instr_principal * self.instr_pricing_ccy_cur_fx

                self.instr_accrued = self.pos_size * self.instr.accrued_multiplier * self.instr_price_cur_accrued_price
                self.instr_accrued_res = self.instr_accrued * self.instr_pricing_ccy_cur_fx

            # Cash related ----------------------------------------------------

            self.cash_res = self.cash * self.stl_ccy_cur_fx

            # full P&L related ----------------------------------------------------
            self.total = self.principal + self.carry + self.overheads

            self.principal_res = self.principal * self.stl_ccy_cur_fx
            self.carry_res = self.carry * self.stl_ccy_cur_fx
            self.overheads_res = self.overheads * self.stl_ccy_cur_fx
            self.total_res = self.total * self.stl_ccy_cur_fx

            self.pl_fx_mul = self.stl_ccy_cur_fx - self.ref_fx * self.trn_ccy_cash_hist_fx
            self.pl_fixed_mul = self.ref_fx * self.trn_ccy_cash_hist_fx

            # full / closed ----------------------------------------------------
            self.principal_closed_res = self.principal_res * self.multiplier
            self.carry_closed_res = self.carry_res * self.multiplier
            self.overheads_closed_res = self.overheads_res * self.multiplier
            self.total_closed_res = self.total_res * self.multiplier

            # full / opened ----------------------------------------------------
            self.principal_opened_res = self.principal_res * (1.0 - self.multiplier)
            self.carry_opened_res = self.carry_res * (1.0 - self.multiplier)
            self.overheads_opened_res = self.overheads_res * (1.0 - self.multiplier)
            self.total_opened_res = self.total_res * (1.0 - self.multiplier)

            # fx ----------------------------------------------------
            self.principal_fx_res = self.principal * self.pl_fx_mul
            self.carry_fx_res = self.carry * self.pl_fx_mul
            self.overheads_fx_res = self.overheads * self.pl_fx_mul
            self.total_fx_res = self.total * self.pl_fx_mul

            # fx / closed ----------------------------------------------------
            self.principal_fx_closed_res = self.principal_fx_res * self.multiplier
            self.carry_fx_closed_res = self.carry_fx_res * self.multiplier
            self.overheads_fx_closed_res = self.overheads_fx_res * self.multiplier
            self.total_fx_closed_res = self.total_fx_res * self.multiplier

            # fx / opened ----------------------------------------------------
            self.principal_fx_opened_res = self.principal_fx_res * (1.0 - self.multiplier)
            self.carry_fx_opened_res = self.carry_fx_res * (1.0 - self.multiplier)
            self.overheads_fx_opened_res = self.overheads_fx_res * (1.0 - self.multiplier)
            self.total_fx_opened_res = self.total_fx_res * (1.0 - self.multiplier)

            # fixed ----------------------------------------------------
            self.principal_fixed_res = self.principal * self.pl_fixed_mul
            self.carry_fixed_res = self.carry * self.pl_fixed_mul
            self.overheads_fixed_res = self.overheads * self.pl_fixed_mul
            self.total_fixed_res = self.total * self.pl_fixed_mul

            # fixed / closed ----------------------------------------------------
            self.principal_fixed_closed_res = self.principal_fixed_res * self.multiplier
            self.carry_fixed_closed_res = self.carry_fixed_res * self.multiplier
            self.overheads_fixed_closed_res = self.overheads_fixed_res * self.multiplier
            self.total_fixed_closed_res = self.total_fixed_res * self.multiplier

            # fixed / opened ----------------------------------------------------
            self.principal_fixed_opened_res = self.principal_fixed_res * (1.0 - self.multiplier)
            self.carry_fixed_opened_res = self.carry_fixed_res * (1.0 - self.multiplier)
            self.overheads_fixed_opened_res = self.overheads_fixed_res * (1.0 - self.multiplier)
            self.total_fixed_opened_res = self.total_fixed_res * (1.0 - self.multiplier)

            # ----------------------------------------------------

            if not self.is_cloned:
                try:
                    self.gross_cost_res = self.principal_res * self.ref_fx * \
                                          (self.trn_ccy_cur_fx / self.instr_pricing_ccy_cur_fx) * \
                                          (1.0 - self.multiplier) / self.pos_size / self.instr.price_multiplier
                except ArithmeticError:
                    self.gross_cost_res = 0.0

                try:
                    self.net_cost_res = (self.principal_res + self.overheads_res) * self.ref_fx * \
                                        (self.trn_ccy_cur_fx / self.instr_pricing_ccy_cur_fx) * \
                                        (1.0 - self.multiplier) / self.pos_size / self.instr.price_multiplier
                except ArithmeticError:
                    self.net_cost_res = 0.0





                try:
                    self.principal_invested_res = self.principal_res * self.ref_fx * \
                                                  (self.trn_ccy_cur_fx / self.instr_pricing_ccy_cur_fx) * \
                                                  (1.0 - self.multiplier)
                except ArithmeticError:
                    self.principal_invested_res = 0.0

                try:
                    self.amount_invested_res = self.total_res * self.ref_fx * \
                                               (self.trn_ccy_cur_fx / self.instr_pricing_ccy_cur_fx) * \
                                               (1.0 - self.multiplier)
                except ArithmeticError:
                    self.amount_invested_res = 0.0

                if self.trn_cls.id in [TransactionClass.BUY, TransactionClass.SELL] and self.instr:
                    # try:
                    #     self.remaining_pos_size_percent = self.remaining_pos_size / balance_pos_size
                    # except ArithmeticError:
                    #     self.remaining_pos_size_percent = 0.0
                    try:
                        future_accrual_payments = self.instr.get_future_accrual_payments(
                            d0=self.acc_date,
                            v0=self.trade_price,
                            principal_ccy_fx=self.instr_pricing_ccy_cur_fx,
                            accrual_ccy_fx=self.instr_accrued_ccy_cur_fx
                        )
                    except (ValueError, TypeError):
                        future_accrual_payments = False
                    self.ytm = f_xirr(future_accrual_payments)

                    self.time_invested_days = (self.report.report_date - self.acc_date).days
                    self.time_invested = self.time_invested_days / 365.0

                    self.weighted_ytm = self.ytm * self.remaining_pos_size_percent
                    self.weighted_time_invested_days = self.time_invested * self.remaining_pos_size_percent
                    self.weighted_time_invested = self.time_invested * self.remaining_pos_size_percent

        elif self.trn_cls.id in [TransactionClass.CASH_INFLOW, TransactionClass.CASH_OUTFLOW]:
            self.pl_fx_mul = self.stl_ccy_cur_fx - self.ref_fx * self.trn_ccy_acc_hist_fx
            self.pl_fixed_mul = self.ref_fx * self.trn_ccy_acc_hist_fx

            self.principal_res = self.cash * self.pl_fx_mul
            self.principal_closed_res = self.principal_res
            self.principal_fx_res = self.principal_res
            self.principal_fx_closed_res = self.principal_res

        if self.trn_cls.id in [TransactionClass.CASH_INFLOW, TransactionClass.CASH_OUTFLOW]:
            self.mismatch = 0.0
        else:
            self.mismatch = self.cash - self.total

    # def calc_pass2(self, balance_pos_size):
    #     # called after "balance"
    #     if not self.is_cloned and self.trn_cls.id in [TransactionClass.BUY, TransactionClass.SELL] and self.instr:
    #         # try:
    #         #     self.remaining_pos_size_percent = self.remaining_pos_size / balance_pos_size
    #         # except ArithmeticError:
    #         #     self.remaining_pos_size_percent = 0.0
    #         try:
    #             future_accrual_payments = self.instr.get_future_accrual_payments(
    #                 d0=self.acc_date,
    #                 v0=self.trade_price,
    #                 principal_ccy_fx=self.instr_pricing_ccy_cur_fx,
    #                 accrual_ccy_fx=self.instr_accrued_ccy_cur_fx
    #             )
    #         except (ValueError, TypeError):
    #             future_accrual_payments = False
    #         self.ytm = f_xirr(future_accrual_payments)
    #
    #         self.time_invested_days = (self.report.report_date - self.acc_date).days
    #         self.time_invested = self.time_invested_days / 365.0
    #
    #         self.weighted_ytm = self.ytm * self.remaining_pos_size_percent
    #         self.weighted_time_invested_days = self.time_invested * self.remaining_pos_size_percent
    #         self.weighted_time_invested = self.time_invested * self.remaining_pos_size_percent

    @staticmethod
    def approach_clone(cur, closed, mul_delta):
        def _clean(t):
            t.is_mismatch = False

            t.report_ccy_cur = None
            t.report_ccy_cur_fx = float('nan')
            t.report_ccy_cash_hist = None
            t.report_ccy_cash_hist_fx = float('nan')
            t.report_ccy_acc_hist = None
            t.report_ccy_acc_hist_fx = float('nan')

            t.instr_price_cur = None
            t.instr_price_cur_principal_price = float('nan')
            t.instr_price_cur_accrued_price = float('nan')
            t.instr_pricing_ccy_cur = None
            t.instr_pricing_ccy_cur_fx = float('nan')
            t.instr_accrued_ccy_cur = None
            t.instr_accrued_ccy_cur_fx = float('nan')

            t.trn_ccy_cash_hist = None
            t.trn_ccy_cash_hist_fx = float('nan')
            t.trn_ccy_acc_hist = None
            t.trn_ccy_acc_hist_fx = float('nan')
            t.trn_ccy_cur = None
            t.trn_ccy_cur_fx = float('nan')

            t.stl_ccy_cash_hist = None
            t.stl_ccy_cash_hist_fx = float('nan')
            t.stl_ccy_acc_hist = None
            t.stl_ccy_acc_hist_fx = float('nan')
            t.stl_ccy_cur = None
            t.stl_ccy_cur_fx = float('nan')

            t.mismatch = 0.0
            t.avco_multiplier = 0.0
            t.avco_closed_by = []
            t.fifo_multiplier = 0.0
            t.fifo_closed_by = []
            t.multiplier = 1.0
            t.closed_by = []
            t.cash = 0.0
            t.cash_res = 0.0

            t.instr_principal = float('nan')
            t.instr_principal_res = 0.0
            t.instr_accrued = float('nan')
            t.instr_accrued_res = 0.0

            t.principal = float('nan')
            t.carry = float('nan')
            t.overheads = float('nan')
            t.total = float('nan')

            t.pl_fx_mul = float('nan')
            t.pl_fixed_mul = float('nan')

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

        # t1 ----
        t1 = closed1.clone()
        t1.trn_cls = cur1.trn_cls
        t1.pk = 'a1,%s,%s,%s' % (closed1.pk, cur1.pk, t1.trn_cls)

        _clean(t1)

        t1.pos_size = -pos_size

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

        # t2 ----
        t2 = cur1.clone()
        t2.trn_cls = closed1.trn_cls
        t2.pk = 'a2,%s,%s,%s' % (closed1.pk, cur1.pk, t2.trn_cls)

        _clean(t2)

        t2.pos_size = -t1.pos_size

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

        return t1, t2

    def transfer_clone(self, t1_cls, t2_cls, t1_pos_sign=-1.0, t1_cash_sign=1.0):
        # t1
        t1 = self.clone()
        t1.is_mismatch = False
        t1.is_hidden = False
        t1.trn_cls = t1_cls
        t1.acc_pos = self.acc_pos
        t1.acc_cash = self.acc_pos
        t1.str1_pos = self.str1_pos
        t1.str1_cash = self.str1_pos
        t1.str2_pos = self.str2_pos
        t1.str2_cash = self.str2_pos
        t1.str3_pos = self.str3_pos
        t1.str3_cash = self.str3_pos

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
        t2.acc_pos = self.acc_cash
        t2.acc_cash = self.acc_cash
        t2.str1_pos = self.str1_cash
        t2.str1_cash = self.str1_cash
        t2.str2_pos = self.str2_cash
        t2.str2_cash = self.str2_cash
        t2.str3_pos = self.str3_cash
        t2.str3_cash = self.str3_cash

        t2.pos_size = -t1.pos_size
        t2.cash = -t1.cash
        t2.principal = -t1.principal
        t2.carry = -t1.carry
        t2.overheads = -t1.overheads
        t2.calc()
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

    # globals ----------------------------------------------------

    def is_show_details(self, acc):
        if self.case in [1, 2] and self.report.show_transaction_details:
            return acc and acc.type and acc.type.show_transaction_details
        return False


class ReportItem(_Base):
    TYPE_UNKNOWN = 0
    TYPE_INSTRUMENT = 1
    TYPE_CURRENCY = 2
    TYPE_TRANSACTION_PL = 3
    TYPE_FX_TRADE = 4
    TYPE_CASH_IN_OUT = 5
    TYPE_MISMATCH = 100  # Linked instrument
    TYPE_SUMMARY = 200
    # TYPE_INVESTED_CURRENCY = 300
    # TYPE_INVESTED_SUMMARY = 301
    TYPE_CHOICES = (
        (TYPE_UNKNOWN, ugettext_lazy('Unknown')),
        (TYPE_INSTRUMENT, ugettext_lazy('Instrument')),
        (TYPE_CURRENCY, ugettext_lazy('Currency')),
        (TYPE_TRANSACTION_PL, ugettext_lazy('Transaction PL')),
        (TYPE_FX_TRADE, ugettext_lazy('FX-Trade')),
        (TYPE_CASH_IN_OUT, ugettext_lazy('Cash In/Out')),
        (TYPE_MISMATCH, ugettext_lazy('Mismatch')),
        (TYPE_SUMMARY, ugettext_lazy('Summary')),
        # (TYPE_INVESTED_CURRENCY, 'Invested'),
        # (TYPE_INVESTED_SUMMARY, 'Invested summary'),
    )

    SUBTYPE_UNKNOWN = 0
    SUBTYPE_TOTAL = 1
    SUBTYPE_CLOSED = 2
    SUBTYPE_OPENED = 3
    SUBTYPE_CHOICES = (
        (SUBTYPE_UNKNOWN, ugettext_lazy('Unknown')),
        (SUBTYPE_TOTAL, ugettext_lazy('Total')),
        (SUBTYPE_CLOSED, ugettext_lazy('Closed')),
        (SUBTYPE_OPENED, ugettext_lazy('Opened')),
    )

    type = TYPE_UNKNOWN
    subtype = SUBTYPE_UNKNOWN
    trn = None

    instr = None
    ccy = None
    trn_ccy = None  # for FX_TRADE
    prtfl = None
    acc = None
    str1 = None
    str2 = None
    str3 = None
    # detail_trn = None
    custom_fields = []
    is_empty = False

    pricing_ccy = None
    last_notes = ''

    # link
    mismatch = 0.0
    # mismatch_ccy = None
    mismatch_prtfl = None
    mismatch_acc = None

    # allocations
    alloc_bl = None
    alloc_pl = None

    # pricing
    report_ccy_cur = None
    report_ccy_cur_fx = 0.0
    instr_price_cur = None
    instr_price_cur_principal_price = 0.0
    instr_price_cur_accrued_price = 0.0
    instr_pricing_ccy_cur = None
    instr_pricing_ccy_cur_fx = 0.0
    instr_accrued_ccy_cur = None
    instr_accrued_ccy_cur_fx = 0.0
    ccy_cur = None
    ccy_cur_fx = 0.0
    pricing_ccy_cur = None
    pricing_ccy_cur_fx = 0.0

    # instr
    instr_principal_res = 0.0
    instr_accrued_res = 0.0
    exposure_res = 0.0
    exposure_loc = 0.0

    instr_accrual = None
    instr_accrual_accrued_price = 0.0

    # ----------------------------------------------------

    pos_size = 0.0
    market_value_res = 0.0
    market_value_loc = 0.0
    cost_res = 0.0
    ytm = 0.0
    modified_duration = 0.0
    ytm_at_cost = 0.0
    time_invested_days = 0.0
    time_invested = 0.0
    gross_cost_res = 0.0
    gross_cost_loc = 0.0
    net_cost_res = 0.0
    net_cost_loc = 0.0
    principal_invested_res = 0.0
    principal_invested_loc = 0.0
    amount_invested_res = 0.0
    amount_invested_loc = 0.0
    pos_return_res = 0.0
    pos_return_loc = 0.0
    net_pos_return_res = 0.0
    net_pos_return_loc = 0.0
    daily_price_change = 0.0
    mtd_price_change = 0.0

    # P&L ----------------------------------------------------

    # full ----------------------------------------------------
    principal_res = 0.0
    carry_res = 0.0
    overheads_res = 0.0
    total_res = 0.0

    principal_loc = 0.0
    carry_loc = 0.0
    overheads_loc = 0.0
    total_loc = 0.0

    # full / closed ----------------------------------------------------
    principal_closed_res = 0.0
    carry_closed_res = 0.0
    overheads_closed_res = 0.0
    total_closed_res = 0.0

    principal_closed_loc = 0.0
    carry_closed_loc = 0.0
    overheads_closed_loc = 0.0
    total_closed_loc = 0.0

    # full / opened ----------------------------------------------------
    principal_opened_res = 0.0
    carry_opened_res = 0.0
    overheads_opened_res = 0.0
    total_opened_res = 0.0

    principal_opened_loc = 0.0
    carry_opened_loc = 0.0
    overheads_opened_loc = 0.0
    total_opened_loc = 0.0

    # fx ----------------------------------------------------
    principal_fx_res = 0.0
    carry_fx_res = 0.0
    overheads_fx_res = 0.0
    total_fx_res = 0.0

    principal_fx_loc = 0.0
    carry_fx_loc = 0.0
    overheads_fx_loc = 0.0
    total_fx_loc = 0.0

    # fx / closed ----------------------------------------------------
    principal_fx_closed_res = 0.0
    carry_fx_closed_res = 0.0
    overheads_fx_closed_res = 0.0
    total_fx_closed_res = 0.0

    principal_fx_closed_loc = 0.0
    carry_fx_closed_loc = 0.0
    overheads_fx_closed_loc = 0.0
    total_fx_closed_loc = 0.0

    # fx / opened ----------------------------------------------------
    principal_fx_opened_res = 0.0
    carry_fx_opened_res = 0.0
    overheads_fx_opened_res = 0.0
    total_fx_opened_res = 0.0

    principal_fx_opened_loc = 0.0
    carry_fx_opened_loc = 0.0
    overheads_fx_opened_loc = 0.0
    total_fx_opened_loc = 0.0

    # fixed ----------------------------------------------------
    principal_fixed_res = 0.0
    carry_fixed_res = 0.0
    overheads_fixed_res = 0.0
    total_fixed_res = 0.0

    principal_fixed_loc = 0.0
    carry_fixed_loc = 0.0
    overheads_fixed_loc = 0.0
    total_fixed_loc = 0.0

    # fixed / closed ----------------------------------------------------
    principal_fixed_closed_res = 0.0
    carry_fixed_closed_res = 0.0
    overheads_fixed_closed_res = 0.0
    total_fixed_closed_res = 0.0

    principal_fixed_closed_loc = 0.0
    carry_fixed_closed_loc = 0.0
    overheads_fixed_closed_loc = 0.0
    total_fixed_closed_loc = 0.0

    # fixed / opened ----------------------------------------------------
    principal_fixed_opened_res = 0.0
    carry_fixed_opened_res = 0.0
    overheads_fixed_opened_res = 0.0
    total_fixed_opened_res = 0.0

    principal_fixed_opened_loc = 0.0
    carry_fixed_opened_loc = 0.0
    overheads_fixed_opened_loc = 0.0
    total_fixed_opened_loc = 0.0

    pl_total_fields = [
        # full ----------------------------------------------------
        ('principal_res', None),
        ('carry_res', None),
        ('overheads_res', None),
        ('total_res', None),

        ('principal_loc', None),
        ('carry_loc', None),
        ('overheads_loc', None),
        ('total_loc', None),

        # fx ----------------------------------------------------
        ('principal_fx_res', None),
        ('carry_fx_res', None),
        ('overheads_fx_res', None),
        ('total_fx_res', None),

        ('principal_fx_loc', None),
        ('carry_fx_loc', None),
        ('overheads_fx_loc', None),
        ('total_fx_loc', None),
        # fixed ----------------------------------------------------
        ('principal_fixed_res', None),
        ('carry_fixed_res', None),
        ('overheads_fixed_res', None),
        ('total_fixed_res', None),

        ('principal_fixed_loc', None),
        ('carry_fixed_loc', None),
        ('overheads_fixed_loc', None),
        ('total_fixed_loc', None),
    ]
    pl_closed_fields = [
        # full / closed ----------------------------------------------------
        ('principal_closed_res', None),
        ('carry_closed_res', None),
        ('overheads_closed_res', None),
        ('total_closed_res', None),

        ('principal_closed_loc', None),
        ('carry_closed_loc', None),
        ('overheads_closed_loc', None),
        ('total_closed_loc', None),

        # fx / closed ----------------------------------------------------
        ('principal_fx_closed_res', None),
        ('carry_fx_closed_res', None),
        ('overheads_fx_closed_res', None),
        ('total_fx_closed_res', None),

        ('principal_fx_closed_loc', None),
        ('carry_fx_closed_loc', None),
        ('overheads_fx_closed_loc', None),
        ('total_fx_closed_loc', None),
        # fixed / closed ----------------------------------------------------
        ('principal_fixed_closed_res', None),
        ('carry_fixed_closed_res', None),
        ('overheads_fixed_closed_res', None),
        ('total_fixed_closed_res', None),

        ('principal_fixed_closed_loc', None),
        ('carry_fixed_closed_loc', None),
        ('overheads_fixed_closed_loc', None),
        ('total_fixed_closed_loc', None),
    ]
    pl_opened_fields = [
        # full / opened ----------------------------------------------------
        ('principal_opened_res', None),
        ('carry_opened_res', None),
        ('overheads_opened_res', None),
        ('total_opened_res', None),

        ('principal_opened_loc', None),
        ('carry_opened_loc', None),
        ('overheads_opened_loc', None),
        ('total_opened_loc', None),

        # fx / opened ----------------------------------------------------
        ('principal_fx_opened_res', None),
        ('carry_fx_opened_res', None),
        ('overheads_fx_opened_res', None),
        ('total_fx_opened_res', None),

        ('principal_fx_opened_loc', None),
        ('carry_fx_opened_loc', None),
        ('overheads_fx_opened_loc', None),
        ('total_fx_opened_loc', None),

        # fixed / opened ----------------------------------------------------
        ('principal_fixed_opened_res', None),
        ('carry_fixed_opened_res', None),
        ('overheads_fixed_opened_res', None),
        ('total_fixed_opened_res', None),

        ('principal_fixed_opened_loc', None),
        ('carry_fixed_opened_loc', None),
        ('overheads_fixed_opened_loc', None),
        ('total_fixed_opened_loc', None),
    ]

    dump_columns = [
        # 'is_cloned',
        'type_code',
        'subtype_code',
        # 'trn',
        'instr',
        'ccy',
        'trn_ccy',
        'prtfl',
        'acc',
        'str1',
        'str2',
        'str3',
        # 'custom_fields',
        # 'is_empty',
        'pricing_ccy',
        'last_notes',
        'mismatch',
        'mismatch_prtfl',
        'mismatch_acc',
        'alloc_bl',
        'alloc_pl',
        'report_ccy_cur',
        'report_ccy_cur_fx',
        'instr_price_cur',
        'instr_price_cur_principal_price',
        'instr_price_cur_accrued_price',
        'instr_pricing_ccy_cur',
        'instr_pricing_ccy_cur_fx',
        'instr_accrued_ccy_cur',
        'instr_accrued_ccy_cur_fx',
        'ccy_cur',
        'ccy_cur_fx',
        'pricing_ccy_cur',
        'pricing_ccy_cur_fx',
        'instr_principal_res',
        'instr_accrued_res',
        'exposure_res',
        'exposure_loc',
        'instr_accrual',
        'instr_accrual_accrued_price',
        'pos_size',
        'market_value_res',
        'market_value_loc',
        'cost_res',
        'ytm',
        'modified_duration',
        'ytm_at_cost',
        'time_invested_days',
        'time_invested',
        'gross_cost_res',
        'gross_cost_loc',
        'net_cost_res',
        'net_cost_loc',
        'principal_invested_res',
        'principal_invested_loc',
        'amount_invested_res',
        'amount_invested_loc',
        'pos_return_res',
        'pos_return_loc',
        'net_pos_return_res',
        'net_pos_return_loc',
        'daily_price_change',
        'mtd_price_change',
        'principal_res',
        'carry_res',
        'overheads_res',
        'total_res',
        'principal_loc',
        'carry_loc',
        'overheads_loc',
        'total_loc',
        'principal_closed_res',
        'carry_closed_res',
        'overheads_closed_res',
        'total_closed_res',
        'principal_closed_loc',
        'carry_closed_loc',
        'overheads_closed_loc',
        'total_closed_loc',
        'principal_opened_res',
        'carry_opened_res',
        'overheads_opened_res',
        'total_opened_res',
        'principal_opened_loc',
        'carry_opened_loc',
        'overheads_opened_loc',
        'total_opened_loc',
        'principal_fx_res',
        'carry_fx_res',
        'overheads_fx_res',
        'total_fx_res',
        'principal_fx_loc',
        'carry_fx_loc',
        'overheads_fx_loc',
        'total_fx_loc',
        'principal_fx_closed_res',
        'carry_fx_closed_res',
        'overheads_fx_closed_res',
        'total_fx_closed_res',
        'principal_fx_closed_loc',
        'carry_fx_closed_loc',
        'overheads_fx_closed_loc',
        'total_fx_closed_loc',
        'principal_fx_opened_res',
        'carry_fx_opened_res',
        'overheads_fx_opened_res',
        'total_fx_opened_res',
        'principal_fx_opened_loc',
        'carry_fx_opened_loc',
        'overheads_fx_opened_loc',
        'total_fx_opened_loc',
        'principal_fixed_res',
        'carry_fixed_res',
        'overheads_fixed_res',
        'total_fixed_res',
        'principal_fixed_loc',
        'carry_fixed_loc',
        'overheads_fixed_loc',
        'total_fixed_loc',
        'principal_fixed_closed_res',
        'carry_fixed_closed_res',
        'overheads_fixed_closed_res',
        'total_fixed_closed_res',
        'principal_fixed_closed_loc',
        'carry_fixed_closed_loc',
        'overheads_fixed_closed_loc',
        'total_fixed_closed_loc',
        'principal_fixed_opened_res',
        'carry_fixed_opened_res',
        'overheads_fixed_opened_res',
        'total_fixed_opened_res',
        'principal_fixed_opened_loc',
        'carry_fixed_opened_loc',
        'overheads_fixed_opened_loc',
        'total_fixed_opened_loc',
    ]

    def __init__(self, report, pricing_provider, fx_rate_provider, type):
        super(ReportItem, self).__init__(report, pricing_provider, fx_rate_provider)
        self.type = type

    @classmethod
    def from_trn(cls, report, pricing_provider, fx_rate_provider, type, trn, instr=None, ccy=None, trn_ccy=None,
                 prtfl=None, acc=None, str1=None, str2=None, str3=None, val=None):
        item = cls(report, pricing_provider, fx_rate_provider, type)
        item.trn = trn

        # item.instr = instr  # -> Instrument
        # item.ccy = ccy  # -> Currency
        item.prtfl = prtfl or trn.prtfl  # -> Portfolio
        item.alloc_bl = trn.alloc_bl
        item.alloc_pl = trn.alloc_pl

        if type in [ReportItem.TYPE_INSTRUMENT, ReportItem.TYPE_TRANSACTION_PL, ReportItem.TYPE_FX_TRADE,
                    ReportItem.TYPE_CASH_IN_OUT]:
            # full ----------------------------------------------------
            item.principal_res = trn.principal_res
            item.carry_res = trn.carry_res
            item.overheads_res = trn.overheads_res
            item.total_res = trn.total_res

            # full / closed ----------------------------------------------------
            item.principal_closed_res = trn.principal_closed_res
            item.carry_closed_res = trn.carry_closed_res
            item.overheads_closed_res = trn.overheads_closed_res
            item.total_closed_res = trn.total_closed_res

            # full / opened ----------------------------------------------------
            item.principal_opened_res = trn.principal_opened_res
            item.carry_opened_res = trn.carry_opened_res
            item.overheads_opened_res = trn.overheads_opened_res
            item.total_opened_res = trn.total_opened_res

            # fx ----------------------------------------------------
            item.principal_fx_res = trn.principal_fx_res
            item.carry_fx_res = trn.carry_fx_res
            item.overheads_fx_res = trn.overheads_fx_res
            item.total_fx_res = trn.total_fx_res

            # fx / closed ----------------------------------------------------
            item.principal_fx_closed_res = trn.principal_fx_closed_res
            item.carry_fx_closed_res = trn.carry_fx_closed_res
            item.overheads_fx_closed_res = trn.overheads_fx_closed_res
            item.total_fx_closed_res = trn.total_fx_closed_res

            # fx / opened ----------------------------------------------------
            item.principal_fx_opened_res = trn.principal_fx_opened_res
            item.carry_fx_opened_res = trn.carry_fx_opened_res
            item.overheads_fx_opened_res = trn.overheads_fx_opened_res
            item.total_fx_opened_res = trn.total_fx_opened_res

            # fixed ----------------------------------------------------
            item.principal_fixed_res = trn.principal_fixed_res
            item.carry_fixed_res = trn.carry_fixed_res
            item.overheads_fixed_res = trn.overheads_fixed_res
            item.total_fixed_res = trn.total_fixed_res

            # fixed / closed ----------------------------------------------------
            item.principal_fixed_closed_res = trn.principal_fixed_closed_res
            item.carry_fixed_closed_res = trn.carry_fixed_closed_res
            item.overheads_fixed_closed_res = trn.overheads_fixed_closed_res
            item.total_fixed_closed_res = trn.total_fixed_closed_res

            # fixed / opened ----------------------------------------------------
            item.principal_fixed_opened_res = trn.principal_fixed_opened_res
            item.carry_fixed_opened_res = trn.carry_fixed_opened_res
            item.overheads_fixed_opened_res = trn.overheads_fixed_opened_res
            item.total_fixed_opened_res = trn.total_fixed_opened_res

        if item.type == ReportItem.TYPE_INSTRUMENT:
            item.acc = acc or trn.acc_pos
            item.str1 = str1 or trn.str1_pos
            item.str2 = str2 or trn.str2_pos
            item.str3 = str3 or trn.str3_pos
            item.instr = instr or trn.instr

            if val is None:
                item.pos_size = trn.pos_size * (1.0 - trn.multiplier)
            else:
                item.pos_size = val
            item.cost_res = trn.principal_res * (1.0 - trn.multiplier)

            if trn.instr:
                item.pricing_ccy = trn.instr.pricing_currency
            else:
                item.pricing_ccy = trn.report.master_user.system_currency

            item.gross_cost_res = trn.gross_cost_res
            item.net_cost_res = trn.net_cost_res
            item.principal_invested_res = trn.principal_invested_res
            item.amount_invested_res = trn.amount_invested_res

            if trn.trn_cls.id in [TransactionClass.BUY, TransactionClass.SELL]:
                item.last_notes = trn.notes

            if not trn.is_cloned:
                item.ytm_at_cost = trn.weighted_ytm
                item.time_invested_days = trn.weighted_time_invested_days
                item.time_invested += trn.weighted_time_invested

        elif item.type == ReportItem.TYPE_CURRENCY:
            item.acc = acc or trn.acc_cash
            item.str1 = str1 or trn.str1_cash
            item.str2 = str2 or trn.str2_cash
            item.str3 = str3 or trn.str3_cash
            item.ccy = ccy or trn.trn_ccy

            if val is None:
                item.pos_size = 0.0
            else:
                item.pos_size = val

            item.pricing_ccy = trn.report.master_user.system_currency

        elif item.type == ReportItem.TYPE_FX_TRADE:
            item.acc = acc or trn.acc_cash
            item.str1 = str1 or trn.str1_cash
            item.str2 = str2 or trn.str2_cash
            item.str3 = str3 or trn.str3_cash
            item.ccy = ccy
            item.trn_ccy = trn_ccy

            item.pricing_ccy = trn.report.master_user.system_currency

        elif item.type == ReportItem.TYPE_CASH_IN_OUT:
            item.acc = acc or trn.acc_cash
            item.str1 = str1 or trn.str1_cash
            item.str2 = str2 or trn.str2_cash
            item.str3 = str3 or trn.str3_cash
            item.ccy = ccy

            item.pricing_ccy = trn.report.master_user.system_currency

        elif item.type == ReportItem.TYPE_TRANSACTION_PL:
            item.acc = acc or trn.acc_cash
            item.str1 = str1 or trn.str1_cash
            item.str2 = str2 or trn.str2_cash
            item.str3 = str3 or trn.str3_cash
            item.ccy = ccy or trn.trn_ccy

            item.pricing_ccy = trn.report.master_user.system_currency

            # item.principal_res = trn.principal_res
            # item.carry_res = trn.carry_res
            # item.overheads_res = trn.overheads_res
            pass

        elif item.type == ReportItem.TYPE_MISMATCH:
            item.prtfl = item.report.master_user.mismatch_portfolio
            item.acc = item.report.master_user.mismatch_account
            item.str1 = item.report.master_user.strategy1
            item.str2 = item.report.master_user.strategy2
            item.str3 = item.report.master_user.strategy3
            item.instr = trn.link_instr
            item.ccy = trn.stl_ccy
            item.mismatch_prtfl = trn.prtfl
            item.mismatch_acc = trn.acc_cash
            item.mismatch = trn.mismatch

        # elif item.type in [ReportItem.TYPE_SUMMARY, ReportItem.TYPE_INVESTED_SUMMARY]:
        elif item.type in [ReportItem.TYPE_SUMMARY, ]:
            item.pos_size = float('nan')

        # if trn.is_show_details(acc):
        #     item.detail_trn = trn

        return item

    @classmethod
    def from_item(cls, src):
        item = cls(src.report, src.pricing_provider, src.fx_rate_provider, src.type)

        item.instr = src.instr  # -> Instrument
        item.ccy = src.ccy  # -> Currency
        item.trn_ccy = src.trn_ccy  # -> Currency
        item.prtfl = src.prtfl  # -> Portfolio if use_portfolio
        # item.instr = src.instr
        item.acc = src.acc  # -> Account if use_account
        item.str1 = src.str1  # -> Strategy1 if use_strategy1
        item.str2 = src.str2  # -> Strategy2 if use_strategy2
        item.str3 = src.str3  # -> Strategy3 if use_strategy3

        item.pricing_ccy = src.pricing_ccy

        # if item.type in [ReportItem.TYPE_TRANSACTION_PL, ReportItem.TYPE_FX_TRADE]:
        #     item.trn = src.trn
        if src.detail_trn:
            item.trn = src.trn

        item.alloc_bl = src.alloc_bl
        item.alloc_pl = src.alloc_pl

        # item.mismatch_ccy = src.mismatch_ccy
        item.mismatch_prtfl = src.mismatch_prtfl
        item.mismatch_acc = src.mismatch_acc

        # if item.type in [ReportItem.TYPE_SUMMARY, ReportItem.TYPE_INVESTED_SUMMARY]:
        if item.type in [ReportItem.TYPE_SUMMARY]:
            item.pos_size = float('nan')

        return item

    def pricing(self):
        self.report_ccy_cur = self.fx_rate_provider[self.report.report_currency]
        self.report_ccy_cur_fx = self.report_ccy_cur.fx_rate

        try:
            report_ccy_cur_fx = 1.0 / self.report_ccy_cur_fx
        except ArithmeticError:
            report_ccy_cur_fx = 0.0

        if self.instr:
            self.instr_price_cur = self.pricing_provider[self.instr]
            self.instr_price_cur_principal_price = self.instr_price_cur.principal_price
            self.instr_price_cur_accrued_price = self.instr_price_cur.accrued_price
            self.instr_pricing_ccy_cur = self.fx_rate_provider[self.instr.pricing_currency]
            self.instr_pricing_ccy_cur_fx = self.instr_pricing_ccy_cur.fx_rate * report_ccy_cur_fx
            self.instr_accrued_ccy_cur = self.fx_rate_provider[self.instr.accrued_currency]
            self.instr_accrued_ccy_cur_fx = self.instr_accrued_ccy_cur.fx_rate * report_ccy_cur_fx

            self.pricing_ccy_cur = self.instr_pricing_ccy_cur
            self.pricing_ccy_cur_fx = self.instr_pricing_ccy_cur_fx

        if self.ccy:
            self.ccy_cur = self.fx_rate_provider[self.ccy]
            self.ccy_cur_fx = self.ccy_cur.fx_rate * report_ccy_cur_fx

            if self.pricing_ccy:
                self.pricing_ccy_cur = self.fx_rate_provider[self.pricing_ccy]
                self.pricing_ccy_cur_fx = self.pricing_ccy_cur.fx_rate * report_ccy_cur_fx

    def add(self, o):
        # TODO: in TYPE_INSTRUMENT or global
        # full ----------------------------------------------------
        self.principal_res += o.principal_res
        self.carry_res += o.carry_res
        self.overheads_res += o.overheads_res

        # full / closed ----------------------------------------------------
        self.principal_closed_res += o.principal_closed_res
        self.carry_closed_res += o.carry_closed_res
        self.overheads_closed_res += o.overheads_closed_res

        # full / opened ----------------------------------------------------
        self.principal_opened_res += o.principal_opened_res
        self.carry_opened_res += o.carry_opened_res
        self.overheads_opened_res += o.overheads_opened_res

        # fx ----------------------------------------------------
        self.principal_fx_res += o.principal_fx_res
        self.carry_fx_res += o.carry_fx_res
        self.overheads_fx_res += o.overheads_fx_res

        # fx / closed ----------------------------------------------------
        self.principal_fx_closed_res += o.principal_fx_closed_res
        self.carry_fx_closed_res += o.carry_fx_closed_res
        self.overheads_fx_closed_res += o.overheads_fx_closed_res

        # fx / opened ----------------------------------------------------
        self.principal_fx_opened_res += o.principal_fx_opened_res
        self.carry_fx_opened_res += o.carry_fx_opened_res
        self.overheads_fx_opened_res += o.overheads_fx_opened_res

        # fixed ----------------------------------------------------
        self.principal_fixed_res += o.principal_fixed_res
        self.carry_fixed_res += o.carry_fixed_res
        self.overheads_fixed_res += o.overheads_fixed_res

        # fixed / closed ----------------------------------------------------
        self.principal_fixed_closed_res += o.principal_fixed_closed_res
        self.carry_fixed_closed_res += o.carry_fixed_closed_res
        self.overheads_fixed_closed_res += o.overheads_fixed_closed_res

        # fixed / opened ----------------------------------------------------
        self.principal_fixed_opened_res += o.principal_fixed_opened_res
        self.carry_fixed_opened_res += o.carry_fixed_opened_res
        self.overheads_fixed_opened_res += o.overheads_fixed_opened_res

        # if self.type == ReportItem.TYPE_CURRENCY or self.type == ReportItem.TYPE_INVESTED_CURRENCY:
        if self.type == ReportItem.TYPE_CURRENCY:
            self.pos_size += o.pos_size

            # self.market_value_res += o.pos_size * o.ccy_cur_fx

        elif self.type == ReportItem.TYPE_INSTRUMENT:
            self.pos_size += o.pos_size

            # self.principal_res += o.instr_principal_res
            # self.carry_res += o.instr_accrued_res

            # self.market_value_res += o.instr_principal_res + o.instr_accrued_res
            self.cost_res += o.cost_res

            # self.total_real_res += o.total_real_res
            # self.total_unreal_res += o.market_value_res + o.cost_res
            # self.total_unreal_res += (o.instr_principal_res + o.instr_accrued_res) + o.cost_res

            self.ytm_at_cost += o.ytm_at_cost
            self.time_invested_days += o.time_invested_days
            self.time_invested += o.time_invested

            self.gross_cost_res += o.gross_cost_res
            self.net_cost_res += o.net_cost_res
            self.principal_invested_res += o.principal_invested_res
            self.amount_invested_res += o.amount_invested_res

            if o.last_notes is not None:
                self.last_notes = o.last_notes

        # elif self.type == ReportItem.TYPE_SUMMARY or self.type == ReportItem.TYPE_INVESTED_SUMMARY:
        elif self.type == ReportItem.TYPE_SUMMARY:
            self.market_value_res += o.market_value_res
            # self.total_real_res += o.total_real_res
            # self.total_unreal_res += o.total_unreal_res

        elif self.type == ReportItem.TYPE_MISMATCH:
            self.mismatch += o.mismatch

    # def add_pass2(self, trn):
    #     if not trn.is_cloned and self.type == ReportItem.TYPE_INSTRUMENT:
    #         self.ytm_at_cost += trn.weighted_ytm
    #         self.time_invested_days += trn.weighted_time_invested_days
    #         # self.time_invested += trn.weighted_time_invested

    # def add_pos(self, o):
    #     if self.type == ReportItem.TYPE_CURRENCY:
    #         self.pos_size += o.pos_size
    #
    #     elif self.type == ReportItem.TYPE_INSTRUMENT:
    #         self.pos_size += o.pos_size

    def close(self):
        # if self.type == ReportItem.TYPE_CURRENCY or self.type == ReportItem.TYPE_INVESTED_CURRENCY:
        if self.type == ReportItem.TYPE_CURRENCY:
            self.market_value_res = self.pos_size * self.ccy_cur_fx

        elif self.type == ReportItem.TYPE_INSTRUMENT:
            if self.instr:
                self.instr_principal_res = self.pos_size * self.instr.price_multiplier * self.instr_price_cur_principal_price * self.instr_pricing_ccy_cur_fx
                self.instr_accrued_res = self.pos_size * self.instr.accrued_multiplier * self.instr_price_cur_accrued_price * self.instr_pricing_ccy_cur_fx

                _l.debug('> instr_accrual: instr=%s', self.instr.id)
                self.instr_accrual = self.instr.find_accrual(self.report.report_date)
                _l.debug('< instr_accrual: %s', self.instr_accrual)
                if self.instr_accrual:
                    _l.debug('> instr_accrual_accrued_price: instr=%s', self.instr.id)
                    self.instr_accrual_accrued_price = self.instr.get_accrued_price(self.report.report_date,
                                                                                    accrual=self.instr_accrual)
                    _l.debug('< instr_accrual_accrued_price: %s', self.instr_accrual_accrued_price)
            else:
                self.instr_principal_res = 0.0
                self.instr_accrued_res = 0.0

                self.instr_accrual = None
                self.instr_accrual_accrued_price = 0.0

            self.exposure_res = self.instr_principal_res + self.instr_accrued_res

            self.market_value_res = self.instr_principal_res + self.instr_accrued_res

            # self.total_unreal_res = self.market_value_res + self.cost_res

            # full ----------------------------------------------------
            self.principal_res += self.instr_principal_res
            self.carry_res += self.instr_accrued_res

            # full / closed ----------------------------------------------------
            pass

            # full / opened ----------------------------------------------------
            self.principal_opened_res += self.instr_principal_res
            self.carry_opened_res += self.instr_accrued_res

            # fx ----------------------------------------------------
            pass

            # fx / closed ----------------------------------------------------
            pass

            # fx / opened ----------------------------------------------------
            pass

            # fixed ----------------------------------------------------
            self.principal_fixed_res += self.instr_principal_res
            self.carry_fixed_res += self.instr_accrued_res

            # fixed / closed ----------------------------------------------------
            pass

            # fixed / opened ----------------------------------------------------
            self.principal_fixed_opened_res += self.instr_principal_res
            self.carry_fixed_opened_res += self.instr_accrued_res

            try:
                self.pos_return_res = (self.principal_opened_res + self.carry_opened_res) / \
                                      self.principal_invested_res / self.instr_pricing_ccy_cur_fx
            except ArithmeticError:
                self.pos_return_res = 0
            try:
                self.net_pos_return_res = (
                                                  self.principal_opened_res + self.carry_opened_res + self.overheads_opened_res) / self.principal_invested_res
            except ArithmeticError:
                self.net_pos_return_res = 0.0


            # def get_future_accrual_payments(self, d0,v0):
            #     //Если есть в кэше, взять оттуда
            #     //if hasattr(self, '_instr_ytm_data'):
            #         //    return self._instr_ytm_data
            #
            #     instr = self.instr
            #
            #     // Если нету maturity_date или maturity_price вернуть пустой список
            #     if instr.maturity_date is None or instr.maturity_date == date.max:
            #         return []
            #     if instr.maturity_price is None or isnan(instr.maturity_price) or isclose(instr.maturity_price, 0.0):
            #         return []
            #
            #     // Эту функцию я опишу в пункте 10
            #     //d0, v0 = self.get_instr_ytm_data_d0_v0() - d0 , v0 уже переданы как аргументы
            #
            #     // d0 - это accounting_date
            #     // v0 - это -(trade_price  price_multiplier  factor)
            #
            #     data = [(d0, v0)]
            #
            #     // Эту функцию я опишу в пункте 12
            # for cpn_date, cpn_val in instr.get_future_coupons(begin_date=d0, with_maturity=False):
            #     try:
            #         // Эту функцию я опишу в пункте 11
            #         factor = instr.get_factor(cpn_date)
            #         k = instr.accrued_multiplier  factor \
            #             (self.instr_accrued_ccy_cur_fx / self.instr_pricing_ccy_cur_fx)
            #     except ArithmeticError:
            #         k = 0
            #     data.append((cpn_date, cpn_val * k))
            #
            # prev_factor = None
            # for factor in instr.factor_schedules.all():
            #     if factor.effective_date < d0 or factor.effective_date > instr.maturity_date:
            #         prev_factor = factor
            #         continue
            #
            #     prev_factor_value = prev_factor.factor_value if prev_factor else 1.0
            #     factor_value = factor.factor_value
            #
            #     k = (prev_factor_value - factor_value) * instr.price_multiplier
            #     data.append((factor.effective_date, instr.maturity_price * k))
            #
            #     prev_factor = factor
            #
            # factor = instr.get_factor(instr.maturity_date)
            # k = instr.price_multiplier * factor
            # data.append((instr.maturity_date, instr.maturity_price * k))
            #
            # data.sort()
            # //self._instr_ytm_data = data  -не уверен зачем это
            #
            #
            # return data

            if self.instr:
                # YTM/Duration - берем price из price history на дату репорта.
                # Для записка итеративного алгоритма, для x0 из accrued schedule
                # берем на текущую дату - (accrued_size * accrued_multiplier)/(price * price_multiplier).

                v0 = -(self.instr_price_cur_principal_price * self.instr.price_multiplier * self.instr.get_factor(self.report.report_date) + self.instr_price_cur_accrued_price * self.instr.accrued_multiplier * self.instr.get_factor(self.report.report_date) * (self.instr_accrued_ccy_cur_fx / self.instr_pricing_ccy_cur_fx))

                try:
                    future_accrual_payments = self.instr.get_future_accrual_payments(
                        d0=self.report.report_date,
                        v0=v0
                    )
                except (ValueError, TypeError):
                    future_accrual_payments = False

                self.ytm = f_xirr(future_accrual_payments)

                self.modified_duration = f_duration(future_accrual_payments, ytm=self.ytm)

            self.time_invested = self.time_invested_days / 365.0

            if self.time_invested_days < 1.0 or isclose(self.time_invested_days, 1.0):
                # T - report date
                #  = (Current Price - Gross Cost Price) / Gross Cost Price, if Time Invested in days= 1 day
                # self.pricing()
                try:
                    self.daily_price_change = (
                                                      self.instr_price_cur_principal_price - self.gross_cost_loc) / self.gross_cost_loc
                except ArithmeticError:
                    self.daily_price_change = 0.0
            else:
                #  = (Current Price at T -  Price from Price History at T-1) / (Price from Price History at T-1) , if Time Invested > 1 day
                price_yest = self.pricing_provider[self.instr, self.report.report_date - timedelta(days=1)]
                try:
                    self.daily_price_change = (
                                                      self.instr_price_cur_principal_price - price_yest.principal_price) / price_yest.principal_price
                except ArithmeticError:
                    self.daily_price_change = 0.0

            if self.time_invested_days <= self.report.report_date.day or isclose(self.time_invested_days,
                                                                                 self.report.report_date.day):
                # T - report date
                #  = (Current Price - Gross Cost Price) / Gross Cost Price, if Time Invested in days <= Day(Report Date)
                try:
                    self.mtd_price_change = (
                                                    self.instr_price_cur_principal_price - self.gross_cost_loc) / self.gross_cost_loc
                except ArithmeticError:
                    self.mtd_price_change = 0.0
            else:
                #  = (Current Price -  Price from Price History at end_of_previous_month (Report Date)) / (Price from Price History at end_of_previous_month (Report Date)) , if Time Invested > Day(Report Date)
                price_eom = self.pricing_provider[
                    self.instr, self.report.report_date - timedelta(days=self.report.report_date.day)]
                try:
                    self.mtd_price_change = (
                                                    self.instr_price_cur_principal_price - price_eom.principal_price) / price_eom.principal_price
                except ArithmeticError:
                    self.mtd_price_change = 0.0

        elif self.type == ReportItem.TYPE_MISMATCH:
            # self.market_value_res = self.pos_size * self.ccy_cur_fx
            #
            # self.is_empty = isclose(self.pos_size, 0.0)
            pass

        self.total_res = self.principal_res + self.carry_res + self.overheads_res
        self.total_closed_res = self.principal_closed_res + self.carry_closed_res + self.overheads_closed_res
        self.total_opened_res = self.principal_opened_res + self.carry_opened_res + self.overheads_opened_res
        self.total_fx_res = self.principal_fx_res + self.carry_fx_res + self.overheads_fx_res
        self.total_fx_closed_res = self.principal_fx_closed_res + self.carry_fx_closed_res + self.overheads_fx_closed_res
        self.total_fx_opened_res = self.principal_fx_opened_res + self.carry_fx_opened_res + self.overheads_fx_opened_res
        self.total_fixed_res = self.principal_fixed_res + self.carry_fixed_res + self.overheads_fixed_res
        self.total_fixed_closed_res = self.principal_fixed_closed_res + self.carry_fixed_closed_res + self.overheads_fixed_closed_res
        self.total_fixed_opened_res = self.principal_fixed_opened_res + self.carry_fixed_opened_res + self.overheads_fixed_opened_res

        # values in pricing ccy ---

        try:
            res_to_loc_fx = 1.0 / self.pricing_ccy_cur_fx
        except ArithmeticError:
            res_to_loc_fx = 0.0

        self.market_value_loc = self.market_value_res * res_to_loc_fx
        self.exposure_loc = self.exposure_res * res_to_loc_fx
        self.gross_cost_loc = self.gross_cost_res * res_to_loc_fx
        self.net_cost_loc = self.net_cost_res * res_to_loc_fx
        self.principal_invested_loc = self.principal_invested_res * res_to_loc_fx
        self.amount_invested_loc = self.amount_invested_res * res_to_loc_fx
        self.pos_return_loc = self.pos_return_res * res_to_loc_fx
        self.net_pos_return_loc = self.net_pos_return_res * res_to_loc_fx

        # p & l

        self.principal_loc = self.principal_res * res_to_loc_fx
        self.carry_loc = self.carry_res * res_to_loc_fx
        self.overheads_loc = self.overheads_res * res_to_loc_fx
        self.total_loc = self.total_res * res_to_loc_fx

        self.principal_closed_loc = self.principal_closed_res * res_to_loc_fx
        self.carry_closed_loc = self.carry_closed_res * res_to_loc_fx
        self.overheads_closed_loc = self.overheads_closed_res * res_to_loc_fx
        self.total_closed_loc = self.total_closed_res * res_to_loc_fx

        self.principal_opened_loc = self.principal_opened_res * res_to_loc_fx
        self.carry_opened_loc = self.carry_opened_res * res_to_loc_fx
        self.overheads_opened_loc = self.overheads_opened_res * res_to_loc_fx
        self.total_opened_loc = self.total_opened_res * res_to_loc_fx

        self.principal_fx_loc = self.principal_fx_res * res_to_loc_fx
        self.carry_fx_loc = self.carry_fx_res * res_to_loc_fx
        self.overheads_fx_loc = self.overheads_fx_res * res_to_loc_fx
        self.total_fx_loc = self.total_fx_res * res_to_loc_fx

        self.principal_fx_closed_loc = self.principal_fx_closed_res * res_to_loc_fx
        self.carry_fx_closed_loc = self.carry_fx_closed_res * res_to_loc_fx
        self.overheads_fx_closed_loc = self.overheads_fx_closed_res * res_to_loc_fx
        self.total_fx_closed_loc = self.total_fx_closed_res * res_to_loc_fx

        self.principal_fx_opened_loc = self.principal_fx_opened_res * res_to_loc_fx
        self.carry_fx_opened_loc = self.carry_fx_opened_res * res_to_loc_fx
        self.overheads_fx_opened_loc = self.overheads_fx_opened_res * res_to_loc_fx
        self.total_fx_opened_loc = self.total_fx_opened_res * res_to_loc_fx

        self.principal_fixed_loc = self.principal_fixed_res * res_to_loc_fx
        self.carry_fixed_loc = self.carry_fixed_res * res_to_loc_fx
        self.overheads_fixed_loc = self.overheads_fixed_res * res_to_loc_fx
        self.total_fixed_loc = self.total_fixed_res * res_to_loc_fx

        self.principal_fixed_closed_loc = self.principal_fixed_closed_res * res_to_loc_fx
        self.carry_fixed_closed_loc = self.carry_fixed_closed_res * res_to_loc_fx
        self.overheads_fixed_closed_loc = self.overheads_fixed_closed_res * res_to_loc_fx
        self.total_fixed_closed_loc = self.total_fixed_closed_res * res_to_loc_fx

        self.principal_fixed_opened_loc = self.principal_fixed_opened_res * res_to_loc_fx
        self.carry_fixed_opened_loc = self.carry_fixed_opened_res * res_to_loc_fx
        self.overheads_fixed_opened_loc = self.overheads_fixed_opened_res * res_to_loc_fx
        self.total_fixed_opened_loc = self.total_fixed_opened_res * res_to_loc_fx

        # ----

        if self.type == ReportItem.TYPE_CURRENCY:
            self.is_empty = isclose(self.pos_size, 0.0)

        elif self.type == ReportItem.TYPE_INSTRUMENT:
            self.is_empty = isclose(self.pos_size, 0.0) and \
                            isclose(self.total_res, 0.0) and \
                            isclose(self.total_closed_res, 0.0) and \
                            isclose(self.total_opened_res, 0.0)

    # def close_pass2(self):
    #     if self.type == ReportItem.TYPE_INSTRUMENT:
    #         self.time_invested = self.time_invested_days / 365.0
    #
    #         if self.time_invested_days < 1.0 or isclose(self.time_invested_days, 1.0):
    #             # T - report date
    #             #  = (Current Price - Gross Cost Price) / Gross Cost Price, if Time Invested in days= 1 day
    #             # self.pricing()
    #             try:
    #                 self.daily_price_change = (
    #                                               self.instr_price_cur_principal_price - self.gross_cost_loc) / self.gross_cost_loc
    #             except ArithmeticError:
    #                 self.daily_price_change = 0.0
    #         else:
    #             #  = (Current Price at T -  Price from Price History at T-1) / (Price from Price History at T-1) , if Time Invested > 1 day
    #             price_yest = self.pricing_provider[self.instr, self.report.report_date - timedelta(days=1)]
    #             try:
    #                 self.daily_price_change = (
    #                                               self.instr_price_cur_principal_price - price_yest.principal_price) / price_yest.principal_price
    #             except ArithmeticError:
    #                 self.daily_price_change = 0.0
    #
    #         if self.time_invested_days <= self.report.report_date.day or isclose(self.time_invested_days,
    #                                                                              self.report.report_date.day):
    #             # T - report date
    #             #  = (Current Price - Gross Cost Price) / Gross Cost Price, if Time Invested in days <= Day(Report Date)
    #             try:
    #                 self.mtd_price_change = (
    #                                             self.instr_price_cur_principal_price - self.gross_cost_loc) / self.gross_cost_loc
    #             except ArithmeticError:
    #                 self.mtd_price_change = 0.0
    #         else:
    #             #  = (Current Price -  Price from Price History at end_of_previous_month (Report Date)) / (Price from Price History at end_of_previous_month (Report Date)) , if Time Invested > Day(Report Date)
    #             price_eom = self.pricing_provider[
    #                 self.instr, self.report.report_date - timedelta(days=self.report.report_date.day)]
    #             try:
    #                 self.mtd_price_change = (
    #                                             self.instr_price_cur_principal_price - price_eom.principal_price) / price_eom.principal_price
    #             except ArithmeticError:
    #                 self.mtd_price_change = 0.0

    def pl_sub_item(self, o):
        self.principal_res -= o.principal_res
        self.carry_res -= o.carry_res
        self.overheads_res -= o.overheads_res
        self.total_res -= o.total_res

        self.principal_closed_res -= o.principal_closed_res
        self.carry_closed_res -= o.carry_closed_res
        self.overheads_closed_res -= o.overheads_closed_res
        self.total_closed_res -= o.total_closed_res

        self.principal_opened_res -= o.principal_opened_res
        self.carry_opened_res -= o.carry_opened_res
        self.overheads_opened_res -= o.overheads_opened_res
        self.total_opened_res -= o.total_opened_res

        self.principal_fx_res -= o.principal_fx_res
        self.carry_fx_res -= o.carry_fx_res
        self.overheads_fx_res -= o.overheads_fx_res
        self.total_fx_res -= o.total_fx_res

        self.principal_fx_closed_res -= o.principal_fx_closed_res
        self.carry_fx_closed_res -= o.carry_fx_closed_res
        self.overheads_fx_closed_res -= o.overheads_fx_closed_res
        self.total_fx_closed_res -= o.total_fx_closed_res

        self.principal_fx_opened_res -= o.principal_fx_opened_res
        self.carry_fx_opened_res -= o.carry_fx_opened_res
        self.overheads_fx_opened_res -= o.overheads_fx_opened_res
        self.total_fx_opened_res -= o.total_fx_opened_res

        self.principal_fixed_res -= o.principal_fixed_res
        self.carry_fixed_res -= o.carry_fixed_res
        self.overheads_fixed_res -= o.overheads_fixed_res
        self.total_fixed_res -= o.total_fixed_res

        self.principal_fixed_closed_res -= o.principal_fixed_closed_res
        self.carry_fixed_closed_res -= o.carry_fixed_closed_res
        self.overheads_fixed_closed_res -= o.overheads_fixed_closed_res
        self.total_fixed_closed_res -= o.total_fixed_closed_res

        self.principal_fixed_opened_res -= o.principal_fixed_opened_res
        self.carry_fixed_opened_res -= o.carry_fixed_opened_res
        self.overheads_fixed_opened_res -= o.overheads_fixed_opened_res
        self.total_fixed_opened_res -= o.total_fixed_opened_res

    # ----------------------------------------------------
    @property
    def pk(self):
        return (
            self.type,
            getattr(self.prtfl, 'id', -1),
            getattr(self.acc, 'id', -1),
            getattr(self.instr, 'id', -1),
            getattr(self.ccy, 'id', -1),
            getattr(self.mismatch_prtfl, 'id', -1),
            getattr(self.mismatch_acc, 'id', -1),
        )

    @property
    def type_name(self):
        for i, n in ReportItem.TYPE_CHOICES:
            if i == self.type:
                return n
        return 'ERR'

    @property
    def type_code(self):
        if self.type == ReportItem.TYPE_UNKNOWN:
            return 'UNKNOWN'

        elif self.type == ReportItem.TYPE_INSTRUMENT:
            return 'INSTR'

        elif self.type == ReportItem.TYPE_CURRENCY:
            return 'CCY'

        elif self.type == ReportItem.TYPE_TRANSACTION_PL:
            return 'TRN_PL'

        elif self.type == ReportItem.TYPE_FX_TRADE:
            return 'FX_TRADE'

        elif self.type == ReportItem.TYPE_CASH_IN_OUT:
            return 'CASH_IN_OUT'

        elif self.type == ReportItem.TYPE_MISMATCH:
            return 'MISMATCH'

        elif self.type == ReportItem.TYPE_SUMMARY:
            return 'SUMMARY'

        # elif self.type == ReportItem.TYPE_INVESTED_CURRENCY:
        #     return 'INV_CCY'
        #
        # elif self.type == ReportItem.TYPE_INVESTED_SUMMARY:
        #     return 'INV_SUMMARY'

        return 'ERR'

    @property
    def subtype_name(self):
        for i, n in ReportItem.SUBTYPE_CHOICES:
            if i == self.subtype:
                return n
        return 'ERR'

    @property
    def subtype_code(self):
        if self.subtype == ReportItem.SUBTYPE_UNKNOWN:
            return 'UNKNOWN'

        elif self.subtype == ReportItem.SUBTYPE_TOTAL:
            return 'TOTAL'

        elif self.subtype == ReportItem.SUBTYPE_CLOSED:
            return 'CLOSED'

        elif self.subtype == ReportItem.SUBTYPE_OPENED:
            return 'OPENED'

        return 'ERR'

    @property
    def user_code(self):
        if self.type == ReportItem.TYPE_UNKNOWN:
            return '<UNKNOWN>'

        elif self.type == ReportItem.TYPE_INSTRUMENT:
            return getattr(self.instr, 'user_code', None)

        elif self.type == ReportItem.TYPE_CURRENCY:
            return getattr(self.ccy, 'user_code', None)

        elif self.type == ReportItem.TYPE_TRANSACTION_PL:
            return 'TRANSACTION_PL'

        elif self.type == ReportItem.TYPE_FX_TRADE:
            # return 'FX_TRADE'
            return '%s/%s' % (getattr(self.trn_ccy, 'user_code', None), getattr(self.ccy, 'user_code', None),)

        elif self.type == ReportItem.TYPE_CASH_IN_OUT:
            # return 'CASH_IN_OUT'
            return getattr(self.ccy, 'user_code', None)

        elif self.type == ReportItem.TYPE_MISMATCH:
            return getattr(self.ccy, 'user_code', None)

        elif self.type == ReportItem.TYPE_SUMMARY:
            return 'SUMMARY'

        return '<ERROR>'

    @property
    def short_name(self):
        if self.type == ReportItem.TYPE_UNKNOWN:
            return '<UNKNOWN>'

        elif self.type == ReportItem.TYPE_INSTRUMENT:
            return getattr(self.instr, 'short_name', None)

        elif self.type == ReportItem.TYPE_CURRENCY:
            return getattr(self.ccy, 'short_name', None)

        elif self.type == ReportItem.TYPE_TRANSACTION_PL:
            return ugettext('Transaction PL')

        elif self.type == ReportItem.TYPE_FX_TRADE:
            # return ugettext('FX-Trade')
            return ugettext('FX-Trades: %s/%s') % (getattr(self.trn_ccy, 'short_name', None),
                                                   getattr(self.ccy, 'short_name', None),)

        elif self.type == ReportItem.TYPE_CASH_IN_OUT:
            # return ugettext('Cash In/Out: %s/%s')
            return ugettext('Cash In/Out: %s') % getattr(self.ccy, 'short_name', None)

        elif self.type == ReportItem.TYPE_MISMATCH:
            return getattr(self.instr, 'short_name', None)

        elif self.type == ReportItem.TYPE_SUMMARY:
            return ugettext('Summary')

        return '<ERROR>'

    @property
    def name(self):
        if self.type == ReportItem.TYPE_UNKNOWN:
            return '<UNKNOWN>'

        elif self.type == ReportItem.TYPE_INSTRUMENT:
            return getattr(self.instr, 'name', None)

        elif self.type == ReportItem.TYPE_CURRENCY:
            return getattr(self.ccy, 'name', None)

        elif self.type == ReportItem.TYPE_TRANSACTION_PL:
            return ugettext('Transaction PL')

        elif self.type == ReportItem.TYPE_FX_TRADE:
            # return ugettext('FX-Trade')
            return ugettext('FX-Trades: %s/%s') % (
                getattr(self.trn_ccy, 'name', None), getattr(self.ccy, 'name', None),)

        elif self.type == ReportItem.TYPE_CASH_IN_OUT:
            # return ugettext('Cash In/Out: %s/%s')
            return ugettext('Cash In/Out: %s') % getattr(self.ccy, 'name', None)

        elif self.type == ReportItem.TYPE_MISMATCH:
            return getattr(self.instr, 'name', None)

        elif self.type == ReportItem.TYPE_SUMMARY:
            return ugettext('Summary')

        return '<ERROR>'

    @property
    def trn_cls(self):
        return getattr(self.trn, 'trn_cls', None)

    @property
    def detail_trn(self):
        if self.trn and self.acc and self.trn.is_show_details(self.acc):
            return self.trn
        return None

    def eval_custom_fields(self):
        res = []
        for cf in self.report.custom_fields:
            if cf.expr and self.report.member:
                try:
                    names = {
                        'item': self
                    }
                    value = formula.safe_eval(cf.expr, names=names, context=self.report.context)
                except formula.InvalidExpression:
                    value = ugettext('Invalid expression')
            else:
                value = None
            res.append({
                'custom_field': cf,
                'value': value
            })
        self.custom_fields = res

    def overwrite_pl_fields_by_subtype(self):
        if self.subtype == ReportItem.SUBTYPE_TOTAL:
            pass

        elif self.subtype == ReportItem.SUBTYPE_CLOSED:
            for sitem, ditem in self.pl_closed_fields:
                if ditem is None:
                    ditem = str(sitem).replace('closed_', '')
                val = getattr(self, sitem)
                setattr(self, ditem, val)

        elif self.subtype == ReportItem.SUBTYPE_OPENED:
            for sitem, ditem in self.pl_opened_fields:
                if ditem is None:
                    ditem = str(sitem).replace('opene_', '')
                val = getattr(self, sitem)
                setattr(self, ditem, val)

        for sitem, ditem in self.pl_closed_fields:
            setattr(self, sitem, float('nan'))

        for sitem, ditem in self.pl_opened_fields:
            setattr(self, sitem, float('nan'))


class Report(object):
    MODE_IGNORE = 0
    MODE_INDEPENDENT = 1
    MODE_INTERDEPENDENT = 2
    MODE_CHOICES = (
        (MODE_IGNORE, 'Ignore'),
        (MODE_INDEPENDENT, 'Independent'),
        (MODE_INTERDEPENDENT, 'Offsetting (Interdependent - 0/100, 100/0, 50/50)'),
    )

    def __init__(self,
                 id=None,
                 master_user=None,
                 member=None,
                 task_id=None,
                 task_status=None,
                 pl_first_date=None,
                 report_date=None,
                 report_currency=None,
                 pricing_policy=None,
                 cost_method=None,
                 portfolio_mode=MODE_INDEPENDENT,
                 account_mode=MODE_INDEPENDENT,
                 strategy1_mode=MODE_INDEPENDENT,
                 strategy2_mode=MODE_INDEPENDENT,
                 strategy3_mode=MODE_INDEPENDENT,
                 show_transaction_details=False,
                 approach_multiplier=0.5,
                 instruments=None,
                 portfolios=None,
                 accounts=None,
                 strategies1=None,
                 strategies2=None,
                 strategies3=None,
                 transaction_classes=None,
                 date_field=None,
                 custom_fields=None,
                 items=None):
        self.id = id
        self.task_id = task_id
        self.task_status = task_status

        self.master_user = master_user
        self.member = member
        self.context = {
            'master_user': self.master_user,
            'member': self.member,
        }
        self.pricing_policy = pricing_policy
        self.pl_first_date = pl_first_date
        self.report_date = report_date or (date_now() - timedelta(days=1))
        self.report_currency = report_currency or master_user.system_currency
        self.cost_method = cost_method or CostMethod.objects.get(pk=CostMethod.AVCO)

        self.portfolio_mode = portfolio_mode
        self.account_mode = account_mode
        self.strategy1_mode = strategy1_mode
        self.strategy2_mode = strategy2_mode
        self.strategy3_mode = strategy3_mode
        self.show_transaction_details = show_transaction_details
        self.approach_multiplier = approach_multiplier

        self.instruments = instruments or []
        self.portfolios = portfolios or []
        self.accounts = accounts or []
        self.strategies1 = strategies1 or []
        self.strategies2 = strategies2 or []
        self.strategies3 = strategies3 or []
        self.transaction_classes = transaction_classes or []
        self.date_field = date_field or 'transaction_date'

        self.custom_fields = custom_fields or []

        self.items = items or []
        self.transactions = []

    def __str__(self):
        return "%s for %s/%s @ %s" % (self.__class__.__name__, self.master_user, self.member, self.report_date)

    def close(self):
        for item in self.items:
            item.eval_custom_fields()

    @property
    def approach_begin_multiplier(self):
        return self.approach_multiplier

    @property
    def approach_end_multiplier(self):
        return 1.0 - self.approach_multiplier

    @property
    def system_ccy(self):
        return self.master_user.system_currency

    def is_system_ccy(self, ccy):
        return self.master_user.system_currency_id == ccy.id


class ReportBuilder(object):
    def __init__(self, instance=None, queryset=None, transactions=None, pricing_provider=None, fx_rate_provider=None):
        self.instance = instance
        self._queryset = queryset
        self._transactions = transactions
        self._pricing_provider = pricing_provider
        self._fx_rate_provider = fx_rate_provider

        self.avco_rolling_positions = Counter()
        self.fifo_rolling_positions = Counter()

        self._transactions = []
        self._mismatch_items = []
        self._items = []
        self._summaries = []

    def build(self, full=True):
        # _l.debug('build report: %s', self.instance)

        self._load_transactions()
        self._transaction_pricing()
        self._transaction_multipliers()
        self._transaction_calc()
        self._clone_transactions_if_need()
        self.instance.transactions = self._transactions
        self._generate_items()
        self._aggregate_items()
        # self._calc_pass2()
        self._aggregate_summary()
        self._detect_mismatches()
        self.instance.items = self._items + self._mismatch_items + self._summaries

        if self.instance.pl_first_date and self.instance.pl_first_date != date.min:
            self._build_on_pl_first_date()

        if full:
            self._refresh_with_perms()

        _l.debug('finalize report')
        self.instance.close()

        _l.debug('done')
        return self.instance

    def build_position_only(self):
        _l.debug('build position only report: %s', self.instance)

        self._load_transactions()
        self.instance.transactions = self._transactions
        if not self._transactions:
            return

        self._generate_items()

        sorted_items = sorted(self._items, key=lambda item: self._item_group_key(item))

        _l.debug('aggregate items')
        res_items = []
        for k, g in groupby(sorted_items, key=lambda item: self._item_group_key(item)):
            res_item = None

            for item in g:
                if item.type in [ReportItem.TYPE_INSTRUMENT, ReportItem.TYPE_CURRENCY, ReportItem.TYPE_TRANSACTION_PL,
                                 ReportItem.TYPE_FX_TRADE, ReportItem.TYPE_CASH_IN_OUT, ]:
                    if res_item is None:
                        res_item = ReportItem.from_item(item)
                    res_item.pos_size += item.trn.pos_size

            if res_item:
                res_items.append(res_item)

        self.instance.items = res_items

        _l.debug('done')
        return self.instance

    def build_pl(self, full=True):
        self.build(full=full)

        items = []
        for oitem in self.instance.items:
            if oitem.type in [ReportItem.TYPE_INSTRUMENT]:
                nitem = oitem.clone()
                nitem.subtype = ReportItem.SUBTYPE_TOTAL
                nitem.overwrite_pl_fields_by_subtype()
                items.append(nitem)

                nitem = oitem.clone()
                nitem.subtype = ReportItem.SUBTYPE_CLOSED
                nitem.overwrite_pl_fields_by_subtype()
                items.append(nitem)

                nitem = oitem.clone()
                nitem.subtype = ReportItem.SUBTYPE_OPENED
                nitem.overwrite_pl_fields_by_subtype()
                items.append(nitem)

            else:
                items.append(oitem)

        self.instance.items = items
        return self.instance

    @cached_property
    def _trn_cls_sell(self):
        return TransactionClass.objects.get(pk=TransactionClass.SELL)

    @cached_property
    def _trn_cls_buy(self):
        return TransactionClass.objects.get(pk=TransactionClass.BUY)

    @cached_property
    def _trn_cls_fx_trade(self):
        return TransactionClass.objects.get(pk=TransactionClass.FX_TRADE)

    def _trn_qs(self):
        if self._queryset is None:
            queryset = Transaction.objects.all()
        else:
            queryset = self._queryset

        # permissions and attributes refreshed after build report
        queryset = queryset.prefetch_related(
            'master_user',
            # 'complex_transaction',
            # 'complex_transaction__transaction_type',
            'transaction_class',
            'instrument',
            'instrument__instrument_type',
            'instrument__instrument_type__instrument_class',
            'instrument__pricing_currency',
            'instrument__accrued_currency',
            'instrument__accrual_calculation_schedules',
            'instrument__accrual_calculation_schedules__accrual_calculation_model',
            'instrument__accrual_calculation_schedules__periodicity',
            'transaction_currency',
            'settlement_currency',
            'portfolio',
            'account_cash',
            # 'account_cash__type',
            'account_position',
            # 'account_position__type',
            'account_interim',
            # 'account_interim__type',
            'strategy1_position',
            # 'strategy1_position__subgroup',
            # 'strategy1_position__subgroup__group',
            'strategy1_cash',
            # 'strategy1_cash__subgroup',
            # 'strategy1_cash__subgroup__group',
            'strategy2_position',
            # 'strategy2_position__subgroup',
            # 'strategy2_position__subgroup__group',
            'strategy2_cash',
            # 'strategy2_cash__subgroup',
            # 'strategy2_cash__subgroup__group',
            'strategy3_position',
            # 'strategy3_position__subgroup',
            # 'strategy3_position__subgroup__group',
            'strategy3_cash',
            # 'strategy3_cash__subgroup',
            # 'strategy3_cash__subgroup__group',
            # 'responsible',
            # 'responsible__group',
            # 'counterparty',
            # 'counterparty__group',
            'linked_instrument',
            # 'linked_instrument__instrument_type',
            # 'linked_instrument__instrument_type__instrument_class',
            'linked_instrument__pricing_currency',
            'linked_instrument__accrued_currency',
            # 'linked_instrument__accrual_calculation_schedules',
            # 'linked_instrument__accrual_calculation_schedules__accrual_calculation_model',
            # 'linked_instrument__accrual_calculation_schedules__periodicity',
            'allocation_balance',
            # 'allocation_balance__instrument_type',
            # 'allocation_balance__instrument_type__instrument_class',
            # 'allocation_balance__pricing_currency',
            # 'allocation_balance__accrued_currency',
            # 'allocation_balance__accrual_calculation_schedules',
            # 'allocation_balance__accrual_calculation_schedules__accrual_calculation_model',
            # 'allocation_balance__accrual_calculation_schedules__periodicity',
            'allocation_pl',
            # 'allocation_pl__instrument_type',
            # 'allocation_pl__instrument_type__instrument_class',
            # 'allocation_pl__pricing_currency',
            # 'allocation_pl__accrued_currency',
            # 'allocation_pl__accrual_calculation_schedules',
            # 'allocation_pl__accrual_calculation_schedules__accrual_calculation_model',
            # 'allocation_pl__accrual_calculation_schedules__periodicity',

            # get_attributes_prefetch(path='portfolio__attributes'),
            # get_attributes_prefetch(path='instrument__attributes'),
            # get_attributes_prefetch(path='instrument__pricing_currency__attributes'),
            # get_attributes_prefetch(path='instrument__accrued_currency__attributes'),
            # get_attributes_prefetch(path='account_cash__attributes'),
            # get_attributes_prefetch(path='account_position__attributes'),
            # get_attributes_prefetch(path='account_interim__attributes'),
            # get_attributes_prefetch(path='transaction_currency__attributes'),
            # get_attributes_prefetch(path='settlement_currency__attributes'),
            # get_attributes_prefetch(path='linked_instrument__attributes'),
            # get_attributes_prefetch(path='linked_instrument__pricing_currency__attributes'),
            # get_attributes_prefetch(path='linked_instrument__accrued_currency__attributes'),
            # get_attributes_prefetch(path='allocation_balance__attributes'),
            # get_attributes_prefetch(path='allocation_balance__pricing_currency__attributes'),
            # get_attributes_prefetch(path='allocation_balance__accrued_currency__attributes'),
            # get_attributes_prefetch(path='allocation_pl__attributes'),
            # get_attributes_prefetch(path='allocation_pl__pricing_currency__attributes'),
            # get_attributes_prefetch(path='allocation_pl__accrued_currency__attributes'),
            # *get_permissions_prefetch_lookups(
            #     ('portfolio', Portfolio),
            #     ('instrument', Instrument),
            #     ('instrument__instrument_type', InstrumentType),
            #     ('account_cash', Account),
            #     ('account_cash__type', AccountType),
            #     ('account_position', Account),
            #     ('account_position__type', AccountType),
            #     ('account_interim', Account),
            #     ('account_interim__type', AccountType),
            #     ('strategy1_position', Strategy1),
            #     ('strategy1_position__subgroup', Strategy1Subgroup),
            #     ('strategy1_position__subgroup__group', Strategy1Group),
            #     ('strategy1_cash', Strategy1),
            #     ('strategy1_cash__subgroup', Strategy1Subgroup),
            #     ('strategy1_cash__subgroup__group', Strategy1Group),
            #     ('strategy2_position', Strategy2),
            #     ('strategy2_position__subgroup', Strategy2Subgroup),
            #     ('strategy2_position__subgroup__group', Strategy2Group),
            #     ('strategy2_cash', Strategy2),
            #     ('strategy2_cash__subgroup', Strategy2Subgroup),
            #     ('strategy2_cash__subgroup__group', Strategy2Group),
            #     ('strategy3_position', Strategy3),
            #     ('strategy3_position__subgroup', Strategy3Subgroup),
            #     ('strategy3_position__subgroup__group', Strategy3Group),
            #     ('strategy3_cash', Strategy3),
            #     ('strategy3_cash__subgroup', Strategy3Subgroup),
            #     ('strategy3_cash__subgroup__group', Strategy3Group),
            #     ('responsible', Responsible),
            #     ('responsible__group', ResponsibleGroup),
            #     ('counterparty', Counterparty),
            #     ('counterparty__group', CounterpartyGroup),
            #     ('linked_instrument', Instrument),
            #     ('linked_instrument__instrument_type', InstrumentType),
            #     ('allocation_balance', Instrument),
            #     ('allocation_balance__instrument_type', InstrumentType),
            #     ('allocation_pl', Instrument),
            #     ('allocation_pl__instrument_type', InstrumentType),
            # )
        )

        a_filters = [
            Q(complex_transaction__isnull=True) | Q(complex_transaction__status=ComplexTransaction.PRODUCTION,
                                                    complex_transaction__is_deleted=False)
        ]

        kw_filters = {
            'master_user': self.instance.master_user,
            'is_deleted': False,
            '%s__lt' % self.instance.date_field: self.instance.report_date
        }

        if self.instance.instruments:
            kw_filters['instrument__in'] = self.instance.instruments

        if self.instance.portfolios:
            kw_filters['portfolio__in'] = self.instance.portfolios

        if self.instance.accounts:
            kw_filters['account_position__in'] = self.instance.accounts
            kw_filters['account_cash__in'] = self.instance.accounts
            kw_filters['account_interim__in'] = self.instance.accounts

        if self.instance.strategies1:
            kw_filters['strategy1_position__in'] = self.instance.strategies1
            kw_filters['strategy1_cash__in'] = self.instance.strategies1

        if self.instance.strategies2:
            kw_filters['strategy2_position__in'] = self.instance.strategies2
            kw_filters['strategy2_cash__in'] = self.instance.strategies2

        if self.instance.strategies3:
            kw_filters['strategy3_position__in'] = self.instance.strategies3
            kw_filters['strategy3_cash__in'] = self.instance.strategies3

        if self.instance.transaction_classes:
            kw_filters['transaction_class__in'] = self.instance.transaction_classes

        queryset = queryset.filter(*a_filters, **kw_filters)

        queryset = queryset.order_by(self.instance.date_field, 'transaction_code', 'id')

        return queryset

    def sort_transactions(self):
        def _trn_key(t):

            d = None
            if self.instance.date_field == 'accounting_date':
                d = t.acc_date
            elif self.instance.date_field == 'cash_date':
                d = t.cash_date
            else:
                if t.trn_date is None:
                    if t.acc_date and t.cash_date:
                        d = min(t.acc_date, t.cash_date)
                else:
                    d = t.trn_date

            return (
                d if d is not None else date.min,
                t.trn_code if t.trn_code is not None else sys.maxsize,
                t.pk if t.pk is not None else sys.maxsize,
            )

        self._transactions = sorted(self._transactions, key=_trn_key)
        return self._transactions

    @property
    def pricing_provider(self):
        if self._pricing_provider is None:
            if self.instance.pricing_policy is None:
                p = FakeInstrumentPricingProvider(self.instance.master_user, None, self.instance.report_date)
            else:
                p = InstrumentPricingProvider(self.instance.master_user, self.instance.pricing_policy,
                                              self.instance.report_date)
                p.fill_using_transactions(self._trn_qs(), lazy=False)
            self._pricing_provider = p
        return self._pricing_provider

    @property
    def fx_rate_provider(self):
        if self._fx_rate_provider is None:
            if self.instance.pricing_policy is None:
                p = FakeCurrencyFxRateProvider(self.instance.master_user, None, self.instance.report_date)
            else:
                p = CurrencyFxRateProvider(self.instance.master_user, self.instance.pricing_policy,
                                           self.instance.report_date)
                p.fill_using_transactions(self._trn_qs(), currencies=[self.instance.report_currency], lazy=False)
            self._fx_rate_provider = p
        return self._fx_rate_provider

    def _load_transactions(self):
        _l.debug('transactions - load')

        self._transactions = []

        trn_qs = self._trn_qs()
        if not trn_qs.exists():
            return

        for t in trn_qs:
            overrides = {}

            if self.instance.portfolio_mode == Report.MODE_IGNORE:
                overrides['portfolio'] = self.instance.master_user.portfolio

            if self.instance.account_mode == Report.MODE_IGNORE:
                overrides['account_position'] = self.instance.master_user.account
                overrides['account_cash'] = self.instance.master_user.account
                overrides['account_interim'] = self.instance.master_user.account

            if self.instance.strategy1_mode == Report.MODE_IGNORE:
                overrides['strategy1_position'] = self.instance.master_user.strategy1
                overrides['strategy1_cash'] = self.instance.master_user.strategy1

            if self.instance.strategy2_mode == Report.MODE_IGNORE:
                overrides['strategy2_position'] = self.instance.master_user.strategy2
                overrides['strategy2_cash'] = self.instance.master_user.strategy2

            if self.instance.strategy3_mode == Report.MODE_IGNORE:
                overrides['strategy3_position'] = self.instance.master_user.strategy3
                overrides['strategy3_cash'] = self.instance.master_user.strategy3

            trn = VirtualTransaction(
                report=self.instance,
                pricing_provider=self.pricing_provider,
                fx_rate_provider=self.fx_rate_provider,
                trn=t,
                overrides=overrides
            )
            # trn.key = self._get_trn_group_key(trn)
            self._transactions.append(trn)

        # _l.debug('transactions - len=%s', len(self._transactions))

    def _transaction_pricing(self):
        # _l.debug('transactions - add pricing')

        for trn in self._transactions:
            trn.pricing()

    def _transaction_calc(self):
        # _l.debug('transactions - calculate')

        for trn in self._transactions:
            trn.calc()

    def _clone_transactions_if_need(self):
        # _l.debug('transactions - clone if need')

        res = []
        for trn in self._transactions:
            res.append(trn)

            if trn.trn_cls.id in [TransactionClass.BUY, TransactionClass.SELL]:
                if trn.closed_by:
                    for closed_by, delta in trn.closed_by:
                        closed_by2, trn2 = VirtualTransaction.approach_clone(closed_by, trn, delta)
                        res.append(trn2)
                        res.append(closed_by2)

            elif trn.trn_cls.id == TransactionClass.FX_TRADE:
                trn.is_hidden = True

                trn1, trn2 = trn.fx_trade_clone()
                res.append(trn1)
                res.append(trn2)

            elif trn.trn_cls.id == TransactionClass.TRANSFER:
                trn.is_hidden = True
                # split TRANSFER to sell/buy or buy/sell
                if trn.pos_size >= 0:
                    trn1, trn2 = trn.transfer_clone(self._trn_cls_sell, self._trn_cls_buy,
                                                    t1_pos_sign=1.0, t1_cash_sign=-1.0)
                else:
                    trn1, trn2 = trn.transfer_clone(self._trn_cls_buy, self._trn_cls_sell,
                                                    t1_pos_sign=-1.0, t1_cash_sign=1.0)
                res.append(trn1)
                res.append(trn2)

            elif trn.trn_cls.id == TransactionClass.FX_TRANSFER:
                trn.is_hidden = True

                trn1, trn2 = trn.transfer_clone(self._trn_cls_fx_trade, self._trn_cls_fx_trade,
                                                t1_pos_sign=1.0, t1_cash_sign=-1.0)
                # res.append(trn1)
                # res.append(trn2)

                trn11, trn12 = trn1.fx_trade_clone()
                res.append(trn11)
                res.append(trn12)

                trn21, trn22 = trn2.fx_trade_clone()
                res.append(trn21)
                res.append(trn22)

        self._transactions = res
        _l.debug('transactions - len=%s', len(self._transactions))

    def _transaction_multipliers(self):
        _l.debug('transactions - calculate multipliers')

        self._calc_avco_multipliers()
        self._calc_fifo_multipliers()

        balances = Counter()
        for t in self._transactions:
            if t.trn_cls.id in [TransactionClass.TRANSACTION_PL, TransactionClass.FX_TRADE]:
                self.multiplier = 1.0

            elif t.trn_cls.id in [TransactionClass.BUY, TransactionClass.SELL]:
                if t.instr and t.instr.instrument_type.instrument_class_id == InstrumentClass.CONTRACT_FOR_DIFFERENCE:
                    t.multiplier = t.fifo_multiplier
                    t.closed_by = t.fifo_closed_by
                    t.rolling_pos_size = t.fifo_rolling_pos_size

                elif self.instance.cost_method.id == CostMethod.AVCO:
                    t.multiplier = t.avco_multiplier
                    t.closed_by = t.avco_closed_by
                    t.rolling_pos_size = t.avco_rolling_pos_size

                elif self.instance.cost_method.id == CostMethod.FIFO:
                    t.multiplier = t.fifo_multiplier
                    t.closed_by = t.fifo_closed_by
                    t.rolling_pos_size = t.fifo_rolling_pos_size

                t.remaining_pos_size = t.pos_size * (1 - t.multiplier)

                t_key = self._get_trn_group_key(t)
                balances[t_key] += t.remaining_pos_size

        for t in self._transactions:
            if t.trn_cls.id in [TransactionClass.BUY, TransactionClass.SELL]:
                t_key = self._get_trn_group_key(t)
                t.balance_pos_size = balances[t_key]
                try:
                    t.remaining_pos_size_percent = t.remaining_pos_size / t.balance_pos_size
                except ArithmeticError:
                    t.remaining_pos_size_percent = 0.0

        sum_remaining_positions = Counter()
        for t in self._transactions:
            if t.trn_cls.id in [TransactionClass.BUY, TransactionClass.SELL]:
                t_key = self._get_trn_group_key(t)
                sum_remaining_positions[t_key] += t.remaining_pos_size

            elif t.trn_cls.id == TransactionClass.INSTRUMENT_PL:
                t_key = self._get_trn_group_key(t)
                t.balance_pos_size = balances[t_key]
                remaining_pos_size = sum_remaining_positions[t_key]
                try:
                    t.multiplier = abs(remaining_pos_size / t.balance_pos_size)
                except ArithmeticError:
                    t.multiplier = 0.0

    def _calc_avco_multipliers(self):
        # _l.debug('transactions - calculate multipliers - avco')

        items = defaultdict(list)

        def _set_mul(t0, avco_multiplier):
            delta = avco_multiplier - t0.avco_multiplier
            t0.avco_multiplier = avco_multiplier
            return delta

        def _close_by(closed, cur, delta):
            # closed.avco_closed_by.append(VirtualTransactionClosedByData(cur, delta))
            closed.avco_closed_by.append((cur, delta))

        for t in self._transactions:
            t_key = self._get_trn_group_key(t)

            if t.trn_cls.id == TransactionClass.INSTRUMENT_PL:
                t.avco_rolling_pos_size = self.avco_rolling_positions[t_key]
                continue

            if t.trn_cls.id not in [TransactionClass.BUY, TransactionClass.SELL]:
                continue

            t.avco_multiplier = 0.0
            t.avco_closed_by = []
            t.avco_rolling_pos_size = 0.0

            rolling_pos = self.avco_rolling_positions[t_key]

            if isclose(rolling_pos, 0.0):
                k = -1
            else:
                k = - t.pos_size / rolling_pos

            if k > 1.0:
                if t_key in items:
                    for t0 in items[t_key]:
                        delta = _set_mul(t0, 1.0)
                        _close_by(t0, t, delta)
                    del items[t_key]
                items[t_key].append(t)
                _set_mul(t, 1.0 / k)
                rolling_pos = t.pos_size * (1.0 - t.avco_multiplier)

            elif isclose(k, 1.0):
                if t_key in items:
                    for t0 in items[t_key]:
                        delta = _set_mul(t0, 1.0)
                        _close_by(t0, t, delta)
                    del items[t_key]
                _set_mul(t, 1.0)
                rolling_pos = 0.0

            elif k > 0.0:
                if t_key in items:
                    for t0 in items[t_key]:
                        delta = _set_mul(t0, t0.avco_multiplier + k * (1.0 - t0.avco_multiplier))
                        _close_by(t0, t, delta)
                _set_mul(t, 1.0)
                rolling_pos += t.pos_size

            else:
                items[t_key].append(t)
                rolling_pos += t.pos_size

            self.avco_rolling_positions[t_key] = rolling_pos
            t.avco_rolling_pos_size = rolling_pos

    def _calc_fifo_multipliers(self):
        # _l.debug('transactions - calculate multipliers - fifo')

        items = defaultdict(list)

        def _set_mul(t0, fifo_multiplier):
            delta = fifo_multiplier - t0.fifo_multiplier
            t0.fifo_multiplier = fifo_multiplier
            return delta

        def _close_by(closed, cur, delta):
            # closed.fifo_closed_by.append(VirtualTransactionClosedByData(cur, delta))
            closed.fifo_closed_by.append((cur, delta))

        for t in self._transactions:
            t_key = self._get_trn_group_key(t)

            if t.trn_cls.id == TransactionClass.INSTRUMENT_PL:
                t.fifo_rolling_pos_size = self.fifo_rolling_positions[t_key]
                continue

            if t.trn_cls.id not in [TransactionClass.BUY, TransactionClass.SELL]:
                continue

            t.fifo_multiplier = 0.0
            t.fifo_closed_by = []
            t.fifo_rolling_pos_size = 0.0

            rolling_pos = self.fifo_rolling_positions[t_key]

            if isclose(rolling_pos, 0.0):
                k = -1
            else:
                k = - t.pos_size / rolling_pos

            if k > 1.0:
                if t_key in items:
                    for t0 in items[t_key]:
                        delta = _set_mul(t0, 1.0)
                        _close_by(t0, t, delta)
                    items[t_key].clear()
                items[t_key].append(t)
                _set_mul(t, 1.0 / k)
                rolling_pos = t.pos_size * (1.0 - t.fifo_multiplier)

            elif isclose(k, 1.0):
                if t_key in items:
                    for t0 in items[t_key]:
                        delta = _set_mul(t0, 1.0)
                        _close_by(t0, t, delta)
                    del items[t_key]
                _set_mul(t, 1.0)
                rolling_pos = 0.0

            elif k > 0.0:
                position = t.pos_size
                if t_key in items:
                    t_items = items[t_key]
                    for t0 in t_items:
                        remaining = t0.pos_size * (1.0 - t0.fifo_multiplier)
                        k0 = - position / remaining
                        if k0 > 1.0:
                            delta = _set_mul(t0, 1.0)
                            _close_by(t0, t, delta)
                            position += remaining
                        elif isclose(k0, 1.0):
                            delta = _set_mul(t0, 1.0)
                            _close_by(t0, t, delta)
                            position += remaining
                        elif k0 > 0.0:
                            position += remaining * k0
                            delta = _set_mul(t0, t0.fifo_multiplier + k0 * (1.0 - t0.fifo_multiplier))
                            _close_by(t0, t, delta)
                        # else:
                        #     break
                        if isclose(position, 0.0):
                            break
                    t_items = [t0 for t0 in t_items if not isclose(t0.fifo_multiplier, 1.0)]
                    if t_items:
                        items[t_key] = t_items
                    else:
                        del items[t_key]

                _set_mul(t, abs((t.pos_size - position) / t.pos_size))
                rolling_pos += t.pos_size * t.fifo_multiplier

            else:
                items[t_key].append(t)
                rolling_pos += t.pos_size

            self.fifo_rolling_positions[t_key] = rolling_pos
            t.fifo_rolling_pos_size = rolling_pos

    def _get_trn_group_key(self, t):
        return (
            getattr(t.prtfl, 'id', None) if self.instance.portfolio_mode == Report.MODE_INDEPENDENT else None,
            getattr(t.acc_pos, 'id', None) if self.instance.account_mode == Report.MODE_INDEPENDENT else None,
            getattr(t.str1_pos, 'id', None) if self.instance.strategy1_mode == Report.MODE_INDEPENDENT else None,
            getattr(t.str2_pos, 'id', None) if self.instance.strategy2_mode == Report.MODE_INDEPENDENT else None,
            getattr(t.str3_pos, 'id', None) if self.instance.strategy3_mode == Report.MODE_INDEPENDENT else None,
            getattr(t.instr, 'id', None),
            getattr(t.alloc_bl, 'id', None),
            getattr(t.alloc_pl, 'id', None),
        )

    def _generate_items(self):
        _l.debug('items - generate')
        for trn in self._transactions:
            if trn.is_hidden:
                continue

            if trn.trn_cls.id in [TransactionClass.BUY, TransactionClass.SELL]:
                self._add_instr(trn)
                self._add_cash(trn, val=trn.cash, ccy=trn.stl_ccy)

            elif trn.trn_cls.id in [TransactionClass.CASH_INFLOW, TransactionClass.CASH_OUTFLOW]:
                self._add_cash(trn, val=trn.cash, ccy=trn.stl_ccy,
                               acc=trn.acc_cash, str1=trn.str1_cash, str2=trn.str2_cash,
                               str3=trn.str3_cash)

                # P&L
                item = ReportItem.from_trn(self.instance, self.pricing_provider, self.fx_rate_provider,
                                           ReportItem.TYPE_CASH_IN_OUT, trn, acc=trn.acc_cash,
                                           str1=trn.str1_cash, str2=trn.str2_cash, str3=trn.str3_cash,
                                           ccy=trn.stl_ccy)
                self._items.append(item)

            elif trn.trn_cls.id == TransactionClass.INSTRUMENT_PL:
                self._add_instr(trn, val=0.0)
                self._add_cash(trn, val=trn.cash, ccy=trn.stl_ccy)

            elif trn.trn_cls.id == TransactionClass.TRANSACTION_PL:
                self._add_cash(trn, val=trn.cash, ccy=trn.stl_ccy)

                item = ReportItem.from_trn(self.instance, self.pricing_provider, self.fx_rate_provider,
                                           ReportItem.TYPE_TRANSACTION_PL, trn, acc=trn.acc_cash,
                                           str1=trn.str1_cash, str2=trn.str2_cash, str3=trn.str3_cash)
                self._items.append(item)

            elif trn.trn_cls.id == TransactionClass.FX_TRADE:
                # TODO: Что используем для strategy?
                self._add_cash(trn, val=trn.principal, ccy=trn.stl_ccy)

                # self._add_cash(trn, val=trn.cash, ccy=trn.stl_ccy)

                # P&L
                item = ReportItem.from_trn(self.instance, self.pricing_provider, self.fx_rate_provider,
                                           ReportItem.TYPE_FX_TRADE, trn, acc=trn.acc_cash,
                                           str1=trn.str1_cash, str2=trn.str2_cash, str3=trn.str3_cash,
                                           ccy=trn.trn.settlement_currency, trn_ccy=trn.trn_ccy)
                self._items.append(item)

            elif trn.trn_cls.id == TransactionClass.TRANSFER:
                # raise RuntimeError('Virtual transaction must be created')
                pass

            elif trn.trn_cls.id == TransactionClass.FX_TRANSFER:
                # raise RuntimeError('Virtual transaction must be created')
                pass

            else:
                raise RuntimeError('Invalid transaction class: %s' % trn.trn_cls.id)

        _l.debug('items - raw.len=%s', len(self._items))

    def _aggregate_items(self):
        _l.debug('items - aggregate')

        aggr_items = []

        sorted_items = sorted(self._items, key=lambda x: self._item_group_key(x))
        for k, g in groupby(sorted_items, key=lambda x: self._item_group_key(x)):
            _l.debug('items - aggregate - group=%s', k)
            res_item = None

            for item in g:
                if item.type in [ReportItem.TYPE_INSTRUMENT, ReportItem.TYPE_CURRENCY, ReportItem.TYPE_TRANSACTION_PL,
                                 ReportItem.TYPE_FX_TRADE, ReportItem.TYPE_CASH_IN_OUT, ]:
                    if res_item is None:
                        res_item = ReportItem.from_item(item)
                    res_item.add(item)

            if res_item:
                _l.debug('items - aggregate - add item=%s, instr=%s', res_item, getattr(res_item.instr, 'id', None))
                _l.debug('pricing')
                res_item.pricing()
                _l.debug('close')
                res_item.close()
                aggr_items.append(res_item)

        self._items = aggr_items

        _l.debug('items - len=%s', len(self._items))

    def _item_group_key(self, item):
        return (
            item.type,
            getattr(item.prtfl, 'id', -1),
            getattr(item.acc, 'id', -1),
            getattr(item.str1, 'id', -1),
            getattr(item.str2, 'id', -1),
            getattr(item.str3, 'id', -1),
            getattr(item.instr, 'id', -1),
            getattr(item.alloc_bl, 'id', -1),
            getattr(item.alloc_pl, 'id', -1),
            getattr(item.ccy, 'id', -1),
            getattr(item.trn_ccy, 'id', -1),
            getattr(item.detail_trn, 'id', -1),
        )

    def _item_mismatch_group_key(self, item):
        return (
            item.type,
            getattr(item.prtfl, 'id', -1),
            getattr(item.acc, 'id', -1),
            getattr(item.instr, 'id', -1),
            getattr(item.ccy, 'id', -1),
            getattr(item.mismatch_prtfl, 'id', -1),
            getattr(item.mismatch_acc, 'id', -1),
        )

    # def _item_group_key_pass2(self, trn=None, item=None):
    #     if trn:
    #         return (
    #             getattr(trn.prtfl, 'id', -1),
    #             getattr(trn.acc_pos, 'id', -1),
    #             getattr(trn.str1_pos, 'id', -1),
    #             getattr(trn.str2_pos, 'id', -1),
    #             getattr(trn.str3_pos, 'id', -1),
    #             getattr(trn.alloc_bl, 'id', -1),
    #             getattr(trn.alloc_pl, 'id', -1),
    #             getattr(trn.instr, 'id', -1),
    #             # getattr(trn.ccy, 'id', -1),
    #             # getattr(trn.trn_ccy, 'id', -1),
    #         )
    #     elif item:
    #         return (
    #             getattr(item.prtfl, 'id', -1),
    #             getattr(item.acc, 'id', -1),
    #             getattr(item.str1, 'id', -1),
    #             getattr(item.str2, 'id', -1),
    #             getattr(item.str3, 'id', -1),
    #             getattr(item.alloc_bl, 'id', -1),
    #             getattr(item.alloc_pl, 'id', -1),
    #             getattr(item.instr, 'id', -1),
    #             # getattr(item.ccy, 'id', -1),
    #             # getattr(item.trn_ccy, 'id', -1),
    #         )
    #     else:
    #         raise RuntimeError('code bug')

    def _build_on_pl_first_date(self):
        report_on_pl_first_date = Report(
            master_user=self.instance.master_user,
            member=self.instance.member,
            pl_first_date=None,
            report_date=self.instance.pl_first_date,
            report_currency=self.instance.report_currency,
            pricing_policy=self.instance.pricing_policy,
            cost_method=self.instance.cost_method,
            portfolio_mode=self.instance.portfolio_mode,
            account_mode=self.instance.account_mode,
            strategy1_mode=self.instance.strategy1_mode,
            strategy2_mode=self.instance.strategy2_mode,
            strategy3_mode=self.instance.strategy3_mode,
            show_transaction_details=self.instance.show_transaction_details,
            approach_multiplier=self.instance.approach_multiplier,
            instruments=self.instance.instruments,
            portfolios=self.instance.portfolios,
            accounts=self.instance.accounts,
            strategies1=self.instance.strategies1,
            strategies2=self.instance.strategies2,
            strategies3=self.instance.strategies3,
            transaction_classes=self.instance.transaction_classes,
            date_field=self.instance.date_field,
            custom_fields=self.instance.custom_fields,
        )

        builder = self.__class__(report_on_pl_first_date)
        builder.build(full=False)

        if not report_on_pl_first_date.items:
            return

        def _item_key(item):
            return (
                item.type,
                getattr(item.prtfl, 'id', -1),
                getattr(item.acc, 'id', -1),
                getattr(item.str1, 'id', -1),
                getattr(item.str2, 'id', -1),
                getattr(item.str3, 'id', -1),
                getattr(item.alloc_bl, 'id', -1),
                getattr(item.alloc_pl, 'id', -1),
                getattr(item.instr, 'id', -1),
                getattr(item.ccy, 'id', -1),
                getattr(item.trn_ccy, 'id', -1),
                getattr(item.detail_trn, 'id', -1),
            )

        items_on_rep_date = {_item_key(i): i for i in self.instance.items}
        # items_on_pl_start_date = {_item_key(i): i for i in report_on_pl_first_date.items}

        for item_plsd in report_on_pl_first_date.items:
            key = _item_key(item_plsd)
            item_rpd = items_on_rep_date.get(key, None)

            if item_rpd:
                item_rpd.pl_sub_item(item_plsd)

            else:
                item_rpd = ReportItem(self.instance, self.pricing_provider, self.fx_rate_provider, item_plsd.type)

                item_rpd.instr = item_plsd.instr
                item_rpd.ccy = item_plsd.ccy
                item_rpd.trn_ccy = item_plsd.trn_ccy
                item_rpd.prtfl = item_plsd.prtfl
                item_rpd.instr = item_plsd.instr
                item_rpd.acc = item_plsd.acc
                item_rpd.str1 = item_plsd.str1
                item_rpd.str2 = item_plsd.str2
                item_rpd.str3 = item_plsd.str3
                item_rpd.pricing_ccy = item_plsd.pricing_ccy
                item_rpd.trn = item_plsd.trn
                item_rpd.alloc_bl = item_plsd.alloc_bl
                item_rpd.alloc_pl = item_plsd.alloc_pl
                item_rpd.mismatch_prtfl = item_plsd.mismatch_prtfl
                item_rpd.mismatch_acc = item_plsd.mismatch_acc

                item_rpd.pricing()
                item_rpd.pl_sub_item(item_plsd)

                self.instance.items.append(item_rpd)

        return report_on_pl_first_date

    # def _calc_pass2(self):
    #     _l.debug('transactions - pass 2')
    #
    #     items_map = {}
    #     for item in self._items:
    #         if item.type == ReportItem.TYPE_INSTRUMENT and item.instr:
    #             key = self._item_group_key_pass2(item=item)
    #             items_map[key] = item
    #
    #     for trn in self._transactions:
    #         if not trn.is_cloned and trn.trn_cls.id in [TransactionClass.BUY, TransactionClass.SELL]:
    #             key = self._item_group_key_pass2(trn=trn)
    #             item = items_map.get(key, None)
    #             if item:
    #                 trn.calc_pass2(balance_pos_size=item.pos_size)
    #                 item.add_pass2(trn)
    #             else:
    #                 raise RuntimeError('Oh error')
    #
    #     _l.debug('items - pass 2')
    #     for item in self._items:
    #         item.close_pass2()

    def _aggregate_summary(self):
        if not settings.DEBUG:
            return

        _l.debug('aggregate summary')
        total = ReportItem(self.instance, self.pricing_provider, self.fx_rate_provider, ReportItem.TYPE_SUMMARY)
        for item in self._items:
            if item.type in [ReportItem.TYPE_INSTRUMENT, ReportItem.TYPE_CURRENCY, ReportItem.TYPE_TRANSACTION_PL,
                             ReportItem.TYPE_FX_TRADE, ReportItem.TYPE_CASH_IN_OUT]:
                total.add(item)
        total.pricing()
        total.close()
        self._summaries.append(total)

    def _detect_mismatches(self):
        _l.debug('mismatches - detect')

        l = []
        for trn in self._transactions:
            if trn.is_mismatch and trn.link_instr and not isclose(trn.mismatch, 0.0):
                item = ReportItem.from_trn(self.instance, self.pricing_provider, self.fx_rate_provider,
                                           ReportItem.TYPE_MISMATCH, trn)
                l.append(item)

        _l.debug('mismatches - raw.len=%s', len(l))

        if not l:
            return

        _l.debug('mismatches - aggregate')
        l = sorted(l, key=lambda x: self._item_mismatch_group_key(x))
        for k, g in groupby(l, key=lambda x: self._item_mismatch_group_key(x)):

            mismatch_item = None
            for item in g:
                if mismatch_item is None:
                    mismatch_item = ReportItem.from_item(item)
                mismatch_item.add(item)

            if mismatch_item:
                mismatch_item.pricing()
                mismatch_item.close()
                self._mismatch_items.append(mismatch_item)

        _l.debug('mismatches - len=%s', len(self._mismatch_items))

    def _add_instr(self, trn, val=None):
        if trn.case == 0:
            item = ReportItem.from_trn(self.instance, self.pricing_provider, self.fx_rate_provider,
                                       ReportItem.TYPE_INSTRUMENT, trn, val=val)
            self._items.append(item)

        elif trn.case == 1:
            item = ReportItem.from_trn(self.instance, self.pricing_provider, self.fx_rate_provider,
                                       ReportItem.TYPE_INSTRUMENT, trn, val=val)
            self._items.append(item)

        elif trn.case == 2:
            pass

        else:
            raise RuntimeError('Invalid transaction case: %s' % trn.case)

    def _add_cash(self, trn, val, ccy, acc=None, acc_interim=None, str1=None, str2=None, str3=None):
        if trn.case == 0:
            item = ReportItem.from_trn(self.instance, self.pricing_provider, self.fx_rate_provider,
                                       ReportItem.TYPE_CURRENCY, trn, ccy=ccy, acc=acc,
                                       str1=str1, str2=str2, str3=str3,
                                       val=val)
            self._items.append(item)

        elif trn.case == 1:
            item = ReportItem.from_trn(self.instance, self.pricing_provider, self.fx_rate_provider,
                                       ReportItem.TYPE_CURRENCY, trn, ccy=ccy, acc=acc_interim or trn.acc_interim,
                                       str1=str1, str2=str2, str3=str3,
                                       val=val)
            self._items.append(item)

        elif trn.case == 2:
            item = ReportItem.from_trn(self.instance, self.pricing_provider, self.fx_rate_provider,
                                       ReportItem.TYPE_CURRENCY, trn, ccy=ccy, acc=acc,
                                       str1=str1, str2=str2, str3=str3,
                                       val=val)
            self._items.append(item)

            item = ReportItem.from_trn(self.instance, self.pricing_provider, self.fx_rate_provider,
                                       ReportItem.TYPE_CURRENCY, trn, ccy=ccy, acc=acc_interim or trn.acc_interim,
                                       str1=str1, str2=str2, str3=str3,
                                       val=-val)
            self._items.append(item)

        else:
            raise RuntimeError('Invalid transaction case: %s' % trn.case)

    def _refresh_with_perms(self):
        # _l.debug('items - refresh all objects with permissions')

        instrs = set()
        ccys = set()
        prtfls = set()
        accs = set()
        strs1 = set()
        strs2 = set()
        strs3 = set()

        for i in self.instance.items:
            if i.instr:
                instrs.add(i.instr.id)
                if i.instr.pricing_currency_id:
                    ccys.add(i.instr.pricing_currency_id)
                if i.instr.accrued_currency_id:
                    ccys.add(i.instr.accrued_currency_id)

            if i.ccy:
                ccys.add(i.ccy.id)
            if i.trn_ccy:
                ccys.add(i.trn_ccy.id)
            if i.pricing_ccy:
                ccys.add(i.pricing_ccy.id)

            if i.prtfl:
                prtfls.add(i.prtfl.id)
            if i.acc:
                accs.add(i.acc.id)

            if i.str1:
                strs1.add(i.str1.id)
            if i.str2:
                strs2.add(i.str2.id)
            if i.str3:
                strs3.add(i.str3.id)

            if i.mismatch_prtfl:
                prtfls.add(i.mismatch_prtfl.id)
            if i.mismatch_acc:
                accs.add(i.mismatch_acc.id)

            if i.alloc_bl:
                instrs.add(i.alloc_bl.id)
                if i.alloc_bl.pricing_currency_id:
                    ccys.add(i.alloc_bl.pricing_currency_id)
                if i.alloc_bl.accrued_currency_id:
                    ccys.add(i.alloc_bl.accrued_currency_id)

            if i.alloc_pl:
                instrs.add(i.alloc_pl.id)
                if i.alloc_pl.pricing_currency_id:
                    ccys.add(i.alloc_pl.pricing_currency_id)
                if i.alloc_pl.accrued_currency_id:
                    ccys.add(i.alloc_pl.accrued_currency_id)

        instrs = Instrument.objects.filter(master_user=self.instance.master_user).prefetch_related(
            'master_user',
            'instrument_type',
            'instrument_type__instrument_class',
            'pricing_currency',
            'accrued_currency',
            'payment_size_detail',
            'daily_pricing_model',
            'price_download_scheme',
            'price_download_scheme__provider',
            get_attributes_prefetch(),
            get_tag_prefetch(),
            # *get_permissions_prefetch_lookups(
            #     (None, Instrument),
            #     ('instrument_type', InstrumentType),
            # )
        ).in_bulk(instrs)
        _l.debug('instrs: %s', sorted(instrs.keys()))

        ccys = Currency.objects.filter(master_user=self.instance.master_user).prefetch_related(
            'master_user',
            'daily_pricing_model',
            'price_download_scheme',
            'price_download_scheme__provider',
            get_attributes_prefetch(),
            get_tag_prefetch()
        ).in_bulk(ccys)
        _l.debug('ccys: %s', sorted(ccys.keys()))

        prtfls = Portfolio.objects.filter(master_user=self.instance.master_user).prefetch_related(
            'master_user',
            get_attributes_prefetch(),
            get_tag_prefetch(),
            # *get_permissions_prefetch_lookups(
            #     (None, Portfolio),
            # )
        ).in_bulk(prtfls)
        _l.debug('prtfls: %s', sorted(prtfls.keys()))

        accs = Account.objects.filter(master_user=self.instance.master_user).prefetch_related(
            'master_user',
            'type',
            get_attributes_prefetch(),
            get_tag_prefetch(),
            # *get_permissions_prefetch_lookups(
            #     (None, Account),
            #     ('type', AccountType),
            # )
        ).in_bulk(accs)
        _l.debug('accs: %s', sorted(accs.keys()))

        strs1 = Strategy1.objects.filter(master_user=self.instance.master_user).prefetch_related(
            'master_user',
            'subgroup',
            'subgroup__group',
            get_tag_prefetch(),
            # *get_permissions_prefetch_lookups(
            #     (None, Strategy1),
            #     ('subgroup', Strategy1Subgroup),
            #     ('subgroup__group', Strategy1Group),
            # )
        ).in_bulk(strs1)
        _l.debug('strs1: %s', sorted(strs1.keys()))

        strs2 = Strategy2.objects.filter(master_user=self.instance.master_user).prefetch_related(
            'master_user',
            'subgroup',
            'subgroup__group',
            get_tag_prefetch(),
            # *get_permissions_prefetch_lookups(
            #     (None, Strategy2),
            #     ('subgroup', Strategy2Subgroup),
            #     ('subgroup__group', Strategy2Group),
            # )
        ).in_bulk(strs2)
        _l.debug('strs2: %s', sorted(strs2.keys()))

        strs3 = Strategy3.objects.filter(master_user=self.instance.master_user).prefetch_related(
            'master_user',
            'subgroup',
            'subgroup__group',
            get_tag_prefetch(),
            # *get_permissions_prefetch_lookups(
            #     (None, Strategy3),
            #     ('subgroup', Strategy3Subgroup),
            #     ('subgroup__group', Strategy3Group),
            # )
        ).in_bulk(strs3)
        _l.debug('strs3: %s', sorted(strs3.keys()))

        for i in self.instance.items:
            if i.instr:
                i.instr = instrs[i.instr.id]
                if i.instr.pricing_currency_id:
                    i.instr.pricing_currency = ccys[i.instr.pricing_currency_id]
                if i.instr.accrued_currency_id:
                    i.instr.accrued_currency = ccys[i.instr.accrued_currency_id]

            if i.ccy:
                i.ccy = ccys[i.ccy.id]
            if i.trn_ccy:
                i.trn_ccy = ccys[i.trn_ccy.id]
            if i.pricing_ccy:
                i.pricing_ccy = ccys[i.pricing_ccy.id]

            if i.prtfl:
                i.prtfl = prtfls[i.prtfl.id]
            if i.acc:
                i.acc = accs[i.acc.id]

            if i.str1:
                i.str1 = strs1[i.str1.id]
            if i.str2:
                i.str2 = strs2[i.str2.id]
            if i.str3:
                i.str3 = strs3[i.str3.id]

            if i.mismatch_prtfl:
                i.mismatch_prtfl = prtfls[i.mismatch_prtfl.id]
            if i.mismatch_acc:
                i.mismatch_acc = accs[i.mismatch_acc.id]

            if i.alloc_bl:
                i.alloc_bl = instrs[i.alloc_bl.id]
                if i.alloc_bl.pricing_currency_id:
                    i.alloc_bl.pricing_currency = ccys[i.alloc_bl.pricing_currency_id]
                if i.alloc_bl.accrued_currency_id:
                    i.alloc_bl.accrued_currency = ccys[i.alloc_bl.accrued_currency_id]

            if i.alloc_pl:
                i.alloc_pl = instrs[i.alloc_pl.id]
                if i.alloc_pl.pricing_currency_id:
                    i.alloc_pl.pricing_currency = ccys[i.alloc_pl.pricing_currency_id]
                if i.alloc_pl.accrued_currency_id:
                    i.alloc_pl.accrued_currency = ccys[i.alloc_pl.accrued_currency_id]
