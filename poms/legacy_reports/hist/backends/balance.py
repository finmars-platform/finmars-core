# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division

import logging
from datetime import date
from functools import reduce

from django.conf import settings

from poms.reports.hist.backends.base import BaseReport2Builder
from poms.reports.models import BalanceReportItem
from poms.transactions.models import TransactionClass

_l = logging.getLogger('poms.reports')


# случаи 1 и 2 возможны для всех транзакций кроме Cash-Inflow/Outflow
# в т.ч. для Трансфер (чуть позже я поясню, что на самом деле Transfer = Sell + Buy)


class BalanceReport2Builder(BaseReport2Builder):
    def __init__(self, *args, **kwargs):
        super(BalanceReport2Builder, self).__init__(*args, **kwargs)
        self._filter_date_attr = 'transaction_date'
        self._invested_items = {}
        self._items = {}

    def _get_item0(self, items, trn, instr=None, ccy=None, acc=None, ext=None):
        strategy1 = None
        if self._detail_by_strategy1:
            if instr:
                strategy1 = trn.strategy1_position
            elif ccy:
                strategy1 = trn.strategy1_cash

        strategy2 = None
        if self._detail_by_strategy2:
            if instr:
                strategy2 = trn.strategy2_position
            elif ccy:
                strategy2 = trn.strategy2_cash

        strategy3 = None
        if self._detail_by_strategy3:
            if instr:
                strategy3 = trn.strategy3_position
            elif ccy:
                strategy3 = trn.strategy3_cash

        t_key = self.make_key(portfolio=trn.portfolio, account=acc, instrument=instr, currency=ccy, ext=ext,
                              strategy1=strategy1, strategy2=strategy2, strategy3=strategy3)
        try:
            return items[t_key]
        except KeyError:
            item = self.make_item(BalanceReportItem, key=t_key, portfolio=trn.portfolio, account=acc, instrument=instr,
                                  currency=ccy, strategy1=strategy1, strategy2=strategy2, strategy3=strategy3)
            items[t_key] = item
            return item

    def _get_item(self, trn, instr=None, ccy=None, acc=None, case=None):
        ext = trn.id if self._is_show_details(trn, case, acc) else None
        item = self._get_item0(self._items, trn, instr=instr, ccy=ccy, acc=acc, ext=ext)
        if ext:
            item.transaction = trn
        return item

    def _is_show_details(self, trn, case, acc):
        if (case == 1 or case == 2) and self.instance.show_transaction_details:
            return acc and acc.type and acc.type.show_transaction_details
        return False

    def _get_invested_items(self, trn, instr=None, ccy=None, acc=None):
        return self._get_item0(self._invested_items, trn, instr=instr, ccy=ccy, acc=acc)

    def _get_trn_case(self, trn):
        accounting_date, cash_date = trn.accounting_date, trn.cash_date
        if cash_date is None:
            cash_date = date.max

        if accounting_date <= self._report_date < cash_date:  # default
            return 1
        elif cash_date <= self._report_date < accounting_date:
            return 2
        else:
            return 0

    def _add_instr(self, item, value):
        item.position += value

    def _add_cash(self, item, value, fx_rate=None, fx_rate_date=None):
        if fx_rate is None:
            fx_rate_date = fx_rate_date or self._report_date
            h = self.find_currency_history(item.currency, date=fx_rate_date)
            fx_rate = getattr(h, 'fx_rate', 0.)
        item.position += value
        item.principal_value_system_ccy += value * fx_rate
        item.market_value_system_ccy = item.principal_value_system_ccy

    def _process_instrument(self, t, val, acc, case):
        if case == 0:
            instrument_item = self._get_item(t, instr=t.instrument, acc=acc)
            instrument_item.position += val

        elif case == 1:
            instrument_item = self._get_item(t, instr=t.instrument, acc=acc)
            instrument_item.position += val

        elif case == 2:
            pass

    def _process_cash(self, t, ccy, ccy_val, acc, acc_interim, case, fx_rate=None, fx_rate_date=None):
        if case == 0:
            cash_item = self._get_item(t, ccy=ccy, acc=acc)
            self._add_cash(cash_item, ccy_val, fx_rate=fx_rate, fx_rate_date=fx_rate_date)

        elif case == 1:
            cash_item = self._get_item(t, ccy=ccy, acc=acc_interim, case=case)
            self._add_cash(cash_item, ccy_val, fx_rate=fx_rate, fx_rate_date=fx_rate_date)

        elif case == 2:
            cash_item = self._get_item(t, ccy=ccy, acc=acc)
            self._add_cash(cash_item, ccy_val, fx_rate=fx_rate, fx_rate_date=fx_rate_date)

            cash_item = self._get_item(t, ccy=ccy, acc=acc_interim, case=case)
            self._add_cash(cash_item, -ccy_val, fx_rate=fx_rate, fx_rate_date=fx_rate_date)

    def get_items(self):
        if self._detail_by_portfolio or self._detail_by_account or self._detail_by_strategy1 or self._detail_by_strategy2 or self._detail_by_strategy3:
            self.set_multiplier()

        for t in self.transactions:
            t_class = t.transaction_class_id
            case = self._get_trn_case(t)

            if t_class == TransactionClass.CASH_INFLOW or t_class == TransactionClass.CASH_OUTFLOW:
                # Cash-Inflow/Cash-Outflow use transaction.reference_fx_rate

                cash_item = self._get_item(t, ccy=t.transaction_currency, acc=t.account_position)
                self._add_cash(cash_item, t.position_size_with_sign, fx_rate=t.reference_fx_rate)

                invested_item = self._get_invested_items(t, ccy=t.transaction_currency, acc=t.account_cash)
                self._add_cash(invested_item, t.position_size_with_sign, fx_rate=t.reference_fx_rate)

            elif t_class == TransactionClass.BUY or t_class == TransactionClass.SELL:
                if self._detail_by_strategy1 or self._detail_by_strategy2 or self._detail_by_strategy3:
                    multiplier_attr = self.multiplier_attr
                    multiplier = getattr(t, multiplier_attr)
                    self._process_instrument(t, val=t.position_size_with_sign * (1. - multiplier),
                                             acc=t.account_position, case=case)
                else:
                    self._process_instrument(t, val=t.position_size_with_sign, acc=t.account_position, case=case)
                self._process_cash(t, ccy=t.settlement_currency, ccy_val=t.cash_consideration,
                                   acc=t.account_cash, acc_interim=t.account_interim, case=case)

            elif t_class == TransactionClass.INSTRUMENT_PL:
                self._process_cash(t, ccy=t.settlement_currency, ccy_val=t.cash_consideration,
                                   acc=t.account_cash, acc_interim=t.account_interim, case=case)

            elif t_class == TransactionClass.TRANSACTION_PL:
                self._process_cash(t, ccy=t.settlement_currency, ccy_val=t.cash_consideration,
                                   acc=t.account_cash, acc_interim=t.account_interim, case=case)

            elif t_class == TransactionClass.FX_TRADE:
                # Fx-Trade use fx-rate on transaction date
                # продублировать логику работу как с кэшь частью BUY/SELL, а не то как делали
                self._process_cash(t, ccy=t.transaction_currency, ccy_val=t.position_size_with_sign,
                                   acc=t.account_position, acc_interim=t.account_interim, case=case)
                self._process_cash(t, ccy=t.settlement_currency, ccy_val=t.cash_consideration,
                                   acc=t.account_cash, acc_interim=t.account_interim, case=case)

            elif t_class == TransactionClass.TRANSFER:
                # make 2 transactions for buy/sell
                raise RuntimeError('TRANSFER: two transaction buy/sell must be created')

            elif t_class == TransactionClass.FX_TRANSFER:
                # make 2 transactions for buy/sell
                raise RuntimeError('FX_TRANSFER: two transaction buy/sell must be created')

        for i in self._invested_items.values():
            if i.instrument:
                self.calc_balance_instrument(i)
            elif i.currency:
                self.calc_balance_currency(i)

        for i in self._items.values():
            if i.instrument:
                self.calc_balance_instrument(i)
            elif i.currency:
                self.calc_balance_currency(i)

        invested_items = [i for i in self._invested_items.values()]
        invested_items = sorted(invested_items, key=lambda x: x.pk)

        items = [i for i in self._items.values()]
        items = sorted(items, key=lambda x: x.pk)

        return items, invested_items

    def build(self):
        items, invested_items = self.get_items()

        self.instance.invested_items = invested_items
        self.instance.items = items

        summary = self.instance.summary
        summary.invested_value_system_ccy = reduce(lambda x, y: x + y.market_value_system_ccy, invested_items, 0.)
        summary.current_value_system_ccy = reduce(lambda x, y: x + y.market_value_system_ccy, items, 0.)
        summary.p_l_system_ccy = summary.current_value_system_ccy - summary.invested_value_system_ccy

        summary.invested_value_report_ccy = self.system_ccy_to_report_ccy(summary.invested_value_system_ccy)
        summary.current_value_report_ccy = self.system_ccy_to_report_ccy(summary.current_value_system_ccy)
        summary.p_l_report_ccy = self.system_ccy_to_report_ccy(summary.p_l_system_ccy)

        if settings.DEBUG:
            self.instance.transactions = self.transactions

        return self.instance
