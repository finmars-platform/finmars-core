# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division

from poms.reports.hist.backends.base import BaseReport2Builder
from poms.reports.models import YTMReportItem
from poms.transactions.models import TransactionClass


class YTMReport2Builder(BaseReport2Builder):
    def __init__(self, *args, **kwargs):
        super(YTMReport2Builder, self).__init__(*args, **kwargs)
        self._filter_date_attr = 'accounting_date'
        self._items = {}

    def _get_item(self, trn, ext=None):
        t_key = self.make_key(portfolio=trn.portfolio, account=trn.account_position, instrument=trn.instrument, ext=ext)
        try:
            return self._items[t_key]
        except KeyError:
            # portfolio = trn.portfolio if self._use_portfolio else None
            # account = trn.account_position if self._use_account else None
            # instrument = trn.instrument
            # item = YTMReportItem(pk=t_key, portfolio=portfolio, account=account, instrument=instrument)
            item = self.make_item(YTMReportItem, key=t_key, portfolio=trn.portfolio, account=trn.account_position,
                                  instrument=trn.instrument)
            self._items[t_key] = item
            return item

    def build(self):
        self.set_multiplier()
        multiplier_attr = self.multiplier_attr

        # calculate total position for instrument
        for t in self.transactions:
            t_class = t.transaction_class_id
            if t_class == TransactionClass.BUY or t_class == TransactionClass.SELL:
                item = self._get_item(t)
                item.position += t.position_size_with_sign

        for t in self.transactions:
            t_class = t.transaction_class_id
            if t_class == TransactionClass.BUY or t_class == TransactionClass.SELL:
                item = self._get_item(t)

                multiplier = getattr(t, multiplier_attr, 0.)

                t.ytm = 0.
                t.time_invested = (self._report_date - t.transaction_date).days
                t.remaining_position = abs(t.position_size_with_sign * (1 - multiplier))
                t.remaining_position_percent = t.remaining_position / item.position
                t.weighted_ytm = t.ytm * t.remaining_position_percent
                t.weighted_time_invested = t.time_invested * t.remaining_position_percent

                item.ytm += t.weighted_ytm
                item.time_invested += t.weighted_time_invested

        items = [i for i in self._items.values()]
        items = sorted(items, key=lambda x: x.pk)

        self.instance.transactions = self.transactions
        self.instance.items = items

        return self.instance
