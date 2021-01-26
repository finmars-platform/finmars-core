# from __future__ import unicode_literals, division
#
# from datetime import date
#
# from poms.reports.hist.backends.pl import PLReport2Builder
# from poms.reports.hist.tests.base import BaseReportTestCase, n
# from poms.reports.models import PLReport
# from poms.transactions.models import Transaction
#
#
# class MultipliersTestCase(BaseReportTestCase):
#     def setUp(self):
#         super(MultipliersTestCase, self).setUp()
#
#         # self.t_buy1 = Transaction.objects.create(
#         #     master_user=self.m,
#         #     transaction_class=self.buy,
#         #     portfolio=self.p1,
#         #     instrument=self.instr1_bond_chf,
#         #     transaction_currency=None,
#         #     position_size_with_sign=100,
#         #     settlement_currency=self.usd,
#         #     cash_consideration=-200.,
#         #     principal_with_sign=-180.,
#         #     carry_with_sign=-5.,
#         #     overheads_with_sign=-15.,
#         #     transaction_date=date(2016, 3, 4),
#         #     accounting_date=date(2016, 3, 4),
#         #     cash_date=date(2016, 3, 4),
#         #     account_position=self.acc1,
#         #     account_cash=self.acc1,
#         #     account_interim=self.prov_acc1,
#         #     reference_fx_rate=None
#         # )
#         self.t_buy1 = self.t(
#             t_class=self.buy, instr=self.instr1_bond_chf, position=100., settlement_ccy=self.usd,
#             principal=-180., carry=-5., overheads=-15., acc_date_delta=3, cash_date_delta=3)
#
#         # self.t_buy1_infuture = Transaction.objects.create(
#         #     master_user=self.m,
#         #     transaction_class=self.buy,
#         #     portfolio=self.p1,
#         #     instrument=self.instr1_bond_chf,
#         #     transaction_currency=None,
#         #     position_size_with_sign=100,
#         #     settlement_currency=self.usd,
#         #     cash_consideration=-200.,
#         #     principal_with_sign=-180.,
#         #     carry_with_sign=-5.,
#         #     overheads_with_sign=-15.,
#         #     transaction_date=date(2016, 4, 4),
#         #     accounting_date=date(2016, 4, 4),
#         #     cash_date=date(2016, 3, 4),
#         #     account_position=self.acc1,
#         #     account_cash=self.acc1,
#         #     account_interim=self.prov_acc1,
#         #     reference_fx_rate=None
#         # )
#         self.t_buy1_infuture = self.t(
#             t_class=self.buy, instr=self.instr1_bond_chf, position=100., settlement_ccy=self.usd,
#             principal=-180., carry=-5., overheads=-15., acc_date_delta=30, cash_date_delta=30)
#
#         # self.t_buy1_acc2 = Transaction.objects.create(
#         #     master_user=self.m,
#         #     transaction_class=self.buy,
#         #     portfolio=self.p1,
#         #     instrument=self.instr1_bond_chf,
#         #     transaction_currency=None,
#         #     position_size_with_sign=100,
#         #     settlement_currency=self.usd,
#         #     cash_consideration=-200.,
#         #     principal_with_sign=-180.,
#         #     carry_with_sign=-5.,
#         #     overheads_with_sign=-15.,
#         #     transaction_date=date(2016, 3, 5),
#         #     accounting_date=date(2016, 3, 5),
#         #     cash_date=date(2016, 3, 5),
#         #     account_position=self.acc2,
#         #     account_cash=self.acc2,
#         #     account_interim=self.prov_acc2,
#         #     reference_fx_rate=None
#         # )
#         self.t_buy1_acc2 = self.t(
#             t_class=self.buy, instr=self.instr1_bond_chf, position=100., settlement_ccy=self.usd,
#             principal=-180., carry=-5., overheads=-15., acc_date_delta=4, cash_date_delta=4,
#             acc_pos=self.acc2, acc_cash=self.acc2, acc_interim=self.prov_acc2)
#
#         # self.t_buy1_p2 = Transaction.objects.create(
#         #     master_user=self.m,
#         #     transaction_class=self.buy,
#         #     portfolio=self.p2,
#         #     instrument=self.instr1_bond_chf,
#         #     transaction_currency=None,
#         #     position_size_with_sign=100,
#         #     settlement_currency=self.usd,
#         #     cash_consideration=-200.,
#         #     principal_with_sign=-180.,
#         #     carry_with_sign=-5.,
#         #     overheads_with_sign=-15.,
#         #     transaction_date=date(2016, 3, 6),
#         #     accounting_date=date(2016, 3, 6),
#         #     cash_date=date(2016, 3, 6),
#         #     account_position=self.acc1,
#         #     account_cash=self.acc1,
#         #     account_interim=self.prov_acc1,
#         #     reference_fx_rate=None
#         # )
#         self.t_buy1_p2 = self.t(
#             t_class=self.buy, instr=self.instr1_bond_chf, position=100., settlement_ccy=self.usd,
#             principal=-180., carry=-5., overheads=-15., acc_date_delta=5, cash_date_delta=5,
#             p=self.p2)
#
#         # self.t_sell1 = Transaction.objects.create(
#         #     master_user=self.m,
#         #     transaction_class=self.sell,
#         #     portfolio=self.p1,
#         #     instrument=self.instr1_bond_chf,
#         #     transaction_currency=None,
#         #     position_size_with_sign=-50,
#         #     settlement_currency=self.usd,
#         #     cash_consideration=100.,
#         #     principal_with_sign=110.,
#         #     carry_with_sign=0.,
#         #     overheads_with_sign=-10.,
#         #     transaction_date=date(2016, 3, 7),
#         #     accounting_date=date(2016, 3, 7),
#         #     cash_date=date(2016, 3, 7),
#         #     account_position=self.acc1,
#         #     account_cash=self.acc1,
#         #     account_interim=self.prov_acc1,
#         #     reference_fx_rate=None
#         # )
#         self.t_sell1 = self.t(
#             t_class=self.sell, instr=self.instr1_bond_chf, position=-50., settlement_ccy=self.usd,
#             principal=110., carry=0., overheads=-10., acc_date_delta=6, cash_date_delta=6)
#
#         # self.t_sell1_acc2 = Transaction.objects.create(
#         #     master_user=self.m,
#         #     transaction_class=self.sell,
#         #     portfolio=self.p1,
#         #     instrument=self.instr1_bond_chf,
#         #     transaction_currency=None,
#         #     position_size_with_sign=-50,
#         #     settlement_currency=self.usd,
#         #     cash_consideration=100.,
#         #     principal_with_sign=110.,
#         #     carry_with_sign=0.,
#         #     overheads_with_sign=-10.,
#         #     transaction_date=date(2016, 3, 8),
#         #     accounting_date=date(2016, 3, 8),
#         #     cash_date=date(2016, 3, 8),
#         #     account_position=self.acc2,
#         #     account_cash=self.acc2,
#         #     account_interim=self.prov_acc2,
#         #     reference_fx_rate=None
#         # )
#         self.t_sell1_acc2 = self.t(
#             t_class=self.sell, instr=self.instr1_bond_chf, position=-50., settlement_ccy=self.usd,
#             principal=110., carry=0., overheads=-10., acc_date_delta=7, cash_date_delta=7,
#             acc_pos=self.acc2, acc_cash=self.acc2, acc_interim=self.prov_acc2)
#
#         # self.t_sell1_p2 = Transaction.objects.create(
#         #     master_user=self.m,
#         #     transaction_class=self.sell,
#         #     portfolio=self.p2,
#         #     instrument=self.instr1_bond_chf,
#         #     transaction_currency=None,
#         #     position_size_with_sign=-50,
#         #     settlement_currency=self.usd,
#         #     cash_consideration=100.,
#         #     principal_with_sign=110.,
#         #     carry_with_sign=0.,
#         #     overheads_with_sign=-10.,
#         #     transaction_date=date(2016, 3, 9),
#         #     accounting_date=date(2016, 3, 9),
#         #     cash_date=date(2016, 3, 9),
#         #     account_position=self.acc1,
#         #     account_cash=self.acc1,
#         #     account_interim=self.prov_acc1,
#         #     reference_fx_rate=None
#         # )
#         self.t_sell1_p2 = self.t(
#             t_class=self.sell, instr=self.instr1_bond_chf, position=-50., settlement_ccy=self.usd,
#             principal=110., carry=0., overheads=-10., acc_date_delta=8, cash_date_delta=8,
#             p=self.p2)
#
#     def _print_ml_transactions(self, transactions):
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
#     def _assertMultipliers(self, transactions, multiplier_attr, exp_multiplier_value, exp_rolling_position):
#         for t in transactions:
#             self.assertEqual(n(getattr(t, multiplier_attr, None)), n(exp_multiplier_value[t.id]))
#             self.assertEqual(n(t.rolling_position), n(exp_rolling_position[t.id]))
#
#     def test_avco(self):
#         queryset = Transaction.objects.filter(pk__in=[
#             self.t_buy1.pk, self.t_buy1_acc2.pk, self.t_buy1_p2.pk,
#             self.t_sell1.pk, self.t_sell1_acc2.pk,
#         ])
#         instance = PLReport(master_user=self.m,
#                             begin_date=None, end_date=date(2016, 3, 10),
#                             use_portfolio=False, use_account=False)
#         b = PLReport2Builder(instance=instance, queryset=queryset)
#         b.set_avco_multiplier()
#         self._print_test_name()
#         self._print_ml_transactions(b.transactions)
#         self._assertMultipliers(b.transactions, multiplier_attr='avco_multiplier',
#                                 exp_multiplier_value={
#                                     self.t_buy1.pk: 0.333333,
#                                     self.t_buy1_acc2.pk: 0.333333,
#                                     self.t_buy1_p2.pk: 0.333333,
#                                     self.t_sell1.pk: 1.0,
#                                     self.t_sell1_acc2.pk: 1.0,
#                                 },
#                                 exp_rolling_position={
#                                     self.t_buy1.pk: 100,
#                                     self.t_buy1_acc2.pk: 200,
#                                     self.t_buy1_p2.pk: 300,
#                                     self.t_sell1.pk: 250,
#                                     self.t_sell1_acc2.pk: 200,
#                                 })
#
#     def test_avco_buy_infuture(self):
#         queryset = Transaction.objects.filter(pk__in=[
#             self.t_sell1.pk, self.t_buy1_infuture.pk,
#         ])
#         instance = PLReport(master_user=self.m,
#                             begin_date=None, end_date=date(2016, 4, 10),
#                             use_portfolio=False, use_account=False)
#         b = PLReport2Builder(instance=instance, queryset=queryset)
#         b.set_avco_multiplier()
#         self._print_test_name()
#         self._print_ml_transactions(b.transactions)
#         self._assertMultipliers(b.transactions, multiplier_attr='avco_multiplier',
#                                 exp_multiplier_value={
#                                     self.t_sell1.pk: 1.0,
#                                     self.t_buy1_infuture.pk: 0.5,
#                                 },
#                                 exp_rolling_position={
#                                     self.t_sell1.pk: -50,
#                                     self.t_buy1_infuture.pk: 50,
#                                 })
#
#     def test_avco_acc(self):
#         queryset = Transaction.objects.filter(pk__in=[
#             self.t_buy1.pk, self.t_buy1_acc2.pk, self.t_buy1_p2.pk,
#             self.t_sell1.pk, self.t_sell1_acc2.pk,
#         ])
#         instance = PLReport(master_user=self.m,
#                             begin_date=None, end_date=date(2016, 3, 10),
#                             use_portfolio=False, use_account=True)
#         b = PLReport2Builder(instance=instance, queryset=queryset)
#         b.set_avco_multiplier()
#         self._print_test_name()
#         self._print_ml_transactions(b.transactions)
#         self._assertMultipliers(b.transactions, multiplier_attr='avco_multiplier',
#                                 exp_multiplier_value={
#                                     self.t_buy1.pk: 0.25,
#                                     self.t_buy1_acc2.pk: 0.5,
#                                     self.t_buy1_p2.pk: 0.25,
#                                     self.t_sell1.pk: 1.0,
#                                     self.t_sell1_acc2.pk: 1.0,
#                                 },
#                                 exp_rolling_position={
#                                     self.t_buy1.pk: 100,
#                                     self.t_buy1_acc2.pk: 100,
#                                     self.t_buy1_p2.pk: 200,
#                                     self.t_sell1.pk: 150,
#                                     self.t_sell1_acc2.pk: 50,
#                                 })
#
#     def test_avco_protf_acc(self):
#         queryset = Transaction.objects.filter(pk__in=[
#             self.t_buy1.pk, self.t_buy1_acc2.pk, self.t_buy1_p2.pk,
#             self.t_sell1.pk, self.t_sell1_acc2.pk,
#         ])
#         instance = PLReport(master_user=self.m,
#                             begin_date=None, end_date=date(2016, 3, 10),
#                             use_portfolio=True, use_account=True)
#         b = PLReport2Builder(instance=instance, queryset=queryset)
#         b.set_avco_multiplier()
#         self._print_test_name()
#         self._print_ml_transactions(b.transactions)
#         self._assertMultipliers(b.transactions, multiplier_attr='avco_multiplier',
#                                 exp_multiplier_value={
#                                     self.t_buy1.pk: 0.5,
#                                     self.t_buy1_acc2.pk: 0.5,
#                                     self.t_buy1_p2.pk: 0.0,
#                                     self.t_sell1.pk: 1.0,
#                                     self.t_sell1_acc2.pk: 1.0,
#                                 },
#                                 exp_rolling_position={
#                                     self.t_buy1.pk: 100,
#                                     self.t_buy1_acc2.pk: 100,
#                                     self.t_buy1_p2.pk: 100,
#                                     self.t_sell1.pk: 50,
#                                     self.t_sell1_acc2.pk: 50,
#                                 })
#
#     def test_fifo(self):
#         queryset = Transaction.objects.filter(pk__in=[
#             self.t_buy1.pk, self.t_buy1_acc2.pk, self.t_buy1_p2.pk,
#             self.t_sell1.pk, self.t_sell1_acc2.pk,
#         ])
#         instance = PLReport(master_user=self.m,
#                             begin_date=None, end_date=date(2016, 3, 10),
#                             use_portfolio=False, use_account=False)
#         b = PLReport2Builder(instance=instance, queryset=queryset)
#         b.set_fifo_multiplier()
#         self._print_test_name()
#         self._print_ml_transactions(b.transactions)
#         self._assertMultipliers(b.transactions, multiplier_attr='fifo_multiplier',
#                                 exp_multiplier_value={
#                                     self.t_buy1.pk: 1.0,
#                                     self.t_buy1_acc2.pk: 0.0,
#                                     self.t_buy1_p2.pk: 0.,
#                                     self.t_sell1.pk: 1.0,
#                                     self.t_sell1_acc2.pk: 1.0,
#                                 },
#                                 exp_rolling_position={
#                                     self.t_buy1.pk: 100,
#                                     self.t_buy1_acc2.pk: 200,
#                                     self.t_buy1_p2.pk: 300,
#                                     self.t_sell1.pk: 250,
#                                     self.t_sell1_acc2.pk: 200,
#                                 })
#
#     def test_fifo_infuture(self):
#         queryset = Transaction.objects.filter(pk__in=[
#             self.t_sell1.pk, self.t_buy1_infuture.pk,
#         ])
#         instance = PLReport(master_user=self.m,
#                             begin_date=None, end_date=date(2016, 4, 10),
#                             use_portfolio=False, use_account=False)
#         b = PLReport2Builder(instance=instance, queryset=queryset)
#         b.set_fifo_multiplier()
#         self._print_test_name()
#         self._print_ml_transactions(b.transactions)
#         self._assertMultipliers(b.transactions, multiplier_attr='fifo_multiplier',
#                                 exp_multiplier_value={
#                                     self.t_sell1.pk: 1.0,
#                                     self.t_buy1_infuture.pk: 0.5,
#                                 },
#                                 exp_rolling_position={
#                                     self.t_sell1.pk: -50,
#                                     self.t_buy1_infuture.pk: 50,
#                                 })
#
#     def test_fifo_acc(self):
#         queryset = Transaction.objects.filter(pk__in=[
#             self.t_buy1.pk, self.t_buy1_acc2.pk, self.t_buy1_p2.pk,
#             self.t_sell1.pk, self.t_sell1_acc2.pk,
#         ])
#         instance = PLReport(master_user=self.m,
#                             begin_date=None, end_date=date(2016, 3, 10),
#                             use_portfolio=False, use_account=True)
#         b = PLReport2Builder(instance=instance, queryset=queryset)
#         b.set_fifo_multiplier()
#         self._print_test_name()
#         self._print_ml_transactions(b.transactions)
#         self._assertMultipliers(b.transactions, multiplier_attr='fifo_multiplier',
#                                 exp_multiplier_value={
#                                     self.t_buy1.pk: 0.5,
#                                     self.t_buy1_acc2.pk: 0.5,
#                                     self.t_buy1_p2.pk: 0.,
#                                     self.t_sell1.pk: 1.0,
#                                     self.t_sell1_acc2.pk: 1.0,
#                                 },
#                                 exp_rolling_position={
#                                     self.t_buy1.pk: 100,
#                                     self.t_buy1_acc2.pk: 100,
#                                     self.t_buy1_p2.pk: 200,
#                                     self.t_sell1.pk: 150,
#                                     self.t_sell1_acc2.pk: 50,
#                                 })
#
#     def test_fifo_portf_acc(self):
#         queryset = Transaction.objects.filter(pk__in=[
#             self.t_buy1.pk, self.t_buy1_acc2.pk, self.t_buy1_p2.pk,
#             self.t_sell1_acc2.pk, self.t_sell1_p2.pk
#         ])
#         instance = PLReport(master_user=self.m,
#                             begin_date=None, end_date=date(2016, 3, 10),
#                             use_portfolio=True, use_account=True)
#         b = PLReport2Builder(instance=instance, queryset=queryset)
#         b.set_fifo_multiplier()
#         self._print_test_name()
#         self._print_ml_transactions(b.transactions)
#         self._assertMultipliers(b.transactions, multiplier_attr='fifo_multiplier',
#                                 exp_multiplier_value={
#                                     self.t_buy1.pk: 0.,
#                                     self.t_buy1_acc2.pk: 0.5,
#                                     self.t_buy1_p2.pk: 0.5,
#                                     self.t_sell1_acc2.pk: 1.0,
#                                     self.t_sell1_p2.pk: 1.0,
#                                 },
#                                 exp_rolling_position={
#                                     self.t_buy1.pk: 100,
#                                     self.t_buy1_acc2.pk: 100,
#                                     self.t_buy1_p2.pk: 100,
#                                     self.t_sell1_acc2.pk: 50,
#                                     self.t_sell1_p2.pk: 50,
#                                 })
