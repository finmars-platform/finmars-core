# from __future__ import unicode_literals, division, print_function
#
# from poms.reports.hist.backends.pl import PLReport2Builder
# from poms.reports.hist.tests.base import BaseReportTestCase, n
# from poms.reports.models import PLReport, PLReportSummary, PLReportItem
# from poms.transactions.models import Transaction, TransactionClass
#
#
# class PLTestCase(BaseReportTestCase):
#     def _print_pl_transactions(self, transactions):
#         self._print_transactions(
#             transactions,
#             'pk',
#             'transaction_class',
#             'portfolio',
#             'instrument', 'transaction_currency', 'position_size_with_sign',
#             'settlement_currency',
#             'cash_consideration', 'principal_with_sign', 'carry_with_sign', 'overheads_with_sign',
#             'account_position', 'account_cash', 'account_interim',
#             'accounting_date', 'cash_date',
#         )
#
#     def _print_pl(self, instance):
#         columns = ['pk',
#                    'portfolio', 'account', 'instrument', 'name',
#                    'principal_with_sign_system_ccy', 'carry_with_sign_system_ccy', 'overheads_with_sign_system_ccy',
#                    'total_system_ccy']
#         data = []
#
#         self.principal_with_sign_system_ccy = 0.
#         self.carry_with_sign_system_ccy = 0.
#         self.overheads_with_sign_system_ccy = 0.
#         self.total_system_ccy = 0.
#
#         for i in instance.items:
#             portfolio = i.portfolio
#             acc = i.account
#             instr = i.instrument
#             data.append([
#                 i.pk,
#                 getattr(portfolio, 'name', None),
#                 getattr(acc, 'name', None),
#                 getattr(instr, 'name', None),
#                 i.name,
#                 i.principal_with_sign_system_ccy,
#                 i.carry_with_sign_system_ccy,
#                 i.overheads_with_sign_system_ccy,
#                 i.total_system_ccy,
#             ])
#         print('-' * 79)
#         print('Positions')
#         # print(pd.DataFrame(data=data, columns=columns))
#         self._print_table(data=data, columns=columns)
#
#         print('-' * 79)
#         print('Summary')
#         # print(pd.DataFrame(
#         #     data=[[instance.summary.principal_with_sign_system_ccy, instance.summary.carry_with_sign_system_ccy,
#         #            instance.summary.overheads_with_sign_system_ccy, instance.summary.total_system_ccy]],
#         #     columns=['principal_with_sign_system_ccy', 'carry_with_sign_system_ccy', 'overheads_with_sign_system_ccy',
#         #              'total_system_ccy']))
#         self._print_table(
#             data=[[instance.summary.principal_with_sign_system_ccy, instance.summary.carry_with_sign_system_ccy,
#                    instance.summary.overheads_with_sign_system_ccy, instance.summary.total_system_ccy]],
#             columns=['principal_with_sign_system_ccy', 'carry_with_sign_system_ccy', 'overheads_with_sign_system_ccy',
#                      'total_system_ccy'])
#
#     def _assertEqualPL(self, result, expected):
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
#             self.assertEqual(ri.name, ei.name, '%s - name' % ri.pk)
#
#             self.assertEqual(n(ri.principal_with_sign_system_ccy), n(ei.principal_with_sign_system_ccy),
#                              '%s - principal_with_sign_system_ccy' % ri.pk)
#             self.assertEqual(n(ri.carry_with_sign_system_ccy), n(ei.carry_with_sign_system_ccy),
#                              '%s - carry_with_sign_system_ccy' % ri.pk)
#             self.assertEqual(n(ri.overheads_with_sign_system_ccy), n(ei.overheads_with_sign_system_ccy),
#                              '%s - overheads_with_sign_system_ccy' % ri.pk)
#             self.assertEqual(n(ri.total_system_ccy), n(ei.total_system_ccy),
#                              '%s - total_system_ccy' % ri.pk)
#
#         self.assertEqual(n(result.summary.principal_with_sign_system_ccy),
#                          n(expected.summary.principal_with_sign_system_ccy),
#                          'principal_with_sign_system_ccy')
#         self.assertEqual(n(result.summary.carry_with_sign_system_ccy),
#                          n(expected.summary.carry_with_sign_system_ccy),
#                          'carry_with_sign_system_ccy')
#         self.assertEqual(n(result.summary.overheads_with_sign_system_ccy),
#                          n(expected.summary.overheads_with_sign_system_ccy),
#                          'overheads_with_sign_system_ccy')
#         self.assertEqual(n(result.summary.total_system_ccy),
#                          n(expected.summary.total_system_ccy),
#                          'total_system_ccy')
#
#     def test_simple(self):
#         queryset = Transaction.objects.filter(pk__in=self.simple_w_trnpl)
#         instance = PLReport(master_user=self.m,
#                             begin_date=None, end_date=self.d(9),
#                             use_portfolio=False, use_account=False)
#         b = PLReport2Builder(instance=instance, queryset=queryset)
#         b.build()
#         self._print_test_name()
#         self._print_pl_transactions(instance.transactions)
#         self._print_pl(instance)
#         self._assertEqualPL(instance, PLReport(
#             items=[
#                 PLReportItem(pk=b.make_key(portfolio=None, account=None, instrument=self.instr1_bond_chf,
#                                            currency=None),
#                              portfolio=None, account=None, instrument=self.instr1_bond_chf,
#                              principal_with_sign_system_ccy=-162.000000, carry_with_sign_system_ccy=13.450000,
#                              overheads_with_sign_system_ccy=-15.000000, total_system_ccy=-163.550000),
#                 PLReportItem(pk=b.make_key(portfolio=None, account=None, instrument=self.instr2_stock, currency=None),
#                              portfolio=None, account=None, instrument=self.instr2_stock,
#                              principal_with_sign_system_ccy=-465.333333, carry_with_sign_system_ccy=4.566667,
#                              overheads_with_sign_system_ccy=-2.233333, total_system_ccy=-463.000000),
#                 PLReportItem(pk=b.make_key(portfolio=None, account=None, instrument=None, currency=None,
#                                            ext=TransactionClass.TRANSACTION_PL),
#                              portfolio=None, account=None, instrument=None, name=TransactionClass.TRANSACTION_PL,
#                              principal_with_sign_system_ccy=0.000000, carry_with_sign_system_ccy=-12.000000,
#                              overheads_with_sign_system_ccy=-1.333333, total_system_ccy=-13.333333),
#             ],
#             summary=PLReportSummary(principal_with_sign_system_ccy=-627.333333,
#                                     carry_with_sign_system_ccy=6.016667,
#                                     overheads_with_sign_system_ccy=-18.566667,
#                                     total_system_ccy=-639.883333)
#         ))
#
#     def test_accs(self):
#         queryset = Transaction.objects.filter(pk__in=self.simple_w_trnpl)
#         instance = PLReport(master_user=self.m,
#                             begin_date=None, end_date=self.d(9),
#                             use_portfolio=False, use_account=True)
#         b = PLReport2Builder(instance=instance, queryset=queryset)
#         b.build()
#         self._print_test_name()
#         self._print_pl_transactions(instance.transactions)
#         self._print_pl(instance)
#         self._assertEqualPL(instance, PLReport(
#             items=[
#                 PLReportItem(pk=b.make_key(portfolio=None, account=self.acc1, instrument=self.instr1_bond_chf,
#                                            currency=None),
#                              portfolio=None, account=self.acc1, instrument=self.instr1_bond_chf,
#                              principal_with_sign_system_ccy=-162.000000, carry_with_sign_system_ccy=13.450000,
#                              overheads_with_sign_system_ccy=-15.000000, total_system_ccy=-163.550000),
#                 PLReportItem(pk=b.make_key(portfolio=None, account=self.acc1, instrument=self.instr2_stock,
#                                            currency=None),
#                              portfolio=None, account=self.acc1, instrument=self.instr2_stock,
#                              principal_with_sign_system_ccy=-465.333333, carry_with_sign_system_ccy=4.566667,
#                              overheads_with_sign_system_ccy=-2.233333, total_system_ccy=-463.000000),
#                 PLReportItem(pk=b.make_key(portfolio=None, account=self.acc1, instrument=None, currency=None,
#                                            ext=TransactionClass.TRANSACTION_PL),
#                              portfolio=None, account=self.acc1, instrument=None, name=TransactionClass.TRANSACTION_PL,
#                              principal_with_sign_system_ccy=0.000000, carry_with_sign_system_ccy=-12.000000,
#                              overheads_with_sign_system_ccy=-1.333333, total_system_ccy=-13.333333),
#             ],
#             summary=PLReportSummary(principal_with_sign_system_ccy=-627.333333,
#                                     carry_with_sign_system_ccy=6.016667,
#                                     overheads_with_sign_system_ccy=-18.566667,
#                                     total_system_ccy=-639.883333)
#         ))
#
#     def test_portf_accs(self):
#         queryset = Transaction.objects.filter(pk__in=self.simple_w_trnpl)
#         instance = PLReport(master_user=self.m,
#                             begin_date=None, end_date=self.d(9),
#                             use_portfolio=True, use_account=True)
#         b = PLReport2Builder(instance=instance, queryset=queryset)
#         b.build()
#         self._print_test_name()
#         self._print_pl_transactions(instance.transactions)
#         self._print_pl(instance)
#         self._assertEqualPL(instance, PLReport(
#             items=[
#                 PLReportItem(pk=b.make_key(portfolio=self.p1, account=self.acc1, instrument=self.instr1_bond_chf,
#                                            currency=None),
#                              portfolio=self.p1, account=self.acc1, instrument=self.instr1_bond_chf,
#                              principal_with_sign_system_ccy=-162.000000, carry_with_sign_system_ccy=13.450000,
#                              overheads_with_sign_system_ccy=-15.000000, total_system_ccy=-163.550000),
#                 PLReportItem(pk=b.make_key(portfolio=self.p1, account=self.acc1, instrument=self.instr2_stock,
#                                            currency=None),
#                              portfolio=self.p1, account=self.acc1, instrument=self.instr2_stock,
#                              principal_with_sign_system_ccy=-465.333333, carry_with_sign_system_ccy=4.566667,
#                              overheads_with_sign_system_ccy=-2.233333, total_system_ccy=-463.000000),
#                 PLReportItem(pk=b.make_key(portfolio=self.p1, account=self.acc1, instrument=None, currency=None,
#                                            ext=TransactionClass.TRANSACTION_PL),
#                              portfolio=self.p1, account=self.acc1, instrument=None,
#                              name=TransactionClass.TRANSACTION_PL,
#                              principal_with_sign_system_ccy=0.000000, carry_with_sign_system_ccy=-12.000000,
#                              overheads_with_sign_system_ccy=-1.333333, total_system_ccy=-13.333333),
#             ],
#             summary=PLReportSummary(principal_with_sign_system_ccy=-627.333333,
#                                     carry_with_sign_system_ccy=6.016667,
#                                     overheads_with_sign_system_ccy=-18.566667,
#                                     total_system_ccy=-639.883333)
#         ))
#
#     def test_fxtrade(self):
#         queryset = Transaction.objects.filter(pk__in=self.simple_w_fxtrade)
#         instance = PLReport(master_user=self.m,
#                             begin_date=None, end_date=self.d(9),
#                             use_portfolio=False, use_account=False)
#         b = PLReport2Builder(instance=instance, queryset=queryset)
#         b.build()
#         self._print_test_name()
#         self._print_pl_transactions(instance.transactions)
#         self._print_pl(instance)
#         self._assertEqualPL(instance, PLReport(
#             items=[
#                 PLReportItem(pk=b.make_key(portfolio=None, account=None, instrument=self.instr1_bond_chf,
#                                            currency=None),
#                              portfolio=None, account=None, instrument=self.instr1_bond_chf,
#                              principal_with_sign_system_ccy=-162.000000, carry_with_sign_system_ccy=13.450000,
#                              overheads_with_sign_system_ccy=-15.000000, total_system_ccy=-163.550000),
#                 PLReportItem(pk=b.make_key(portfolio=None, account=None, instrument=self.instr2_stock, currency=None),
#                              portfolio=None, account=None, instrument=self.instr2_stock,
#                              principal_with_sign_system_ccy=-465.333333, carry_with_sign_system_ccy=4.566667,
#                              overheads_with_sign_system_ccy=-2.233333, total_system_ccy=-463.000000),
#                 PLReportItem(pk=b.make_key(portfolio=None, account=None, instrument=None, currency=None,
#                                            ext=TransactionClass.TRANSACTION_PL),
#                              portfolio=None, account=None, instrument=None, name=TransactionClass.TRANSACTION_PL,
#                              principal_with_sign_system_ccy=0.000000, carry_with_sign_system_ccy=-12.000000,
#                              overheads_with_sign_system_ccy=-1.333333, total_system_ccy=-13.333333),
#                 PLReportItem(pk=b.make_key(portfolio=None, account=None, instrument=None, currency=None,
#                                            ext=TransactionClass.FX_TRADE),
#                              portfolio=None, account=None, instrument=None, name=TransactionClass.FX_TRADE,
#                              principal_with_sign_system_ccy=75.000000, carry_with_sign_system_ccy=0.000000,
#                              overheads_with_sign_system_ccy=-1.500000, total_system_ccy=73.500000),
#             ],
#             summary=PLReportSummary(principal_with_sign_system_ccy=-552.333333,
#                                     carry_with_sign_system_ccy=6.016667,
#                                     overheads_with_sign_system_ccy=-20.066667,
#                                     total_system_ccy=-566.383333)
#         ))
#
#     # def test_fx_trade_fx_rate_on_date(self):
#     #     queryset = Transaction.objects.filter(pk__in=[
#     #         self.t_fxtrade.pk, self.t_fxtrade2.pk
#     #     ])
#     #     instance = PLReport(master_user=self.m,
#     #                         begin_date=None, end_date=self.d(60),
#     #                         use_portfolio=False, use_account=True)
#     #     b = PLReport2Builder(instance=instance, queryset=queryset)
#     #     b.build()
#     #     self._print_test_name()
#     #     self._print_pl_transactions(instance.transactions)
#     #     self._print_pl(instance)
#     #     self._assertEqualPL(instance, PLReport(
#     #         items=[
#     #             PLReportItem(pk=b.make_key(portfolio=None, account=self.acc1, instrument=None, None, TransactionClass.FX_TRADE),
#     #                          portfolio=None, account=self.acc1, instrument=None, name=TransactionClass.FX_TRADE,
#     #                          principal_with_sign_system_ccy=75., carry_with_sign_system_ccy=0.,
#     #                          overheads_with_sign_system_ccy=-1.5, total_system_ccy=73.5),
#     #
#     #             PLReportItem(pk=b.make_key(portfolio=None, account=self.acc2, instrument=None, None, TransactionClass.FX_TRADE),
#     #                          portfolio=None, account=self.acc2, instrument=None, name=TransactionClass.FX_TRADE,
#     #                          principal_with_sign_system_ccy=74., carry_with_sign_system_ccy=0.,
#     #                          overheads_with_sign_system_ccy=-1., total_system_ccy=73.),
#     #         ],
#     #         summary=PLReportSummary(principal_with_sign_system_ccy=149,
#     #                                 carry_with_sign_system_ccy=0.,
#     #                                 overheads_with_sign_system_ccy=-2.5,
#     #                                 total_system_ccy=146.5)
#     #     ))
#
#     def test_multiple(self):
#         queryset = Transaction.objects.filter(pk__in=[
#             self.t_in.pk, self.t_buy_bond.pk, self.t_buy_bond_acc2.pk, self.t_buy_bond_p2.pk
#         ])
#         instance = PLReport(master_user=self.m,
#                             begin_date=None, end_date=self.d(9),
#                             use_portfolio=False, use_account=False)
#         b = PLReport2Builder(instance=instance, queryset=queryset)
#         b.build()
#         self._print_test_name()
#         self._print_pl_transactions(instance.transactions)
#         self._print_pl(instance)
#         self._assertEqualPL(instance, PLReport(
#             items=[
#                 PLReportItem(pk=b.make_key(portfolio=None, account=None, instrument=self.instr1_bond_chf,
#                                            currency=None),
#                              portfolio=None, account=None, instrument=self.instr1_bond_chf,
#                              principal_with_sign_system_ccy=-486.000000, carry_with_sign_system_ccy=-13.65,
#                              overheads_with_sign_system_ccy=-45, total_system_ccy=-544.65),
#             ],
#             summary=PLReportSummary(principal_with_sign_system_ccy=-486.000000,
#                                     carry_with_sign_system_ccy=-13.65,
#                                     overheads_with_sign_system_ccy=-45,
#                                     total_system_ccy=-544.65)
#         ))
#
#     def test_multiple_acc(self):
#         queryset = Transaction.objects.filter(pk__in=[
#             self.t_in.pk, self.t_buy_bond.pk, self.t_buy_bond_acc2.pk, self.t_buy_bond_p2.pk
#         ])
#         instance = PLReport(master_user=self.m,
#                             begin_date=None, end_date=self.d(9),
#                             use_portfolio=False, use_account=True)
#         b = PLReport2Builder(instance=instance, queryset=queryset)
#         b.build()
#         self._print_test_name()
#         self._print_pl_transactions(instance.transactions)
#         self._print_pl(instance)
#         self._assertEqualPL(instance, PLReport(
#             items=[
#                 PLReportItem(pk=b.make_key(portfolio=None, account=self.acc1, instrument=self.instr1_bond_chf,
#                                            currency=None),
#                              portfolio=None, account=self.acc1, instrument=self.instr1_bond_chf,
#                              principal_with_sign_system_ccy=-324.000000, carry_with_sign_system_ccy=-9.1,
#                              overheads_with_sign_system_ccy=-30, total_system_ccy=-363.1),
#                 PLReportItem(pk=b.make_key(portfolio=None, account=self.acc2, instrument=self.instr1_bond_chf,
#                                            currency=None),
#                              portfolio=None, account=self.acc2, instrument=self.instr1_bond_chf,
#                              principal_with_sign_system_ccy=-162, carry_with_sign_system_ccy=-4.55,
#                              overheads_with_sign_system_ccy=-15, total_system_ccy=-181.55),
#             ],
#             summary=PLReportSummary(principal_with_sign_system_ccy=-486.000000,
#                                     carry_with_sign_system_ccy=-13.65,
#                                     overheads_with_sign_system_ccy=-45,
#                                     total_system_ccy=-544.65)
#         ))
#
#     def test_multiple_portf_acc(self):
#         queryset = Transaction.objects.filter(pk__in=[
#             self.t_in.pk, self.t_buy_bond.pk, self.t_buy_bond_acc2.pk, self.t_buy_bond_p2.pk
#         ])
#         instance = PLReport(master_user=self.m,
#                             begin_date=None, end_date=self.d(9),
#                             use_portfolio=True, use_account=True)
#         b = PLReport2Builder(instance=instance, queryset=queryset)
#         b.build()
#         self._print_test_name()
#         self._print_pl_transactions(instance.transactions)
#         self._print_pl(instance)
#         self._assertEqualPL(instance, PLReport(
#             items=[
#                 PLReportItem(pk=b.make_key(portfolio=self.p1, account=self.acc1, instrument=self.instr1_bond_chf,
#                                            currency=None),
#                              portfolio=self.p1, account=self.acc1, instrument=self.instr1_bond_chf,
#                              principal_with_sign_system_ccy=-162, carry_with_sign_system_ccy=-4.55,
#                              overheads_with_sign_system_ccy=-15, total_system_ccy=-181.55),
#                 PLReportItem(pk=b.make_key(portfolio=self.p1, account=self.acc2, instrument=self.instr1_bond_chf,
#                                            currency=None),
#                              portfolio=self.p1, account=self.acc2, instrument=self.instr1_bond_chf,
#                              principal_with_sign_system_ccy=-162, carry_with_sign_system_ccy=-4.55,
#                              overheads_with_sign_system_ccy=-15, total_system_ccy=-181.55),
#                 PLReportItem(pk=b.make_key(portfolio=self.p2, account=self.acc1, instrument=self.instr1_bond_chf,
#                                            currency=None),
#                              portfolio=self.p2, account=self.acc1, instrument=self.instr1_bond_chf,
#                              principal_with_sign_system_ccy=-162, carry_with_sign_system_ccy=-4.55,
#                              overheads_with_sign_system_ccy=-15, total_system_ccy=-181.55),
#             ],
#             summary=PLReportSummary(principal_with_sign_system_ccy=-486.000000,
#                                     carry_with_sign_system_ccy=-13.65,
#                                     overheads_with_sign_system_ccy=-45,
#                                     total_system_ccy=-544.65)
#         ))
#
#     def test_transfer_case0(self):
#         trn = self.t(
#             t_class=self.transfer, instr=self.instr1_bond_chf, position=100., settlement_ccy=self.eur,
#             cash_consideration=0., principal=50., carry=4., overheads=0.,
#             acc_date_delta=3., cash_date_delta=3.,
#             acc_cash=self.acc2, acc_pos=self.acc1,  # acc2 -> acc1
#             acc_interim=self.prov_acc1)
#
#         queryset = Transaction.objects.filter(pk__in=[
#             trn.pk
#         ])
#         instance = PLReport(master_user=self.m,
#                             begin_date=None, end_date=self.d(4),
#                             use_portfolio=False, use_account=True)
#         b = PLReport2Builder(instance=instance, queryset=queryset)
#         b.build()
#         self._print_test_name()
#         self._print_pl_transactions(instance.transactions)
#         self._print_pl(instance)
#         self._assertEqualPL(instance, PLReport(
#             items=[
#                 PLReportItem(pk=b.make_key(portfolio=None, account=self.acc2, instrument=self.instr1_bond_chf,
#                                            currency=None),
#                              portfolio=None, account=self.acc2, instrument=self.instr1_bond_chf,
#                              principal_with_sign_system_ccy=47.000000, carry_with_sign_system_ccy=4.75,
#                              overheads_with_sign_system_ccy=0.000000, total_system_ccy=51.75),
#
#                 PLReportItem(pk=b.make_key(portfolio=None, account=self.acc1, instrument=self.instr1_bond_chf,
#                                            currency=None),
#                              portfolio=None, account=self.acc1, instrument=self.instr1_bond_chf,
#                              principal_with_sign_system_ccy=-47.000000, carry_with_sign_system_ccy=-4.75,
#                              overheads_with_sign_system_ccy=0.000000, total_system_ccy=-51.75),
#             ],
#             summary=PLReportSummary(principal_with_sign_system_ccy=0.,
#                                     carry_with_sign_system_ccy=0.,
#                                     overheads_with_sign_system_ccy=0.,
#                                     total_system_ccy=0.)
#         ))
#
#     def test_fx_transfer_case0(self):
#         trn = self.t(
#             t_class=self.fx_transfer, transaction_ccy=self.rub, position=1000., settlement_ccy=self.eur,
#             cash_consideration=0., principal=30., carry=0., overheads=0.,
#             acc_date_delta=3., cash_date_delta=3.,
#             acc_cash=self.acc2, acc_pos=self.acc1,  # acc2 -> acc1
#             acc_interim=self.prov_acc1)
#
#         queryset = Transaction.objects.filter(pk__in=[
#             trn.pk
#         ])
#         instance = PLReport(master_user=self.m,
#                             begin_date=None, end_date=self.d(4),
#                             use_portfolio=False, use_account=True)
#         b = PLReport2Builder(instance=instance, queryset=queryset)
#         b.build()
#         self._print_test_name()
#         self._print_pl_transactions(instance.transactions)
#         self._print_pl(instance)
#         self._assertEqualPL(instance, PLReport(
#             items=[
#                 PLReportItem(pk=b.make_key(portfolio=None, account=self.acc1, instrument=None, currency=None,
#                                            ext=TransactionClass.FX_TRADE),
#                              portfolio=None, account=self.acc1, instrument=None, name=TransactionClass.FX_TRADE,
#                              principal_with_sign_system_ccy=-25.666667, carry_with_sign_system_ccy=0.,
#                              overheads_with_sign_system_ccy=0., total_system_ccy=-25.666667),
#
#                 PLReportItem(pk=b.make_key(portfolio=None, account=self.acc2, instrument=None, currency=None,
#                                            ext=TransactionClass.FX_TRADE),
#                              portfolio=None, account=self.acc2, instrument=None, name=TransactionClass.FX_TRADE,
#                              principal_with_sign_system_ccy=25.666667, carry_with_sign_system_ccy=0.,
#                              overheads_with_sign_system_ccy=0., total_system_ccy=25.666667),
#             ],
#             summary=PLReportSummary(principal_with_sign_system_ccy=0.,
#                                     carry_with_sign_system_ccy=0.,
#                                     overheads_with_sign_system_ccy=0.,
#                                     total_system_ccy=0.)
#         ))
