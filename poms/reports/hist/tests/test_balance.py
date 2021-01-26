# from __future__ import unicode_literals, division, print_function
#
# from poms.instruments.models import CostMethod
# from poms.reports.hist.backends.balance import BalanceReport2Builder
# from poms.reports.hist.tests.base import BaseReportTestCase, n
# from poms.reports.models import BalanceReport, BalanceReportItem, BalanceReportSummary
# from poms.transactions.models import Transaction
#
#
# class BalanceTestCase(BaseReportTestCase):
#     def _print_balance_transactions(self, transactions, *columns):
#         self._print_transactions(transactions,
#                                  'pk',
#                                  'transaction_class',
#                                  'accounting_date', 'cash_date',
#                                  'portfolio',
#                                  'instrument', 'transaction_currency', 'position_size_with_sign',
#                                  'settlement_currency', 'cash_consideration',
#                                  'account_position', 'account_cash', 'account_interim',
#                                  'strategy1_position', 'strategy1_cash',
#                                  'strategy2_position', 'strategy2_cash',
#                                  'strategy3_position', 'strategy3_cash',
#                                  'avco_multiplier',
#                                  'fifo_multiplier',
#                                  'reference_fx_rate')
#
#     def _print_balance(self, instance):
#         columns = ['pk', 'portfolio', 'account', 'strategy1', 'strategy2', 'strategy3', 'instrument', 'currency',
#                    'position', 'market_value',
#                    'transaction']
#         data = []
#         for i in instance.items:
#             data.append([
#                 i.pk,
#                 getattr(i.portfolio, 'name', None),
#                 getattr(i.account, 'name', None),
#                 getattr(i.strategy1, 'name', None),
#                 getattr(i.strategy2, 'name', None),
#                 getattr(i.strategy3, 'name', None),
#                 getattr(i.instrument, 'name', None),
#                 getattr(i.currency, 'name', None),
#                 i.balance_position,
#                 i.market_value_system_ccy,
#                 i.transaction,
#             ])
#         print('*' * 79)
#         print('Positions')
#         # print(pd.DataFrame(data=data, columns=columns))
#         self._print_table(data=data, columns=columns)
#
#         print('-' * 79)
#         print('Summary')
#         # print(pd.DataFrame(
#         #     data=[[instance.summary.invested_value_system_ccy, instance.summary.current_value_system_ccy,
#         #            instance.summary.p_l_system_ccy], ],
#         #     columns=['invested_value_system_ccy', 'current_value_system_ccy', 'p_l_system_ccy']))
#         self._print_table(
#             data=[[instance.summary.invested_value_system_ccy, instance.summary.current_value_system_ccy,
#                    instance.summary.p_l_system_ccy]],
#             columns=['invested_value_system_ccy', 'current_value_system_ccy', 'p_l_system_ccy'])
#
#     def _assertEqualBalance(self, result, expected):
#         self.assertEqual(len(result.items), len(expected.items), 'len items')
#
#         r_expected = {i.pk: i for i in expected.items}
#
#         for i, ri in enumerate(result.items):
#             ei = r_expected.pop(ri.pk)
#
#             self.assertEqual(ri.portfolio, ei.portfolio, 'portfolio: id=%s, index=%s' % (ri.pk, i))
#             self.assertEqual(ri.account, ei.account, 'account: id=%s, index=%s' % (ri.pk, i))
#             self.assertEqual(ri.instrument, ei.instrument, 'instrument: id=%s, index=%s' % (ri.pk, i))
#             self.assertEqual(ri.currency, ei.currency, 'currency: id=%s, index=%s' % (ri.pk, i))
#
#             # self.assertEqual(ri.strategies, ei.strategies, 'strategies: id=%s, index=%s' % (ri.pk, i))
#             self.assertEqual(ri.strategy1, ei.strategy1, 'strategy1: id=%s, index=%s' % (ri.pk, i))
#             self.assertEqual(ri.strategy2, ei.strategy2, 'strategy2: id=%s, index=%s' % (ri.pk, i))
#             self.assertEqual(ri.strategy3, ei.strategy3, 'strategy3: id=%s, index=%s' % (ri.pk, i))
#
#             self.assertEqual(n(ri.balance_position), n(ei.balance_position),
#                              'balance_position: id=%s, index=%s' % (ri.pk, i))
#             self.assertEqual(n(ri.market_value_system_ccy), n(ei.market_value_system_ccy),
#                              'market_value_system_ccy: id=%s, index=%s' % (ri.pk, i))
#
#         self.assertEqual(n(result.summary.invested_value_system_ccy), n(expected.summary.invested_value_system_ccy),
#                          'invested_value_system_ccy')
#         self.assertEqual(n(result.summary.current_value_system_ccy), n(expected.summary.current_value_system_ccy),
#                          'current_value_system_ccy')
#         self.assertEqual(n(result.summary.p_l_system_ccy), n(expected.summary.p_l_system_ccy),
#                          'p_l_system_ccy')
#
#     def test_simple(self):
#         queryset = Transaction.objects.filter(pk__in=self.simple)
#         instance = BalanceReport(master_user=self.m,
#                                  begin_date=None, end_date=self.d(9),
#                                  use_portfolio=False, use_account=False,
#                                  show_transaction_details=False)
#         b = BalanceReport2Builder(instance=instance, queryset=queryset)
#         b.build()
#         self._print_test_name()
#         self._print_balance_transactions(instance.transactions)
#         self._print_balance(instance)
#         self._assertEqualBalance(instance, BalanceReport(
#             items=[
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=self.acc1, instrument=self.instr1_bond_chf,
#                                                 currency=None),
#                                   portfolio=None, account=None, instrument=self.instr1_bond_chf, currency=None,
#                                   balance_position=100.000000, market_value_system_ccy=18.450000),
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=None, instrument=self.instr2_stock,
#                                                 currency=None),
#                                   portfolio=None, account=None, instrument=self.instr2_stock, currency=None,
#                                   balance_position=-200.000000, market_value_system_ccy=-485.333333),
#
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=None, instrument=None, currency=self.usd),
#                                   portfolio=None, account=None, instrument=None, currency=self.usd,
#                                   balance_position=-200.000000, market_value_system_ccy=-200.000000),
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=None, instrument=None, currency=self.rub),
#                                   portfolio=None, account=None, instrument=None, currency=self.rub,
#                                   balance_position=0.000000, market_value_system_ccy=0.000000),
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=None, instrument=None, currency=self.eur),
#                                   portfolio=None, account=None, instrument=None, currency=self.eur,
#                                   balance_position=1000.000000, market_value_system_ccy=1300.000000),
#             ],
#             summary=BalanceReportSummary(invested_value_system_ccy=1286.666667,
#                                          current_value_system_ccy=633.116667,
#                                          p_l_system_ccy=-653.550000)
#         ))
#
#     def test_simple_accs(self):
#         queryset = Transaction.objects.filter(pk__in=self.simple)
#         instance = BalanceReport(master_user=self.m,
#                                  begin_date=None, end_date=self.d(14),
#                                  use_portfolio=False, use_account=True,
#                                  show_transaction_details=False)
#         b = BalanceReport2Builder(instance=instance, queryset=queryset)
#         b.build()
#         self._print_test_name()
#         self._print_balance_transactions(instance.transactions)
#         self._print_balance(instance)
#         self._assertEqualBalance(instance, BalanceReport(
#             items=[
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=self.acc1, instrument=self.instr1_bond_chf,
#                                                 currency=None),
#                                   portfolio=None, account=self.acc1, instrument=self.instr1_bond_chf, currency=None,
#                                   balance_position=100.000000, market_value_system_ccy=18.450000),
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=self.acc1, instrument=self.instr2_stock,
#                                                 currency=None),
#                                   portfolio=None, account=self.acc1, instrument=self.instr2_stock, currency=None,
#                                   balance_position=-200.000000, market_value_system_ccy=-485.333333),
#
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=self.acc1, instrument=None, currency=self.usd),
#                                   portfolio=None, account=self.acc1, instrument=None, currency=self.usd,
#                                   balance_position=-200.000000, market_value_system_ccy=-200.000000),
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=self.acc1, instrument=None, currency=self.rub),
#                                   portfolio=None, account=self.acc1, instrument=None, currency=self.rub,
#                                   balance_position=0.000000, market_value_system_ccy=0.000000),
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=self.acc1, instrument=None, currency=self.eur),
#                                   portfolio=None, account=self.acc1, instrument=None, currency=self.eur,
#                                   balance_position=1000.000000, market_value_system_ccy=1300.000000),
#             ],
#             summary=BalanceReportSummary(invested_value_system_ccy=1286.666667,
#                                          current_value_system_ccy=633.116667,
#                                          p_l_system_ccy=-653.550000)
#         ))
#
#     def test_simple_portf_accs(self):
#         queryset = Transaction.objects.filter(pk__in=self.simple)
#         instance = BalanceReport(master_user=self.m,
#                                  begin_date=None, end_date=self.d(14),
#                                  use_portfolio=True, use_account=True,
#                                  show_transaction_details=False)
#         b = BalanceReport2Builder(instance=instance, queryset=queryset)
#         b.build()
#         self._print_test_name()
#         self._print_balance_transactions(instance.transactions)
#         self._print_balance(instance)
#         self._assertEqualBalance(instance, BalanceReport(
#             items=[
#                 BalanceReportItem(pk=b.make_key(portfolio=self.p1, account=self.acc1, instrument=self.instr1_bond_chf,
#                                                 currency=None),
#                                   portfolio=self.p1, account=self.acc1, instrument=self.instr1_bond_chf, currency=None,
#                                   balance_position=100.000000, market_value_system_ccy=18.450000),
#                 BalanceReportItem(pk=b.make_key(portfolio=self.p1, account=self.acc1, instrument=self.instr2_stock,
#                                                 currency=None),
#                                   portfolio=self.p1, account=self.acc1, instrument=self.instr2_stock, currency=None,
#                                   balance_position=-200.000000, market_value_system_ccy=-485.333333),
#
#                 BalanceReportItem(pk=b.make_key(portfolio=self.p1, account=self.acc1, instrument=None,
#                                                 currency=self.usd),
#                                   portfolio=self.p1, account=self.acc1, instrument=None, currency=self.usd,
#                                   balance_position=-200.000000, market_value_system_ccy=-200.000000),
#                 BalanceReportItem(pk=b.make_key(portfolio=self.p1, account=self.acc1, instrument=None,
#                                                 currency=self.rub),
#                                   portfolio=self.p1, account=self.acc1, instrument=None, currency=self.rub,
#                                   balance_position=0.000000, market_value_system_ccy=0.000000),
#                 BalanceReportItem(pk=b.make_key(portfolio=self.p1, account=self.acc1, instrument=None,
#                                                 currency=self.eur),
#                                   portfolio=self.p1, account=self.acc1, instrument=None, currency=self.eur,
#                                   balance_position=1000.000000, market_value_system_ccy=1300.000000),
#             ],
#             summary=BalanceReportSummary(invested_value_system_ccy=1286.666667,
#                                          current_value_system_ccy=633.116667,
#                                          p_l_system_ccy=-653.550000)
#         ))
#
#     def test_trnpl(self):
#         queryset = Transaction.objects.filter(pk__in=self.simple_w_trnpl)
#         instance = BalanceReport(master_user=self.m,
#                                  begin_date=None, end_date=self.d(14),
#                                  use_portfolio=False, use_account=False,
#                                  show_transaction_details=False)
#         b = BalanceReport2Builder(instance=instance, queryset=queryset)
#         b.build()
#         self._print_test_name()
#         self._print_balance_transactions(instance.transactions)
#         self._print_balance(instance)
#         self._assertEqualBalance(instance, BalanceReport(
#             items=[
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=self.acc1, instrument=self.instr1_bond_chf,
#                                                 currency=None),
#                                   portfolio=None, account=None, instrument=self.instr1_bond_chf, currency=None,
#                                   balance_position=100.000000, market_value_system_ccy=18.450000),
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=None, instrument=self.instr2_stock,
#                                                 currency=None),
#                                   portfolio=None, account=None, instrument=self.instr2_stock, currency=None,
#                                   balance_position=-200.000000, market_value_system_ccy=-485.333333),
#
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=None, instrument=None, currency=self.usd),
#                                   portfolio=None, account=None, instrument=None, currency=self.usd,
#                                   balance_position=-200.000000, market_value_system_ccy=-200.000000),
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=None, instrument=None, currency=self.eur),
#                                   portfolio=None, account=None, instrument=None, currency=self.eur,
#                                   balance_position=1000.000000, market_value_system_ccy=1300.000000),
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=None, instrument=None, currency=self.chf),
#                                   portfolio=None, account=None, instrument=None, currency=self.chf,
#                                   balance_position=30.000000, market_value_system_ccy=27.000000),
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=None, instrument=None, currency=self.rub),
#                                   portfolio=None, account=None, instrument=None, currency=self.rub,
#                                   balance_position=-1000.000000, market_value_system_ccy=-13.333333),
#             ],
#             summary=BalanceReportSummary(invested_value_system_ccy=1286.666667,
#                                          current_value_system_ccy=646.783333,
#                                          p_l_system_ccy=-639.883333)
#         ))
#
#     def test_trnpl_acc(self):
#         queryset = Transaction.objects.filter(pk__in=self.simple_w_trnpl)
#         instance = BalanceReport(master_user=self.m,
#                                  begin_date=None, end_date=self.d(14),
#                                  use_portfolio=False, use_account=True,
#                                  show_transaction_details=False)
#         b = BalanceReport2Builder(instance=instance, queryset=queryset)
#         b.build()
#         self._print_test_name()
#         self._print_balance_transactions(instance.transactions)
#         self._print_balance(instance)
#         self._assertEqualBalance(instance, BalanceReport(
#             items=[
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=self.acc1, instrument=self.instr1_bond_chf,
#                                                 currency=None),
#                                   portfolio=None, account=self.acc1, instrument=self.instr1_bond_chf, currency=None,
#                                   balance_position=100.000000, market_value_system_ccy=18.450000),
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=self.acc1, instrument=self.instr2_stock,
#                                                 currency=None),
#                                   portfolio=None, account=self.acc1, instrument=self.instr2_stock, currency=None,
#                                   balance_position=-200.000000, market_value_system_ccy=-485.333333),
#
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=self.acc1, instrument=None, currency=self.usd),
#                                   portfolio=None, account=self.acc1, instrument=None, currency=self.usd,
#                                   balance_position=-200.000000, market_value_system_ccy=-200.000000),
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=self.acc1, instrument=None, currency=self.eur),
#                                   portfolio=None, account=self.acc1, instrument=None, currency=self.eur,
#                                   balance_position=1000.000000, market_value_system_ccy=1300.000000),
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=self.acc1, instrument=None, currency=self.chf),
#                                   portfolio=None, account=self.acc1, instrument=None, currency=self.chf,
#                                   balance_position=30.000000, market_value_system_ccy=27.000000),
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=self.acc1, instrument=None, currency=self.rub),
#                                   portfolio=None, account=self.acc1, instrument=None, currency=self.rub,
#                                   balance_position=-1000.000000, market_value_system_ccy=-13.333333),
#             ],
#             summary=BalanceReportSummary(invested_value_system_ccy=1286.666667,
#                                          current_value_system_ccy=646.783333,
#                                          p_l_system_ccy=-639.883333)
#         ))
#
#     def test_trnpl_portf_acc(self):
#         queryset = Transaction.objects.filter(pk__in=self.simple_w_trnpl)
#         instance = BalanceReport(master_user=self.m,
#                                  begin_date=None, end_date=self.d(14),
#                                  use_portfolio=True, use_account=True,
#                                  show_transaction_details=False)
#         b = BalanceReport2Builder(instance=instance, queryset=queryset)
#         b.build()
#         self._print_test_name()
#         self._print_balance_transactions(instance.transactions)
#         self._print_balance(instance)
#         self._assertEqualBalance(instance, BalanceReport(
#             items=[
#                 BalanceReportItem(pk=b.make_key(portfolio=self.p1, account=self.acc1, instrument=self.instr1_bond_chf,
#                                                 currency=None),
#                                   portfolio=self.p1, account=self.acc1, instrument=self.instr1_bond_chf, currency=None,
#                                   balance_position=100.000000, market_value_system_ccy=18.450000),
#                 BalanceReportItem(pk=b.make_key(portfolio=self.p1, account=self.acc1, instrument=self.instr2_stock,
#                                                 currency=None),
#                                   portfolio=self.p1, account=self.acc1, instrument=self.instr2_stock, currency=None,
#                                   balance_position=-200.000000, market_value_system_ccy=-485.333333),
#
#                 BalanceReportItem(pk=b.make_key(portfolio=self.p1, account=self.acc1, instrument=None,
#                                                 currency=self.usd),
#                                   portfolio=self.p1, account=self.acc1, instrument=None, currency=self.usd,
#                                   balance_position=-200.000000, market_value_system_ccy=-200.000000),
#                 BalanceReportItem(pk=b.make_key(portfolio=self.p1, account=self.acc1, instrument=None,
#                                                 currency=self.eur),
#                                   portfolio=self.p1, account=self.acc1, instrument=None, currency=self.eur,
#                                   balance_position=1000.000000, market_value_system_ccy=1300.000000),
#                 BalanceReportItem(pk=b.make_key(portfolio=self.p1, account=self.acc1, instrument=None,
#                                                 currency=self.chf),
#                                   portfolio=self.p1, account=self.acc1, instrument=None, currency=self.chf,
#                                   balance_position=30.000000, market_value_system_ccy=27.000000),
#                 BalanceReportItem(pk=b.make_key(portfolio=self.p1, account=self.acc1, instrument=None,
#                                                 currency=self.rub),
#                                   portfolio=self.p1, account=self.acc1, instrument=None, currency=self.rub,
#                                   balance_position=-1000.000000, market_value_system_ccy=-13.333333),
#             ],
#             summary=BalanceReportSummary(invested_value_system_ccy=1286.666667,
#                                          current_value_system_ccy=646.783333,
#                                          p_l_system_ccy=-639.883333)
#         ))
#
#     def test_fxtrade(self):
#         queryset = Transaction.objects.filter(pk__in=self.simple_w_fxtrade)
#         instance = BalanceReport(master_user=self.m,
#                                  begin_date=None, end_date=self.d(14),
#                                  use_portfolio=False, use_account=False,
#                                  show_transaction_details=False)
#         b = BalanceReport2Builder(instance=instance, queryset=queryset)
#         b.build()
#         self._print_test_name()
#         self._print_balance_transactions(instance.transactions)
#         self._print_balance(instance)
#         self._assertEqualBalance(instance, BalanceReport(
#             items=[
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=self.acc1, instrument=self.instr1_bond_chf,
#                                                 currency=None),
#                                   portfolio=None, account=None, instrument=self.instr1_bond_chf, currency=None,
#                                   balance_position=100.000000, market_value_system_ccy=18.450000),
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=None, instrument=self.instr2_stock,
#                                                 currency=None),
#                                   portfolio=None, account=None, instrument=self.instr2_stock, currency=None,
#                                   balance_position=-200.000000, market_value_system_ccy=-485.333333),
#
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=None, instrument=None, currency=self.usd),
#                                   portfolio=None, account=None, instrument=None, currency=self.usd,
#                                   balance_position=-200.000000, market_value_system_ccy=-200.000000),
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=None, instrument=None, currency=self.eur),
#                                   portfolio=None, account=None, instrument=None, currency=self.eur,
#                                   balance_position=1000.000000, market_value_system_ccy=1300.000000),
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=None, instrument=None, currency=self.chf),
#                                   portfolio=None, account=None, instrument=None, currency=self.chf,
#                                   balance_position=30.000000, market_value_system_ccy=27.000000),
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=None, instrument=None, currency=self.rub),
#                                   portfolio=None, account=None, instrument=None, currency=self.rub,
#                                   balance_position=-1000.000000, market_value_system_ccy=-13.333333),
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=None, instrument=None, currency=self.cad),
#                                   portfolio=None, account=None, instrument=None, currency=self.cad,
#                                   balance_position=80.000000, market_value_system_ccy=96.000000),
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=None, instrument=None, currency=self.mex),
#                                   portfolio=None, account=None, instrument=None, currency=self.mex,
#                                   balance_position=-150.000000, market_value_system_ccy=-22.500000),
#             ],
#             summary=BalanceReportSummary(invested_value_system_ccy=1286.666667,
#                                          current_value_system_ccy=720.283333,
#                                          p_l_system_ccy=-566.383333)
#         ))
#
#     def test_fxtrade_acc(self):
#         queryset = Transaction.objects.filter(pk__in=self.simple_w_fxtrade)
#         instance = BalanceReport(master_user=self.m,
#                                  begin_date=None, end_date=self.d(14),
#                                  use_portfolio=False, use_account=True,
#                                  show_transaction_details=False)
#         b = BalanceReport2Builder(instance=instance, queryset=queryset)
#         b.build()
#         self._print_test_name()
#         self._print_balance_transactions(instance.transactions)
#         self._print_balance(instance)
#         self._assertEqualBalance(instance, BalanceReport(
#             items=[
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=self.acc1, instrument=self.instr1_bond_chf,
#                                                 currency=None),
#                                   portfolio=None, account=self.acc1, instrument=self.instr1_bond_chf, currency=None,
#                                   balance_position=100.000000, market_value_system_ccy=18.450000),
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=self.acc1, instrument=self.instr2_stock,
#                                                 currency=None),
#                                   portfolio=None, account=self.acc1, instrument=self.instr2_stock, currency=None,
#                                   balance_position=-200.000000, market_value_system_ccy=-485.333333),
#
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=self.acc1, instrument=None, currency=self.usd),
#                                   portfolio=None, account=self.acc1, instrument=None, currency=self.usd,
#                                   balance_position=-200.000000, market_value_system_ccy=-200.000000),
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=self.acc1, instrument=None, currency=self.eur),
#                                   portfolio=None, account=self.acc1, instrument=None, currency=self.eur,
#                                   balance_position=1000.000000, market_value_system_ccy=1300.000000),
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=self.acc1, instrument=None, currency=self.chf),
#                                   portfolio=None, account=self.acc1, instrument=None, currency=self.chf,
#                                   balance_position=30.000000, market_value_system_ccy=27.000000),
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=self.acc1, instrument=None, currency=self.rub),
#                                   portfolio=None, account=self.acc1, instrument=None, currency=self.rub,
#                                   balance_position=-1000.000000, market_value_system_ccy=-13.333333),
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=self.acc1, instrument=None, currency=self.cad),
#                                   portfolio=None, account=self.acc1, instrument=None, currency=self.cad,
#                                   balance_position=80.000000, market_value_system_ccy=96.000000),
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=self.acc1, instrument=None, currency=self.mex),
#                                   portfolio=None, account=self.acc1, instrument=None, currency=self.mex,
#                                   balance_position=-150.000000, market_value_system_ccy=-22.500000),
#             ],
#             summary=BalanceReportSummary(invested_value_system_ccy=1286.666667,
#                                          current_value_system_ccy=720.283333,
#                                          p_l_system_ccy=-566.383333)
#         ))
#
#     def test_fxtrade_portf_acc(self):
#         queryset = Transaction.objects.filter(pk__in=self.simple_w_fxtrade)
#         instance = BalanceReport(master_user=self.m,
#                                  begin_date=None, end_date=self.d(14),
#                                  use_portfolio=True, use_account=True,
#                                  show_transaction_details=False)
#         b = BalanceReport2Builder(instance=instance, queryset=queryset)
#         b.build()
#         self._print_test_name()
#         self._print_balance_transactions(instance.transactions)
#         self._print_balance(instance)
#         self._assertEqualBalance(instance, BalanceReport(
#             items=[
#                 BalanceReportItem(pk=b.make_key(portfolio=self.p1, account=self.acc1, instrument=self.instr1_bond_chf,
#                                                 currency=None),
#                                   portfolio=self.p1, account=self.acc1, instrument=self.instr1_bond_chf, currency=None,
#                                   balance_position=100.000000, market_value_system_ccy=18.450000),
#                 BalanceReportItem(pk=b.make_key(portfolio=self.p1, account=self.acc1, instrument=self.instr2_stock,
#                                                 currency=None),
#                                   portfolio=self.p1, account=self.acc1, instrument=self.instr2_stock, currency=None,
#                                   balance_position=-200.000000, market_value_system_ccy=-485.333333),
#
#                 BalanceReportItem(pk=b.make_key(portfolio=self.p1, account=self.acc1, instrument=None,
#                                                 currency=self.usd),
#                                   portfolio=self.p1, account=self.acc1, instrument=None, currency=self.usd,
#                                   balance_position=-200.000000, market_value_system_ccy=-200.000000),
#                 BalanceReportItem(pk=b.make_key(portfolio=self.p1, account=self.acc1, instrument=None,
#                                                 currency=self.eur),
#                                   portfolio=self.p1, account=self.acc1, instrument=None, currency=self.eur,
#                                   balance_position=1000.000000, market_value_system_ccy=1300.000000),
#                 BalanceReportItem(pk=b.make_key(portfolio=self.p1, account=self.acc1, instrument=None,
#                                                 currency=self.chf),
#                                   portfolio=self.p1, account=self.acc1, instrument=None, currency=self.chf,
#                                   balance_position=30.000000, market_value_system_ccy=27.000000),
#                 BalanceReportItem(pk=b.make_key(portfolio=self.p1, account=self.acc1, instrument=None,
#                                                 currency=self.rub),
#                                   portfolio=self.p1, account=self.acc1, instrument=None, currency=self.rub,
#                                   balance_position=-1000.000000, market_value_system_ccy=-13.333333),
#                 BalanceReportItem(pk=b.make_key(portfolio=self.p1, account=self.acc1, instrument=None,
#                                                 currency=self.cad),
#                                   portfolio=self.p1, account=self.acc1, instrument=None, currency=self.cad,
#                                   balance_position=80.000000, market_value_system_ccy=96.000000),
#                 BalanceReportItem(pk=b.make_key(portfolio=self.p1, account=self.acc1, instrument=None,
#                                                 currency=self.mex),
#                                   portfolio=self.p1, account=self.acc1, instrument=None, currency=self.mex,
#                                   balance_position=-150.000000, market_value_system_ccy=-22.500000),
#             ],
#             summary=BalanceReportSummary(invested_value_system_ccy=1286.666667,
#                                          current_value_system_ccy=720.283333,
#                                          p_l_system_ccy=-566.383333)
#         ))
#
#     def test_dates_case_1_2(self):
#         queryset = Transaction.objects.filter(pk__in=self.simple)
#         instance = BalanceReport(master_user=self.m,
#                                  begin_date=None, end_date=self.d(4),
#                                  use_portfolio=False, use_account=True,
#                                  show_transaction_details=False)
#         b = BalanceReport2Builder(instance=instance, queryset=queryset)
#         b.build()
#         self._print_test_name()
#         self._print_balance_transactions(instance.transactions)
#         self._print_balance(instance)
#         self._assertEqualBalance(instance, BalanceReport(
#             items=[
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=self.acc1, instrument=self.instr1_bond_chf,
#                                                 currency=None),
#                                   portfolio=None, account=self.acc1, instrument=self.instr1_bond_chf, currency=None,
#                                   balance_position=100.000000, market_value_system_ccy=18.450000),
#
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=self.acc1, instrument=None, currency=self.eur),
#                                   portfolio=None, account=self.acc1, instrument=None, currency=self.eur,
#                                   balance_position=1000.000000, market_value_system_ccy=1300.000000),
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=self.prov_acc1, instrument=None,
#                                                 currency=self.usd),
#                                   portfolio=None, account=self.prov_acc1, instrument=None, currency=self.usd,
#                                   balance_position=-200.000000, market_value_system_ccy=-200.000000),
#
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=self.acc1, instrument=None, currency=self.rub),
#                                   portfolio=None, account=self.acc1, instrument=None, currency=self.rub,
#                                   balance_position=1000.000000, market_value_system_ccy=13.333333),
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=self.prov_acc1, instrument=None,
#                                                 currency=self.rub),
#                                   portfolio=None, account=self.prov_acc1, instrument=None, currency=self.rub,
#                                   balance_position=-1000.000000, market_value_system_ccy=-13.333333),
#             ],
#             summary=BalanceReportSummary(invested_value_system_ccy=1300.000000,
#                                          current_value_system_ccy=1118.450000,
#                                          p_l_system_ccy=-181.55)
#         ))
#
#     def test_dates_case_1_2_show_transaction_details(self):
#         queryset = Transaction.objects.filter(pk__in=[
#             self.t_buy_bond.pk,
#             self.t_buy_bond_acc2.pk
#         ])
#         instance = BalanceReport(master_user=self.m,
#                                  begin_date=None, end_date=self.d(4),
#                                  use_portfolio=False, use_account=True,
#                                  show_transaction_details=True)
#         b = BalanceReport2Builder(instance=instance, queryset=queryset)
#         b.build()
#         self._print_test_name()
#         self._print_balance_transactions(instance.transactions)
#         self._print_balance(instance)
#         self._assertEqualBalance(instance, BalanceReport(
#             items=[
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=self.acc1, instrument=self.instr1_bond_chf,
#                                                 currency=None),
#                                   portfolio=None, account=self.acc1, instrument=self.instr1_bond_chf, currency=None,
#                                   balance_position=100.000000, market_value_system_ccy=18.450000),
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=self.acc2, instrument=self.instr1_bond_chf,
#                                                 currency=None),
#                                   portfolio=None, account=self.acc2, instrument=self.instr1_bond_chf, currency=None,
#                                   balance_position=100.000000, market_value_system_ccy=18.450000),
#
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=self.prov_acc1, instrument=None,
#                                                 currency=self.usd),
#                                   portfolio=None, account=self.prov_acc1, instrument=None, currency=self.usd,
#                                   balance_position=-200.000000, market_value_system_ccy=-200.000000),
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=self.prov_acc2, instrument=None,
#                                                 currency=self.usd, ext=self.t_buy_bond_acc2.pk),
#                                   portfolio=None, account=self.prov_acc2, instrument=None, currency=self.usd,
#                                   balance_position=-200.000000, market_value_system_ccy=-200.000000),
#             ],
#             summary=BalanceReportSummary(invested_value_system_ccy=0,
#                                          current_value_system_ccy=-363.1,
#                                          p_l_system_ccy=-363.1)
#         ))
#
#     def test_dates_case_1_2_over(self):
#         queryset = Transaction.objects.filter(pk__in=self.simple)
#         instance = BalanceReport(master_user=self.m,
#                                  begin_date=None, end_date=self.d(5),
#                                  use_portfolio=False, use_account=True,
#                                  show_transaction_details=False)
#         b = BalanceReport2Builder(instance=instance, queryset=queryset)
#         b.build()
#         self._print_test_name()
#         self._print_balance_transactions(instance.transactions)
#         self._print_balance(instance)
#         self._assertEqualBalance(instance, BalanceReport(
#             items=[
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=self.acc1, instrument=self.instr1_bond_chf,
#                                                 currency=None),
#                                   portfolio=None, account=self.acc1, instrument=self.instr1_bond_chf, currency=None,
#                                   balance_position=100.000000, market_value_system_ccy=18.450000),
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=self.acc1, instrument=self.instr2_stock,
#                                                 currency=None),
#                                   portfolio=None, account=self.acc1, instrument=self.instr2_stock, currency=None,
#                                   balance_position=-200.000000, market_value_system_ccy=-485.333333),
#
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=self.acc1, instrument=None, currency=self.eur),
#                                   portfolio=None, account=self.acc1, instrument=None, currency=self.eur,
#                                   balance_position=1000.000000, market_value_system_ccy=1300.000000),
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=self.acc1, instrument=None, currency=self.usd),
#                                   portfolio=None, account=self.acc1, instrument=None, currency=self.usd,
#                                   balance_position=-200.000000, market_value_system_ccy=-200.000000),
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=self.acc1, instrument=None, currency=self.rub),
#                                   portfolio=None, account=self.acc1, instrument=None, currency=self.rub,
#                                   balance_position=1000.000000, market_value_system_ccy=13.333333),
#             ],
#             summary=BalanceReportSummary(invested_value_system_ccy=1300.000000,
#                                          current_value_system_ccy=646.450000,
#                                          p_l_system_ccy=-653.550000)
#         ))
#
#     def test_multiple(self):
#         queryset = Transaction.objects.filter(pk__in=[
#             self.t_in.pk, self.t_buy_bond.pk, self.t_buy_bond_acc2.pk, self.t_buy_bond_p2.pk
#         ])
#         instance = BalanceReport(master_user=self.m,
#                                  begin_date=None, end_date=self.d(9),
#                                  use_portfolio=False, use_account=False,
#                                  show_transaction_details=False)
#         b = BalanceReport2Builder(instance=instance, queryset=queryset)
#         b.build()
#         self._print_test_name()
#         self._print_balance_transactions(instance.transactions)
#         self._print_balance(instance)
#         self._assertEqualBalance(instance, BalanceReport(
#             items=[
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=self.acc1, instrument=self.instr1_bond_chf,
#                                                 currency=None),
#                                   portfolio=None, account=None, instrument=self.instr1_bond_chf, currency=None,
#                                   balance_position=300.000000, market_value_system_ccy=55.350000),
#
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=None, instrument=None, currency=self.eur),
#                                   portfolio=None, account=None, instrument=None, currency=self.eur,
#                                   balance_position=1000.000000, market_value_system_ccy=1300.000000),
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=None, instrument=None, currency=self.usd),
#                                   portfolio=None, account=None, instrument=None, currency=self.usd,
#                                   balance_position=-600.000000, market_value_system_ccy=-600.000000),
#             ],
#             summary=BalanceReportSummary(invested_value_system_ccy=1300.,
#                                          current_value_system_ccy=755.350000,
#                                          p_l_system_ccy=-544.650000)
#         ))
#
#     def test_multiple_acc(self):
#         queryset = Transaction.objects.filter(pk__in=[
#             self.t_in.pk, self.t_buy_bond.pk, self.t_buy_bond_acc2.pk, self.t_buy_bond_p2.pk
#         ])
#         instance = BalanceReport(master_user=self.m,
#                                  begin_date=None, end_date=self.d(9),
#                                  use_portfolio=False, use_account=True,
#                                  show_transaction_details=False)
#         b = BalanceReport2Builder(instance=instance, queryset=queryset)
#         b.build()
#         self._print_test_name()
#         self._print_balance_transactions(instance.transactions)
#         self._print_balance(instance)
#         self._assertEqualBalance(instance, BalanceReport(
#             items=[
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=self.acc1, instrument=self.instr1_bond_chf,
#                                                 currency=None),
#                                   portfolio=None, account=self.acc1, instrument=self.instr1_bond_chf, currency=None,
#                                   balance_position=200.000000, market_value_system_ccy=36.900000),
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=self.acc2, instrument=self.instr1_bond_chf,
#                                                 currency=None),
#                                   portfolio=None, account=self.acc2, instrument=self.instr1_bond_chf, currency=None,
#                                   balance_position=100.000000, market_value_system_ccy=18.450000),
#
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=self.acc1, instrument=None, currency=self.eur),
#                                   portfolio=None, account=self.acc1, instrument=None, currency=self.eur,
#                                   balance_position=1000.000000, market_value_system_ccy=1300.000000),
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=self.acc1, instrument=None, currency=self.usd),
#                                   portfolio=None, account=self.acc1, instrument=None, currency=self.usd,
#                                   balance_position=-400.000000, market_value_system_ccy=-400.000000),
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=self.acc2, instrument=None, currency=self.usd),
#                                   portfolio=None, account=self.acc2, instrument=None, currency=self.usd,
#                                   balance_position=-200.000000, market_value_system_ccy=-200.000000),
#             ],
#             summary=BalanceReportSummary(invested_value_system_ccy=1300.,
#                                          current_value_system_ccy=755.350000,
#                                          p_l_system_ccy=-544.650000)
#         ))
#
#     def test_multiple_portf_acc(self):
#         queryset = Transaction.objects.filter(pk__in=[
#             self.t_in.pk, self.t_buy_bond.pk, self.t_buy_bond_acc2.pk, self.t_buy_bond_p2.pk
#         ])
#         instance = BalanceReport(master_user=self.m,
#                                  begin_date=None, end_date=self.d(9),
#                                  use_portfolio=True, use_account=True,
#                                  show_transaction_details=False)
#         b = BalanceReport2Builder(instance=instance, queryset=queryset)
#         b.build()
#         self._print_test_name()
#         self._print_balance_transactions(instance.transactions)
#         self._print_balance(instance)
#         self._assertEqualBalance(instance, BalanceReport(
#             items=[
#                 BalanceReportItem(pk=b.make_key(portfolio=self.p1, account=self.acc1, instrument=self.instr1_bond_chf,
#                                                 currency=None),
#                                   portfolio=self.p1, account=self.acc1, instrument=self.instr1_bond_chf, currency=None,
#                                   balance_position=100.000000, market_value_system_ccy=18.450000),
#                 BalanceReportItem(pk=b.make_key(portfolio=self.p1, account=self.acc2, instrument=self.instr1_bond_chf,
#                                                 currency=None),
#                                   portfolio=self.p1, account=self.acc2, instrument=self.instr1_bond_chf, currency=None,
#                                   balance_position=100.000000, market_value_system_ccy=18.450000),
#                 BalanceReportItem(pk=b.make_key(portfolio=self.p2, account=self.acc1, instrument=self.instr1_bond_chf,
#                                                 currency=None),
#                                   portfolio=self.p2, account=self.acc1, instrument=self.instr1_bond_chf, currency=None,
#                                   balance_position=100.000000, market_value_system_ccy=18.450000),
#
#                 BalanceReportItem(pk=b.make_key(portfolio=self.p1, account=self.acc1, instrument=None,
#                                                 currency=self.eur),
#                                   portfolio=self.p1, account=self.acc1, instrument=None, currency=self.eur,
#                                   balance_position=1000.000000, market_value_system_ccy=1300.000000),
#                 BalanceReportItem(pk=b.make_key(portfolio=self.p1, account=self.acc1, instrument=None,
#                                                 currency=self.usd),
#                                   portfolio=self.p1, account=self.acc1, instrument=None, currency=self.usd,
#                                   balance_position=-200.000000, market_value_system_ccy=-200.000000),
#                 BalanceReportItem(pk=b.make_key(portfolio=self.p1, account=self.acc2, instrument=None,
#                                                 currency=self.usd),
#                                   portfolio=self.p1, account=self.acc2, instrument=None, currency=self.usd,
#                                   balance_position=-200.000000, market_value_system_ccy=-200.000000),
#                 BalanceReportItem(pk=b.make_key(portfolio=self.p2, account=self.acc1, instrument=None,
#                                                 currency=self.usd),
#                                   portfolio=self.p2, account=self.acc1, instrument=None, currency=self.usd,
#                                   balance_position=-200.000000, market_value_system_ccy=-200.000000),
#             ],
#             summary=BalanceReportSummary(invested_value_system_ccy=1300.,
#                                          current_value_system_ccy=755.350000,
#                                          p_l_system_ccy=-544.650000)
#         ))
#
#     def test_multiple_portf_acc_case1(self):
#         queryset = Transaction.objects.filter(pk__in=[
#             self.t_in.pk, self.t_buy_bond.pk, self.t_buy_bond_acc2.pk, self.t_buy_bond_p2.pk
#         ])
#         instance = BalanceReport(master_user=self.m,
#                                  begin_date=None, end_date=self.d(4),
#                                  use_portfolio=True, use_account=True,
#                                  show_transaction_details=False)
#         b = BalanceReport2Builder(instance=instance, queryset=queryset)
#         b.build()
#         self._print_test_name()
#         self._print_balance_transactions(instance.transactions)
#         self._print_balance(instance)
#         self._assertEqualBalance(instance, BalanceReport(
#             items=[
#                 BalanceReportItem(pk=b.make_key(portfolio=self.p1, account=self.acc1, instrument=self.instr1_bond_chf,
#                                                 currency=None),
#                                   portfolio=self.p1, account=self.acc1, instrument=self.instr1_bond_chf, currency=None,
#                                   balance_position=100.000000, market_value_system_ccy=18.450000),
#                 BalanceReportItem(pk=b.make_key(portfolio=self.p1, account=self.acc2, instrument=self.instr1_bond_chf,
#                                                 currency=None),
#                                   portfolio=self.p1, account=self.acc2, instrument=self.instr1_bond_chf, currency=None,
#                                   balance_position=100.000000, market_value_system_ccy=18.450000),
#                 BalanceReportItem(pk=b.make_key(portfolio=self.p2, account=self.acc1, instrument=self.instr1_bond_chf,
#                                                 currency=None),
#                                   portfolio=self.p2, account=self.acc1, instrument=self.instr1_bond_chf, currency=None,
#                                   balance_position=100.000000, market_value_system_ccy=18.450000),
#
#                 BalanceReportItem(pk=b.make_key(portfolio=self.p1, account=self.acc1, instrument=None,
#                                                 currency=self.eur),
#                                   portfolio=self.p1, account=self.acc1, instrument=None, currency=self.eur,
#                                   balance_position=1000.000000, market_value_system_ccy=1300.000000),
#                 BalanceReportItem(pk=b.make_key(portfolio=self.p1, account=self.prov_acc1, instrument=None,
#                                                 currency=self.usd),
#                                   portfolio=self.p1, account=self.prov_acc1, instrument=None, currency=self.usd,
#                                   balance_position=-200.000000, market_value_system_ccy=-200.000000),
#                 BalanceReportItem(pk=b.make_key(portfolio=self.p1, account=self.prov_acc2, instrument=None,
#                                                 currency=self.usd),
#                                   portfolio=self.p1, account=self.prov_acc2, instrument=None, currency=self.usd,
#                                   balance_position=-200.000000, market_value_system_ccy=-200.000000),
#                 BalanceReportItem(pk=b.make_key(portfolio=self.p2, account=self.prov_acc1, instrument=None,
#                                                 currency=self.usd),
#                                   portfolio=self.p2, account=self.prov_acc1, instrument=None, currency=self.usd,
#                                   balance_position=-200.000000, market_value_system_ccy=-200.000000),
#             ],
#             summary=BalanceReportSummary(invested_value_system_ccy=1300.,
#                                          current_value_system_ccy=755.350000,
#                                          p_l_system_ccy=-544.650000)
#         ))
#
#     def test_multiple_portf_acc_case2(self):
#         queryset = Transaction.objects.filter(pk__in=[
#             self.t_in.pk, self.t_sell_stock.pk, self.t_sell_stock_acc2.pk, self.t_sell_stock_p2.pk
#         ])
#         instance = BalanceReport(master_user=self.m,
#                                  begin_date=None, end_date=self.d(4),
#                                  use_portfolio=True, use_account=True,
#                                  show_transaction_details=False)
#         b = BalanceReport2Builder(instance=instance, queryset=queryset)
#         b.build()
#         self._print_test_name()
#         self._print_balance_transactions(instance.transactions)
#         self._print_balance(instance)
#         self._assertEqualBalance(instance, BalanceReport(
#             items=[
#                 BalanceReportItem(pk=b.make_key(portfolio=self.p1, account=self.acc1, instrument=None,
#                                                 currency=self.eur),
#                                   portfolio=self.p1, account=self.acc1, instrument=None, currency=self.eur,
#                                   balance_position=1000.000000, market_value_system_ccy=1300.000000),
#
#                 BalanceReportItem(pk=b.make_key(portfolio=self.p1, account=self.acc1, instrument=None,
#                                                 currency=self.rub),
#                                   portfolio=self.p1, account=self.acc1, instrument=None, currency=self.rub,
#                                   balance_position=1000.000000, market_value_system_ccy=13.333333),
#                 BalanceReportItem(pk=b.make_key(portfolio=self.p1, account=self.prov_acc1, instrument=None,
#                                                 currency=self.rub),
#                                   portfolio=self.p1, account=self.prov_acc1, instrument=None, currency=self.rub,
#                                   balance_position=-1000.000000, market_value_system_ccy=-13.333333),
#
#                 BalanceReportItem(pk=b.make_key(portfolio=self.p1, account=self.acc2, instrument=None,
#                                                 currency=self.rub),
#                                   portfolio=self.p1, account=self.acc2, instrument=None, currency=self.rub,
#                                   balance_position=1000.000000, market_value_system_ccy=13.333333),
#                 BalanceReportItem(pk=b.make_key(portfolio=self.p1, account=self.prov_acc2, instrument=None,
#                                                 currency=self.rub),
#                                   portfolio=self.p1, account=self.prov_acc2, instrument=None, currency=self.rub,
#                                   balance_position=-1000.000000, market_value_system_ccy=-13.333333),
#
#                 BalanceReportItem(pk=b.make_key(portfolio=self.p2, account=self.acc1, instrument=None,
#                                                 currency=self.rub),
#                                   portfolio=self.p2, account=self.acc1, instrument=None, currency=self.rub,
#                                   balance_position=1000.000000, market_value_system_ccy=13.333333),
#                 BalanceReportItem(pk=b.make_key(portfolio=self.p2, account=self.prov_acc1, instrument=None,
#                                                 currency=self.rub),
#                                   portfolio=self.p2, account=self.prov_acc1, instrument=None, currency=self.rub,
#                                   balance_position=-1000.000000, market_value_system_ccy=-13.333333),
#             ],
#             summary=BalanceReportSummary(invested_value_system_ccy=1300.000000,
#                                          current_value_system_ccy=1300.000000,
#                                          p_l_system_ccy=0.000000)
#         ))
#
#     def test_reference_fx_rate(self):
#         queryset = Transaction.objects.filter(pk__in=[
#             self.t_in.pk, self.t_in2.pk
#         ])
#         instance = BalanceReport(master_user=self.m,
#                                  begin_date=None, end_date=self.d(30),
#                                  use_portfolio=False, use_account=False,
#                                  show_transaction_details=False)
#         b = BalanceReport2Builder(instance=instance, queryset=queryset)
#         b.build()
#         self._print_test_name()
#         self._print_balance_transactions(instance.transactions)
#         self._print_balance(instance)
#         self._assertEqualBalance(instance, BalanceReport(
#             items=[
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=None, instrument=None, currency=self.eur),
#                                   portfolio=None, account=None, instrument=None, currency=self.eur,
#                                   balance_position=2000.000000, market_value_system_ccy=2700.000000),
#             ],
#             summary=BalanceReportSummary(invested_value_system_ccy=2700.,
#                                          current_value_system_ccy=2700.,
#                                          p_l_system_ccy=0.)
#         ))
#
#     def test_fx_trade_fx_rate_on_date(self):
#         queryset = Transaction.objects.filter(pk__in=[
#             self.t_fxtrade.pk, self.t_fxtrade2.pk
#         ])
#         instance = BalanceReport(master_user=self.m,
#                                  begin_date=None, end_date=self.d(60),
#                                  use_portfolio=False, use_account=False,
#                                  show_transaction_details=False)
#         b = BalanceReport2Builder(instance=instance, queryset=queryset)
#         b.build()
#         self._print_test_name()
#         self._print_balance_transactions(instance.transactions)
#         self._print_balance(instance)
#         self._assertEqualBalance(instance, BalanceReport(
#             items=[
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=None, instrument=None, currency=self.cad),
#                                   portfolio=None, account=None, instrument=None, currency=self.cad,
#                                   balance_position=160., market_value_system_ccy=176.),
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=None, instrument=None, currency=self.mex),
#                                   portfolio=None, account=None, instrument=None, currency=self.mex,
#                                   balance_position=-300, market_value_system_ccy=-30.),
#             ],
#             summary=BalanceReportSummary(invested_value_system_ccy=0,
#                                          current_value_system_ccy=146.,
#                                          p_l_system_ccy=146.)
#         ))
#
#     def test_transfer_sell_buy_case0(self):
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
#         instance = BalanceReport(master_user=self.m,
#                                  begin_date=None, end_date=self.d(4),
#                                  use_portfolio=False, use_account=True,
#                                  show_transaction_details=False)
#         b = BalanceReport2Builder(instance=instance, queryset=queryset)
#         b.build()
#         self._print_test_name()
#         self._print_balance_transactions(instance.transactions)
#         self._print_balance(instance)
#         self._assertEqualBalance(instance, BalanceReport(
#             items=[
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=self.acc2, instrument=self.instr1_bond_chf,
#                                                 currency=None),
#                                   portfolio=None, account=self.acc2, instrument=self.instr1_bond_chf, currency=None,
#                                   balance_position=-100.000000, market_value_system_ccy=-18.450000),
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=self.acc2, instrument=None, currency=self.eur),
#                                   portfolio=None, account=self.acc2, instrument=None, currency=self.eur,
#                                   balance_position=0.000000, market_value_system_ccy=0.00000),
#
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=self.acc1, instrument=self.instr1_bond_chf,
#                                                 currency=None),
#                                   portfolio=None, account=self.acc1, instrument=self.instr1_bond_chf, currency=None,
#                                   balance_position=100.000000, market_value_system_ccy=18.450000),
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=self.acc1, instrument=None, currency=self.eur),
#                                   portfolio=None, account=self.acc1, instrument=None, currency=self.eur,
#                                   balance_position=0.000000, market_value_system_ccy=0.00000),
#
#             ],
#             summary=BalanceReportSummary(invested_value_system_ccy=0,
#                                          current_value_system_ccy=0.,
#                                          p_l_system_ccy=0.)
#         ))
#
#     def test_transfer_buy_sell_case0(self):
#         trn = self.t(
#             t_class=self.transfer, instr=self.instr1_bond_chf, position=-100., settlement_ccy=self.eur,
#             cash_consideration=0., principal=-50., carry=-4., overheads=0.,
#             acc_date_delta=3., cash_date_delta=3.,
#             acc_cash=self.acc2, acc_pos=self.acc1,  # acc2 -> acc1
#             acc_interim=self.prov_acc1)
#
#         queryset = Transaction.objects.filter(pk__in=[
#             trn.pk
#         ])
#         instance = BalanceReport(master_user=self.m,
#                                  begin_date=None, end_date=self.d(4),
#                                  use_portfolio=False, use_account=True,
#                                  show_transaction_details=False)
#         b = BalanceReport2Builder(instance=instance, queryset=queryset)
#         b.build()
#         self._print_test_name()
#         self._print_balance_transactions(instance.transactions)
#         self._print_balance(instance)
#         self._assertEqualBalance(instance, BalanceReport(
#             items=[
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=self.acc1, instrument=self.instr1_bond_chf,
#                                                 currency=None),
#                                   portfolio=None, account=self.acc1, instrument=self.instr1_bond_chf, currency=None,
#                                   balance_position=-100.000000, market_value_system_ccy=-18.450000),
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=self.acc1, instrument=None, currency=self.eur),
#                                   portfolio=None, account=self.acc1, instrument=None, currency=self.eur,
#                                   balance_position=0.000000, market_value_system_ccy=0.00000),
#
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=self.acc2, instrument=self.instr1_bond_chf,
#                                                 currency=None),
#                                   portfolio=None, account=self.acc2, instrument=self.instr1_bond_chf, currency=None,
#                                   balance_position=100.000000, market_value_system_ccy=18.450000),
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=self.acc2, instrument=None, currency=self.eur),
#                                   portfolio=None, account=self.acc2, instrument=None, currency=self.eur,
#                                   balance_position=0.000000, market_value_system_ccy=0.00000),
#
#             ],
#             summary=BalanceReportSummary(invested_value_system_ccy=0,
#                                          current_value_system_ccy=0.,
#                                          p_l_system_ccy=0.)
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
#         instance = BalanceReport(master_user=self.m,
#                                  begin_date=None, end_date=self.d(4),
#                                  use_portfolio=False, use_account=True,
#                                  show_transaction_details=False)
#         b = BalanceReport2Builder(instance=instance, queryset=queryset)
#         b.build()
#         self._print_test_name()
#         self._print_balance_transactions(instance.transactions)
#         self._print_balance(instance)
#         self._assertEqualBalance(instance, BalanceReport(
#             items=[
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=self.acc1, instrument=None, currency=self.rub),
#                                   portfolio=None, account=self.acc1, instrument=None, currency=self.rub,
#                                   balance_position=1000., market_value_system_ccy=13.333333),
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=self.acc1, instrument=None, currency=self.eur),
#                                   portfolio=None, account=self.acc1, instrument=None, currency=self.eur,
#                                   balance_position=0.000000, market_value_system_ccy=0.00000),
#
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=self.acc2, instrument=None, currency=self.rub),
#                                   portfolio=None, account=self.acc2, instrument=None, currency=self.rub,
#                                   balance_position=-1000., market_value_system_ccy=-13.333333),
#                 BalanceReportItem(pk=b.make_key(portfolio=None, account=self.acc2, instrument=None, currency=self.eur),
#                                   portfolio=None, account=self.acc2, instrument=None, currency=self.eur,
#                                   balance_position=0.000000, market_value_system_ccy=0.00000),
#             ],
#             summary=BalanceReportSummary(invested_value_system_ccy=0,
#                                          current_value_system_ccy=0.,
#                                          p_l_system_ccy=0.)
#         ))
#
#     def test_strategies_1(self):
#         t1 = self.t(
#             t_class=self.buy, instr=self.instr1_bond_sys, position=20., settlement_ccy=self.usd,
#             principal=-100., carry=0., overheads=0., acc_date_delta=3, cash_date_delta=3,
#             s1_position=self.s1_11, s1_cash=self.s1_22,
#             s2_position=self.s2_11, s2_cash=self.s2_22,
#             s3_position=self.s3_11, s3_cash=self.s3_22)
#
#         t2 = self.t(
#             t_class=self.sell, instr=self.instr1_bond_sys, position=-10., settlement_ccy=self.usd,
#             principal=70., carry=0., overheads=0., acc_date_delta=4, cash_date_delta=4,
#             s1_position=self.s1_11, s1_cash=self.s1_22,
#             s2_position=self.s2_11, s2_cash=self.s2_22,
#             s3_position=self.s3_11, s3_cash=self.s3_22)
#
#         queryset = Transaction.objects.filter(pk__in=[
#             t1.pk, t2.pk
#         ])
#         instance = BalanceReport(master_user=self.m,
#                                  begin_date=None, end_date=self.d(6),
#                                  use_portfolio=False, use_account=True, use_strategy=True,
#                                  cost_method=CostMethod.objects.get(pk=CostMethod.AVCO),
#                                  show_transaction_details=False)
#         b = BalanceReport2Builder(instance=instance, queryset=queryset)
#         b.build()
#         self._print_test_name()
#         self._print_balance_transactions(instance.transactions)
#         self._print_balance(instance)
#         self._assertEqualBalance(instance, BalanceReport(
#             items=[
#                 BalanceReportItem(
#                     pk=b.make_key(portfolio=None, account=self.acc1, instrument=self.instr1_bond_sys, currency=None,
#                                   strategy1=self.s1_11, strategy2=self.s2_11, strategy3=self.s3_11),
#                     portfolio=None, account=self.acc1, instrument=self.instr1_bond_sys, currency=None,
#                     strategy1=self.s1_11, strategy2=self.s2_11, strategy3=self.s3_11,
#                     balance_position=10., market_value_system_ccy=2.05),
#                 BalanceReportItem(
#                     pk=b.make_key(portfolio=None, account=self.acc1, instrument=None, currency=self.usd,
#                                   strategy1=self.s1_22, strategy2=self.s2_22, strategy3=self.s3_22),
#                     portfolio=None, account=self.acc1, instrument=None, currency=self.usd,
#                     strategy1=self.s1_22, strategy2=self.s2_22, strategy3=self.s3_22,
#                     balance_position=-30., market_value_system_ccy=0.),
#             ],
#             summary=BalanceReportSummary(invested_value_system_ccy=0,
#                                          current_value_system_ccy=-28.155,
#                                          p_l_system_ccy=-28.155)
#         ))
