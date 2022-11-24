# from __future__ import unicode_literals, division, print_function
#
# from poms.instruments.models import CostMethod
# from poms.reports.hist.backends import CostReport2Builder
# from poms.reports.hist.tests.base import BaseReportTestCase, n
# from poms.reports.models import CostReport, CostReportItem
# from poms.transactions.models import Transaction
#
#
# class CostTestCase(BaseReportTestCase):
#     def setUp(self):
#         super(CostTestCase, self).setUp()
#
#     def _print_cost_transactions(self, transactions):
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
#     def _print_cost(self, instance):
#         columns = ['pk', 'portfolio', 'account', 'instrument', 'position',
#                    'cost_instrument_ccy', 'cost_system_ccy',
#                    'cost_price', 'cost_price_adjusted', ]
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
#                 i.cost_instrument_ccy,
#                 i.cost_system_ccy,
#                 i.cost_price,
#                 i.cost_price_adjusted,
#             ])
#         print('*' * 79)
#         print('Positions')
#         # print(pd.DataFrame(data=data, columns=columns))
#         self._print_table(data=data, columns=columns)
#
#     def _assertEqualCost(self, result, expected):
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
#             self.assertEqual(n(ri.cost_instrument_ccy), n(ei.cost_instrument_ccy), '%s - cost_instrument_ccy' % ri.pk)
#             self.assertEqual(n(ri.cost_system_ccy), n(ei.cost_system_ccy), '%s - cost_system_ccy' % ri.pk)
#             self.assertEqual(n(ri.cost_price), n(ei.cost_price), '%s - cost_price' % ri.pk)
#             self.assertEqual(n(ri.cost_price_adjusted), n(ei.cost_price_adjusted), '%s - cost_price_adjusted' % ri.pk)
#
#     def test_avco(self):
#         queryset = Transaction.objects.filter(pk__in=[
#             self.t_buy_bond.pk,
#             self.t_sell_stock.pk
#         ])
#         instance = CostReport(master_user=self.m,
#                               cost_method=CostMethod.objects.get(pk=CostMethod.AVCO),
#                               begin_date=None, end_date=self.d(9),
#                               use_portfolio=False, use_account=False)
#         b = CostReport2Builder(instance=instance, queryset=queryset)
#         b.build()
#         self._print_test_name()
#         self._print_cost_transactions(b.transactions)
#         self._print_cost(instance)
#         self._assertEqualCost(instance, CostReport(
#             items=[
#                 CostReportItem(pk=b.make_key(portfolio=None, account=None, instrument=self.instr1_bond_chf,
#                                              currency=None),
#                                portfolio=None, account=None, instrument=self.instr1_bond_chf,
#                                position=100.,
#                                cost_instrument_ccy=-200., cost_system_ccy=-180.,
#                                cost_price=2., cost_price_adjusted=200.),
#                 CostReportItem(pk=b.make_key(portfolio=None, account=None, instrument=self.instr2_stock, currency=None),
#                                portfolio=None, account=None, instrument=self.instr2_stock,
#                                position=200.,
#                                cost_instrument_ccy=9.166667, cost_system_ccy=14.666667,
#                                cost_price=0.045833, cost_price_adjusted=0.045833),
#             ]
#         ))
#
#     def test_fifo(self):
#         queryset = Transaction.objects.filter(pk__in=[
#             self.t_buy_bond.pk, self.t_sell_stock.pk
#         ])
#         instance = CostReport(master_user=self.m, cost_method=CostMethod.objects.get(pk=CostMethod.FIFO),
#                               begin_date=None, end_date=self.d(9),
#                               use_portfolio=False, use_account=False)
#         b = CostReport2Builder(instance=instance, queryset=queryset)
#         b.build()
#         self._print_test_name()
#         self._print_cost_transactions(b.transactions)
#         self._print_cost(instance)
