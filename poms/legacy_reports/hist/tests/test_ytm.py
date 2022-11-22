# from __future__ import unicode_literals, division, print_function
#
# from poms.instruments.models import CostMethod
# from poms.reports.hist.backends.ytm import YTMReport2Builder
# from poms.reports.hist.tests.base import BaseReportTestCase, n
# from poms.reports.models import YTMReport, YTMReportItem
# from poms.transactions.models import Transaction
#
#
# class YTMTestCase(BaseReportTestCase):
#     def setUp(self):
#         super(YTMTestCase, self).setUp()
#
#     def _print_ytm_transactions(self, transactions):
#         self._print_transactions(
#             transactions,
#             'accounting_date',
#             'portfolio',
#             'instrument',
#             'account_position',
#             'position_size_with_sign',
#             'avco_multiplier',
#             'fifo_multiplier',
#             'rolling_position')
#
#     def _print_ytm(self, instance):
#         columns = ['pk', 'portfolio', 'account', 'instrument', 'position', 'ytm', 'time_invested']
#         data = []
#         for i in instance.items:
#             portfolio = i.portfolio
#             acc = i.account
#             instr = i.instrument
#             data.append([
#                 i.pk,
#                 getattr(portfolio, 'name', None),
#                 getattr(acc, 'name', None),
#                 getattr(instr, 'name', None),
#                 i.position,
#                 i.ytm,
#                 i.time_invested,
#             ])
#         print('*' * 79)
#         print('Positions')
#         # print(pd.DataFrame(data=data, columns=columns))
#         self._print_table(data=data, columns=columns)
#
#     def _assertEqualYTM(self, result, expected):
#         self.assertEqual(len(result.items), len(expected.items), 'len items')
#
#         r_expected = {i.pk: i for i in expected.items}
#
#         for ri in result.items:
#             ei = r_expected.pop(ri.pk)
#
#             self.assertEqual(ri.portfolio, ei.portfolio, '%s - portfolio' % ri.pk)
#             self.assertEqual(ri.account, ei.account, '%s - account' % ri.pk)
#             self.assertEqual(ri.instrument, ei.instrument, '%s - instrument' % ri.pk)
#
#             self.assertEqual(n(ri.position), n(ei.position), '%s - position' % ri.pk)
#             self.assertEqual(n(ri.ytm), n(ei.ytm), '%s - ytm' % ri.pk)
#             self.assertEqual(n(ri.time_invested), n(ei.time_invested), '%s - time_invested' % ri.pk)
#
#     def test_avco(self):
#         queryset = Transaction.objects.filter(pk__in=[
#             self.t_buy_bond.pk, self.t_sell_stock.pk
#         ])
#         instance = YTMReport(master_user=self.m, cost_method=CostMethod.objects.get(pk=CostMethod.AVCO),
#                              begin_date=None, end_date=self.d(9),
#                              use_portfolio=False, use_account=False)
#         b = YTMReport2Builder(instance=instance, queryset=queryset)
#         b.build()
#         self._print_test_name()
#         self._print_ytm_transactions(b.transactions)
#         self._print_ytm(instance)
#         self._assertEqualYTM(instance, YTMReport(
#             items=[
#                 YTMReportItem(pk=b.make_key(portfolio=None, account=None, instrument=self.instr1_bond_chf,
#                                             currency=None),
#                               portfolio=None, account=None, instrument=self.instr1_bond_chf,
#                               position=100., ytm=0., time_invested=6),
#                 YTMReportItem(pk=b.make_key(portfolio=None, account=None, instrument=self.instr2_stock, currency=None),
#                               portfolio=None, account=None, instrument=self.instr2_stock,
#                               position=-200., ytm=0., time_invested=-6)
#             ]
#         ))
#
#     def test_fifo(self):
#         queryset = Transaction.objects.filter(pk__in=[
#             self.t_buy_bond.pk, self.t_sell_stock.pk
#         ])
#         instance = YTMReport(master_user=self.m, cost_method=CostMethod.objects.get(pk=CostMethod.FIFO),
#                              begin_date=None, end_date=self.d(9),
#                              use_portfolio=False, use_account=False)
#         b = YTMReport2Builder(instance=instance, queryset=queryset)
#         b.build()
#         self._print_test_name()
#         self._print_ytm_transactions(b.transactions)
#         self._print_ytm(instance)
#         self._assertEqualYTM(instance, YTMReport(
#             items=[
#                 YTMReportItem(pk=b.make_key(portfolio=None, account=None, instrument=self.instr1_bond_chf,
#                                             currency=None),
#                               portfolio=None, account=None, instrument=self.instr1_bond_chf,
#                               position=100., ytm=0., time_invested=6),
#                 YTMReportItem(pk=b.make_key(portfolio=None, account=None, instrument=self.instr2_stock, currency=None),
#                               portfolio=None, account=None, instrument=self.instr2_stock,
#                               position=-200., ytm=0., time_invested=-6)
#             ]
#         ))
