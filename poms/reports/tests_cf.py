# import logging
# import uuid
# from datetime import date, timedelta
#
# from django.contrib.auth.models import User
# from django.test import TestCase
# from django.utils.functional import cached_property
#
# from poms.accounts.models import AccountType, Account
# from poms.currencies.models import Currency, CurrencyHistory
# from poms.instruments.models import Instrument, PriceHistory, PricingPolicy, CostMethod, InstrumentType, \
#     InstrumentClass, AccrualCalculationSchedule, AccrualCalculationModel, Periodicity, InstrumentFactorSchedule
# from poms.portfolios.models import Portfolio
# from poms.reports.builders.base_item import BaseReportItem
# from poms.reports.builders.cash_flow_projection import CashFlowProjectionReportBuilder
# from poms.reports.builders.cash_flow_projection_item import CashFlowProjectionReport
# from poms.strategies.models import Strategy1Group, Strategy1Subgroup, Strategy1, Strategy2Group, Strategy2Subgroup, \
#     Strategy2, Strategy3Subgroup, Strategy3Group, Strategy3
# from poms.transactions.models import Transaction, TransactionClass, TransactionType
# from poms.users.models import MasterUser, Member
#
# _l = logging.getLogger('poms.reports')
#
#
# class AbstractReportTestMixin:
#     def setUp(self):
#         self.report_date = date(2016, 3, 1)
#
#         user1 = User.objects.create(username=str(uuid.uuid4()))
#
#         self.m = MasterUser.objects.create_master_user(user=user1, name=user1.username)
#         self.mm = Member.objects.create(master_user=self.m, user=user1, is_owner=True, is_admin=True)
#
#         self.pp = PricingPolicy.objects.create(master_user=self.m)
#
#         self.usd = self.m.system_currency
#         self.eur = self._ccy('EUR')
#         self.chf = self._ccy('CHF')
#         self.cad = self._ccy('CAD')
#         self.mex = self._ccy('MEX')
#         self.rub = self._ccy('RUB')
#         self.gbp = self._ccy('GBP')
#
#         self.at1 = self._tacc('at1', detail=False)
#         self.at2 = self._tacc('at2', detail=False)
#         self.at3 = self._tacc('at3', detail=True)
#         self.a1_1 = self._acc('a1_1', t='at1')
#         self.a1_2 = self._acc('a1_2', t='at1')
#         self.a2_3 = self._acc('a2_3', t='at2')
#         self.a3_4 = self._acc('a3_4', t='at3')
#         self.a1 = self._acc('a1')
#         self.a2 = self._acc('a2')
#         self.a3 = self._acc('a3')
#         self.a4 = self._acc('a4')
#
#         self.p1 = self._prtfl('p1')
#         self.p2 = self._prtfl('p2')
#         self.p3 = self._prtfl('p3')
#         self.p4 = self._prtfl('p4')
#
#         self.mismatch_p = self._prtfl('mismatch-prtfl')
#         self.mismatch_a = self._acc('mismatch-acc')
#         self.m.mismatch_portfolio = self.mismatch_p
#         self.m.mismatch_account = self.mismatch_a
#         self.m.save()
#
#         self.s1_1_1_1, self.s1_1_1, self.s1_1 = self._str(1, '1-1-1', '1-1', '1', path=True)
#         self.s1_1_1_2, self.s1_1_1, self.s1_1 = self._str(1, '1-1-2', '1-1', '1', path=True)
#         self.s1_1_1_3, self.s1_1_1, self.s1_1 = self._str(1, '1-1-3', '1-1', '1', path=True)
#         self.s1_1_1_4, self.s1_1_1, self.s1_1 = self._str(1, '1-1-4', '1-1', '1', path=True)
#         self.s1_1_2_1, self.s1_1_2, self.s1_1 = self._str(1, '1-1-1', '1-2', '1', path=True)
#         self.s1_1_2_2, self.s1_1_2, self.s1_1 = self._str(1, '1-1-2', '1-2', '1', path=True)
#         self.s1_1_2_3, self.s1_1_2, self.s1_1 = self._str(1, '1-1-3', '1-2', '1', path=True)
#         self.s1_1_2_4, self.s1_1_2, self.s1_1 = self._str(1, '1-1-4', '1-2', '1', path=True)
#         self.s1_2_1_1, self.s1_2_1, self.s2_1 = self._str(1, '2-1-1', '2-1', '2', path=True)
#         self.s1_2_1_2, self.s1_2_1, self.s2_1 = self._str(1, '2-1-2', '2-1', '2', path=True)
#         self.s1_2_1_3, self.s1_2_1, self.s2_1 = self._str(1, '2-1-3', '2-1', '2', path=True)
#         self.s1_2_1_4, self.s1_2_1, self.s2_1 = self._str(1, '2-1-4', '2-1', '2', path=True)
#         self.s1_2_2_1, self.s1_2_2, self.s2_1 = self._str(1, '2-1-1', '2-2', '2', path=True)
#         self.s1_2_2_2, self.s1_2_2, self.s2_1 = self._str(1, '2-1-2', '2-2', '2', path=True)
#         self.s1_2_2_3, self.s1_2_2, self.s2_1 = self._str(1, '2-1-3', '2-2', '2', path=True)
#         self.s1_2_2_4, self.s1_2_2, self.s2_1 = self._str(1, '2-1-4', '2-2', '2', path=True)
#
#         self.s2_1_1_1, self.s2_1_1, self.s2_1 = self._str(2, '1-1-1', '1-1', '1', path=True)
#         self.s2_1_1_2, self.s2_1_1, self.s2_1 = self._str(2, '1-1-2', '1-1', '1', path=True)
#         self.s2_1_1_3, self.s2_1_1, self.s2_1 = self._str(2, '1-1-3', '1-1', '1', path=True)
#         self.s2_1_1_4, self.s2_1_1, self.s2_1 = self._str(2, '1-1-4', '1-1', '1', path=True)
#
#         self.s3_1_1_1, self.s3_1_1, self.s3_1 = self._str(3, '1-1-1', '1-1', '1', path=True)
#         self.s3_1_1_2, self.s3_1_1, self.s3_1 = self._str(3, '1-1-2', '1-1', '1', path=True)
#         self.s3_1_1_3, self.s3_1_1, self.s3_1 = self._str(3, '1-1-3', '1-1', '1', path=True)
#         self.s3_1_1_4, self.s3_1_1, self.s3_1 = self._str(3, '1-1-4', '1-1', '1', path=True)
#
#     def _ccy(self, code='-'):
#         obj, created = Currency.objects.get_or_create(user_code=code, master_user=self.m, defaults={'name': code})
#         return obj
#
#     def _tacc(self, code='-', detail=False):
#         if code == '-':
#             return self.m.account_type
#         obj, created = AccountType.objects.get_or_create(
#             master_user=self.m,
#             user_code=code,
#             defaults={
#                 'name': code,
#                 'show_transaction_details': detail
#             }
#         )
#         return obj
#
#     def _acc(self, code='-', t='-'):
#         if code == '-':
#             return self.m.account
#         t = self._tacc(t)
#         obj, created = Account.objects.get_or_create(
#             master_user=self.m,
#             user_code=code,
#             defaults={
#                 'name': code,
#                 'type': t
#             }
#         )
#         return obj
#
#     def _tinstr(self, code='-'):
#         if code == '-':
#             return self.m.instrument_type
#         obj, created = InstrumentType.objects.get_or_create(
#             master_user=self.m,
#             user_code=code,
#             defaults={
#                 'name': code,
#             }
#         )
#         return obj
#
#     def _instr(self, code, t='-', pricing_ccy=None, price_mult=1.0, accrued_ccy=None, accrued_mult=1.0):
#         if code == '-':
#             return self.m.instrument
#         t = self._tinstr(t)
#         if not isinstance(pricing_ccy, Currency):
#             pricing_ccy = self._ccy(pricing_ccy)
#         if not isinstance(accrued_ccy, Currency):
#             accrued_ccy = self._ccy(accrued_ccy)
#         obj, created = Instrument.objects.get_or_create(
#             master_user=self.m,
#             user_code=code,
#             defaults={
#                 'instrument_type': t,
#                 'pricing_currency': pricing_ccy,
#                 'price_multiplier': price_mult,
#                 'accrued_currency': accrued_ccy,
#                 'accrued_multiplier': accrued_mult
#             }
#         )
#         return obj
#
#     def _str_g(self, n, code='-'):
#         if n == 1:
#             model = Strategy1Group
#         elif n == 2:
#             model = Strategy2Group
#         elif n == 3:
#             model = Strategy3Group
#         else:
#             raise RuntimeError('Bad strategy index: {}'.format(n))
#         obj, created = model.objects.get_or_create(
#             master_user=self.m,
#             user_code=code,
#             defaults={
#                 'name': code,
#             }
#         )
#         return obj
#
#     def _str_sg(self, n, code='-', group='-', path=False):
#         if n == 1:
#             model = Strategy1Subgroup
#         elif n == 2:
#             model = Strategy2Subgroup
#         elif n == 3:
#             model = Strategy3Subgroup
#         else:
#             raise RuntimeError('Bad strategy index: {}'.format(n))
#         group = self._str_g(n, group)
#         obj, created = model.objects.get_or_create(
#             master_user=self.m,
#             user_code=code,
#             defaults={
#                 'name': code,
#                 'group': group
#             }
#         )
#         if path:
#             return obj, group
#         return obj
#
#     def _str(self, n, code='-', subgroup='-', group='-', path=False):
#         if n == 1:
#             model = Strategy1
#         elif n == 2:
#             model = Strategy2
#         elif n == 3:
#             model = Strategy3
#         else:
#             raise RuntimeError('Bad strategy index: {}'.format(n))
#         subgroup, group = self._str_sg(n, subgroup, group=group, path=True)
#         obj, created = model.objects.get_or_create(
#             master_user=self.m,
#             user_code=code,
#             defaults={
#                 'name': code,
#                 'subgroup': subgroup
#             }
#         )
#         if path:
#             return obj, subgroup, group
#         return obj
#
#     def _prtfl(self, code='-'):
#         if code == '-':
#             return self.m.portfolio
#         obj, created = Portfolio.objects.get_or_create(
#             master_user=self.m,
#             user_code=code,
#             defaults={
#                 'name': code,
#             }
#         )
#         return obj
#
#     def _instr_hist(self, instr, d, principal_price, accrued_price):
#         return PriceHistory.objects.create(instrument=instr, pricing_policy=self.pp, date=d,
#                                            principal_price=principal_price, accrued_price=accrued_price)
#
#     def _ccy_hist(self, ccy, d, fx):
#         return CurrencyHistory.objects.create(currency=ccy, pricing_policy=self.pp, date=d, fx_rate=fx)
#
#     def _d(self, days=None):
#         if isinstance(days, date):
#             return days
#         if days is None or days == 0:
#             return self.report_date
#         else:
#             return self.report_date + timedelta(days=days)
#
#     def _t(self, t_class=None, p=None, instr=None, trn_ccy=None, position=0.0,
#            stl_ccy=None, cash=None, principal=0.0, carry=0.0, overheads=0.0,
#            acc_date=None, acc_date_days=None, cash_date=None, cash_date_days=None, days=-1,
#            acc_pos=None, acc_cash=None, acc_interim=None, fx_rate=None,
#            s1_pos=None, s1_cash=None, s2_pos=None, s2_cash=None, s3_pos=None, s3_cash=None,
#            link_instr=None, alloc_bl=None, alloc_pl=None, notes=None,
#            save=True):
#
#         if stl_ccy is None:
#             stl_ccy = self.usd
#         if trn_ccy is None:
#             trn_ccy = stl_ccy
#
#         t = Transaction()
#
#         t.master_user = self.m
#         t.transaction_class = t_class
#
#         t.instrument = instr
#         t.transaction_currency = trn_ccy if trn_ccy else stl_ccy
#         t.position_size_with_sign = position
#
#         t.settlement_currency = stl_ccy
#         t.cash_consideration = cash if cash is not None else (principal + carry + overheads)
#         t.principal_with_sign = principal
#         t.carry_with_sign = carry
#         t.overheads_with_sign = overheads
#
#         t.accounting_date = acc_date if acc_date else self._d(acc_date_days if acc_date_days is not None else days)
#         t.cash_date = cash_date if cash_date else self._d(cash_date_days if cash_date_days is not None else days)
#         t.transaction_date = min(t.accounting_date, t.cash_date)
#
#         t.portfolio = p or self.m.portfolio
#
#         t.account_position = acc_pos or self.m.account
#         t.account_cash = acc_cash or self.m.account
#         t.account_interim = acc_interim or self.m.account
#
#         t.strategy1_position = s1_pos or self.m.strategy1
#         t.strategy1_cash = s1_cash or self.m.strategy1
#         t.strategy2_position = s2_pos or self.m.strategy2
#         t.strategy2_cash = s2_cash or self.m.strategy2
#         t.strategy3_position = s3_pos or self.m.strategy3
#         t.strategy3_cash = s3_cash or self.m.strategy3
#
#         if fx_rate is None:
#             if trn_ccy.id == stl_ccy.id:
#                 t.reference_fx_rate = 1.0
#             else:
#                 t.reference_fx_rate = 0.0
#         else:
#             t.reference_fx_rate = fx_rate
#
#         t.linked_instrument = link_instr or self.m.instrument
#         t.allocation_balance = alloc_bl or self.m.instrument
#         t.allocation_pl = alloc_pl or self.m.instrument
#
#         t.notes = notes
#
#         if save:
#             t.save()
#
#         return t
#
#     def _t_cash_in(self, **kwargs):
#         kwargs.setdefault('t_class', self._cash_inflow)
#         return self._t(**kwargs)
#
#     def _t_cash_out(self, **kwargs):
#         kwargs.setdefault('t_class', self._cash_outflow)
#         return self._t(**kwargs)
#
#     def _t_buy(self, **kwargs):
#         kwargs.setdefault('t_class', self._buy)
#         return self._t(**kwargs)
#
#     def _t_sell(self, **kwargs):
#         kwargs.setdefault('t_class', self._sell)
#         return self._t(**kwargs)
#
#     def _t_instr_pl(self, **kwargs):
#         kwargs.setdefault('t_class', self._instrument_pl)
#         return self._t(**kwargs)
#
#     def _t_trn_pl(self, **kwargs):
#         kwargs.setdefault('t_class', self._transaction_pl)
#         return self._t(**kwargs)
#
#     def _t_fx_tade(self, **kwargs):
#         kwargs.setdefault('t_class', self._fx_tade)
#         return self._t(**kwargs)
#
#     def _t_transfer(self, **kwargs):
#         kwargs.setdefault('t_class', self._transfer)
#         return self._t(**kwargs)
#
#     def _t_fx_transfer(self, **kwargs):
#         kwargs.setdefault('t_class', self._fx_transfer)
#         return self._t(**kwargs)
#
#     @cached_property
#     def _cash_inflow(self):
#         return TransactionClass.objects.get(id=TransactionClass.CASH_INFLOW)
#
#     @cached_property
#     def _cash_outflow(self):
#         return TransactionClass.objects.get(id=TransactionClass.CASH_OUTFLOW)
#
#     @cached_property
#     def _buy(self):
#         return TransactionClass.objects.get(id=TransactionClass.BUY)
#
#     @cached_property
#     def _sell(self):
#         return TransactionClass.objects.get(id=TransactionClass.SELL)
#
#     @cached_property
#     def _instrument_pl(self):
#         return TransactionClass.objects.get(id=TransactionClass.INSTRUMENT_PL)
#
#     @cached_property
#     def _transaction_pl(self):
#         return TransactionClass.objects.get(id=TransactionClass.TRANSACTION_PL)
#
#     @cached_property
#     def _fx_tade(self):
#         return TransactionClass.objects.get(id=TransactionClass.FX_TRADE)
#
#     @cached_property
#     def _transfer(self):
#         return TransactionClass.objects.get(id=TransactionClass.TRANSFER)
#
#     @cached_property
#     def _fx_transfer(self):
#         return TransactionClass.objects.get(id=TransactionClass.FX_TRANSFER)
#
#     @cached_property
#     def _avco(self):
#         return CostMethod.objects.get(pk=CostMethod.AVCO)
#
#     @cached_property
#     def _fifo(self):
#         return CostMethod.objects.get(pk=CostMethod.FIFO)
#
#
# class CFReportTestCase(AbstractReportTestMixin, TestCase):
#     def _dumps_tinstr(self, items):
#         _l.debug('Instrument types: \n %s',
#                 BaseReportItem.sdumps(
#                     items=items,
#                     columns=[
#                         'user_code',
#                         'instrument_class',
#                         'one_off_event',
#                         'regular_event',
#                         'factor_same',
#                         'factor_up',
#                         'factor_down',
#                     ]
#                 ))
#
#     def _dumps_instr(self, items):
#         _l.debug('Instuments: \n %s',
#                 BaseReportItem.sdumps(
#                     items=items,
#                     columns=[
#                         'user_code',
#                         'instrument_type',
#                         'pricing_currency',
#                         'price_multiplier',
#                         'accrued_currency',
#                         'accrued_multiplier',
#                         'maturity_date',
#                         'maturity_price',
#                     ]
#                 ))
#
#     def _dumps_accruals(self, items):
#         _l.debug('AccrualCalculationSchedule: \n %s',
#                 BaseReportItem.sdumps(
#                     items=items,
#                     columns=[
#                         'accrual_start_date',
#                         'first_payment_date',
#                         'accrual_size',
#                         'accrual_calculation_model',
#                         'periodicity',
#                         'periodicity_n',
#                     ]
#                 ))
#
#     def _dumps_factors(self, items):
#         _l.debug('InstrumentFactorSchedule: \n %s',
#                 BaseReportItem.sdumps(
#                     items=items,
#                     columns=[
#                         'effective_date',
#                         'factor_value',
#                     ]
#                 ))
#
#     def _dumps_events_shed(self, items):
#         _l.debug('EventSchedule: \n %s',
#                 BaseReportItem.sdumps(
#                     items=items,
#                     columns=[
#                         'effective_date',
#                         'event_class',
#                         'notification_class',
#                         'notify_in_n_days',
#                         'periodicity',
#                         'periodicity_n',
#                         'final_date',
#                         'is_auto_generated',
#                         'accrual_calculation_schedule',
#                         'factor_schedule',
#                     ]
#                 ))
#
#     def _dumps_cpns(self, cpns):
#         _l.debug('get_future_coupons:')
#         for d, v in cpns:
#             _l.debug('\t%s - %s', str(d), v)
#
#     def _test_cf1(self):
#         # settings.DEBUG = True
#
#         tt1 = TransactionType.objects.create(
#             master_user=self.m,
#             group=self.m.transaction_type_group,
#             date_expr='effective_date',
#         )
#
#         it1 = InstrumentType.objects.create(
#             master_user=self.m,
#             user_code='itype1',
#             instrument_class=InstrumentClass.objects.get(pk=InstrumentClass.REGULAR_EVENT_AT_MATURITY),
#             one_off_event=tt1,
#             regular_event=tt1,
#             factor_same=tt1,
#             factor_up=tt1,
#             factor_down=tt1,
#         )
#
#         i1 = Instrument.objects.create(
#             master_user=self.m,
#             user_code='i1',
#             instrument_type=it1,
#             pricing_currency=self.usd,
#             price_multiplier=1.0,
#             accrued_currency=self.usd,
#             accrued_multiplier=1.0,
#             maturity_date=date(2103, 1, 1),
#             maturity_price=1000,
#         )
#
#         es1 = AccrualCalculationSchedule.objects.create(
#             instrument=i1,
#             accrual_start_date=date(2100, 1, 1),
#             first_payment_date=date(2100, 7, 1),
#             accrual_size=10,
#             accrual_calculation_model=AccrualCalculationModel.objects.get(pk=AccrualCalculationModel.ISMA_30_360),
#             periodicity=Periodicity.objects.get(pk=Periodicity.SEMI_ANNUALLY),
#             periodicity_n=1
#         )
#
#         i1.rebuild_event_schedules()
#
#         self._dumps_tinstr([it1])
#         self._dumps_instr([i1])
#         self._dumps_accruals(i1.accrual_calculation_schedules.all())
#         self._dumps_factors(i1.factor_schedules.all())
#         self._dumps_events_shed(i1.event_schedules.all())
#         self._dumps_cpns(i1.get_future_coupons(begin_date=date(2101, 2, 1)))
#
#         _l.debug('-' * 80)
#
#         self._t_buy(instr=i1, position=10,
#                     stl_ccy=self.usd, principal=-10, carry=0, overheads=-10,
#                     acc_date=date(2101, 2, 1), cash_date=date(2101, 2, 1))
#
#         report = CashFlowProjectionReport(
#             master_user=self.m,
#             member=self.mm,
#             balance_date=date(2101, 2, 1),
#             report_date=date(2104, 1, 1),
#         )
#         report_builder = CashFlowProjectionReportBuilder(report)
#         report_builder.build()
#
#     def test_cf2(self):
#         # settings.DEBUG = True
#
#         tt1 = TransactionType.objects.create(
#             master_user=self.m,
#             group=self.m.transaction_type_group,
#             name='tt1',
#             date_expr='effective_date',
#         )
#         tt2 = TransactionType.objects.create(
#             master_user=self.m,
#             group=self.m.transaction_type_group,
#             name='tt2',
#             date_expr='effective_date',
#         )
#         tt3 = TransactionType.objects.create(
#             master_user=self.m,
#             group=self.m.transaction_type_group,
#             name='tt3',
#             date_expr='effective_date',
#         )
#         tt4 = TransactionType.objects.create(
#             master_user=self.m,
#             group=self.m.transaction_type_group,
#             name='tt4',
#             date_expr='effective_date',
#         )
#         tt5 = TransactionType.objects.create(
#             master_user=self.m,
#             group=self.m.transaction_type_group,
#             name='tt5',
#             date_expr='effective_date',
#         )
#
#         self.m.instrument_event_schedule_config.notify_in_n_days = 2
#         self.m.instrument_event_schedule_config.save()
#
#         it1 = InstrumentType.objects.create(
#             master_user=self.m,
#             user_code='itype1',
#             instrument_class=InstrumentClass.objects.get(pk=InstrumentClass.REGULAR_EVENT_AT_MATURITY),
#             one_off_event=tt1,
#             regular_event=tt2,
#             factor_same=tt3,
#             factor_up=tt4,
#             factor_down=tt5,
#         )
#
#         i1 = Instrument.objects.create(
#             master_user=self.m,
#             user_code='i1',
#             instrument_type=it1,
#             pricing_currency=self.usd,
#             price_multiplier=1.0,
#             accrued_currency=self.usd,
#             accrued_multiplier=1.0,
#             maturity_date=date(2103, 2, 1),
#             maturity_price=1000,
#         )
#
#         AccrualCalculationSchedule.objects.create(
#             instrument=i1,
#             accrual_start_date=date(2100, 2, 1),
#             first_payment_date=date(2100, 7, 1),
#             accrual_size=10,
#             accrual_calculation_model=AccrualCalculationModel.objects.get(pk=AccrualCalculationModel.ISMA_30_360),
#             periodicity=Periodicity.objects.get(pk=Periodicity.SEMI_ANNUALLY),
#             periodicity_n=1
#         )
#
#         InstrumentFactorSchedule.objects.create(
#             instrument=i1,
#             effective_date=date(2100, 2, 1),
#             factor_value=1,
#         )
#         InstrumentFactorSchedule.objects.create(
#             instrument=i1,
#             effective_date=date(2102, 4, 21),
#             factor_value=2,
#         )
#
#         i1.rebuild_event_schedules()
#
#         self._dumps_tinstr([it1])
#         self._dumps_instr([i1])
#         self._dumps_accruals(i1.accrual_calculation_schedules.all())
#         self._dumps_factors(i1.factor_schedules.all())
#         self._dumps_events_shed(i1.event_schedules.all())
#         self._dumps_cpns(i1.get_future_coupons(begin_date=date(2101, 2, 2)))
#
#         _l.debug('-' * 80)
#
#         self._t_buy(instr=i1, position=10,
#                     stl_ccy=self.usd, principal=-10, carry=0, overheads=-10,
#                     acc_date=date(2101, 2, 1), cash_date=date(2101, 2, 1))
#
#         report = CashFlowProjectionReport(
#             master_user=self.m,
#             member=self.mm,
#             balance_date=date(2101, 2, 2),
#             report_date=date(2104, 1, 1),
#         )
#         report_builder = CashFlowProjectionReportBuilder(report)
#         report_builder.build()
