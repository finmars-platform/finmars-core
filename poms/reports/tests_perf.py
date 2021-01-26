# import logging
# import os
# from datetime import date, datetime
#
# import math
# from dateutil.relativedelta import relativedelta
# from django.test import TestCase
#
# from poms.instruments.models import Instrument
# from poms.reports.builders.performance import PerformanceReportBuilder
# from poms.reports.builders.performance_item import PerformanceReport, PerformanceReportItem
# from poms.reports.builders.performance_virt_trn import PerformanceVirtualTransaction
# from poms.reports.tests_cf import AbstractReportTestMixin
# from poms.transactions.models import Transaction
#
# _l = logging.getLogger('poms.reports')
#
#
# class PerfReportTestCase(AbstractReportTestMixin, TestCase):
#     VERIFY_TRN_COLS = [
#         # 'pk',
#         # 'lid',
#         # 'is_cloned',
#         # 'is_hidden',
#         'trn_code',
#         'trn_cls',
#         'instr',
#         'trn_ccy',
#         # 'notes',
#         'pos_size',
#         'stl_ccy',
#         'cash',
#         'principal',
#         'carry',
#         'overheads',
#         'ref_fx',
#         # 'trn_date',
#         'acc_date',
#         'cash_date',
#         'prtfl',
#         'acc_pos',
#         'acc_cash',
#         'acc_interim',
#         'str1_pos',
#         'str1_cash',
#         'str2_pos',
#         'str2_cash',
#         'str3_pos',
#         'str3_cash',
#         'link_instr',
#         'alloc_bl',
#         'alloc_pl',
#     ]
#
#     VERIFY_ITEM_COLS = [
#         'period_begin',
#         'period_end',
#         'period_name',
#         # 'period_key',
#         'portfolio',
#         'account',
#         'strategy1',
#         'strategy2',
#         'strategy3',
#         'src_trns_id',
#         'return_pl',
#         'return_nav',
#         'accumulated_pl',
#         'pl_in_period',
#         'nav_change',
#         'nav_period_start',
#         'nav_period_end',
#         'cash_inflows',
#         'cash_outflows',
#         'time_weighted_cash_inflows',
#         'time_weighted_cash_outflows',
#         'avg_nav_in_period',
#         'cumulative_return_pl',
#         'cumulative_return_nav'
#     ]
#
#     def _sdump(self, builder, name, show_trns=True, show_items=True, trn_cols=None, item_cols=None, trn_filter=None):
#         transpose = True
#         showindex = 'always'
#         if show_trns or show_items:
#             s = 'Report: %s\n' % (
#                 name,
#             )
#             if show_trns:
#                 trn_cols = trn_cols or self.VERIFY_TRN_COLS
#                 s += '\nVirtual transactions: \n%s\n' % (
#                     PerformanceVirtualTransaction.sdumps(builder.instance.transactions, columns=trn_cols,
#                                                          filter=trn_filter, transpose=transpose, showindex=showindex)
#                 )
#
#             if show_items:
#                 item_cols = item_cols or self.VERIFY_ITEM_COLS
#                 s += '\nItems: \n%s\n' % (
#                     PerformanceReportItem.sdumps(builder.instance.items, columns=item_cols,
#                                                  transpose=transpose, showindex=showindex)
#                 )
#             return s
#         return None
#
#     def _dump(self, *args, **kwargs):
#         for r in self._sdump(*args, **kwargs).splitlines():
#             _l.debug(r)
#
#     def _simple_run(self, name, trns=False, trn_cols=None, item_cols=None, **kwargs):
#         _l.debug('')
#         _l.debug('')
#         _l.debug('*' * 79)
#
#         kwargs.setdefault('pricing_policy', self.pp)
#
#         r = PerformanceReport(master_user=self.m, member=self.mm, **kwargs)
#         queryset = None
#         if isinstance(trns, (list, tuple)):
#             queryset = Transaction.objects.filter(pk__in=[t if isinstance(t, int) else t.id for t in trns])
#         b = PerformanceReportBuilder(instance=r, queryset=queryset)
#         b.build_performance()
#         r.transactions = b._original_transactions
#
#         name = ' / '.join([
#             name,
#             '[%s,%s]' % (r.begin_date, r.end_date),
#             '%s' % r.report_currency,
#             # 'prtfl_%s' % mode_names[r.portfolio_mode],
#             # 'acc_%s' % mode_names[r.account_mode],
#             # 'str1_%s' % mode_names[r.strategy1_mode],
#             # 'str2_%s' % mode_names[r.strategy2_mode],
#             # 'str3_%s' % mode_names[r.strategy3_mode],
#         ])
#         self._dump(b, name, trn_cols=trn_cols, item_cols=item_cols)
#         return r
#
#     def _write_results(self, reports, file_name=None, trn_cols=None, item_cols=None):
#         import xlsxwriter
#
#         trn_cols = trn_cols or self.VERIFY_TRN_COLS
#         item_cols = item_cols or self.VERIFY_ITEM_COLS
#
#         def _val(val):
#             # if isinstance(val, (bool, int, float, str, date, datetime)):
#             #     return val
#             if val is None:
#                 return val
#             if isinstance(val, (bool, int, float, str, datetime)):
#                 return val
#             if isinstance(val, date):
#                 return datetime(val.year, month=val.month, day=val.day)
#             return str(val)
#
#         # data_path = os.path.join(tempfile.gettempdir(), 'data.xlsx')
#         data_path = os.path.join('/home', 'ailyukhin', 'tmp', file_name or 'data.xlsx')
#
#         workbook = xlsxwriter.Workbook(data_path)
#         header_fmt = workbook.add_format({'bold': True})
#         date_fmt = workbook.add_format({'num_format': 'dd-mm-yyyy'})
#         col_fmt = workbook.add_format({'bold': True, 'bg_color': '#EEEEEE'})
#         delim_fmt = workbook.add_format({'bg_color': 'gray'})
#         # num_fmt = workbook.add_format({'num_format': '#,###.###'})
#         num_fmt = None
#
#         modes_map = {
#             PerformanceReport.MODE_IGNORE: 'Ignore',
#             PerformanceReport.MODE_INDEPENDENT: 'Independent',
#             PerformanceReport.MODE_INTERDEPENDENT: 'Offsetting/Interdependent',
#         }
#
#         approach_map = {
#             0.0: '0/100',
#             0.5: '50/50',
#             1.0: '100/0',
#         }
#
#         worksheet = workbook.add_worksheet()
#
#         row = 0
#         for r in reports:
#             worksheet.set_row(row, cell_format=delim_fmt)
#             row += 1
#
#             # worksheet.write(row, 0, 'Report date:', header_fmt)
#             worksheet.merge_range(row, 0, row, 2, 'Begin date:', header_fmt)
#             worksheet.write_datetime(row, 3, r.begin_date, date_fmt)
#             row += 1
#
#             worksheet.merge_range(row, 0, row, 2, 'End date:', header_fmt)
#             worksheet.write_datetime(row, 3, r.end_date, date_fmt)
#             row += 1
#
#             # worksheet.write(row, 0, 'Report currency:', header_fmt)
#             worksheet.merge_range(row, 0, row, 2, 'Report currency:', header_fmt)
#             worksheet.write(row, 3, _val(r.report_currency))
#             row += 1
#
#             worksheet.merge_range(row, 0, row, 2, 'Portfolio:', header_fmt)
#             worksheet.write(row, 3, _val(modes_map[r.portfolio_mode]))
#             row += 1
#
#             worksheet.merge_range(row, 0, row, 2, 'Account:', header_fmt)
#             worksheet.write(row, 3, _val(modes_map[r.account_mode]))
#             row += 1
#
#             worksheet.merge_range(row, 0, row, 2, 'Strategy1:', header_fmt)
#             worksheet.write(row, 3, _val(modes_map[r.strategy1_mode]))
#             row += 1
#
#             worksheet.merge_range(row, 0, row, 2, 'Strategy2:', header_fmt)
#             worksheet.write(row, 3, _val(modes_map[r.strategy2_mode]))
#             row += 1
#
#             worksheet.merge_range(row, 0, row, 2, 'Strategy3:', header_fmt)
#             worksheet.write(row, 3, _val(modes_map[r.strategy3_mode]))
#             row += 1
#
#             worksheet.merge_range(row, 0, row, 2, 'Approach:', header_fmt)
#             worksheet.write(row, 3, _val(approach_map[r.approach_multiplier]))
#             row += 1
#
#             # worksheet.write(row, 0, 'Virtual Transactions', header_fmt)
#             worksheet.merge_range(row, 0, row, len(trn_cols), 'Transactions:', header_fmt)
#             row += 1
#             for col, name in enumerate(trn_cols):
#                 worksheet.write(row, col, name, col_fmt)
#             row += 1
#             for trn in r.transactions:
#                 if trn.is_cloned:
#                     continue
#                 for col, val in enumerate(PerformanceVirtualTransaction.dump_values(trn, trn_cols)):
#                     val = _val(val)
#                     if trn_cols[col] in ['trn_date', 'acc_date', 'cash_date']:
#                         worksheet.write_datetime(row, col, val, date_fmt)
#                     elif isinstance(val, (int, float)):
#                         worksheet.write_number(row, col, val, num_fmt)
#                     else:
#                         worksheet.write(row, col, val)
#                 row += 1
#
#             row += 2
#             # worksheet.write(row, 0, 'Items', header_fmt)
#             worksheet.merge_range(row, 0, row, len(item_cols), 'Items:', header_fmt)
#             row += 1
#             for col, name in enumerate(item_cols):
#                 worksheet.write(row, col, name, col_fmt)
#             row += 1
#             for item in r.items:
#                 for col, val in enumerate(PerformanceReportItem.dump_values(item, item_cols)):
#                     val = _val(val)
#                     if item_cols[col] in ['period_begin', 'period_end']:
#                         worksheet.write_datetime(row, col, val, date_fmt)
#                     elif isinstance(val, (int, float)):
#                         if math.isnan(val):
#                             val = 0.0
#                         worksheet.write_number(row, col, val, num_fmt)
#                     else:
#                         worksheet.write(row, col, val)
#                 row += 1
#
#             row += 5
#
#         workbook.close()
#
#     def _test_perf1(self):
#         # settings.DEBUG = True
#
#         i1 = Instrument.objects.create(
#             master_user=self.m,
#             user_code='i1',
#             instrument_type=self.m.instrument_type,
#             pricing_currency=self.usd,
#             price_multiplier=1.0,
#             accrued_currency=self.usd,
#             accrued_multiplier=1.0,
#             maturity_date=date(2103, 1, 1),
#             maturity_price=1000,
#         )
#         self._instr_hist(i1, date(2020, 1, 31), 1, 1)
#         self._instr_hist(i1, date(2020, 2, 29), 1, 1)
#
#         self._t_buy(
#             instr=i1, position=10,
#             stl_ccy=self.usd, principal=-10, carry=0, overheads=-1,
#             acc_pos=self.a1_1, acc_cash=self.a1_2,
#             acc_date=date(2020, 1, 10), cash_date=date(2020, 1, 10)
#         )
#
#         # self._t_buy(
#         #     instr=i1, position=10,
#         #     stl_ccy=self.usd, principal=-20, carry=0, overheads=-1,
#         #     acc_pos=self.a1_1, acc_cash=self.a1_2,
#         #     acc_date=date(2020, 2, 10), cash_date=date(2020, 2, 10)
#         # )
#
#         report = PerformanceReport(
#             master_user=self.m,
#             member=self.mm,
#             begin_date=date(2020, 1, 1),
#             end_date=date(2020, 12, 31),
#             report_currency=self.usd,
#             pricing_policy=self.pp,
#             periods='date_group(transaction.accounting_date,[[None,None,timedelta(months=1),["[","%Y-%m-%d","/","","%Y-%m-%d","]"]]], "Err")',
#         )
#         report_builder = PerformanceReportBuilder(report)
#         report_builder.build_performance()
#         # self._dumps(report.items)
#
#     def test_perf2(self):
#         # settings.DEBUG = True
#         test_prefix = 'td_0'
#
#         i1 = Instrument.objects.create(
#             master_user=self.m,
#             user_code='i1',
#             instrument_type=self.m.instrument_type,
#             pricing_currency=self.usd,
#             price_multiplier=1.0,
#             accrued_currency=self.usd,
#             accrued_multiplier=1.0,
#             maturity_date=date(2103, 1, 1),
#             maturity_price=1000,
#         )
#         i2 = Instrument.objects.create(
#             master_user=self.m,
#             user_code='i',
#             instrument_type=self.m.instrument_type,
#             pricing_currency=self.eur,
#             price_multiplier=1.0,
#             accrued_currency=self.eur,
#             accrued_multiplier=1.0,
#             maturity_date=date(2103, 1, 1),
#             maturity_price=1000,
#         )
#
#         sd = date(2020, 1, 31)
#         for m in range(0, 12):
#             d = sd + relativedelta(months=m)
#             self._ccy_hist(self.eur, d, 1.1)
#             self._instr_hist(i1, d, 1, 1)
#             self._instr_hist(i2, d, 1, 1)
#
#         self._t_buy(
#             instr=i1, position=10,
#             stl_ccy=self.usd, principal=-10, carry=0, overheads=-1,
#             p=self.p1, acc_pos=self.a1, acc_cash=self.a4,
#             s1_pos=self.s1_1_1_1, s1_cash=self.s1_1_1_1,
#             acc_date=date(2020, 1, 11), cash_date=date(2020, 1, 11)
#         )
#         self._t_buy(
#             instr=i1, position=10,
#             stl_ccy=self.usd, principal=-20, carry=0, overheads=-1,
#             p=self.p2, acc_pos=self.a2, acc_cash=self.a4,
#             s1_pos=self.s1_1_1_1, s1_cash=self.s1_1_1_2,
#             acc_date=date(2020, 2, 12), cash_date=date(2020, 2, 12)
#         )
#         self._t_sell(
#             instr=i1, position=-10,
#             stl_ccy=self.usd, principal=15, carry=0, overheads=-1,
#             p=self.p3, acc_pos=self.a3, acc_cash=self.a4,
#             s1_pos=self.s1_1_1_1, s1_cash=self.s1_1_1_3,
#             acc_date=date(2020, 3, 13), cash_date=date(2020, 2, 13)
#         )
#
#         self._t_instr_pl(
#             instr=i1, position=0,
#             stl_ccy=self.usd, principal=5, carry=0, overheads=0,
#             p=self.p1, acc_pos=self.a1, acc_cash=self.a4,
#             s1_pos=self.s1_1_1_1, s1_cash=self.s1_1_1_1,
#             acc_date=date(2020, 4, 14), cash_date=date(2020, 4, 14)
#         )
#
#         self._t_fx_tade(
#             trn_ccy=self.eur, position=10,
#             stl_ccy=self.usd, principal=-20, carry=0, overheads=-1,
#             p=self.p1, acc_pos=self.a1, acc_cash=self.a2,
#             s1_pos=self.s1_1_1_1, s1_cash=self.s1_1_1_2,
#             acc_date=date(2020, 5, 15), cash_date=date(2020, 5, 15)
#         )
#         self._t_cash_in(
#             trn_ccy=self.usd, position=1000,
#             stl_ccy=self.usd, principal=1000, carry=0, overheads=0,
#             p=self.p1, acc_pos=self.a1, acc_cash=self.a2,
#             s1_pos=self.s1_1_1_1, s1_cash=self.s1_1_1_2,
#             acc_date=date(2020, 6, 16), cash_date=date(2020, 6, 16)
#         )
#         self._t_cash_out(
#             trn_ccy=self.usd, position=-500,
#             stl_ccy=self.usd, principal=-500, carry=0, overheads=0,
#             p=self.p2, acc_pos=self.a1, acc_cash=self.a2,
#             s1_pos=self.s1_1_1_1, s1_cash=self.s1_1_1_2,
#             acc_date=date(2020, 7, 17), cash_date=date(2020, 7, 17)
#         )
#         self._t_trn_pl(
#             stl_ccy=self.usd, principal=0., carry=-9, overheads=-1,
#             p=self.p2, acc_pos=self.a1, acc_cash=self.a2,
#             s1_pos=self.s1_1_1_1, s1_cash=self.s1_1_1_2,
#             acc_date=date(2020, 8, 18), cash_date=date(2020, 8, 18)
#         )
#         self._t_transfer(
#             instr=i1, position=10,
#             p=self.p1, acc_pos=self.a1, acc_cash=self.a3,
#             s1_pos=self.s1_1_1_1, s1_cash=self.s1_1_1_2,
#             acc_date=date(2020, 9, 19), cash_date=date(2020, 8, 19)
#         )
#         self._t_fx_transfer(
#             trn_ccy=self.usd, position=-10,
#             p=self.p1, acc_pos=self.a1, acc_cash=self.a3,
#             s1_pos=self.s1_1_1_1, s1_cash=self.s1_1_1_2,
#             acc_date=date(2020, 10, 20), cash_date=date(2020, 10, 20)
#         )
#
#         report_currencies = [
#             self.usd,
#             # self.eur,
#         ]
#
#         consolidations = [
#             {
#                 'portfolio_mode': PerformanceReport.MODE_IGNORE,
#                 'account_mode': PerformanceReport.MODE_IGNORE,
#                 'strategy1_mode': PerformanceReport.MODE_IGNORE,
#                 'strategy2_mode': PerformanceReport.MODE_IGNORE,
#                 'strategy3_mode': PerformanceReport.MODE_IGNORE,
#             },
#             # {
#             #     'portfolio_mode': PerformanceReport.MODE_INDEPENDENT,
#             #     'account_mode': PerformanceReport.MODE_INDEPENDENT,
#             #     'strategy1_mode': PerformanceReport.MODE_INDEPENDENT,
#             #     'strategy2_mode': PerformanceReport.MODE_INDEPENDENT,
#             #     'strategy3_mode': PerformanceReport.MODE_INDEPENDENT,
#             # },
#             # {
#             #     'portfolio_mode': PerformanceReport.MODE_INDEPENDENT,
#             #     'account_mode': PerformanceReport.MODE_INDEPENDENT,
#             #     'strategy1_mode': PerformanceReport.MODE_IGNORE,
#             #     'strategy2_mode': PerformanceReport.MODE_IGNORE,
#             #     'strategy3_mode': PerformanceReport.MODE_IGNORE,
#             # },
#             # {
#             #     'portfolio_mode': PerformanceReport.MODE_INDEPENDENT,
#             #     'account_mode': PerformanceReport.MODE_IGNORE,
#             #     'strategy1_mode': PerformanceReport.MODE_IGNORE,
#             #     'strategy2_mode': PerformanceReport.MODE_IGNORE,
#             #     'strategy3_mode': PerformanceReport.MODE_IGNORE,
#             # },
#             # {
#             #     'portfolio_mode': PerformanceReport.MODE_IGNORE,
#             #     'account_mode': PerformanceReport.MODE_INDEPENDENT,
#             #     'strategy1_mode': PerformanceReport.MODE_IGNORE,
#             #     'strategy2_mode': PerformanceReport.MODE_IGNORE,
#             #     'strategy3_mode': PerformanceReport.MODE_IGNORE,
#             # },
#             # {
#             #     'portfolio_mode': PerformanceReport.MODE_INDEPENDENT,
#             #     'account_mode': PerformanceReport.MODE_INDEPENDENT,
#             #     'strategy1_mode': PerformanceReport.MODE_INTERDEPENDENT,
#             #     'strategy2_mode': PerformanceReport.MODE_IGNORE,
#             #     'strategy3_mode': PerformanceReport.MODE_IGNORE,
#             # },
#             # {
#             #     'portfolio_mode': PerformanceReport.MODE_IGNORE,
#             #     'account_mode': PerformanceReport.MODE_IGNORE,
#             #     'strategy1_mode': PerformanceReport.MODE_INTERDEPENDENT,
#             #     'strategy2_mode': PerformanceReport.MODE_IGNORE,
#             #     'strategy3_mode': PerformanceReport.MODE_IGNORE,
#             # },
#         ]
#         cost_method = self._avco
#         periods = 'date_group(transaction.accounting_date,[[None,None,timedelta(months=1),["[","%d.%m.%Y","/","","%d.%m.%Y","]"]]], "Err")'
#
#         reports = []
#         for report_currency in report_currencies:
#             _l.warn('\t%s', report_currency)
#             for consolidation0 in consolidations:
#                 consolidation = consolidation0.copy()
#                 _l.warn('\t\t%s', sorted(consolidation.items()))
#                 r = self._simple_run(
#                     name='Tests',
#                     begin_date=date(2020, 1, 1),
#                     end_date=date(2020, 12, 31),
#                     cost_method=cost_method,
#                     report_currency=report_currency,
#                     periods=periods,
#                     **consolidation,
#                 )
#
#                 reports.append(r)
#
#         _l.warn('write results')
#         self._write_results(reports, '%s_perf.xlsx' % test_prefix)
