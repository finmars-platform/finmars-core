import datetime
import logging
import sys
import time
from collections import defaultdict
from itertools import groupby

from django.db import transaction

from poms.common.utils import isclose
from poms.instruments.handlers import GeneratedEventProcess
from poms.instruments.models import GeneratedEvent
from poms.reports.builders.cash_flow_projection_item import CashFlowProjectionReportItem
from poms.reports.builders.transaction import TransactionReportBuilder
from poms.reports.builders.transaction_item import empty, check_int_min, check_date_min
from poms.transactions.models import TransactionType, TransactionClass

_l = logging.getLogger('poms.reports')


class CashFlowProjectionReportBuilder(TransactionReportBuilder):
    def __init__(self, instance):
        super(CashFlowProjectionReportBuilder, self).__init__(instance)

        self._transactions_by_date = defaultdict(list)
        self._items = []
        self._balance_items = {}
        self._rolling_items = {}

        # self._generated_transactions = []
        # self._instrument_event_cache = {}

        self._id_seq = 0
        self._transaction_order_seq = 0

    def build(self):
        st = time.perf_counter()
        _l.debug('build cash flow projection')

        with transaction.atomic():
            try:
                self._load()
                # self._set_trns_refs(self._transactions)

                self._calc_balance()
                self._calc_future()
                self._calc_before_after()

                self.instance.items = self._items
                self._refresh_from_db()
                # self._set_items_refs(self._items)
                # self._update_instance()
                self.instance.close()
            finally:
                transaction.set_rollback(True)

        _l.debug('done: %s', (time.perf_counter() - st))
        return self.instance

    def _fake_id_gen(self):
        self._id_seq -= 1
        return self._id_seq

    def _trn_qs(self):
        qs = super(CashFlowProjectionReportBuilder, self)._trn_qs()
        qs = qs.prefetch_related(
            'instrument__event_schedules',
            'instrument__event_schedules__actions',
        )
        return qs

    def _trn_order_gen(self):
        self._transaction_order_seq += 1
        return self._transaction_order_seq

    def _balance_trn_key(self, trn, stl_ccy=None, prtfl=empty, acc=empty):
        if prtfl is empty:
            prtfl = trn.portfolio
        if acc is empty:
            acc = trn.account_cash
        if stl_ccy is empty:
            stl_ccy = trn.settlement_currency
        return (
            check_int_min(getattr(prtfl, 'id', None)),
            check_int_min(getattr(acc, 'id', None)),
            check_int_min(getattr(stl_ccy, 'id', None)),
        )

    def _instr_rolling_trn_key(self, trn, prtfl=empty, acc=empty, instr=empty):
        if prtfl is empty:
            prtfl = trn.portfolio
        if acc is empty:
            acc = trn.account_position
        if instr is empty:
            instr = trn.instrument
        return (getattr(prtfl, 'id', None), getattr(acc, 'id', None), getattr(instr, 'id', -1),)

    def _item(self, cache, trn, key, itype=CashFlowProjectionReportItem.DEFAULT):
        if key is None:
            raise RuntimeError('key must be specified')
        item = cache.get(key, None)
        if item is None:
            # override by '-'
            if itype in [CashFlowProjectionReportItem.BALANCE, CashFlowProjectionReportItem.ROLLING]:
                # ctrn = ComplexTransaction(
                #     id=self._fake_id_gen(),
                #     date=self.instance.balance_date,
                #     status=ComplexTransaction.PRODUCTION,
                #     code=-sys.maxsize,
                # )
                # ctrn._fake_transactions = []
                ctrn = None
                item = CashFlowProjectionReportItem(
                    self.instance,
                    type=itype,
                    # id=self._fake_id_gen(),
                    complex_transaction=ctrn,
                    complex_transaction_order=0,
                    transaction_code=-sys.maxsize,
                    trn=trn,
                    transaction_currency=trn.settlement_currency,
                    account_cash=self.instance.master_user.account,
                    account_interim=self.instance.master_user.account,
                    strategy1_position=self.instance.master_user.strategy1,
                    strategy1_cash=self.instance.master_user.strategy1,
                    strategy2_position=self.instance.master_user.strategy2,
                    strategy2_cash=self.instance.master_user.strategy2,
                    strategy3_position=self.instance.master_user.strategy3,
                    strategy3_cash=self.instance.master_user.strategy3,
                    responsible=self.instance.master_user.responsible,
                    counterparty=self.instance.master_user.counterparty,
                    linked_instrument=self.instance.master_user.instrument,
                    allocation_balance=self.instance.master_user.instrument,
                    allocation_pl=self.instance.master_user.instrument,
                    attributes=[],
                    transaction_class=None,
                    position_size_with_sign=0.0,
                    cash_consideration=0.0,
                    principal_with_sign=0.0,
                    carry_with_sign=0.0,
                    overheads_with_sign=0.0,
                    transaction_date=self.instance.balance_date,
                    accounting_date=self.instance.balance_date,
                    cash_date=self.instance.balance_date,
                    reference_fx_rate=1.0,
                )
                if itype == CashFlowProjectionReportItem.BALANCE:
                    item.instrument = None
                elif itype == CashFlowProjectionReportItem.ROLLING:
                    if item.complex_transaction:
                        item.complex_transaction.date = datetime.date.max
                    # item.complex_transaction.code = sys.maxsize
                    # item.transaction_code = sys.maxsize
                    item.transaction_date = datetime.date.max
                    item.accounting_date = datetime.date.max
                    item.cash_date = datetime.date.max
            else:
                item = CashFlowProjectionReportItem(self.instance, type=itype, trn=trn)
            item.key = key
            cache[key] = item
        return item

    def _balance(self, trn, key=None):
        if key is None:
            key = self._balance_trn_key(trn)
        return self._item(self._balance_items, trn, key, itype=CashFlowProjectionReportItem.BALANCE)

    def _rolling(self, trn, key=None):
        if key is None:
            key = self._instr_rolling_trn_key(trn)
        return self._item(self._rolling_items, trn, key, itype=CashFlowProjectionReportItem.ROLLING)

    def _calc_balance(self):
        # calculate balance
        for t in self._transactions:
            self._transaction_order_seq = max(self._transaction_order_seq, int(t.transaction_code))

            d = getattr(t.complex_transaction, 'date', datetime.date.min)
            self._transactions_by_date[d].append(t)

            if d <= self.instance.balance_date:
                bitem = self._balance(t)
                bitem.add_balance(t)

                if t.transaction_class_id in [TransactionClass.BUY, TransactionClass.SELL]:
                    ritem = self._rolling(t)
                    ritem.add_balance(t)
                elif t.transaction_class_id in [TransactionClass.TRANSFER]:
            # raise RuntimeError('implement me please')

        # remove items with position_size_with_sign close to zero
        rolling_items_to_remove = set()
        for key, ritem in self._rolling_items.items():
            if isclose(ritem.position_size_with_sign, 0.0):
                rolling_items_to_remove.add(key)
                # del self._rolling_items[key]

        for key in rolling_items_to_remove:
            del self._rolling_items[key]

        for k, bitem in self._balance_items.items():
            self._items.append(bitem)

            # if settings.DEBUG:
            #     for k, ritem in self._rolling_items.items():
            #         self._items.append(ritem)

    def _calc_future(self):
        # eval future events

        # for key, ritem in self._rolling_items.items():
        #     instr = ritem.instrument
        #     for es in instr.event_schedules.all():
        #         _l.info('event_schedule.get_dates: %s -> %s', es, [(str(edate), str(ndate)) for edate, ndate in es.all_dates])

        now = self.instance.balance_date
        td1 = datetime.timedelta(days=1)
        while now < self.instance.report_date:
            now += td1
            # _l.debug('now=%s', now.isoformat())

            # check events only for exist elements on balance date
            for key, ritem in self._rolling_items.items():
                instr = ritem.instrument

                if instr is None:
                    raise RuntimeError('code bug (instrument is None)')

                # _l.debug('instr: id=%s, code=%s, position=%s',
                #          instr.id, instr.user_code, ritem.position_size_with_sign)

                # for es in instr.event_schedules.all():
                #     is_complies, edate, ndate = es.check_date(now)
                #
                #     # _l.debug('sched: %s, instr=%s, id=%s, is_complies=%s, edate=%s, ndate=%s',
                #     #          now, instr, es.id, is_complies, edate, ndate)
                #
                #     if is_complies:
                #         e = GeneratedEvent()
                #         e.master_user = self.instance.master_user
                #         e.event_schedule = es
                #         e.status = GeneratedEvent.NEW
                #         e.effective_date = edate
                #         e.notification_date = ndate
                #         e.instrument = ritem.instrument
                #         e.portfolio = ritem.portfolio
                #         e.account = ritem.account_position
                #         e.strategy1 = ritem.strategy1_position
                #         e.strategy2 = ritem.strategy2_position
                #         e.strategy3 = ritem.strategy3_position
                #         e.position = ritem.position_size_with_sign
                #
                #         is_apply_default_on_date = e.is_apply_default_on_date(now)
                #         is_need_reaction_on_date = e.is_need_reaction_on_date(now)
                #         # is_apply = is_apply_default_on_date
                #         is_apply = edate == now
                #         action = e.get_default_action() if is_apply else None
                #
                #         _l.debug(
                #             'evt: %s, '
                #             'es=%s, accrual=%s, factor=%s, '
                #             'action=%s/%s, '
                #             'effective_date=%s, notification_date=%s, '
                #             'is_apply_default_on_date=%s, is_need_reaction_on_date=%s',
                #             str(now),
                #             es.id, es.accrual_calculation_schedule, es.factor_schedule,
                #             getattr(action, 'transaction_type', None), getattr(action, 'is_book_automatic', None),
                #             str(edate), str(ndate),
                #             is_apply_default_on_date, is_need_reaction_on_date
                #         )
                #
                #         if action:
                #             # continue
                #             # if not action.is_book_automatic:
                #             #     continue
                #
                #             self._set_ref(action, 'transaction_type', clazz=TransactionType)
                #             gep = GeneratedEventProcess(
                #                 generated_event=e,
                #                 action=action,
                #                 fake_id_gen=self._fake_id_gen,
                #                 transaction_order_gen=self._trn_order_gen,
                #                 now=now,
                #                 context={
                #                     'master_user': self.instance.master_user,
                #                     'member': self.instance.member,
                #                 }
                #             )
                #             gep.process()
                #             if gep.has_errors:
                #                 self.instance.has_errors = True
                #             else:
                #                 for t2 in gep.transactions:
                #                     _l.debug('gen trn: id=%s, c.id=%s, c.date=%s, acc_date=%s, cash_date=%s',
                #                              t2.id, t2.complex_transaction.id, t2.complex_transaction.date,
                #                              t2.accounting_date, t2.cash_date)
                #                     # d = t2.complex_transaction.date or datetime.date.max
                #                     # self._transactions_by_date[d].append(t2)
                #
                #                     d = t2.accounting_date or datetime.date.max
                #                     self._transactions_by_date[d].append(t2)
                self._generate(ritem, now)

            # process transactions for current date
            # if now in self._transactions_by_date:
            #     for t in self._transactions_by_date[now]:
            #         _l.debug('trn=%s', t.id)
            #         item = CashFlowProjectionReportItem(self.instance, trn=t)
            #         self._items.append(item)
            #
            #         if t.transaction_class_id in [TransactionClass.BUY, TransactionClass.SELL]:
            #             key = self._instr_rolling_trn_key(t)
            #             ritem = self._rolling(t, key=key)
            #             ritem.add_balance(t)
            #
            #             _l.debug('instr check pos: key=%s; pos_size=%s', key, ritem.position_size_with_sign)
            #             if isclose(ritem.position_size_with_sign, 0.0):
            #                 del self._rolling_items[key]
            #
            #         elif t.transaction_class_id in [TransactionClass.TRANSFER]:
            #             # TODO: check me
            #             src_key = self._instr_rolling_trn_key(t, acc=t.account_cash)
            #             src_item = self._rolling(t, key=src_key)
            #             src_item.add_balance(t, sign=-1)
            #
            #             dst_key = self._instr_rolling_trn_key(t, acc=t.account_position)
            #             dst_item = self._rolling(t, key=dst_key)
            #             dst_item.add_balance(t)
            #
            #             _l.debug('instr check pos (trnfr, src): key=%s; pos_size=%s', src_key,
            #                      src_item.position_size_with_sign)
            #             if isclose(src_item.position_size_with_sign, 0.0):
            #                 del self._rolling_items[src_key]
            #
            #             _l.debug('instr check pos (trnfr, dst): key=%s; pos_size=%s', dst_key,
            #                      dst_item.position_size_with_sign)
            #             if isclose(dst_item.position_size_with_sign, 0.0):
            #                 del self._rolling_items[dst_key]
            self._process_transactions(now)

    def _generate(self, ritem, now):
        for es in ritem.instrument.event_schedules.all():
            is_complies, edate, ndate = es.check_effective_date(now)

            if not is_complies:
                continue

            e = GeneratedEvent()
            e.master_user = self.instance.master_user
            e.event_schedule = es
            e.status = GeneratedEvent.NEW
            e.effective_date = edate
            e.notification_date = ndate
            e.instrument = ritem.instrument
            e.portfolio = ritem.portfolio
            e.account = ritem.account_position
            e.strategy1 = ritem.strategy1_position
            e.strategy2 = ritem.strategy2_position
            e.strategy3 = ritem.strategy3_position
            e.position = ritem.position_size_with_sign

            # is_apply_default_on_date = e.is_apply_default_on_date(now)
            # is_need_reaction_on_date = e.is_need_reaction_on_date(now)
            # is_apply = is_apply_default_on_date
            # is_apply = edate == now
            action = e.get_default_action() if edate == now else None

            _l.debug(
                'evt: %s, es=%s, accrual=%s, factor=%s, action=%s, edate=%s, ndate=%s',
                now, es.id, es.accrual_calculation_schedule, es.factor_schedule,
                getattr(action, 'transaction_type', None), edate, ndate,
            )

            if not action:
                continue

            self._set_ref(action, 'transaction_type', clazz=TransactionType)

            gep = GeneratedEventProcess(
                generated_event=e,
                action=action,
                fake_id_gen=self._fake_id_gen,
                transaction_order_gen=self._trn_order_gen,
                now=now,
                context={
                    'master_user': self.instance.master_user,
                    'member': self.instance.member,
                }
            )
            gep.process()

            if gep.has_errors:
                self.instance.has_errors = True
                continue

            _l.debug('evt: cplx=%s, trns=%s', gep.complex_transaction, gep.transactions)

            for t2 in gep.transactions:
                _l.debug('evt: trn: id=%s, c.id=%s, c.date=%s, acc_date=%s, cash_date=%s',
                         t2.id, t2.complex_transaction.id, t2.complex_transaction.date,
                         t2.accounting_date, t2.cash_date)
                # d = t2.complex_transaction.date or datetime.date.max
                # self._transactions_by_date[d].append(t2)

                d = t2.accounting_date or datetime.date.max
                self._transactions_by_date[d].append(t2)

    def _process_transactions(self, now):
        if now not in self._transactions_by_date:
            return

        for t in self._transactions_by_date[now]:
            # _l.debug('trn=%s', t.id)

            item = CashFlowProjectionReportItem(self.instance, trn=t)
            self._items.append(item)

            if t.transaction_class_id in [TransactionClass.BUY, TransactionClass.SELL]:
                key = self._instr_rolling_trn_key(t)
                ritem = self._rolling(t, key=key)
                ritem.add_balance(t)

                _l.debug('rolling: instr check pos: %s, src_key=%s; pos_size=%s',
                         t.transaction_class, key, ritem.position_size_with_sign)

                if isclose(ritem.position_size_with_sign, 0.0):
                    del self._rolling_items[key]

            elif t.transaction_class_id in [TransactionClass.TRANSFER]:
                # TODO: check me
                src_key = self._instr_rolling_trn_key(t, acc=t.account_cash)
                src_item = self._rolling(t, key=src_key)
                src_item.add_balance(t, sign=-1)

                dst_key = self._instr_rolling_trn_key(t, acc=t.account_position)
                dst_item = self._rolling(t, key=dst_key)
                dst_item.add_balance(t)

                _l.debug('rolling: instr check pos: %s, src_key=%s; pos_size=%s',
                         t.transaction_class, src_key, src_item.position_size_with_sign)
                if isclose(src_item.position_size_with_sign, 0.0):
                    del self._rolling_items[src_key]

                _l.debug('rolling: instr check pos: %s, dst_key=%s; pos_size=%s',
                         t.transaction_class, dst_key, dst_item.position_size_with_sign)
                if isclose(dst_item.position_size_with_sign, 0.0):
                    del self._rolling_items[dst_key]

    def _calc_before_after(self):
        # aggregate some rolling values
        # sort result

        def _sort_key(i):
            if i.type == CashFlowProjectionReportItem.BALANCE:
                type_sort_val = 0
            elif i.type == CashFlowProjectionReportItem.DEFAULT:
                type_sort_val = 1
            else:
                type_sort_val = 2
            return (
                check_int_min(getattr(i.settlement_currency, 'id', None)),
                check_int_min(getattr(i.portfolio, 'id', None)),
                check_int_min(getattr(i.account_cash, 'id', None)),
                # getattr(trn.instrument, 'id', -1),
                type_sort_val,
                check_date_min(getattr(i.complex_transaction, 'date', None)),
                check_int_min(getattr(i.complex_transaction, 'code', None)),
                check_int_min(i.complex_transaction_order),
                check_int_min(i.transaction_code),
            )

        def _group_key(i):
            return (
                # _check_date_min(getattr(i.complex_transaction, 'date', None)),
                # _check_int_min(getattr(i.complex_transaction, 'code', None)),
                # _check_int_min(i.complex_transaction_order),
                # _check_int_min(i.transaction_code),
                check_int_min(getattr(i.settlement_currency, 'id', None)),
                check_int_min(getattr(i.portfolio, 'id', None)),
                check_int_min(getattr(i.account_cash, 'id', None)),
            )

        items = sorted(self._items, key=_sort_key)
        for k, g in groupby(items, key=_group_key):
            rolling_cash_consideration = 0.0
            for i in g:
                if i.type == CashFlowProjectionReportItem.BALANCE:
                    rolling_cash_consideration = i.cash_consideration
                    i.cash_consideration_before = 0.0
                    i.cash_consideration_after = rolling_cash_consideration
                else:
                    i.cash_consideration_before = rolling_cash_consideration
                    i.cash_consideration_after = i.cash_consideration_before + i.cash_consideration
                    rolling_cash_consideration = i.cash_consideration_after

        def _resp_sort_key(i):
            # if i.type == CashFlowProjectionReportItem.BALANCE:
            #     type_sort_val = 0
            # elif i.type == CashFlowProjectionReportItem.DEFAULT:
            #     type_sort_val = 1
            # else:
            #     type_sort_val = 2
            return (
                check_date_min(getattr(i.complex_transaction, 'date', None)),
                # type_sort_val,
                check_int_min(getattr(i.complex_transaction, 'code', None)),
                check_int_min(i.complex_transaction_order),
                check_int_min(i.transaction_code),
            )

        self._items = sorted(self._items, key=_resp_sort_key)
