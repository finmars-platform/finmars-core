# import datetime
# import logging
# import random
# import sys
# from collections import defaultdict
# from itertools import groupby
#
# from django.db import transaction
# from django.db.models import Q
# from django.utils.translation import gettext_lazy
#
# from poms.accounts.models import Account, AccountType
# from poms.common import formula
# from poms.common.utils import isclose
# from poms.counterparties.models import Counterparty, ResponsibleGroup, CounterpartyGroup
# from poms.counterparties.models import Responsible
# from poms.currencies.models import Currency
# from poms.instruments.handlers import GeneratedEventProcess
# from poms.instruments.models import Instrument, GeneratedEvent, InstrumentType
# from poms.obj_attrs.models import GenericAttributeType
# from poms.obj_attrs.utils import get_attributes_prefetch
# from poms.obj_perms.utils import get_permissions_prefetch_lookups
# from poms.portfolios.models import Portfolio
# from poms.strategies.models import Strategy1, Strategy2, Strategy3, Strategy1Subgroup, Strategy1Group, \
#     Strategy2Subgroup, \
#     Strategy2Group, Strategy3Subgroup, Strategy3Group
# from poms.transactions.models import Transaction, ComplexTransaction, TransactionType, TransactionClass, \
#     TransactionTypeGroup
#
# _l = logging.getLogger('poms.reports')
#
# empty = object()
#
#
# def _check_int_min(val):
#     return val if val is not None else sys.maxsize
#
#
# def _check_int_max(val):
#     return val if val is not None else -sys.maxsize
#
#
# def _check_date_min(val):
#     return val if val is not None else datetime.date.min
#
#
# def _check_date_max(val):
#     return val if val is not None else datetime.date.max
#
#
# def _val(obj, val, attr, default=None):
#     if val is empty:
#         if callable(attr):
#             val = attr()
#         else:
#             val = getattr(obj, attr, None)
#     if val is None:
#         return default
#     return val
#
#
# class TransactionReportItem:
#     def __init__(self,
#                  report,
#                  trn=None,
#                  id=empty,
#                  complex_transaction=empty,
#                  complex_transaction_order=empty,
#                  transaction_code=empty,
#                  transaction_class=empty,
#                  instrument=empty,
#                  transaction_currency=empty,
#                  position_size_with_sign=empty,
#                  settlement_currency=empty,
#                  cash_consideration=empty,
#                  principal_with_sign=empty,
#                  carry_with_sign=empty,
#                  overheads_with_sign=empty,
#                  transaction_date=empty,
#                  accounting_date=empty,
#                  cash_date=empty,
#                  portfolio=empty,
#                  account_position=empty,
#                  account_cash=empty,
#                  account_interim=empty,
#                  strategy1_position=empty,
#                  strategy1_cash=empty,
#                  strategy2_position=empty,
#                  strategy2_cash=empty,
#                  strategy3_position=empty,
#                  strategy3_cash=empty,
#                  responsible=empty,
#                  counterparty=empty,
#                  linked_instrument=empty,
#                  allocation_balance=empty,
#                  allocation_pl=empty,
#                  reference_fx_rate=empty,
#
#                  factor=empty,
#                  trade_price=empty,
#                  position_amount=empty,
#                  principal_amount=empty,
#                  carry_amount=empty,
#                  overheads=empty,
#                  notes=empty,
#
#                  attributes=empty):
#         self.report = report
#
#         self.id = _val(trn, id, 'id')
#         self.complex_transaction = _val(trn, complex_transaction, 'complex_transaction')
#         self.complex_transaction_order = _val(trn, complex_transaction_order, 'complex_transaction_order')
#         self.transaction_code = _val(trn, transaction_code, 'transaction_code')
#         self.transaction_class = _val(trn, transaction_class, 'transaction_class')
#
#         self.instrument = _val(trn, instrument, 'instrument')
#         self.transaction_currency = _val(trn, transaction_currency, 'transaction_currency')
#         self.position_size_with_sign = _val(trn, position_size_with_sign, 'position_size_with_sign')
#         self.settlement_currency = _val(trn, settlement_currency, 'settlement_currency')
#         self.cash_consideration = _val(trn, cash_consideration, 'cash_consideration')
#         self.principal_with_sign = _val(trn, principal_with_sign, 'principal_with_sign')
#         self.carry_with_sign = _val(trn, carry_with_sign, 'carry_with_sign')
#         self.overheads_with_sign = _val(trn, overheads_with_sign, 'overheads_with_sign')
#
#         self.transaction_date = _val(trn, transaction_date, 'transaction_date')
#         self.accounting_date = _val(trn, accounting_date, 'accounting_date')
#         self.cash_date = _val(trn, cash_date, 'cash_date')
#
#         self.portfolio = _val(trn, portfolio, 'portfolio')
#         self.account_position = _val(trn, account_position, 'account_position')
#         self.account_cash = _val(trn, account_cash, 'account_cash')
#         self.account_interim = _val(trn, account_interim, 'account_interim')
#
#         self.strategy1_position = _val(trn, strategy1_position, 'strategy1_position')
#         self.strategy1_cash = _val(trn, strategy1_cash, 'strategy1_cash')
#         self.strategy2_position = _val(trn, strategy2_position, 'strategy2_position')
#         self.strategy2_cash = _val(trn, strategy2_cash, 'strategy2_cash')
#         self.strategy3_position = _val(trn, strategy3_position, 'strategy3_position')
#         self.strategy3_cash = _val(trn, strategy3_cash, 'strategy3_cash')
#
#         self.responsible = _val(trn, responsible, 'responsible')
#         self.counterparty = _val(trn, counterparty, 'counterparty')
#
#         self.linked_instrument = _val(trn, linked_instrument, 'linked_instrument')
#         self.allocation_balance = _val(trn, allocation_balance, 'allocation_balance')
#         self.allocation_pl = _val(trn, allocation_pl, 'allocation_pl')
#
#         self.reference_fx_rate = _val(trn, reference_fx_rate, 'reference_fx_rate')
#         self.factor = _val(trn, factor, 'factor')
#         self.trade_price = _val(trn, trade_price, 'trade_price')
#         self.position_amount = _val(trn, position_amount, 'position_amount')
#         self.principal_amount = _val(trn, principal_amount, 'principal_amount')
#         self.carry_amount = _val(trn, carry_amount, 'carry_amount')
#         self.overheads = _val(trn, overheads, 'overheads')
#         self.notes = _val(trn, notes, 'notes')
#
#         if self.id is None or self.id < 0:
#             self.attributes = []
#         else:
#             self.attributes = _val(trn, attributes, lambda: list(trn.attributes.all()))
#             # self.attributes = attributes if attributes is not empty else \
#             #     list(getattr(trn, 'attributes', None).all())
#
#         self.custom_fields = []
#
#     def __str__(self):
#         return 'TransactionReportItem:%s' % self.id
#
#     def eval_custom_fields(self):
#         # from poms.reports.serializers import ReportItemSerializer
#         res = []
#         for cf in self.report.custom_fields:
#             if cf.expr and self.report.member:
#                 try:
#                     names = {
#                         'item': self
#                     }
#                     value = formula.safe_eval(cf.expr, names=names, context=self.report.context)
#                 except formula.InvalidExpression:
#                     value = gettext_lazy('Invalid expression')
#             else:
#                 value = None
#             res.append({
#                 'custom_field': cf,
#                 'value': value
#             })
#         self.custom_fields = res
#
#
# class TransactionReport:
#     def __init__(self, id=None, task_id=None, task_status=None, master_user=None, member=None,
#                  begin_date=None, end_date=None, custom_fields=None, items=None):
#         self.has_errors = False
#         self.id = id
#         self.task_id = task_id
#         self.task_status = task_status
#         self.master_user = master_user
#         self.member = member
#         self.begin_date = begin_date
#         self.end_date = end_date
#         self.custom_fields = custom_fields or []
#
#         self.context = {
#             'master_user': self.master_user,
#             'member': self.member,
#         }
#
#         self.items = items
#
#         self.complex_transactions = []
#         self.transaction_types = []
#         self.transaction_classes = []
#         self.instruments = []
#         self.currencies = []
#         self.portfolios = []
#         self.accounts = []
#         self.strategies1 = []
#         self.strategies2 = []
#         self.strategies3 = []
#         self.responsibles = []
#         self.counterparties = []
#
#         self.complex_transaction_attribute_types = []
#         self.transaction_attribute_types = []
#         self.instrument_attribute_types = []
#         self.currency_attribute_types = []
#         self.portfolio_attribute_types = []
#         self.account_attribute_types = []
#         self.responsible_attribute_types = []
#         self.counterparty_attribute_types = []
#
#     def __str__(self):
#         return 'TransactionReport:%s' % self.id
#
#     def close(self):
#         for item in self.items:
#             item.eval_custom_fields()
#
#
# class TransactionReportBuilder:
#     def __init__(self, instance):
#         self.instance = instance
#         self._transactions = []
#         self._items = []
#
#         self._similar_cache = defaultdict(dict)
#
#         # self._complex_transactions = {}
#         # self._transaction_types = {}
#         # self._transaction_classes = {}
#         # self._instruments = {}
#         # self._currencies = {}
#         # self._portfolios ={}
#         # self._accounts = {}
#         # self._strategies1 = {}
#         # self._strategies2 = {}
#         # self._strategies3 = {}
#         # self._responsibles = {}
#         # self._counterparties = {}
#         # self._attribute_types = {}
#
#     def _get_ref(self, clazz, pk, obj=None):
#         tc = self._similar_cache[clazz]
#         try:
#             return tc[pk]
#         except KeyError:
#             if obj is not None:
#                 tc[pk] = obj
#                 return obj
#         return None
#
#     def _set_ref(self, obj, attr, attr_id=None, clazz=None):
#         if attr_id is None:
#             attr_id = '%s_id' % attr
#         pk = getattr(obj, attr_id, None)
#         if pk is None:
#             return
#         if clazz is None:
#             obj = getattr(obj, attr, None)
#             if obj is None:
#                 return
#             clazz = type(obj)
#         tc = self._similar_cache[clazz]
#         if pk in tc:
#             val = tc[pk]
#             setattr(obj, attr, val)
#         else:
#             val = getattr(obj, attr)
#             tc[pk] = val
#         return val
#
#     def _set_attrs(self, obj):
#         if obj:
#             for a in obj.attributes.all():
#                 self._set_ref(a, 'attribute_type', clazz=GenericAttributeType)
#
#     def _load(self):
#         from poms.obj_attrs.utils import get_attributes_prefetch
#
#         _l.debug('> _load')
#
#         qs = Transaction.objects.filter(
#             master_user=self.instance.master_user,
#             is_deleted=False,
#         ).filter(
#             Q(complex_transaction__isnull=True) | Q(complex_transaction__status=ComplexTransaction.PRODUCTION,
#                                                     complex_transaction__is_deleted=False)
#         ).prefetch_related(
#             'complex_transaction',
#             'transaction_class',
#             'instrument',
#             'transaction_currency',
#             'settlement_currency',
#             'portfolio',
#             'account_position',
#             'account_cash',
#             'account_interim',
#             'strategy1_position',
#             'strategy1_cash',
#             'strategy2_position',
#             'strategy2_cash',
#             'strategy3_position',
#             'strategy3_cash',
#             'responsible',
#             'counterparty',
#             'linked_instrument',
#             'allocation_balance',
#             'allocation_pl',
#             get_attributes_prefetch(),
#             get_attributes_prefetch('complex_transaction__attributes'),
#             get_attributes_prefetch('instrument__attributes'),
#             get_attributes_prefetch('transaction_currency__attributes'),
#             get_attributes_prefetch('settlement_currency__attributes'),
#             get_attributes_prefetch('portfolio__attributes'),
#             get_attributes_prefetch('account_position__attributes'),
#             get_attributes_prefetch('account_cash__attributes'),
#             get_attributes_prefetch('account_interim__attributes'),
#             get_attributes_prefetch('responsible__attributes'),
#             get_attributes_prefetch('counterparty__attributes'),
#             get_attributes_prefetch('linked_instrument__attributes'),
#             get_attributes_prefetch('allocation_balance__attributes'),
#             get_attributes_prefetch('allocation_pl__attributes'),
#         ).order_by(
#             'complex_transaction__date', 'complex_transaction__code', 'transaction_code'
#         )
#         # if settings.DEBUG:
#         #     qs = qs.filter(id__gt=1000)
#         begin_date = getattr(self.instance, 'begin_date', None)
#         if begin_date:
#             qs = qs.filter(complex_transaction__date__gte=begin_date)
#         end_date = getattr(self.instance, 'end_date', None)
#         if end_date:
#             qs = qs.filter(complex_transaction__date__lte=end_date)
#         self._transactions = list(qs)
#
#         _l.debug('< _load %s', len(self._transactions))
#
#     def _set_trns_refs(self, transactions):
#         # make all refs to single object
#         # _l.debug('> _set_trns_refs')
#         for t in transactions:
#             self._set_ref(t, 'complex_transaction', clazz=ComplexTransaction)
#             if t.complex_transaction:
#                 self._set_ref(t.complex_transaction, 'transaction_type', clazz=TransactionType)
#
#                 # for a in t.complex_transaction.attributes.all():
#                 #     self._set_ref(a, 'attribute_type', clazz=GenericAttributeType)
#                 self._set_attrs(t.complex_transaction)
#
#             self._set_ref(t, 'transaction_class', clazz=TransactionClass)
#             self._set_ref(t, 'instrument', clazz=Instrument)
#             self._set_attrs(t.instrument)
#             # if t.instrument:
#             #     self._set_ref(t.instrument, 'pricing_currency', clazz=Currency)
#             #     self._set_ref(t.instrument, 'accrued_currency', clazz=Currency)
#             self._set_ref(t, 'transaction_currency', clazz=Currency)
#             self._set_attrs(t.transaction_currency)
#             self._set_ref(t, 'settlement_currency', clazz=Currency)
#             self._set_attrs(t.settlement_currency)
#             self._set_ref(t, 'portfolio', clazz=Portfolio)
#             self._set_attrs(t.portfolio)
#             self._set_ref(t, 'account_position', clazz=Account)
#             self._set_attrs(t.account_position)
#             self._set_ref(t, 'account_cash', clazz=Account)
#             self._set_attrs(t.account_cash)
#             self._set_ref(t, 'account_interim', clazz=Account)
#             self._set_attrs(t.account_interim)
#             self._set_ref(t, 'strategy1_position', clazz=Strategy1)
#             self._set_ref(t, 'strategy1_cash', clazz=Strategy1)
#             self._set_ref(t, 'strategy2_position', clazz=Strategy2)
#             self._set_ref(t, 'strategy2_cash', clazz=Strategy2)
#             self._set_ref(t, 'strategy3_position', clazz=Strategy3)
#             self._set_ref(t, 'strategy3_cash', clazz=Strategy3)
#             self._set_ref(t, 'responsible', clazz=Responsible)
#             self._set_attrs(t.responsible)
#             self._set_ref(t, 'counterparty', clazz=Counterparty)
#             self._set_attrs(t.counterparty)
#             self._set_ref(t, 'linked_instrument', clazz=Instrument)
#             self._set_attrs(t.linked_instrument)
#             self._set_ref(t, 'allocation_balance', clazz=Instrument)
#             self._set_attrs(t.allocation_balance)
#             self._set_ref(t, 'allocation_pl', clazz=Instrument)
#             self._set_attrs(t.allocation_pl)
#
#             # if t.id > 0:
#             #     for a in t.attributes.all():
#             #         self._set_ref(a, 'attribute_type', clazz=GenericAttributeType)
#             #         # _l.debug('< _set_trns_refs')
#             self._set_attrs(t)
#
#     def _set_items_refs(self, items):
#         for t in items:
#             self._set_ref(t, 'complex_transaction', clazz=ComplexTransaction)
#             if t.complex_transaction:
#                 self._set_ref(t.complex_transaction, 'transaction_type', clazz=TransactionType)
#             self._set_ref(t, 'transaction_class', clazz=TransactionClass)
#             self._set_ref(t, 'instrument', clazz=Instrument)
#             if t.instrument:
#                 self._set_ref(t.instrument, 'pricing_currency', clazz=Currency)
#                 self._set_ref(t.instrument, 'accrued_currency', clazz=Currency)
#             self._set_ref(t, 'transaction_currency', clazz=Currency)
#             self._set_ref(t, 'settlement_currency', clazz=Currency)
#             self._set_ref(t, 'portfolio', clazz=Portfolio)
#             self._set_ref(t, 'account_position', clazz=Account)
#             self._set_ref(t, 'account_cash', clazz=Account)
#             self._set_ref(t, 'account_interim', clazz=Account)
#             self._set_ref(t, 'strategy1_position', clazz=Strategy1)
#             self._set_ref(t, 'strategy1_cash', clazz=Strategy1)
#             self._set_ref(t, 'strategy2_position', clazz=Strategy2)
#             self._set_ref(t, 'strategy2_cash', clazz=Strategy2)
#             self._set_ref(t, 'strategy3_position', clazz=Strategy3)
#             self._set_ref(t, 'strategy3_cash', clazz=Strategy3)
#             self._set_ref(t, 'responsible', clazz=Responsible)
#             self._set_ref(t, 'counterparty', clazz=Counterparty)
#             self._set_ref(t, 'linked_instrument', clazz=Instrument)
#             if t.linked_instrument:
#                 self._set_ref(t.linked_instrument, 'pricing_currency', clazz=Currency)
#                 self._set_ref(t.linked_instrument, 'accrued_currency', clazz=Currency)
#             self._set_ref(t, 'allocation_balance', clazz=Instrument)
#             if t.allocation_balance:
#                 self._set_ref(t.allocation_balance, 'pricing_currency', clazz=Currency)
#                 self._set_ref(t.allocation_balance, 'accrued_currency', clazz=Currency)
#             self._set_ref(t, 'allocation_pl', clazz=Instrument)
#             if t.allocation_pl:
#                 self._set_ref(t.allocation_pl, 'pricing_currency', clazz=Currency)
#                 self._set_ref(t.allocation_pl, 'accrued_currency', clazz=Currency)
#
#     def _refresh_from_db(self):
#         _l.debug('> _refresh_from_db')
#
#         complex_transactions = self._similar_cache[ComplexTransaction]
#         if complex_transactions:
#             qs = ComplexTransaction.objects.filter(
#                 transaction_type__master_user=self.instance.master_user,
#             ).prefetch_related(
#                 get_attributes_prefetch(),
#             )
#             complex_transactions.update(qs.in_bulk(id_list=complex_transactions.keys()))
#
#         transaction_types = self._similar_cache[TransactionType]
#         if transaction_types:
#             qs = TransactionType.objects.filter(
#                 master_user=self.instance.master_user,
#             ).prefetch_related(
#                 'group',
#                 *get_permissions_prefetch_lookups(
#                     (None, TransactionType),
#                     ('group', TransactionTypeGroup),
#                 )
#             )
#             transaction_types.update(qs.in_bulk(id_list=transaction_types.keys()))
#
#         instruments = self._similar_cache[Instrument]
#         if instruments:
#             qs = Instrument.objects.filter(
#                 master_user=self.instance.master_user,
#             ).prefetch_related(
#                 'instrument_type',
#                 'instrument_type__instrument_class',
#                 'pricing_currency',
#                 'accrued_currency',
#                 get_attributes_prefetch(),
#                 *get_permissions_prefetch_lookups(
#                     (None, Instrument),
#                     ('instrument_type', InstrumentType),
#                 )
#             )
#             instruments.update(qs.in_bulk(id_list=[pk for pk in instruments.keys() if pk > 0]))
#
#             for i in instruments.values():
#                 self._set_ref(i, 'pricing_currency', clazz=Currency)
#                 self._set_ref(i, 'accrued_currency', clazz=Currency)
#
#         currencies = self._similar_cache[Currency]
#         if currencies:
#             qs = Currency.objects.filter(
#                 master_user=self.instance.master_user,
#             ).prefetch_related(
#                 get_attributes_prefetch(),
#             )
#             currencies.update(qs.in_bulk(id_list=currencies.keys()))
#
#             for i in instruments.values():
#                 self._set_ref(i, 'pricing_currency', clazz=Currency)
#                 self._set_ref(i, 'accrued_currency', clazz=Currency)
#
#         portfolios = self._similar_cache[Portfolio]
#         if portfolios:
#             qs = Portfolio.objects.filter(
#                 master_user=self.instance.master_user,
#             ).prefetch_related(
#                 get_attributes_prefetch(),
#                 *get_permissions_prefetch_lookups(
#                     (None, Portfolio),
#                 )
#             )
#             portfolios.update(qs.in_bulk(id_list=portfolios.keys()))
#
#         accounts = self._similar_cache[Account]
#         if accounts:
#             qs = Account.objects.filter(
#                 master_user=self.instance.master_user,
#             ).prefetch_related(
#                 'type',
#                 get_attributes_prefetch(),
#                 *get_permissions_prefetch_lookups(
#                     (None, Account),
#                     ('type', AccountType),
#                 )
#             )
#             accounts.update(qs.in_bulk(id_list=accounts.keys()))
#
#         strategies1 = self._similar_cache[Strategy1]
#         if strategies1:
#             qs = Strategy1.objects.filter(
#                 master_user=self.instance.master_user,
#             ).prefetch_related(
#                 'subgroup',
#                 'subgroup__group',
#                 *get_permissions_prefetch_lookups(
#                     (None, Strategy1),
#                     ('subgroup', Strategy1Subgroup),
#                     ('subgroup__group', Strategy1Group),
#                 )
#             )
#             strategies1.update(qs.in_bulk(id_list=strategies1.keys()))
#
#         strategies2 = self._similar_cache[Strategy2]
#         if strategies2:
#             qs = Strategy2.objects.filter(
#                 master_user=self.instance.master_user,
#             ).prefetch_related(
#                 'subgroup',
#                 'subgroup__group',
#                 *get_permissions_prefetch_lookups(
#                     (None, Strategy2),
#                     ('subgroup', Strategy2Subgroup),
#                     ('subgroup__group', Strategy2Group),
#                 )
#             )
#             strategies2.update(qs.in_bulk(id_list=strategies2.keys()))
#
#         strategies3 = self._similar_cache[Strategy3]
#         if strategies3:
#             qs = Strategy3.objects.filter(
#                 master_user=self.instance.master_user,
#             ).prefetch_related(
#                 'subgroup',
#                 'subgroup__group',
#                 *get_permissions_prefetch_lookups(
#                     (None, Strategy3),
#                     ('subgroup', Strategy3Subgroup),
#                     ('subgroup__group', Strategy3Group),
#                 )
#             )
#             strategies3.update(qs.in_bulk(id_list=strategies3.keys()))
#
#         responsibles = self._similar_cache[Responsible]
#         if responsibles:
#             qs = Responsible.objects.filter(
#                 master_user=self.instance.master_user,
#             ).prefetch_related(
#                 'group',
#                 get_attributes_prefetch(),
#                 *get_permissions_prefetch_lookups(
#                     (None, Responsible),
#                     ('group', ResponsibleGroup),
#                 )
#             )
#             responsibles.update(qs.in_bulk(id_list=responsibles.keys()))
#
#         counterparties = self._similar_cache[Counterparty]
#         if counterparties:
#             qs = Counterparty.objects.filter(
#                 master_user=self.instance.master_user,
#             ).prefetch_related(
#                 'group',
#                 get_attributes_prefetch(),
#                 *get_permissions_prefetch_lookups(
#                     (None, Counterparty),
#                     ('group', CounterpartyGroup),
#                 )
#             )
#             counterparties.update(qs.in_bulk(id_list=counterparties.keys()))
#
#         attribute_types = self._similar_cache[GenericAttributeType]
#         if attribute_types:
#             qs = GenericAttributeType.objects.filter(
#                 master_user=self.instance.master_user,
#             ).prefetch_related(
#                 'content_type',
#                 'options',
#                 'classifiers',
#                 *get_permissions_prefetch_lookups(
#                     (None, GenericAttributeType),
#                 )
#             )
#             attribute_types.update(qs.in_bulk(id_list=attribute_types.keys()))
#
#         _l.debug('< _refresh_from_db')
#
#     def _update_instance(self):
#         self.instance.items = self._items
#
#         for clazz, objects in self._similar_cache.items():
#
#             if clazz is ComplexTransaction:
#                 self.instance.complex_transactions = list(objects.values())
#
#             elif clazz is TransactionType:
#                 self.instance.transaction_types = list(objects.values())
#
#             elif clazz is TransactionClass:
#                 self.instance.transaction_classes = list(objects.values())
#
#             elif clazz is Instrument:
#                 self.instance.instruments = list(objects.values())
#
#             elif clazz is Currency:
#                 self.instance.currencies = list(objects.values())
#
#             elif clazz is Portfolio:
#                 self.instance.portfolios = list(objects.values())
#
#             elif clazz is Account:
#                 self.instance.accounts = list(objects.values())
#
#             elif clazz is Strategy1:
#                 self.instance.strategies1 = list(objects.values())
#
#             elif clazz is Strategy2:
#                 self.instance.strategies2 = list(objects.values())
#
#             elif clazz is Strategy3:
#                 self.instance.strategies3 = list(objects.values())
#
#             elif clazz is Responsible:
#                 self.instance.responsibles = list(objects.values())
#
#             elif clazz is Counterparty:
#                 self.instance.counterparties = list(objects.values())
#
#             elif clazz is GenericAttributeType:
#                 self.instance.complex_transaction_attribute_types = []
#                 self.instance.transaction_attribute_types = []
#                 self.instance.instrument_attribute_types = []
#                 self.instance.currency_attribute_types = []
#                 self.instance.portfolio_attribute_types = []
#                 self.instance.account_attribute_types = []
#                 self.instance.responsible_attribute_types = []
#                 self.instance.counterparty_attribute_types = []
#
#                 for at in objects.values():
#                     model_class = at.content_type.model_class()
#
#                     if issubclass(model_class, ComplexTransaction):
#                         self.instance.complex_transaction_attribute_types.append(at)
#
#                     elif issubclass(model_class, Transaction):
#                         self.instance.transaction_attribute_types.append(at)
#
#                     elif issubclass(model_class, Instrument):
#                         self.instance.instrument_attribute_types.append(at)
#
#                     elif issubclass(model_class, Currency):
#                         self.instance.currency_attribute_types.append(at)
#
#                     elif issubclass(model_class, Portfolio):
#                         self.instance.portfolio_attribute_types.append(at)
#
#                     elif issubclass(model_class, Account):
#                         self.instance.account_attribute_types.append(at)
#
#                     elif issubclass(model_class, Responsible):
#                         self.instance.responsible_attribute_types.append(at)
#
#                     elif issubclass(model_class, Counterparty):
#                         self.instance.counterparty_attribute_types.append(at)
#
#     def build(self):
#         _l.debug('> build')
#         with transaction.atomic():
#             # if settings.DEBUG:
#             #     _l.debug('> _make_transactions')
#             #     self._make_transactions(10000)
#             #     _l.debug('< _make_transactions')
#
#             self._load()
#             self._set_trns_refs(self._transactions)
#             self._items = [TransactionReportItem(self.instance, trn=t) for t in self._transactions]
#             self._refresh_from_db()
#             self._set_items_refs(self._items)
#             self._update_instance()
#             self.instance.close()
#
#             # if settings.DEBUG:
#             #     _l.debug('> pickle')
#             #     import pickle
#             #     data = pickle.dumps(self.instance, protocol=pickle.HIGHEST_PROTOCOL)
#             #     _l.debug('< pickle: %s', len(data))
#             #     _l.debug('> pickle.zlib')
#             #     import zlib
#             #     data1 = zlib.compress(data)
#             #     _l.debug('< pickle.zlib: %s', len(data1))
#             #
#             #     _l.debug('> json')
#             #     from poms.reports.serializers import TransactionReportSerializer
#             #     from rest_framework.renderers import JSONRenderer
#             #     s = TransactionReportSerializer(instance=self.instance, context={
#             #         'master_user': self.instance.master_user,
#             #         'member': self.instance.member,
#             #     })
#             #     data_dict = s.data
#             #     r = JSONRenderer()
#             #     data = r.render(data_dict)
#             #     _l.debug('< json: %s', len(data))
#             #     _l.debug('> json.zlib')
#             #     import zlib
#             #     data1 = zlib.compress(data)
#             #     _l.debug('< json.zlib: %s', len(data1))
#
#             transaction.set_rollback(True)
#         _l.debug('< build')
#         return self.instance
#
#     def _make_transactions(self, count=100):
#         from poms.common.utils import date_now
#
#         tcls = TransactionClass.objects.get(pk=TransactionClass.BUY)
#
#         tt = list(TransactionType.objects.filter(master_user=self.instance.master_user).all())
#         instr = list(Instrument.objects.filter(master_user=self.instance.master_user).all())
#         ccy = list(Currency.objects.filter(master_user=self.instance.master_user).all())
#         p = list(Portfolio.objects.filter(master_user=self.instance.master_user).all())
#         acc = list(Account.objects.filter(master_user=self.instance.master_user).all())
#         s1 = list(Strategy1.objects.filter(master_user=self.instance.master_user).all())
#         s2 = list(Strategy2.objects.filter(master_user=self.instance.master_user).all())
#         s3 = list(Strategy3.objects.filter(master_user=self.instance.master_user).all())
#         r = list(Responsible.objects.filter(master_user=self.instance.master_user).all())
#         c = list(Counterparty.objects.filter(master_user=self.instance.master_user).all())
#
#         ctrns = []
#         trns = []
#
#         for i in range(0, count):
#             ct = ComplexTransaction(
#                 transaction_type=random.choice(tt),
#                 date=date_now() + datetime.timedelta(days=i),
#                 status=ComplexTransaction.PRODUCTION,
#                 code=i
#             )
#             ctrns.append(ct)
#             t = Transaction(
#                 master_user=self.instance.master_user,
#                 complex_transaction=ct,
#                 complex_transaction_order=1,
#                 transaction_code=1,
#                 transaction_class=tcls,
#                 instrument=random.choice(instr),
#                 transaction_currency=random.choice(ccy),
#                 position_size_with_sign=100,
#                 settlement_currency=random.choice(ccy),
#                 cash_consideration=-90,
#                 principal_with_sign=100,
#                 carry_with_sign=100,
#                 overheads_with_sign=100,
#                 transaction_date=date_now() + datetime.timedelta(days=i),
#                 accounting_date=date_now() + datetime.timedelta(days=i),
#                 cash_date=date_now() + datetime.timedelta(days=i),
#                 portfolio=random.choice(p),
#                 account_position=random.choice(acc),
#                 account_cash=random.choice(acc),
#                 account_interim=random.choice(acc),
#                 strategy1_position=random.choice(s1),
#                 strategy1_cash=random.choice(s1),
#                 strategy2_position=random.choice(s2),
#                 strategy2_cash=random.choice(s2),
#                 strategy3_position=random.choice(s3),
#                 strategy3_cash=random.choice(s3),
#                 responsible=random.choice(r),
#                 counterparty=random.choice(c),
#                 linked_instrument=random.choice(instr),
#                 allocation_balance=random.choice(instr),
#                 allocation_pl=random.choice(instr),
#             )
#             trns.append(t)
#
#         ComplexTransaction.objects.bulk_create(ctrns)
#         Transaction.objects.bulk_create(trns)
#
#
# class CashFlowProjectionReportItem(TransactionReportItem):
#     DEFAULT = 1
#     BALANCE = 2
#     ROLLING = 3
#     TYPE_CHOICE = (
#         (DEFAULT, 'Default'),
#         (BALANCE, 'Balance'),
#     )
#
#     def __init__(self, report, type=DEFAULT, trn=None, cash_consideration_before=0.0, cash_consideration_after=0.0, **kwargs):
#         super(CashFlowProjectionReportItem, self).__init__(report, trn, **kwargs)
#         self.type = type
#         # self.position_size_with_sign_before = position_size_with_sign_before
#         # self.position_size_with_sign_after = position_size_with_sign_after
#         self.cash_consideration_before = cash_consideration_before
#         self.cash_consideration_after = cash_consideration_after
#
#     def add_balance(self, trn_or_item):
#         self.position_size_with_sign += trn_or_item.position_size_with_sign
#         self.cash_consideration += trn_or_item.cash_consideration
#         self.principal_with_sign += trn_or_item.principal_with_sign
#         self.carry_with_sign += trn_or_item.carry_with_sign
#         self.overheads_with_sign += trn_or_item.overheads_with_sign
#
#     def __str__(self):
#         return 'CashFlowProjectionReportItem:%s' % self.id
#
#
# class CashFlowProjectionReport(TransactionReport):
#     def __init__(self, balance_date=None, report_date=None, **kwargs):
#         super(CashFlowProjectionReport, self).__init__(**kwargs)
#         self.balance_date = balance_date
#         self.report_date = report_date
#
#     def __str__(self):
#         return 'CashFlowProjectionReport:%s' % self.id
#
#
# class CashFlowProjectionReportBuilder(TransactionReportBuilder):
#     def __init__(self, instance):
#         super(CashFlowProjectionReportBuilder, self).__init__(instance)
#
#         self._transactions_by_date = None
#
#         self._balance_items = {}
#         self._rolling_items = {}
#         # self._generated_transactions = []
#
#         # self._instrument_event_cache = {}
#
#         self._id_seq = 0
#         self._transaction_order_seq = 0
#
#     def _fake_id_gen(self):
#         self._id_seq -= 1
#         return self._id_seq
#
#     def _trn_order_gen(self):
#         self._transaction_order_seq += 1
#         return self._transaction_order_seq
#
#     def _trn_key(self, trn, acc=empty):
#         if acc is empty:
#             acc = trn.account_cash
#         return (
#             _check_int_min(getattr(trn.settlement_currency, 'id', None)),
#             _check_int_min(getattr(trn.portfolio, 'id', None)),
#             _check_int_min(getattr(acc, 'id', None)),
#             # getattr(trn.instrument, 'id', -1),
#         )
#
#     def _item(self, cache, trn, key, itype=CashFlowProjectionReportItem.DEFAULT):
#         if key is None:
#             key = self._trn_key(trn)
#         item = cache.get(key, None)
#         if item is None:
#             # override by '-'
#             if itype in [CashFlowProjectionReportItem.BALANCE, CashFlowProjectionReportItem.ROLLING]:
#                 ctrn = ComplexTransaction(
#                     # id=self._fake_id_gen(),
#                     date=self.instance.balance_date,
#                     status=ComplexTransaction.PRODUCTION,
#                     code=-sys.maxsize,
#                 )
#                 ctrn._fake_transactions = []
#                 item = CashFlowProjectionReportItem(
#                     self.instance,
#                     type=itype,
#                     # id=self._fake_id_gen(),
#                     complex_transaction=ctrn,
#                     complex_transaction_order=0,
#                     transaction_code=-sys.maxsize,
#                     trn=trn,
#                     transaction_currency=trn.settlement_currency,
#                     account_cash=self.instance.master_user.account,
#                     account_interim=self.instance.master_user.account,
#                     strategy1_position=self.instance.master_user.strategy1,
#                     strategy1_cash=self.instance.master_user.strategy1,
#                     strategy2_position=self.instance.master_user.strategy2,
#                     strategy2_cash=self.instance.master_user.strategy2,
#                     strategy3_position=self.instance.master_user.strategy3,
#                     strategy3_cash=self.instance.master_user.strategy3,
#                     responsible=self.instance.master_user.responsible,
#                     counterparty=self.instance.master_user.counterparty,
#                     linked_instrument=self.instance.master_user.instrument,
#                     allocation_balance=self.instance.master_user.instrument,
#                     allocation_pl=self.instance.master_user.instrument,
#                     attributes=[],
#                     transaction_class=None,
#                     position_size_with_sign=0.0,
#                     cash_consideration=0.0,
#                     principal_with_sign=0.0,
#                     carry_with_sign=0.0,
#                     overheads_with_sign=0.0,
#                     transaction_date=self.instance.balance_date,
#                     accounting_date=self.instance.balance_date,
#                     cash_date=self.instance.balance_date,
#                     reference_fx_rate=1.0,
#                 )
#                 if itype == CashFlowProjectionReportItem.BALANCE:
#                     item.instrument = None
#                 elif itype == CashFlowProjectionReportItem.ROLLING:
#                     item.complex_transaction.date = datetime.date.max
#                     # item.complex_transaction.code = sys.maxsize
#                     # item.transaction_code = sys.maxsize
#                     item.transaction_date = datetime.date.max
#                     item.accounting_date = datetime.date.max
#                     item.cash_date = datetime.date.max
#             else:
#                 item = CashFlowProjectionReportItem(self.instance, type=itype, trn=trn)
#             cache[key] = item
#         return item
#
#     def _balance(self, trn, key=None):
#         return self._item(self._balance_items, trn, key, itype=CashFlowProjectionReportItem.BALANCE)
#
#     def _rolling(self, trn, key=None):
#         return self._item(self._rolling_items, trn, key, itype=CashFlowProjectionReportItem.ROLLING)
#
#     def build(self):
#         _l.debug('> build')
#         with transaction.atomic():
#             self._load()
#             self._set_trns_refs(self._transactions)
#             self._step1()
#             self._step2()
#             self._step3()
#             self._refresh_from_db()
#             self._set_items_refs(self._items)
#             self._update_instance()
#             self.instance.close()
#             transaction.set_rollback(True)
#         _l.debug('< build')
#         return self.instance
#
#     def _step1(self):
#         self._transactions_by_date = defaultdict(list)
#         self._items = []
#         self._balance_items = {}
#         self._rolling_items = {}
#
#         for t in self._transactions:
#             self._transaction_order_seq = max(self._transaction_order_seq, int(t.transaction_code))
#
#             d = getattr(t.complex_transaction, 'date', datetime.date.min)
#             self._transactions_by_date[d].append(t)
#
#             if d <= self.instance.balance_date:
#                 key = self._trn_key(t)
#                 bitem = self._balance(t, key)
#                 bitem.add_balance(t)
#
#                 if t.transaction_class_id in [TransactionClass.BUY, TransactionClass.SELL]:
#                     key = self._trn_key(t)
#                     ritem = self._rolling(t, key)
#                     ritem.add_balance(t)
#                 elif t.transaction_class_id in [TransactionClass.TRANSFER]:
#                     raise RuntimeError('implement me please')
#
#         for k, bitem in self._balance_items.items():
#             self._items.append(bitem)
#
#             # if settings.DEBUG:
#             #     for k, ritem in self._rolling_items.items():
#             #         self._items.append(ritem)
#
#     def _step2(self):
#         # eval future events
#         now = self.instance.balance_date
#         td1 = datetime.timedelta(days=1)
#         while now < self.instance.report_date:
#             now += td1
#             _l.debug('\tnow=%s', now.isoformat())
#
#             # check events
#             for key, ritem in self._rolling_items.items():
#                 instr = ritem.instrument
#                 if instr is None:
#                     raise RuntimeError('code bug (instrument is None)')
#
#                 for es in instr.event_schedules.all():
#                     is_complies, edate, ndate = es.check_date(now)
#                     if is_complies:
#                         e = GeneratedEvent()
#                         e.master_user = self.instance.master_user
#                         e.event_schedule = es
#                         e.status = GeneratedEvent.NEW
#                         e.effective_date = edate
#                         e.notification_date = ndate
#                         e.instrument = ritem.instrument
#                         e.portfolio = ritem.portfolio
#                         e.account = ritem.account_position
#                         e.strategy1 = ritem.strategy1_position
#                         e.strategy2 = ritem.strategy2_position
#                         e.strategy3 = ritem.strategy3_position
#                         e.position = ritem.position_size_with_sign
#
#                         if e.is_apply_default_on_date(now):
#                             a = e.get_default_action()
#                             if a:
#                                 self._set_ref(a, 'transaction_type', clazz=TransactionType)
#
#                                 _l.debug('\t\t\tevent_schedule=%s, action=%s, confirmed', es.id, a.id)
#                                 gep = GeneratedEventProcess(
#                                     generated_event=e,
#                                     action=a,
#                                     fake_id_gen=self._fake_id_gen,
#                                     transaction_order_gen=self._trn_order_gen,
#                                     now=now
#                                 )
#                                 gep.process()
#                                 if gep.has_errors:
#                                     self.instance.has_errors = True
#                                 else:
#                                     # for i2 in gep.instruments:
#                                     #     if i2.id < 0 and i2.id not in self._instruments:
#                                     #         self._instruments[i2.id] = i2
#                                     # gep.complex_transaction._fake_transactions = list(gep.transactions)
#                                     # self._prefetch(gep.transactions)
#                                     self._set_trns_refs(gep.transactions)
#                                     for t2 in gep.transactions:
#                                         _l.debug('\t\t\t+trn=%s', t2.id)
#                                         d = getattr(t2.complex_transaction, 'date', datetime.date.max)
#                                         self._transactions_by_date[d].append(t2)
#
#             # process transactions
#             if now in self._transactions_by_date:
#                 for t in self._transactions_by_date[now]:
#                     _l.debug('\t\t\ttrn=%s', t.id)
#                     key = self._trn_key(t)
#                     item = CashFlowProjectionReportItem(self.instance, trn=t)
#                     self._items.append(item)
#
#                     ritem = None
#                     if t.transaction_class_id in [TransactionClass.BUY, TransactionClass.SELL]:
#                         ritem = self._rolling(t, key)
#                         ritem.add_balance(t)
#                     elif t.transaction_class_id in [TransactionClass.TRANSFER]:
#                         raise RuntimeError('implement me please')
#
#                     if ritem and isclose(ritem.position_size_with_sign, 0.0):
#                         del self._rolling_items[key]
#
#     def _step3(self):
#         # aggregate some rolling values
#         # sort result
#
#         def _sort_key(i):
#             if i.type == CashFlowProjectionReportItem.BALANCE:
#                 type_sort_val = 0
#             elif i.type == CashFlowProjectionReportItem.DEFAULT:
#                 type_sort_val = 1
#             else:
#                 type_sort_val = 2
#             return (
#                 _check_int_min(getattr(i.settlement_currency, 'id', None)),
#                 _check_int_min(getattr(i.portfolio, 'id', None)),
#                 _check_int_min(getattr(i.account_cash, 'id', None)),
#                 # getattr(trn.instrument, 'id', -1),
#                 type_sort_val,
#                 _check_date_min(getattr(i.complex_transaction, 'date', None)),
#                 _check_int_min(getattr(i.complex_transaction, 'code', None)),
#                 _check_int_min(i.complex_transaction_order),
#                 _check_int_min(i.transaction_code),
#             )
#
#         def _group_key(i):
#             return (
#                 # _check_date_min(getattr(i.complex_transaction, 'date', None)),
#                 # _check_int_min(getattr(i.complex_transaction, 'code', None)),
#                 # _check_int_min(i.complex_transaction_order),
#                 # _check_int_min(i.transaction_code),
#                 _check_int_min(getattr(i.settlement_currency, 'id', None)),
#                 _check_int_min(getattr(i.portfolio, 'id', None)),
#                 _check_int_min(getattr(i.account_cash, 'id', None)),
#             )
#
#         items = sorted(self._items, key=_sort_key)
#         for k, g in groupby(items, key=_group_key):
#             rolling_cash_consideration = 0.0
#             for i in g:
#                 if i.type == CashFlowProjectionReportItem.BALANCE:
#                     rolling_cash_consideration = i.cash_consideration
#                     i.cash_consideration_before = 0.0
#                     i.cash_consideration_after = rolling_cash_consideration
#                 else:
#                     i.cash_consideration_before = rolling_cash_consideration
#                     i.cash_consideration_after = i.cash_consideration_before + i.cash_consideration
#                     rolling_cash_consideration = i.cash_consideration_after
#
#         def _resp_sort_key(i):
#             # if i.type == CashFlowProjectionReportItem.BALANCE:
#             #     type_sort_val = 0
#             # elif i.type == CashFlowProjectionReportItem.DEFAULT:
#             #     type_sort_val = 1
#             # else:
#             #     type_sort_val = 2
#             return (
#                 _check_date_min(getattr(i.complex_transaction, 'date', None)),
#                 # type_sort_val,
#                 _check_int_min(getattr(i.complex_transaction, 'code', None)),
#                 _check_int_min(i.complex_transaction_order),
#                 _check_int_min(i.transaction_code),
#             )
#
#         self._items = sorted(self._items, key=_resp_sort_key)
