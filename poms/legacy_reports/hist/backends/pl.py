# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division

from django.conf import settings

from poms.reports.hist.backends.base import BaseReport2Builder
from poms.reports.models import PLReportItem, BalanceReportItem
from poms.transactions.models import TransactionClass


class PLReport2Builder(BaseReport2Builder):
    def __init__(self, *args, **kwargs):
        super(PLReport2Builder, self).__init__(*args, **kwargs)
        self._filter_date_attr = 'accounting_date'
        self._items = {}
        self._balance_items = {}

    def _get_item(self, trn, acc, ext=None):
        t_key = self.make_key(portfolio=trn.portfolio, account=acc, instrument=trn.instrument, ext=ext)
        try:
            return self._items[t_key]
        except KeyError:
            item = self.make_item(PLReportItem, key=t_key, portfolio=trn.portfolio, account=acc,
                                  instrument=trn.instrument)
            self._items[t_key] = item
            return item

    def _get_balance_items(self, trn, acc, ext=None):
        t_key = self.make_key(portfolio=trn.portfolio, account=acc, instrument=trn.instrument, ext=ext)
        try:
            return self._balance_items[t_key]
        except KeyError:
            item = self.make_item(BalanceReportItem, key=t_key, portfolio=trn.portfolio, account=acc,
                                  instrument=trn.instrument)
            self._balance_items[t_key] = item
            return item

    def _process_instrument(self, t, item, sign=1.):
        # default case
        # self.set_currency_fx_rate(t, 'transaction_currency')
        # self.set_currency_fx_rate(t, 'settlement_currency')
        settlement_currency_history = self.find_currency_history(t.settlement_currency)

        t.principal_with_sign_system_ccy = t.principal_with_sign * settlement_currency_history.fx_rate
        t.carry_with_sign_system_ccy = t.carry_with_sign * settlement_currency_history.fx_rate
        t.overheads_with_sign_system_ccy = t.overheads_with_sign * settlement_currency_history.fx_rate

        item.principal_with_sign_system_ccy += sign * t.principal_with_sign_system_ccy
        item.carry_with_sign_system_ccy += sign * t.carry_with_sign_system_ccy
        item.overheads_with_sign_system_ccy += sign * t.overheads_with_sign_system_ccy

    def _process_fx_trade(self, t, item, sign=1.):
        # self.set_currency_fx_rate(t, 'transaction_currency')
        # self.set_currency_fx_rate(t, 'settlement_currency')
        transaction_currency_history = self.find_currency_history(t.transaction_currency)
        settlement_currency_history = self.find_currency_history(t.settlement_currency)

        t.principal_with_sign_system_ccy = t.principal_with_sign * settlement_currency_history.fx_rate + \
                                           t.position_size_with_sign * transaction_currency_history.fx_rate
        t.carry_with_sign_system_ccy = t.carry_with_sign * settlement_currency_history.fx_rate
        t.overheads_with_sign_system_ccy = t.overheads_with_sign * settlement_currency_history.fx_rate

        item.principal_with_sign_system_ccy += sign * t.principal_with_sign_system_ccy
        item.carry_with_sign_system_ccy += sign * t.carry_with_sign_system_ccy
        item.overheads_with_sign_system_ccy += sign * t.overheads_with_sign_system_ccy

    def build(self):
        for t in self.transactions:
            t_class = t.transaction_class_id
            # item = None
            if t_class == TransactionClass.CASH_INFLOW or t_class == TransactionClass.CASH_OUTFLOW:
                pass
            elif t_class == TransactionClass.BUY or t_class == TransactionClass.SELL:
                item = self._get_item(t, acc=t.account_position)
                self._process_instrument(t, item)

                bitem = self._get_balance_items(t, acc=t.account_position)
                bitem.position += t.position_size_with_sign

            elif t_class == TransactionClass.INSTRUMENT_PL:
                item = self._get_item(t, acc=t.account_position)
                self._process_instrument(t, item)

            elif t_class == TransactionClass.TRANSACTION_PL:
                item = self._get_item(t, acc=t.account_position, ext=TransactionClass.TRANSACTION_PL)
                item.name = TransactionClass.TRANSACTION_PL
                self._process_instrument(t, item)

            elif t_class == TransactionClass.FX_TRADE:
                spec = self._get_item(t, acc=t.account_position, ext=TransactionClass.FX_TRADE)
                spec.name = TransactionClass.FX_TRADE
                self._process_fx_trade(t, spec)

            elif t_class == TransactionClass.TRANSFER:
                # make 2 transactions for buy/sell
                raise RuntimeError('TRANSFER: two transaction buy/sell must be created')

            elif t_class == TransactionClass.FX_TRANSFER:
                # make 2 transactions for buy/sell
                raise RuntimeError('FX_TRANSFER: two transaction buy/sell must be created')

        for i in self._balance_items.values():
            self.calc_balance_instrument(i)

            pli = self._items[i.pk]

            pli.principal_with_sign_system_ccy += i.principal_value_system_ccy
            pli.carry_with_sign_system_ccy += i.accrued_value_system_ccy
            pli.overheads_with_sign_system_ccy += 0.0

            pli.total_system_ccy = pli.principal_with_sign_system_ccy + \
                                   pli.carry_with_sign_system_ccy + \
                                   pli.overheads_with_sign_system_ccy

            pli.principal_with_sign_report_ccy = self.system_ccy_to_report_ccy(pli.principal_with_sign_system_ccy)
            pli.carry_with_sign_report_ccy = self.system_ccy_to_report_ccy(pli.carry_with_sign_system_ccy)
            pli.overheads_with_sign_report_ccy = self.system_ccy_to_report_ccy(pli.overheads_with_sign_system_ccy)

            pli.total_report_ccy = pli.principal_with_sign_report_ccy + \
                        pli.carry_with_sign_report_ccy + \
                        pli.overheads_with_sign_report_ccy

        summary = self.instance.summary
        for i in self._items.values():
            summary.principal_with_sign_system_ccy += i.principal_with_sign_system_ccy
            summary.carry_with_sign_system_ccy += i.carry_with_sign_system_ccy
            summary.overheads_with_sign_system_ccy += i.overheads_with_sign_system_ccy
            summary.total_system_ccy += i.total_system_ccy

        summary.principal_with_sign_report_ccy = self.system_ccy_to_report_ccy(summary.principal_with_sign_system_ccy)
        summary.carry_with_sign_report_ccy = self.system_ccy_to_report_ccy(summary.carry_with_sign_system_ccy)
        summary.overheads_with_sign_report_ccy = self.system_ccy_to_report_ccy(summary.overheads_with_sign_system_ccy)
        summary.total_report_ccy = self.system_ccy_to_report_ccy(summary.total_system_ccy)

        items = [i for i in self._items.values()]
        items = sorted(items, key=lambda x: '%s' % (x.pk,))

        self.instance.items = items

        if settings.DEBUG:
            self.instance.transactions = self.transactions

        return self.instance
