# from __future__ import unicode_literals, division, print_function
#
# import inspect
# from datetime import date, timedelta
#
# from django.contrib.auth.models import User
# from django.test import TestCase
#
# from poms.accounts.models import Account, AccountType
# from poms.currencies.models import Currency, CurrencyHistory
# from poms.instruments.models import Instrument, PriceHistory, InstrumentType, InstrumentClass
# from poms.portfolios.models import Portfolio
# from poms.strategies.models import Strategy1, Strategy3, Strategy2
# from poms.transactions.models import Transaction, TransactionClass
# from poms.users.models import MasterUser
#
# try:
#     import pandas as pd
# except ImportError:
#     pd = None
#
#
# def n(v):
#     return "%.6f" % v
#
#
# class BaseReportTestCase(TestCase):
#     def setUp(self):
#         if pd:
#             pd.set_option('display.width', 2000)
#             pd.set_option('display.max_rows', 2000)
#
#         u = User.objects.create_user('a1')
#         self.m = m = MasterUser.objects.create()
#
#         # self.cash_inflow = TransactionClass.objects.create(code=TransactionClass.CASH_INFLOW,
#         #                                                    name=TransactionClass.CASH_INFLOW)
#         # self.cash_outflow = TransactionClass.objects.create(code=TransactionClass.CASH_OUTFLOW,
#         #                                                     name=TransactionClass.CASH_OUTFLOW)
#         # self.buy = TransactionClass.objects.create(code=TransactionClass.BUY,
#         #                                            name=TransactionClass.BUY)
#         # self.sell = TransactionClass.objects.create(code=TransactionClass.SELL,
#         #                                             name=TransactionClass.SELL)
#         # self.instrument_pl = TransactionClass.objects.create(code=TransactionClass.INSTRUMENT_PL,
#         #                                                      name=TransactionClass.INSTRUMENT_PL)
#         # self.transaction_pl = TransactionClass.objects.create(code=TransactionClass.TRANSACTION_PL,
#         #                                                       name=TransactionClass.TRANSACTION_PL)
#         # self.fx_tade = TransactionClass.objects.create(code=TransactionClass.FX_TRADE,
#         #                                                name=TransactionClass.FX_TRADE)
#         self.cash_inflow = TransactionClass.objects.get(id=TransactionClass.CASH_INFLOW)
#         self.cash_outflow = TransactionClass.objects.get(id=TransactionClass.CASH_OUTFLOW)
#         self.buy = TransactionClass.objects.get(id=TransactionClass.BUY)
#         self.sell = TransactionClass.objects.get(id=TransactionClass.SELL)
#         self.instrument_pl = TransactionClass.objects.get(id=TransactionClass.INSTRUMENT_PL)
#         self.transaction_pl = TransactionClass.objects.get(id=TransactionClass.TRANSACTION_PL)
#         self.fx_tade = TransactionClass.objects.get(id=TransactionClass.FX_TRADE)
#         self.transfer = TransactionClass.objects.get(id=TransactionClass.TRANSFER)
#         self.fx_transfer = TransactionClass.objects.get(id=TransactionClass.FX_TRANSFER)
#
#         self.ccy_ = Currency.objects.create(user_code='-', master_user=self.m)
#         self.usd = Currency.objects.create(user_code='USD', name='USD', master_user=self.m)
#         self.eur = Currency.objects.create(user_code='EUR', name='EUR', master_user=self.m)
#         self.chf = Currency.objects.create(user_code='CHF', name='CHF', master_user=self.m)
#         self.cad = Currency.objects.create(user_code='CAD', name='CAD', master_user=self.m)
#         self.mex = Currency.objects.create(user_code='MEX', name='MEX', master_user=self.m)
#         self.rub = Currency.objects.create(user_code='RUB', name='RUB', master_user=self.m)
#         self.gbp = Currency.objects.create(user_code='GBP', name='GBP', master_user=self.m)
#
#         self.base_date = date(2016, 3, 1)
#
#         cd1 = self.d()
#         CurrencyHistory.objects.create(currency=self.eur, date=cd1, fx_rate=1.3)
#         CurrencyHistory.objects.create(currency=self.chf, date=cd1, fx_rate=0.9)
#         CurrencyHistory.objects.create(currency=self.cad, date=cd1, fx_rate=1.2)
#         CurrencyHistory.objects.create(currency=self.mex, date=cd1, fx_rate=0.15)
#         CurrencyHistory.objects.create(currency=self.rub, date=cd1, fx_rate=1. / 75.)
#         CurrencyHistory.objects.create(currency=self.gbp, date=cd1, fx_rate=1.6)
#
#         cd2 = self.d(30)
#         CurrencyHistory.objects.create(currency=self.eur, date=cd2, fx_rate=1.2)
#         CurrencyHistory.objects.create(currency=self.chf, date=cd2, fx_rate=0.8)
#         CurrencyHistory.objects.create(currency=self.cad, date=cd2, fx_rate=1.1)
#         CurrencyHistory.objects.create(currency=self.mex, date=cd2, fx_rate=0.1)
#         CurrencyHistory.objects.create(currency=self.rub, date=cd2, fx_rate=1. / 100.)
#         CurrencyHistory.objects.create(currency=self.gbp, date=cd2, fx_rate=1.5)
#
#         self.instr_t = InstrumentType.objects.create(
#             name='-', master_user=self.m,
#             instrument_class=InstrumentClass.objects.get(id=InstrumentClass.GENERAL))
#
#         self.instr1_bond_chf = Instrument.objects.create(
#             master_user=m, name="instr1-bond, CHF", instrument_type=self.instr_t,
#             pricing_currency=self.chf, price_multiplier=0.01,
#             accrued_currency=self.chf, accrued_multiplier=0.01)
#         self.instr2_stock = Instrument.objects.create(
#             master_user=m, name="instr2-stock",
#             instrument_type=self.instr_t,
#             pricing_currency=self.gbp, price_multiplier=1.,
#             accrued_currency=self.rub, accrued_multiplier=1.)
#
#         self.instr1_bond_sys = Instrument.objects.create(
#             master_user=m, name="instr1-bond, USD", instrument_type=self.instr_t,
#             pricing_currency=self.usd, price_multiplier=0.01,
#             accrued_currency=self.usd, accrued_multiplier=0.01)
#         self.instr2_stock_sys = Instrument.objects.create(
#             master_user=m, name="instr2-stock, USD", instrument_type=self.instr_t,
#             pricing_currency=self.usd, price_multiplier=1.,
#             accrued_currency=self.usd, accrued_multiplier=1.)
#
#         phd1 = self.d()
#         PriceHistory.objects.create(instrument=self.instr1_bond_chf, date=phd1, principal_price=20., accrued_price=0.5)
#         PriceHistory.objects.create(instrument=self.instr2_stock, date=phd1, principal_price=1.5, accrued_price=2)
#         PriceHistory.objects.create(instrument=self.instr1_bond_sys, date=phd1, principal_price=20., accrued_price=0.5)
#         PriceHistory.objects.create(instrument=self.instr2_stock_sys, date=phd1, principal_price=1.5, accrued_price=2)
#
#         self.acc_t = AccountType.objects.create(master_user=m, name='Def', show_transaction_details=False)
#         self.prov_acc_t = AccountType.objects.create(master_user=m, name='Prov', show_transaction_details=False)
#         self.prov_acc_t2 = AccountType.objects.create(master_user=m, name='Prov2', show_transaction_details=True)
#         self.acc1 = Account.objects.create(master_user=m, name='Acc1', type=self.acc_t)
#         self.acc2 = Account.objects.create(master_user=m, name='Acc2', type=self.acc_t)
#         self.prov_acc1 = Account.objects.create(master_user=m, name='Prov Acc1', type=self.prov_acc_t)
#         self.prov_acc2 = Account.objects.create(master_user=m, name='Prov Acc2', type=self.prov_acc_t2)
#
#         self.p1 = Portfolio.objects.create(master_user=m, name='p1')
#         self.p2 = Portfolio.objects.create(master_user=m, name='p2')
#
#         self.s1_1 = Strategy1.objects.create(master_user=m, name='s1_1')
#         self.s1_11 = Strategy1.objects.create(master_user=m, name='s1_11', parent=self.s1_1)
#         self.s1_12 = Strategy1.objects.create(master_user=m, name='s1_12', parent=self.s1_1)
#         self.s1_2 = Strategy1.objects.create(master_user=m, name='s1_2')
#         self.s1_21 = Strategy1.objects.create(master_user=m, name='s1_21', parent=self.s1_2)
#         self.s1_22 = Strategy1.objects.create(master_user=m, name='s1_22', parent=self.s1_2)
#
#         self.s2_1 = Strategy2.objects.create(master_user=m, name='s2_1')
#         self.s2_11 = Strategy2.objects.create(master_user=m, name='s2_11', parent=self.s2_1)
#         self.s2_12 = Strategy2.objects.create(master_user=m, name='s2_12', parent=self.s2_1)
#         self.s2_2 = Strategy2.objects.create(master_user=m, name='s2_2')
#         self.s2_21 = Strategy2.objects.create(master_user=m, name='s2_21', parent=self.s2_2)
#         self.s2_22 = Strategy2.objects.create(master_user=m, name='s2_22', parent=self.s2_2)
#
#         self.s3_1 = Strategy3.objects.create(master_user=m, name='s3_1')
#         self.s3_11 = Strategy3.objects.create(master_user=m, name='s3_11', parent=self.s3_1)
#         self.s3_12 = Strategy3.objects.create(master_user=m, name='s3_12', parent=self.s3_1)
#         self.s3_2 = Strategy3.objects.create(master_user=m, name='s3_2')
#         self.s3_21 = Strategy3.objects.create(master_user=m, name='s3_21', parent=self.s3_2)
#         self.s3_22 = Strategy3.objects.create(master_user=m, name='s3_22', parent=self.s3_2)
#
#         # self.t_in = Transaction.objects.create(
#         #     master_user=m,
#         #     transaction_class=self.cash_inflow,
#         #     portfolio=self.p1,
#         #     instrument=None,
#         #     transaction_currency=self.eur,
#         #     position_size_with_sign=1000,
#         #     settlement_currency=self.eur,  # TODO: must be None
#         #     cash_consideration=0.,
#         #     principal_with_sign=0.,
#         #     carry_with_sign=0.,
#         #     overheads_with_sign=0.,
#         #     transaction_date=date(2016, 3, 1),
#         #     accounting_date=date(2016, 3, 1),
#         #     cash_date=date(2016, 3, 1),
#         #     account_position=self.acc1,
#         #     account_cash=self.acc1,
#         #     account_interim=self.prov_acc1,
#         #     reference_fx_rate=1.3
#         # )
#         self.t_in = self.t(t_class=self.cash_inflow, transaction_ccy=self.eur, position=1000, fx_rate=1.3)
#
#         # self.t_in2 = Transaction.objects.create(
#         #     master_user=m,
#         #     transaction_class=self.cash_inflow,
#         #     portfolio=self.p1,
#         #     instrument=None,
#         #     transaction_currency=self.eur,
#         #     position_size_with_sign=1000,
#         #     settlement_currency=self.eur,  # TODO: must be None
#         #     cash_consideration=0.,
#         #     principal_with_sign=0.,
#         #     carry_with_sign=0.,
#         #     overheads_with_sign=0.,
#         #     transaction_date=date(2016, 3, 10),
#         #     accounting_date=date(2016, 3, 10),
#         #     cash_date=date(2016, 3, 10),
#         #     account_position=self.acc1,
#         #     account_cash=self.acc1,
#         #     account_interim=self.prov_acc1,
#         #     reference_fx_rate=1.4
#         # )
#         self.t_in2 = self.t(t_class=self.cash_inflow, transaction_ccy=self.eur, position=1000, fx_rate=1.4,
#                             acc_date_delta=9, cash_date_delta=9)
#
#         # self.t_buy_bond = Transaction.objects.create(
#         #     master_user=m,
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
#         #     cash_date=date(2016, 3, 6),
#         #     account_position=self.acc1,
#         #     account_cash=self.acc1,
#         #     account_interim=self.prov_acc1,
#         #     reference_fx_rate=None
#         # )
#         self.t_buy_bond = self.t(
#             t_class=self.buy, instr=self.instr1_bond_chf, position=100, settlement_ccy=self.usd,
#             principal=-180., carry=-5., overheads=-15., acc_date_delta=3, cash_date_delta=5)
#
#         # self.t_buy_bond_acc2 = Transaction.objects.create(
#         #     master_user=m,
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
#         #     cash_date=date(2016, 3, 6),
#         #     account_position=self.acc2,
#         #     account_cash=self.acc2,
#         #     account_interim=self.prov_acc2,
#         #     reference_fx_rate=None
#         # )
#         self.t_buy_bond_acc2 = self.t(
#             t_class=self.buy, instr=self.instr1_bond_chf, position=100, settlement_ccy=self.usd,
#             principal=-180., carry=-5., overheads=-15., acc_date_delta=3, cash_date_delta=5,
#             acc_pos=self.acc2, acc_cash=self.acc2, acc_interim=self.prov_acc2)
#
#         # self.t_buy_bond_p2 = Transaction.objects.create(
#         #     master_user=m,
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
#         #     transaction_date=date(2016, 3, 4),
#         #     accounting_date=date(2016, 3, 4),
#         #     cash_date=date(2016, 3, 6),
#         #     account_position=self.acc1,
#         #     account_cash=self.acc1,
#         #     account_interim=self.prov_acc1,
#         #     reference_fx_rate=None
#         # )
#         self.t_buy_bond_p2 = self.t(
#             t_class=self.buy, instr=self.instr1_bond_chf, position=100, settlement_ccy=self.usd,
#             principal=-180., carry=-5., overheads=-15., acc_date_delta=3, cash_date_delta=5,
#             p=self.p2)
#
#         # self.t_sell_stock = Transaction.objects.create(
#         #     master_user=m,
#         #     transaction_class=self.sell,
#         #     portfolio=self.p1,
#         #     instrument=self.instr2_stock,
#         #     transaction_currency=None,
#         #     position_size_with_sign=-200,
#         #     settlement_currency=self.rub,
#         #     cash_consideration=1000.,
#         #     principal_with_sign=1100.,
#         #     carry_with_sign=0.,
#         #     overheads_with_sign=-100.,
#         #     transaction_date=date(2016, 3, 4),
#         #     accounting_date=date(2016, 3, 6),
#         #     cash_date=date(2016, 3, 4),
#         #     account_position=self.acc1,
#         #     account_cash=self.acc1,
#         #     account_interim=self.prov_acc1,
#         #     reference_fx_rate=None
#         # )
#         self.t_sell_stock = self.t(
#             t_class=self.buy, instr=self.instr2_stock, position=-200, settlement_ccy=self.rub,
#             principal=1100., carry=0., overheads=-100., acc_date_delta=5, cash_date_delta=3)
#
#         # self.t_sell_stock_acc2 = Transaction.objects.create(
#         #     master_user=m,
#         #     transaction_class=self.sell,
#         #     portfolio=self.p1,
#         #     instrument=self.instr2_stock,
#         #     transaction_currency=None,
#         #     position_size_with_sign=-200,
#         #     settlement_currency=self.rub,
#         #     cash_consideration=1000.,
#         #     principal_with_sign=1100.,
#         #     carry_with_sign=0.,
#         #     overheads_with_sign=-100.,
#         #     transaction_date=date(2016, 3, 4),
#         #     accounting_date=date(2016, 3, 6),
#         #     cash_date=date(2016, 3, 4),
#         #     account_position=self.acc2,
#         #     account_cash=self.acc2,
#         #     account_interim=self.prov_acc2,
#         #     reference_fx_rate=None
#         # )
#         self.t_sell_stock_acc2 = self.t(
#             t_class=self.buy, instr=self.instr2_stock, position=-200, settlement_ccy=self.rub,
#             principal=1100., carry=0., overheads=-100., acc_date_delta=5, cash_date_delta=3,
#             acc_pos=self.acc2, acc_cash=self.acc2, acc_interim=self.prov_acc2)
#
#         # self.t_sell_stock_p2 = Transaction.objects.create(
#         #     master_user=m,
#         #     transaction_class=self.sell,
#         #     portfolio=self.p2,
#         #     instrument=self.instr2_stock,
#         #     transaction_currency=None,
#         #     position_size_with_sign=-200,
#         #     settlement_currency=self.rub,
#         #     cash_consideration=1000.,
#         #     principal_with_sign=1100.,
#         #     carry_with_sign=0.,
#         #     overheads_with_sign=-100.,
#         #     transaction_date=date(2016, 3, 4),
#         #     accounting_date=date(2016, 3, 6),
#         #     cash_date=date(2016, 3, 4),
#         #     account_position=self.acc1,
#         #     account_cash=self.acc1,
#         #     account_interim=self.prov_acc1,
#         #     reference_fx_rate=None
#         # )
#         self.t_sell_stock_p2 = self.t(
#             t_class=self.buy, instr=self.instr2_stock, position=-200, settlement_ccy=self.rub,
#             principal=1100., carry=0., overheads=-100., acc_date_delta=5, cash_date_delta=3,
#             p=self.p2)
#
#         # self.t_out = Transaction.objects.create(
#         #     master_user=m,
#         #     transaction_class=self.cash_outflow,
#         #     portfolio=self.p1,
#         #     instrument=None,
#         #     transaction_currency=self.rub,
#         #     position_size_with_sign=-1000,
#         #     settlement_currency=self.rub,  # TODO: must be None
#         #     cash_consideration=0.,
#         #     principal_with_sign=0,
#         #     carry_with_sign=0.,
#         #     overheads_with_sign=0.,
#         #     transaction_date=date(2016, 3, 7),
#         #     accounting_date=date(2016, 3, 7),
#         #     cash_date=date(2016, 3, 7),
#         #     account_position=self.acc1,
#         #     account_cash=self.acc1,
#         #     account_interim=self.prov_acc1,
#         #     reference_fx_rate=1 / 75.
#         # )
#         self.t_out = self.t(
#             t_class=self.cash_outflow, transaction_ccy=self.rub, position=-1000,
#             principal=0., carry=0., overheads=0., acc_date_delta=6, cash_date_delta=6,
#             fx_rate=1 / 75.)
#
#         # self.t_instrpl_stock = Transaction.objects.create(
#         #     master_user=m,
#         #     transaction_class=self.instrument_pl,
#         #     portfolio=self.p1,
#         #     instrument=self.instr2_stock,
#         #     transaction_currency=None,
#         #     position_size_with_sign=0.,
#         #     settlement_currency=self.chf,
#         #     cash_consideration=10.,
#         #     principal_with_sign=0,
#         #     carry_with_sign=11.,
#         #     overheads_with_sign=-1.,
#         #     transaction_date=date(2016, 3, 8),
#         #     accounting_date=date(2016, 3, 8),
#         #     cash_date=date(2016, 3, 8),
#         #     account_position=self.acc1,
#         #     account_cash=self.acc1,
#         #     account_interim=self.prov_acc1,
#         #     reference_fx_rate=None
#         # )
#         self.t_instrpl_stock = self.t(
#             t_class=self.instrument_pl, instr=self.instr2_stock, position=0., settlement_ccy=self.chf,
#             principal=0., carry=11., overheads=-1., acc_date_delta=7, cash_date_delta=7)
#
#         # self.t_instrpl_bond = Transaction.objects.create(
#         #     master_user=m,
#         #     transaction_class=self.instrument_pl,
#         #     portfolio=self.p1,
#         #     instrument=self.instr1_bond_chf,
#         #     transaction_currency=None,
#         #     position_size_with_sign=0.,
#         #     settlement_currency=self.chf,
#         #     cash_consideration=20.,
#         #     principal_with_sign=0,
#         #     carry_with_sign=20.,
#         #     overheads_with_sign=0.,
#         #     transaction_date=date(2016, 3, 9),
#         #     accounting_date=date(2016, 3, 9),
#         #     cash_date=date(2016, 3, 9),
#         #     account_position=self.acc1,
#         #     account_cash=self.acc1,
#         #     account_interim=self.prov_acc1,
#         #     reference_fx_rate=None
#         # )
#         self.t_instrpl_bond = self.t(
#             t_class=self.instrument_pl, instr=self.instr1_bond_chf, position=0., settlement_ccy=self.chf,
#             principal=0., carry=20., overheads=0., acc_date_delta=8, cash_date_delta=8)
#
#         # self.t_instrpl_bond_acc2 = Transaction.objects.create(
#         #     master_user=m,
#         #     transaction_class=self.instrument_pl,
#         #     portfolio=self.p1,
#         #     instrument=self.instr1_bond_chf,
#         #     transaction_currency=None,
#         #     position_size_with_sign=0.,
#         #     settlement_currency=self.chf,
#         #     cash_consideration=20.,
#         #     principal_with_sign=0,
#         #     carry_with_sign=20.,
#         #     overheads_with_sign=0.,
#         #     transaction_date=date(2016, 3, 9),
#         #     accounting_date=date(2016, 3, 9),
#         #     cash_date=date(2016, 3, 9),
#         #     account_position=self.acc2,
#         #     account_cash=self.acc2,
#         #     account_interim=self.prov_acc2,
#         #     reference_fx_rate=None
#         # )
#         self.t_instrpl_bond_acc2 = self.t(
#             t_class=self.instrument_pl, instr=self.instr1_bond_chf, position=0., settlement_ccy=self.chf,
#             principal=0., carry=20., overheads=0., acc_date_delta=8, cash_date_delta=8,
#             acc_pos=self.acc2, acc_cash=self.acc2, acc_interim=self.prov_acc2)
#
#         # self.t_instrpl_bond_p2 = Transaction.objects.create(
#         #     master_user=m,
#         #     transaction_class=self.instrument_pl,
#         #     portfolio=self.p2,
#         #     instrument=self.instr1_bond_chf,
#         #     transaction_currency=None,
#         #     position_size_with_sign=0.,
#         #     settlement_currency=self.chf,
#         #     cash_consideration=20.,
#         #     principal_with_sign=0,
#         #     carry_with_sign=20.,
#         #     overheads_with_sign=0.,
#         #     transaction_date=date(2016, 3, 9),
#         #     accounting_date=date(2016, 3, 9),
#         #     cash_date=date(2016, 3, 9),
#         #     account_position=self.acc1,
#         #     account_cash=self.acc1,
#         #     account_interim=self.prov_acc1,
#         #     reference_fx_rate=None
#         # )
#         self.t_instrpl_bond_p2 = self.t(
#             t_class=self.instrument_pl, instr=self.instr1_bond_chf, position=0., settlement_ccy=self.chf,
#             principal=0., carry=20., overheads=0., acc_date_delta=8, cash_date_delta=8,
#             p=self.p2)
#
#         # self.t_trnpl = Transaction.objects.create(
#         #     master_user=m,
#         #     transaction_class=self.transaction_pl,
#         #     portfolio=self.p1,
#         #     instrument=None,
#         #     transaction_currency=None,
#         #     position_size_with_sign=0.,
#         #     settlement_currency=self.rub,
#         #     cash_consideration=-1000.,
#         #     principal_with_sign=0,
#         #     carry_with_sign=-900.,
#         #     overheads_with_sign=-100.,
#         #     transaction_date=date(2016, 3, 9),
#         #     accounting_date=date(2016, 3, 9),
#         #     cash_date=date(2016, 3, 9),
#         #     account_position=self.acc1,
#         #     account_cash=self.acc1,
#         #     account_interim=self.prov_acc1,
#         #     reference_fx_rate=None
#         # )
#         self.t_trnpl = self.t(
#             t_class=self.transaction_pl, position=0., settlement_ccy=self.rub,
#             principal=0., carry=-900., overheads=-100., acc_date_delta=8, cash_date_delta=8)
#
#         # self.t_fxtrade = Transaction.objects.create(
#         #     master_user=m,
#         #     transaction_class=self.fx_tade,
#         #     portfolio=self.p1,
#         #     instrument=None,
#         #     transaction_currency=self.cad,
#         #     position_size_with_sign=80.,
#         #     settlement_currency=self.mex,
#         #     cash_consideration=-150.,
#         #     principal_with_sign=-140,
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
#         self.t_fxtrade = self.t(
#             t_class=self.fx_tade, transaction_ccy=self.cad, position=80., settlement_ccy=self.mex,
#             principal=-140., carry=0., overheads=-10., acc_date_delta=8, cash_date_delta=8)
#         # self.t_fxtrade2 = Transaction.objects.create(
#         #     master_user=m,
#         #     transaction_class=self.fx_tade,
#         #     portfolio=self.p1,
#         #     instrument=None,
#         #     transaction_currency=self.cad,
#         #     position_size_with_sign=80.,
#         #     settlement_currency=self.mex,
#         #     cash_consideration=-150.,
#         #     principal_with_sign=-140,
#         #     carry_with_sign=0.,
#         #     overheads_with_sign=-10.,
#         #     transaction_date=date(2016, 4, 9),
#         #     accounting_date=date(2016, 4, 9),
#         #     cash_date=date(2016, 4, 9),
#         #     account_position=self.acc2,
#         #     account_cash=self.acc2,
#         #     account_interim=self.prov_acc2,
#         #     reference_fx_rate=None
#         # )
#         self.t_fxtrade2 = self.t(
#             t_class=self.fx_tade, transaction_ccy=self.cad, position=80., settlement_ccy=self.mex,
#             principal=-140., carry=0., overheads=-10., acc_date_delta=40, cash_date_delta=40,
#             acc_pos=self.acc2, acc_cash=self.acc2, acc_interim=self.prov_acc2)
#
#         self.simple = [
#             self.t_in.pk, self.t_buy_bond.pk, self.t_sell_stock.pk, self.t_out.pk
#         ]
#         self.simple_w_trnpl = [
#             self.t_in.pk, self.t_buy_bond.pk, self.t_sell_stock.pk, self.t_out.pk, self.t_instrpl_stock.pk,
#             self.t_instrpl_bond.pk, self.t_trnpl.pk
#         ]
#         self.simple_w_fxtrade = [
#             self.t_in.pk, self.t_buy_bond.pk, self.t_sell_stock.pk, self.t_out.pk, self.t_instrpl_stock.pk,
#             self.t_instrpl_bond.pk, self.t_trnpl.pk, self.t_fxtrade.pk
#         ]
#
#     def d(self, days=None):
#         if days is None or days == 0:
#             return self.base_date
#         else:
#             return self.base_date + timedelta(days=days)
#
#     def t(self, master=None, t_class=None, p=None, instr=None, transaction_ccy=None,
#           position=None, settlement_ccy=None, cash_consideration=None, principal=0., carry=0., overheads=0.,
#           acc_date=None, acc_date_delta=None, cash_date=None, cash_date_delta=None,
#           acc_pos=None, acc_cash=None, acc_interim=None, fx_rate=None,
#           s1_position=None, s1_cash=None, s2_position=None, s2_cash=None, s3_position=None, s3_cash=None):
#
#         # if p is None:
#         #     p = self.p1
#         # if cash_consideration is None:
#         #     cash_consideration = principal + carry + overheads
#         # if acc_date is None:
#         #     acc_date = self.d(acc_date_delta)
#         # if cash_date is None:
#         #     cash_date = self.d(cash_date_delta)
#         # if acc_pos is None:
#         #     acc_pos = self.acc1
#         # if acc_cash is None:
#         #     acc_cash = self.acc1
#         # if acc_interim is None:
#         #     acc_interim = self.prov_acc1
#         # if settlement_ccy is None:
#         #     settlement_ccy = self.ccy_
#
#         # t = Transaction(
#         #     master_user=master if master else self.m,
#         #     transaction_class=t_class,
#         #     portfolio=p if p else self.p1,
#         #     instrument=instr,
#         #     transaction_currency=transaction_ccy,
#         #     position_size_with_sign=position,
#         #     settlement_currency=settlement_ccy if settlement_ccy else self.ccy_,
#         #     cash_consideration=cash_consideration if cash_consideration is not None else (principal + carry + overheads),
#         #     principal_with_sign=principal,
#         #     carry_with_sign=carry,
#         #     overheads_with_sign=overheads,
#         #     accounting_date=acc_date if acc_date else self.d(acc_date_delta),
#         #     cash_date=cash_date if cash_date else self.d(cash_date_delta),
#         #     account_position=acc_pos if acc_pos else self.acc1,
#         #     account_cash=acc_cash if acc_cash else self.acc1,
#         #     account_interim=acc_interim if acc_interim else self.prov_acc1,
#         #     reference_fx_rate=fx_rate)
#
#         t = Transaction()
#         t.master_user = master if master else self.m
#         t.transaction_class = t_class
#         t.portfolio = p if p else self.p1
#         t.instrument = instr
#         t.transaction_currency = transaction_ccy
#         t.position_size_with_sign = position
#         t.settlement_currency = settlement_ccy if settlement_ccy else self.ccy_
#         t.cash_consideration = cash_consideration if cash_consideration is not None else (principal + carry + overheads)
#         t.principal_with_sign = principal
#         t.carry_with_sign = carry
#         t.overheads_with_sign = overheads
#         t.accounting_date = acc_date if acc_date else self.d(acc_date_delta)
#         t.cash_date = cash_date if cash_date else self.d(cash_date_delta)
#         t.account_position = acc_pos if acc_pos else self.acc1
#         t.account_cash = acc_cash if acc_cash else self.acc1
#         t.account_interim = acc_interim if acc_interim else self.prov_acc1
#         t.reference_fx_rate = fx_rate
#
#         t.strategy1_position = s1_position
#         t.strategy1_cash = s1_cash
#         t.strategy2_position = s2_position
#         t.strategy2_cash = s2_cash
#         t.strategy3_position = s3_position
#         t.strategy3_cash = s3_cash
#
#         t.save()
#         return t
#
#     def _print_table(self, data, columns):
#         if pd:
#             print(pd.DataFrame(data=data, columns=columns))
#         else:
#             print(columns)
#             for r in data:
#                 print(r)
#
#     def _print_transactions(self, transactions, *columns):
#         # print('=' * 79)
#         print('Transactions')
#         data = []
#         for t in transactions:
#             data.append([getattr(t, c, None) for c in columns])
#         self._print_table(data, columns)
#         # print(pd.DataFrame(data=data, columns=columns))
#
#     def _print_test_name(self):
#         print('=' * 79)
#         curframe = inspect.currentframe()
#         calframe = inspect.getouterframes(curframe, 2)
#         print(calframe[1][3])
