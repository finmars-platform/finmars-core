# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import unicode_literals, division

import logging

from poms.reports.hist.backends.base import BaseReport2Builder

_l = logging.getLogger('poms.reports')


# class SimpleMultipliersReportBuilder(BaseReportBuilder):
#     def __init__(self, *args, **kwargs):
#         super(SimpleMultipliersReportBuilder, self).__init__(*args, **kwargs)
#         self._filter_date_attr = 'accounting_date'
#
#     def build(self):
#         self.annotate_avco_multiplier()
#         self.annotate_fifo_multiplier()
#         self.instance.results = self.transactions
#         return self.instance


class SimpleMultipliersReport2Builder(BaseReport2Builder):
    def __init__(self, *args, **kwargs):
        super(SimpleMultipliersReport2Builder, self).__init__(*args, **kwargs)
        self._filter_date_attr = 'accounting_date'

    def build(self):
        self.set_fifo_multiplier()
        self.set_avco_multiplier()
        self.instance.transactions = self.transactions
        return self.instance
