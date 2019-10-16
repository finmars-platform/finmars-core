import logging
import sys
import time
from collections import Counter, defaultdict
from datetime import date
from itertools import groupby

from django.conf import settings
from django.db.models import Q

from poms.common.utils import isclose, force_qs_evaluation
from poms.instruments.models import CostMethod, InstrumentClass, Instrument
from poms.reports.builders.balance_item import ReportItem, Report
from poms.reports.builders.balance_virt_trn import VirtualTransaction
from poms.reports.builders.base_builder import BaseReportBuilder
from poms.reports.builders.pricing import FakeInstrumentPricingProvider, FakeCurrencyFxRateProvider, \
    CurrencyFxRateProvider
from poms.reports.builders.pricing import InstrumentPricingProvider
from poms.reports.models import BalanceReportCustomField
from poms.transactions.models import TransactionClass, Transaction, ComplexTransaction

_l = logging.getLogger('poms.reports')


class ReportBuilder(BaseReportBuilder):
    trn_cls = VirtualTransaction

    transaction_qs = []

    def __init__(self, instance=None, queryset=None, transactions=None, pricing_provider=None, fx_rate_provider=None):
        super(ReportBuilder, self).__init__(instance, queryset=queryset)

        # self._queryset = queryset
        self._transactions = transactions
        self._original_transactions = transactions
        self._pricing_provider = pricing_provider
        self._fx_rate_provider = fx_rate_provider

        self.avco_rolling_positions = Counter()
        self.fifo_rolling_positions = Counter()

        self._transactions = []
        self._mismatch_items = []
        self._items = []
        self._summaries = []

    def build_balance(self, full=True):
        st = time.perf_counter()
        _l.debug('build balance report: %s', self.instance)

        self.instance.report_type = Report.TYPE_BALANCE
        self.instance.pl_first_date = None

        build_st = time.perf_counter()
        self.build(full=full)
        _l.debug('build_st done: %s', (time.perf_counter() - build_st))

        def _accepted(item):
            return item.type in [ReportItem.TYPE_INSTRUMENT, ReportItem.TYPE_CURRENCY] and \
                   not isclose(item.pos_size, 0.0)

        self.instance.items = [item for item in self.instance.items if _accepted(item)]

        self._alloc_aggregation()

        _l.debug('build_balance done: %s', (time.perf_counter() - st))
        return self.instance

    def build_balance_for_tests(self, full=True):
        st = time.perf_counter()
        _l.debug('build balance report: %s', self.instance)

        self.instance.report_type = Report.TYPE_BALANCE
        self.instance.pl_first_date = None
        self.build(full=full)

        _l.debug('done: %s', (time.perf_counter() - st))
        return self.instance

    def build_pl(self, full=True):
        st = time.perf_counter()
        _l.debug('build pl report: %s', self.instance)
        _l.debug('build pl report pl_first_date: %s', self.instance.pl_first_date)

        self.instance.report_type = Report.TYPE_PL
        self.build(full=full)

        def _accepted(item):
            return item.type not in [ReportItem.TYPE_CURRENCY]

        self.instance.items = [item for item in self.instance.items if _accepted(item)]

        self._alloc_aggregation()

        self._pl_regrouping()

        _l.debug('done: %s', (time.perf_counter() - st))
        return self.instance

    def build(self, full=True):
        st = time.perf_counter()
        _l.debug('build report: %s', self.instance)

        load_transactions_st = time.perf_counter()

        self._load_transactions()

        _l.debug('build load_transactions_st done: %s', (time.perf_counter() - load_transactions_st))

        transactions_pricing_st = time.perf_counter()

        self._transaction_pricing()

        _l.debug('build transactions_pricing_st done: %s', (time.perf_counter() - transactions_pricing_st))

        transactions_multipliers_st = time.perf_counter()

        self._transaction_multipliers()

        _l.debug('build transactions_multipliers_st done: %s', (time.perf_counter() - transactions_multipliers_st))

        clone_transactions_if_need_st = time.perf_counter()

        self._clone_transactions_if_need()

        _l.debug('build clone_transactions_if_need_st done: %s', (time.perf_counter() - clone_transactions_if_need_st))

        transaction_calc_st = time.perf_counter()

        self._transaction_calc()

        _l.debug('build transaction_calc_st done: %s', (time.perf_counter() - transaction_calc_st))

        # self.instance.transactions = self._transactions

        _generate_items_st = time.perf_counter()

        self._generate_items()

        _l.debug('build _generate_items_st done: %s', (time.perf_counter() - _generate_items_st))

        _aggregate_items = time.perf_counter()

        self._aggregate_items()

        _l.debug('build _aggregate_items done: %s', (time.perf_counter() - _aggregate_items))

        # self._calc_pass2()

        _aggregate_summary = time.perf_counter()

        self._aggregate_summary()

        _l.debug('build _aggregate_summary done: %s', (time.perf_counter() - _aggregate_summary))

        _detect_mismatches = time.perf_counter()

        self._detect_mismatches()

        _l.debug('build _detect_mismatches done: %s', (time.perf_counter() - _detect_mismatches))

        _concat_st = time.perf_counter()

        self.instance.items = self._items + self._mismatch_items + self._summaries

        _l.debug('build _concat_st done: %s', (time.perf_counter() - _concat_st))

        if self.instance.pl_first_date and self.instance.pl_first_date != date.min:
            self._build_on_pl_first_date()

        if full:
            _refresh_st = time.perf_counter()
            self._refresh_with_perms()
            _l.debug('build _refresh_st done: %s', (time.perf_counter() - _refresh_st))

        self.instance.custom_fields = BalanceReportCustomField.objects.filter(master_user=self.instance.master_user)

        self.instance.close()

        _l.debug('done: %s', (time.perf_counter() - st))

        return self.instance

    def build_position_only(self):
        st = time.perf_counter()

        _l.debug('build position only report: %s', self.instance)

        self.instance.report_type = Report.TYPE_BALANCE
        self.instance.pl_first_date = None

        load_transactions_st = time.perf_counter()

        self._load_transactions()

        _l.debug('build_position_only load_transactions_st done: %s', (time.perf_counter() - load_transactions_st))

        clone_transactions_st = time.perf_counter()

        self._clone_transactions_if_need()

        _l.debug('build_position_only clone_transactions_st done: %s', (time.perf_counter() - clone_transactions_st))

        # self.instance.transactions = self._transactions
        if not self._transactions:
            return

        generate_items_st = time.perf_counter()

        self._generate_items()

        _l.debug('build_position_only generate_items_st done: %s', (time.perf_counter() - generate_items_st))

        sorted_items_st = time.perf_counter()

        sorted_items = sorted(self._items, key=lambda item: self._item_group_key(item))

        _l.debug('build_position_only sorted_items_st done: %s', (time.perf_counter() - sorted_items_st))

        _l.debug('build_position_only aggregate items')

        last_action_st = time.perf_counter()

        res_items = []
        for k, g in groupby(sorted_items, key=lambda item: self._item_group_key(item)):
            res_item = None

            for item in g:
                if item.type in [ReportItem.TYPE_INSTRUMENT, ReportItem.TYPE_CURRENCY, ReportItem.TYPE_TRANSACTION_PL,
                                 ReportItem.TYPE_FX_TRADE, ReportItem.TYPE_CASH_IN_OUT, ]:
                    if res_item is None:
                        res_item = ReportItem.from_item(item)
                    res_item.pos_size += item.trn.pos_size

            if res_item:
                res_items.append(res_item)

        self.instance.items = res_items

        _l.debug('build_position_only last_action_st done: %s', (time.perf_counter() - last_action_st))

        _l.debug('build_position_only done: %s', (time.perf_counter() - st))

        return self.instance

    @property
    def transactions(self):
        return self._transactions

    def _trn_qs_filter(self, qs):

        filters = Q(**{'%s__lte' % self.instance.date_field: self.instance.report_date})

        if self.instance.report_type == Report.TYPE_PL:
            filters = Q(**{'accounting_date__lte': self.instance.report_date})

        # TODO pl_first_date is not used as a parameter, instead it passed as report_date
        # if self.instance.pl_first_date:
        #     filters &= Q(**{'%s__gt' % self.instance.date_field: self.instance.pl_first_date})

        if self.instance.instruments:
            # kw_filters['instrument__in'] = self.instance.instruments
            filters &= Q(instrument__in=self.instance.instruments)

        if self.instance.transaction_classes:
            filters &= Q(transaction_class__in=self.instance.transaction_classes)

        qs = qs.filter(filters)

        qs = qs.order_by(self.instance.date_field, 'transaction_code', 'id')

        # if self.instance.member is not None:
        #     from poms.transactions.filters import TransactionObjectPermissionFilter
        #     qs = TransactionObjectPermissionFilter.filter_qs(qs, self.instance.master_user, self.instance.member)

        return qs

    def sort_transactions(self):
        def _trn_key(t):

            d = None
            if self.instance.date_field == 'accounting_date':
                d = t.acc_date
            elif self.instance.date_field == 'cash_date':
                d = t.cash_date
            else:
                if t.trn_date is None:
                    if t.acc_date and t.cash_date:
                        d = min(t.acc_date, t.cash_date)
                else:
                    d = t.trn_date

            return (
                d if d is not None else date.min,
                t.trn_code if t.trn_code is not None else sys.maxsize,
                t.pk if t.pk is not None else sys.maxsize,
            )

        self._transactions = sorted(self._transactions, key=_trn_key)
        return self._transactions

    @property
    def pricing_provider(self):
        if self._pricing_provider is None:
            if self.instance.pricing_policy is None:
                p = FakeInstrumentPricingProvider(self.instance.master_user, None, self.instance.report_date)
            else:
                p = InstrumentPricingProvider(self.instance.master_user, self.instance.pricing_policy,
                                              self.instance.report_date)
                p.fill_using_transactions(self._trn_qs())
                # p.fill_using_transactions(self.transaction_qs)
            self._pricing_provider = p
        return self._pricing_provider

    @property
    def fx_rate_provider(self):
        if self._fx_rate_provider is None:
            if self.instance.pricing_policy is None:
                p = FakeCurrencyFxRateProvider(self.instance.master_user, None, self.instance.report_date)
            else:
                p = CurrencyFxRateProvider(self.instance.master_user, self.instance.pricing_policy,
                                           self.instance.report_date)
                p.fill_using_transactions(self._trn_qs(), currencies=[self.instance.report_currency])
                # p.fill_using_transactions(self.transaction_qs, currencies=[self.instance.report_currency])
            self._fx_rate_provider = p
        return self._fx_rate_provider

    def list_as_dict(self, list):

        result = {}

        for item in list:
            result[item.pk] = item

        return result

    def inject_relations(self, trn_qs):

        result = [];

        st = time.perf_counter()

        from poms.currencies.models import Currency
        from poms.portfolios.models import Portfolio
        from poms.accounts.models import Account
        from poms.accounts.models import AccountType

        from poms.strategies.models import Strategy1
        from poms.strategies.models import Strategy2
        from poms.strategies.models import Strategy3

        from poms.obj_perms.utils import get_permissions_prefetch_lookups

        transaction_classes_list = TransactionClass.objects.all()

        transaction_classes_dict = self.list_as_dict(transaction_classes_list)

        instruments_list = Instrument.objects.select_related(
            'instrument_type',
            'pricing_currency',
            'accrued_currency'
        ).prefetch_related(
            'factor_schedules',
            'accrual_calculation_schedules',
            # *get_permissions_prefetch_lookups(
            #     (None, Instrument),
            # )

        ).filter(master_user=self.instance.master_user).defer('object_permissions')

        instruments_dict = self.list_as_dict(instruments_list)

        currencies_list = Currency.objects.filter(master_user=self.instance.master_user)

        currencies_dict = self.list_as_dict(currencies_list)

        portfolios_list = Portfolio.objects.prefetch_related(
            # *get_permissions_prefetch_lookups(
            #     (None, Portfolio),
            # )

        ).filter(master_user=self.instance.master_user).defer('object_permissions')

        portfolios_dict = self.list_as_dict(portfolios_list)

        accounts_list = Account.objects.select_related(
            'type'
        ).prefetch_related(
            # *get_permissions_prefetch_lookups(
            #     (None, Account),
            #     ('type', AccountType),
            #     ('portfolios', Portfolio),
            # )

        ).filter(master_user=self.instance.master_user).defer('object_permissions')

        accounts_dict = self.list_as_dict(accounts_list)

        strategies1_list = Strategy1.objects.select_related(
            'subgroup',
            'subgroup__group'
        ).filter(master_user=self.instance.master_user).defer('object_permissions')
        strategies1_dict = self.list_as_dict(strategies1_list)

        strategies2_list = Strategy2.objects.select_related(
            'subgroup',
            'subgroup__group'
        ).filter(master_user=self.instance.master_user).defer('object_permissions')
        strategies2_dict = self.list_as_dict(strategies2_list)

        strategies3_list = Strategy3.objects.select_related(
            'subgroup',
            'subgroup__group'
        ).filter(master_user=self.instance.master_user).defer('object_permissions')
        strategies3_dict = self.list_as_dict(strategies3_list)

        values_list = self.get_trn_values_list()
        o = self.get_trn_values_list_keys_as_obj(values_list)

        class Trn:
            pass

        print(values_list)
        print(trn_qs[0])
        print(o.__dict__)

        # print('ecoded')
        # print(str(trn_qs[0]).encode("utf-8"))

        print(o.instrument_id)

        for tuple_trn in trn_qs:

            # _l.debug(tuple_trn)

            t = Trn()

            # Set non-relation props
            index = 0
            for val in tuple_trn:
                setattr(t, values_list[index], val)
                index = index + 1

            setattr(t, 'transaction_class', transaction_classes_dict[tuple_trn[o.transaction_class_id]])

            try:
                setattr(t, 'instrument', instruments_dict[tuple_trn[o.instrument_id]])
            except KeyError:
                setattr(t, 'instrument', None)

            try:
                setattr(t, 'linked_instrument', instruments_dict[tuple_trn[o.linked_instrument_id]])
            except KeyError:
                setattr(t, 'linked_instrument', None)

            try:
                setattr(t, 'allocation_balance', instruments_dict[tuple_trn[o.allocation_balance_id]])
            except KeyError:
                setattr(t, 'allocation_balance', None)

            try:
                setattr(t, 'allocation_pl', instruments_dict[tuple_trn[o.allocation_pl_id]])
            except KeyError:
                setattr(t, 'allocation_pl', None)


            try:
                setattr(t, 'transaction_currency', currencies_dict[tuple_trn[o.transaction_currency_id]])
            except KeyError:
                setattr(t, 'transaction_currency', None)

            try:
                setattr(t, 'settlement_currency', currencies_dict[tuple_trn[o.settlement_currency_id]])
            except KeyError:
                setattr(t, 'settlement_currency', None)

            try:
                setattr(t, 'portfolio', portfolios_dict[tuple_trn[o.portfolio_id]])
            except KeyError:
                setattr(t, 'portfolio', None)

            try:
                setattr(t, 'account_cash', accounts_dict[tuple_trn[o.account_cash_id]])
            except KeyError:
                setattr(t, 'account_cash', None)

            try:
                setattr(t, 'account_position', accounts_dict[tuple_trn[o.account_position_id]])
            except KeyError:
                setattr(t, 'account_position', None)

            try:
                setattr(t, 'account_interim', accounts_dict[tuple_trn[o.account_interim_id]])
            except KeyError:
                setattr(t, 'account_interim', None)

            try:
                setattr(t, 'strategy1_position', strategies1_dict[tuple_trn[o.strategy1_position_id]])
            except KeyError:
                setattr(t, 'strategy1_position', None)

            try:
                setattr(t, 'strategy1_cash', strategies1_dict[tuple_trn[o.strategy1_cash_id]])
            except KeyError:
                setattr(t, 'strategy1_cash', None)

            try:
                setattr(t, 'strategy2_position', strategies2_dict[tuple_trn[o.strategy2_position_id]])
            except KeyError:
                setattr(t, 'strategy2_position', None)

            try:
                setattr(t, 'strategy2_cash', strategies2_dict[tuple_trn[o.strategy2_cash_id]])
            except KeyError:
                setattr(t, 'strategy2_cash', None)

            try:
                setattr(t, 'strategy3_position', strategies3_dict[tuple_trn[o.strategy3_position_id]])
            except KeyError:
                setattr(t, 'strategy3_position', None)

            try:
                setattr(t, 'strategy3_cash', strategies3_dict[tuple_trn[o.strategy3_cash_id]])
            except KeyError:
                setattr(t, 'strategy3_cash', None)

            result.append(t)

        _l.debug('_load_transactions inject relations done: %s', (time.perf_counter() - st))

        return result

    def get_trn_values_list(self):

        return ["pk",
                "master_user_id",
                "complex_transaction_id",
                "complex_transaction_order",
                "transaction_code",
                "transaction_class_id",
                "instrument_id",
                "transaction_currency_id",
                "position_size_with_sign",
                "settlement_currency_id",
                "cash_consideration",
                "principal_with_sign",
                "carry_with_sign",
                "overheads_with_sign",
                "transaction_date",
                "accounting_date",
                "cash_date",
                "portfolio_id",
                "account_position_id",
                "account_cash_id",
                "account_interim_id",
                "strategy1_position_id",
                "strategy1_cash_id",
                "strategy2_position_id",
                "strategy2_cash_id",
                "strategy3_position_id",
                "strategy3_cash_id",
                "responsible_id",
                "counterparty_id",
                "linked_instrument_id",
                "allocation_balance_id",
                "allocation_pl_id",
                "reference_fx_rate",
                "factor",
                "trade_price",
                "ytm_at_cost",
                "position_amount",
                "principal_amount",
                "carry_amount",
                "overheads",
                "notes"]

    def get_trn_values_list_keys_as_obj(self, values_list):

        class Trn:
            pass

        result = Trn()

        index = 0
        for item in values_list:
            setattr(result, item, index)
            index = index + 1

        return result

    def _load_transactions(self):
        _l.debug('transactions - load')

        _load_transactions_st = time.perf_counter()

        self._transactions = []
        self._original_transactions = []

        trn_qs_st = time.perf_counter()

        # self.transaction_qs = self._trn_qs()

        # TODO DO OWN FETCH TRANSACTIONS HERE
        # trn_qs = self._trn_qs()

        # complex_qs = ComplexTransaction.objects.filter(status=ComplexTransaction.PRODUCTION,
        #                                                master_user=self.instance.master_user, is_deleted=False)

        trn_qs = Transaction.objects

        # trn_qs = Transaction.objects.select_related(
        #     'complex_transaction',
        #     'complex_transaction__transaction_type',
        #     'transaction_class',
        #
        #     'instrument',
        #     'instrument__instrument_type',
        #     'instrument__instrument_type__instrument_class',
        #     'instrument__pricing_currency',
        #     'instrument__accrued_currency',
        #
        #     'transaction_currency',
        #     'settlement_currency',
        #     'portfolio',
        #     'account_position',
        #     'account_cash',
        #     'account_interim',
        #     'strategy1_position',
        #     'strategy1_cash',
        #     'strategy2_position',
        #     'strategy2_cash',
        #     'strategy3_position',
        #     'strategy3_cash',
        #     'responsible',
        #     'counterparty',
        #     'linked_instrument__instrument_type',
        #     'allocation_balance',
        #     'allocation_pl').prefetch_related('instrument__factor_schedules',
        #                                       'instrument__accrual_calculation_schedules').all()

        # trn_qs = trn_qs.filter(complex_transaction__in=complex_qs)
        trn_qs = trn_qs.filter(master_user=self.instance.master_user, is_canceled=False)

        trn_qs = self._trn_qs_filter(trn_qs)

        _l.debug('_load_transactions trn_qs_st done: %s', (time.perf_counter() - trn_qs_st))

        if trn_qs.count() == 0:
            return

        val_list = self.get_trn_values_list()

        trn_qs = trn_qs.values_list(*val_list)

        # trn_qs = trn_qs[:1]

        trn_qs = self.inject_relations(trn_qs)

        _instance = self.instance
        _pricing_provider = self.pricing_provider
        _fx_rate_provider = self.fx_rate_provider

        _iteration_st = time.perf_counter()

        for t in trn_qs:

            overrides = {}

            if self.instance.portfolio_mode == Report.MODE_IGNORE:
                overrides['portfolio'] = self.instance.master_user.portfolio

            if self.instance.account_mode == Report.MODE_IGNORE:
                overrides['account_position'] = self.instance.master_user.account
                overrides['account_cash'] = self.instance.master_user.account
                overrides['account_interim'] = self.instance.master_user.account

            if self.instance.strategy1_mode == Report.MODE_IGNORE:
                overrides['strategy1_position'] = self.instance.master_user.strategy1
                overrides['strategy1_cash'] = self.instance.master_user.strategy1

            if self.instance.strategy2_mode == Report.MODE_IGNORE:
                overrides['strategy2_position'] = self.instance.master_user.strategy2
                overrides['strategy2_cash'] = self.instance.master_user.strategy2

            if self.instance.strategy3_mode == Report.MODE_IGNORE:
                overrides['strategy3_position'] = self.instance.master_user.strategy3
                overrides['strategy3_cash'] = self.instance.master_user.strategy3

            if self.instance.allocation_mode == Report.MODE_IGNORE:
                overrides['allocation_balance'] = self.instance.master_user.instrument
                overrides['allocation_pl'] = self.instance.master_user.instrument

            trn = self.trn_cls(
                report=_instance,
                pricing_provider=_pricing_provider,
                fx_rate_provider=_fx_rate_provider,
                trn=t,
                overrides=overrides
            )

            self._transactions.append(trn)

            otrn = self.trn_cls(
                report=_instance,
                pricing_provider=_pricing_provider,
                fx_rate_provider=_fx_rate_provider,
                trn=t,
            )

            self._original_transactions.append(otrn)

        _l.debug('_load_transactions iteration done: %s', (time.perf_counter() - _iteration_st))

        _l.debug('_self._transactions len %s' % len(self._transactions))

        _l.debug('_load_transactions done: %s', (time.perf_counter() - _load_transactions_st))

    def _transaction_pricing(self):
        # _l.debug('transactions - add pricing')

        for trn in self._transactions:
            trn.pricing()

    def _transaction_calc(self):
        # _l.debug('transactions - calculate')

        for trn in self._transactions:
            trn.calc()

    def _clone_transactions_if_need(self):
        # _l.debug('transactions - clone if need')

        res = []
        for trn in self._transactions:
            res.append(trn)

            if trn.trn_cls.id in [TransactionClass.BUY, TransactionClass.SELL]:
                if trn.closed_by:
                    for closed_by, delta in trn.closed_by:
                        closed_by2, trn2 = self.trn_cls.approach_clone(closed_by, trn, delta)
                        res.append(trn2)
                        res.append(closed_by2)

            elif trn.trn_cls.id == TransactionClass.FX_TRADE:
                trn.is_hidden = True

                trn1, trn2 = trn.fx_trade_clone()
                res.append(trn1)
                res.append(trn2)

            elif trn.trn_cls.id == TransactionClass.TRANSFER:
                trn.is_hidden = True
                # split TRANSFER to sell/buy or buy/sell
                if trn.pos_size >= 0:
                    trn1, trn2 = trn.transfer_clone(self._trn_cls_sell, self._trn_cls_buy,
                                                    t1_pos_sign=1.0, t1_cash_sign=-1.0)
                else:
                    trn1, trn2 = trn.transfer_clone(self._trn_cls_buy, self._trn_cls_sell,
                                                    t1_pos_sign=-1.0, t1_cash_sign=1.0)
                res.append(trn1)
                res.append(trn2)

            elif trn.trn_cls.id == TransactionClass.FX_TRANSFER:
                trn.is_hidden = True

                trn1, trn2 = trn.fx_transfer_clone(trn_cls_out=self._trn_cls_cash_out,
                                                   trn_cls_in=self._trn_cls_cash_in)
                res.append(trn1)
                res.append(trn2)

                # trn11, trn12 = trn1.fx_trade_clone()
                # res.append(trn11)
                # res.append(trn12)
                #
                # trn21, trn22 = trn2.fx_trade_clone()
                # res.append(trn21)
                # res.append(trn22)

        self._transactions = res
        # _l.debug('transactions - len=%s', len(self._transactions))

    def _transaction_multipliers(self):
        # _l.debug('transactions - calculate multipliers')

        self._calc_avco_multipliers()
        self._calc_fifo_multipliers()

        balances = Counter()

        for t in self._transactions:
            if t.trn_cls.id in [TransactionClass.TRANSACTION_PL, TransactionClass.FX_TRADE]:
                t.multiplier = 1.0

            if t.trn_cls.id in [TransactionClass.INSTRUMENT_PL]:
                # TODO: remove after new algo
                t.multiplier = 1.0

                if t.instr and t.instr.instrument_type.instrument_class_id == InstrumentClass.CONTRACT_FOR_DIFFERENCE:
                    t.rolling_pos_size = t.fifo_rolling_pos_size

                elif self.instance.cost_method.id == CostMethod.AVCO:
                    t.rolling_pos_size = t.avco_rolling_pos_size

                elif self.instance.cost_method.id == CostMethod.FIFO:
                    t.rolling_pos_size = t.fifo_rolling_pos_size

            elif t.trn_cls.id in [TransactionClass.BUY, TransactionClass.SELL]:
                if t.instr and t.instr.instrument_type.instrument_class_id == InstrumentClass.CONTRACT_FOR_DIFFERENCE:
                    t.multiplier = t.fifo_multiplier
                    t.closed_by = t.fifo_closed_by
                    t.rolling_pos_size = t.fifo_rolling_pos_size

                elif self.instance.cost_method.id == CostMethod.AVCO:
                    t.multiplier = t.avco_multiplier
                    t.closed_by = t.avco_closed_by
                    t.rolling_pos_size = t.avco_rolling_pos_size

                elif self.instance.cost_method.id == CostMethod.FIFO:
                    t.multiplier = t.fifo_multiplier
                    t.closed_by = t.fifo_closed_by
                    t.rolling_pos_size = t.fifo_rolling_pos_size

                t.remaining_pos_size = t.pos_size * (1 - t.multiplier)

                t_key = self._get_trn_group_key(t, walloc=True)
                balances[t_key] += t.remaining_pos_size

        remaining_positions = Counter()

        for t in self._transactions:
            if t.trn_cls.id in [TransactionClass.BUY, TransactionClass.SELL]:
                t_key = self._get_trn_group_key(t, walloc=True)

                t.balance_pos_size = balances[t_key]

                remaining_positions[t_key] += t.remaining_pos_size

                t.sum_remaining_pos_size = remaining_positions[t_key]

            elif t.trn_cls.id in [TransactionClass.INSTRUMENT_PL]:
                t_key = self._get_trn_group_key(t, walloc=True)
                t.balance_pos_size = balances[t_key]
                t.sum_remaining_pos_size = remaining_positions[t_key]
                try:
                    t.multiplier = 1.0 - abs(t.sum_remaining_pos_size / t.balance_pos_size)
                except ArithmeticError:
                    t.multiplier = 0.0

        # for t in self._transactions:
        #     if t.trn_cls.id in [TransactionClass.INSTRUMENT_PL]:
        #         t_key = self._get_trn_group_key(t)
        #         t.balance_pos_size = balances[t_key]
        #         try:
        #             t.remaining_pos_size_percent = t.remaining_pos_size / t.balance_pos_size
        #         except ArithmeticError:
        #             t.remaining_pos_size_percent = 0.0
        #
        # sum_remaining_positions = Counter()
        # for t in self._transactions:
        #     if t.trn_cls.id in [TransactionClass.BUY, TransactionClass.SELL]:
        #         t_key = self._get_trn_group_key(t)
        #         sum_remaining_positions[t_key] += t.remaining_pos_size
        #
        #     elif t.trn_cls.id == TransactionClass.INSTRUMENT_PL:
        #         t_key = self._get_trn_group_key(t)
        #         balance_pos_size = balances[t_key]
        #         remaining_pos_size = sum_remaining_positions[t_key]
        #         try:
        #             t.multiplier = abs(remaining_pos_size / balance_pos_size)
        #         except ArithmeticError:
        #             t.multiplier = 0.0
        pass

    def _calc_avco_multipliers(self):
        # _l.debug('transactions - calculate multipliers - avco')

        items = defaultdict(list)

        def _set_mul(t0, avco_multiplier):
            delta = avco_multiplier - t0.avco_multiplier
            t0.avco_multiplier = avco_multiplier
            return delta

        def _close_by(closed, cur, delta):
            # closed.avco_closed_by.append(VirtualTransactionClosedByData(cur, delta))
            closed.avco_closed_by.append((cur, delta))

        for t in self._transactions:
            t_key = self._get_trn_group_key(t)

            if t.trn_cls.id == TransactionClass.INSTRUMENT_PL:
                t.avco_rolling_pos_size = self.avco_rolling_positions[t_key]
                continue

            if t.trn_cls.id not in [TransactionClass.BUY, TransactionClass.SELL]:
                continue

            t.avco_multiplier = 0.0
            t.avco_closed_by = []
            t.avco_rolling_pos_size = 0.0

            rolling_pos = self.avco_rolling_positions[t_key]

            if isclose(rolling_pos, 0.0):
                k = -1
            else:
                k = - t.pos_size / rolling_pos

            if k > 1.0:
                if t_key in items:
                    for t0 in items[t_key]:
                        delta = _set_mul(t0, 1.0)
                        _close_by(t0, t, delta)
                    del items[t_key]
                items[t_key].append(t)
                _set_mul(t, 1.0 / k)
                rolling_pos = t.pos_size * (1.0 - t.avco_multiplier)

            elif isclose(k, 1.0):
                if t_key in items:
                    for t0 in items[t_key]:
                        delta = _set_mul(t0, 1.0)
                        _close_by(t0, t, delta)
                    del items[t_key]
                _set_mul(t, 1.0)
                rolling_pos = 0.0

            elif k > 0.0:
                if t_key in items:
                    for t0 in items[t_key]:
                        delta = _set_mul(t0, t0.avco_multiplier + k * (1.0 - t0.avco_multiplier))
                        _close_by(t0, t, delta)
                _set_mul(t, 1.0)
                rolling_pos += t.pos_size

            else:
                items[t_key].append(t)
                rolling_pos += t.pos_size

            self.avco_rolling_positions[t_key] = rolling_pos
            t.avco_rolling_pos_size = rolling_pos

    def _calc_fifo_multipliers(self):
        # _l.debug('transactions - calculate multipliers - fifo')

        items = defaultdict(list)

        def _set_mul(t0, fifo_multiplier):
            delta = fifo_multiplier - t0.fifo_multiplier
            t0.fifo_multiplier = fifo_multiplier
            return delta

        def _close_by(closed, cur, delta):
            # closed.fifo_closed_by.append(VirtualTransactionClosedByData(cur, delta))
            closed.fifo_closed_by.append((cur, delta))

        for t in self._transactions:
            t_key = self._get_trn_group_key(t)

            if t.trn_cls.id == TransactionClass.INSTRUMENT_PL:
                t.fifo_rolling_pos_size = self.fifo_rolling_positions[t_key]
                continue

            if t.trn_cls.id not in [TransactionClass.BUY, TransactionClass.SELL]:
                continue

            t.fifo_multiplier = 0.0
            t.fifo_closed_by = []
            t.fifo_rolling_pos_size = 0.0

            rolling_pos = self.fifo_rolling_positions[t_key]

            if isclose(rolling_pos, 0.0):
                k = -1
            else:
                k = - t.pos_size / rolling_pos

            if k > 1.0:
                if t_key in items:
                    for t0 in items[t_key]:
                        delta = _set_mul(t0, 1.0)
                        _close_by(t0, t, delta)
                    items[t_key].clear()
                items[t_key].append(t)
                _set_mul(t, 1.0 / k)
                rolling_pos = t.pos_size * (1.0 - t.fifo_multiplier)

            elif isclose(k, 1.0):
                if t_key in items:
                    for t0 in items[t_key]:
                        delta = _set_mul(t0, 1.0)
                        _close_by(t0, t, delta)
                    del items[t_key]
                _set_mul(t, 1.0)
                rolling_pos = 0.0

            elif k > 0.0:
                position = t.pos_size
                if t_key in items:
                    t_items = items[t_key]
                    for t0 in t_items:
                        remaining = t0.pos_size * (1.0 - t0.fifo_multiplier)
                        k0 = - position / remaining
                        if k0 > 1.0:
                            delta = _set_mul(t0, 1.0)
                            _close_by(t0, t, delta)
                            position += remaining
                        elif isclose(k0, 1.0):
                            delta = _set_mul(t0, 1.0)
                            _close_by(t0, t, delta)
                            position += remaining
                        elif k0 > 0.0:
                            position += remaining * k0
                            delta = _set_mul(t0, t0.fifo_multiplier + k0 * (1.0 - t0.fifo_multiplier))
                            _close_by(t0, t, delta)
                        # else:
                        #     break
                        if isclose(position, 0.0):
                            break
                    t_items = [t0 for t0 in t_items if not isclose(t0.fifo_multiplier, 1.0)]
                    if t_items:
                        items[t_key] = t_items
                    else:
                        del items[t_key]

                _set_mul(t, abs((t.pos_size - position) / t.pos_size))
                rolling_pos += t.pos_size * t.fifo_multiplier

            else:
                items[t_key].append(t)
                rolling_pos += t.pos_size

            self.fifo_rolling_positions[t_key] = rolling_pos
            t.fifo_rolling_pos_size = rolling_pos

    def _get_trn_group_key(self, t, walloc=False):
        if self.instance.portfolio_mode == Report.MODE_INDEPENDENT:
            prtfl = t.prtfl
        else:
            prtfl = None

        if self.instance.account_mode == Report.MODE_INDEPENDENT:
            acc_pos = t.acc_pos
        else:
            acc_pos = None

        if self.instance.strategy1_mode == Report.MODE_INDEPENDENT:
            str1_pos = t.str1_pos
        else:
            str1_pos = None

        if self.instance.strategy2_mode == Report.MODE_INDEPENDENT:
            str2_pos = t.str2_pos
        else:
            str2_pos = None

        if self.instance.strategy3_mode == Report.MODE_INDEPENDENT:
            str3_pos = t.str3_pos
        else:
            str3_pos = None

        instr = t.instr

        alloc = None
        if walloc:
            if self.instance.report_type == Report.TYPE_BALANCE:
                alloc = t.alloc_bl
            elif self.instance.report_type == Report.TYPE_BALANCE:
                alloc = t.alloc_pl

        return (
            getattr(prtfl, 'id', None),
            getattr(acc_pos, 'id', None),
            getattr(str1_pos, 'id', None),
            getattr(str2_pos, 'id', None),
            getattr(str3_pos, 'id', None),
            getattr(alloc, 'id', None),
            getattr(instr, 'id', None),
        )

    def _generate_items(self):
        _l.debug('items - generate')
        for trn in self._transactions:
            if trn.is_hidden:
                continue

            if trn.trn_cls.id in [TransactionClass.BUY, TransactionClass.SELL]:
                self._add_instr(trn)
                self._add_cash(trn, val=trn.cash, ccy=trn.stl_ccy)

            elif trn.trn_cls.id in [TransactionClass.CASH_INFLOW, TransactionClass.CASH_OUTFLOW]:
                self._add_cash(trn, val=trn.cash, ccy=trn.stl_ccy,
                               acc=trn.acc_cash, str1=trn.str1_cash, str2=trn.str2_cash,
                               str3=trn.str3_cash)

                # P&L
                if trn.case in [0, 1]:
                    item = ReportItem.from_trn(self.instance, self.pricing_provider, self.fx_rate_provider,
                                               ReportItem.TYPE_CASH_IN_OUT, trn, acc=trn.acc_pos,
                                               str1=trn.str1_pos, str2=trn.str2_pos, str3=trn.str3_pos,
                                               # ccy=trn.stl_ccy
                                               )
                    self._items.append(item)

            elif trn.trn_cls.id == TransactionClass.INSTRUMENT_PL:
                self._add_instr(trn, val=0.0)
                self._add_cash(trn, val=trn.cash, ccy=trn.stl_ccy)

            elif trn.trn_cls.id == TransactionClass.TRANSACTION_PL:
                self._add_cash(trn, val=trn.cash, ccy=trn.stl_ccy)

                if trn.case in [0, 1]:
                    item = ReportItem.from_trn(self.instance, self.pricing_provider, self.fx_rate_provider,
                                               ReportItem.TYPE_TRANSACTION_PL, trn, acc=trn.acc_pos,
                                               str1=trn.str1_pos, str2=trn.str2_pos, str3=trn.str3_pos)
                    self._items.append(item)

            elif trn.trn_cls.id == TransactionClass.FX_TRADE:
                # TODO: Что используем для strategy?
                self._add_cash(trn, val=trn.principal, ccy=trn.stl_ccy)

                # self._add_cash(trn, val=trn.cash, ccy=trn.stl_ccy)

                # P&L
                if trn.case in [0, 1]:
                    item = ReportItem.from_trn(self.instance, self.pricing_provider, self.fx_rate_provider,
                                               ReportItem.TYPE_FX_TRADE, trn, acc=trn.acc_pos,
                                               str1=trn.str1_pos, str2=trn.str2_pos, str3=trn.str3_pos,
                                               # ccy=trn.trn.settlement_currency, trn_ccy=trn.trn_ccy
                                               )
                    self._items.append(item)

            elif trn.trn_cls.id == TransactionClass.TRANSFER:
                # raise RuntimeError('Virtual transaction must be created')
                pass

            elif trn.trn_cls.id == TransactionClass.FX_TRANSFER:
                # raise RuntimeError('Virtual transaction must be created')
                pass

            else:
                raise RuntimeError('Invalid transaction class: %s' % trn.trn_cls.id)

        # _l.debug('items - raw.len=%s', len(self._items))

    def _aggregate_items(self):
        _l.debug('items - aggregate')

        aggr_items = []

        sorted_items = sorted(self._items, key=lambda x: self._item_group_key(x))

        # _l.debug('_aggregate_items sorted_items[0] %s ' % sorted_items[0])
        # _l.debug('_aggregate_items sorted_items len %s ' % len(sorted_items))
        #
        # _l.debug('_aggregate_items self._items before len %s ' % len(self._items))

        for k, g in groupby(sorted_items, key=lambda x: self._item_group_key(x)):
            # _l.debug('items - aggregate - group=%s', k)
            res_item = None

            for item in g:

                if item.type in [ReportItem.TYPE_INSTRUMENT, ReportItem.TYPE_CURRENCY, ReportItem.TYPE_TRANSACTION_PL,
                                 ReportItem.TYPE_FX_TRADE, ReportItem.TYPE_CASH_IN_OUT, ]:
                    if res_item is None:
                        res_item = ReportItem.from_item(item)
                    res_item.add(item)

            if res_item:
                # _l.debug('items - aggregate - add item=%s, instr=%s', res_item, getattr(res_item.instr, 'id', None))
                # _l.debug('pricing')
                res_item.pricing()
                # _l.debug('close')
                res_item.close()
                aggr_items.append(res_item)

        self._items = aggr_items

        # _l.debug('_aggregate_items self._items after len %s ' % len(self._items))

        # _l.debug('items - len=%s', len(self._items))

    def _item_group_key(self, item):
        return (
            item.type,
            getattr(item.prtfl, 'id', -1),
            getattr(item.acc, 'id', -1),
            getattr(item.str1, 'id', -1),
            getattr(item.str2, 'id', -1),
            getattr(item.str3, 'id', -1),
            getattr(item.instr, 'id', -1),
            getattr(item.alloc, 'id', -1),
            # getattr(item.alloc_bl, 'id', -1),
            # getattr(item.alloc_pl, 'id', -1),
            getattr(item.ccy, 'id', -1),
            # getattr(item.trn_ccy, 'id', -1),
            item.notes,
            getattr(item.detail_trn, 'id', -1),
        )

    def _item_mismatch_group_key(self, item):
        return (
            item.type,
            getattr(item.prtfl, 'id', -1),
            getattr(item.acc, 'id', -1),
            getattr(item.instr, 'id', -1),
            getattr(item.ccy, 'id', -1),
            getattr(item.mismatch_prtfl, 'id', -1),
            getattr(item.mismatch_acc, 'id', -1),
        )

    # def _item_group_key_pass2(self, trn=None, item=None):
    #     if trn:
    #         return (
    #             getattr(trn.prtfl, 'id', -1),
    #             getattr(trn.acc_pos, 'id', -1),
    #             getattr(trn.str1_pos, 'id', -1),
    #             getattr(trn.str2_pos, 'id', -1),
    #             getattr(trn.str3_pos, 'id', -1),
    #             getattr(trn.alloc, 'id', -1),
    #             # getattr(trn.alloc_bl, 'id', -1),
    #             # getattr(trn.alloc_pl, 'id', -1),
    #             getattr(trn.instr, 'id', -1),
    #             # getattr(trn.ccy, 'id', -1),
    #             # getattr(trn.trn_ccy, 'id', -1),
    #         )
    #     elif item:
    #         return (
    #             getattr(item.prtfl, 'id', -1),
    #             getattr(item.acc, 'id', -1),
    #             getattr(item.str1, 'id', -1),
    #             getattr(item.str2, 'id', -1),
    #             getattr(item.str3, 'id', -1),
    #             getattr(item.alloc, 'id', -1),
    #             # getattr(item.alloc_bl, 'id', -1),
    #             # getattr(item.alloc_pl, 'id', -1),
    #             getattr(item.instr, 'id', -1),
    #             # getattr(item.ccy, 'id', -1),
    #             # getattr(item.trn_ccy, 'id', -1),
    #         )
    #     else:
    #         raise RuntimeError('code bug')

    def _build_on_pl_first_date(self):
        report_on_pl_first_date = Report(
            master_user=self.instance.master_user,
            member=self.instance.member,
            pl_first_date=None,
            report_date=self.instance.pl_first_date,
            report_currency=self.instance.report_currency,
            pricing_policy=self.instance.pricing_policy,
            cost_method=self.instance.cost_method,
            portfolio_mode=self.instance.portfolio_mode,
            account_mode=self.instance.account_mode,
            strategy1_mode=self.instance.strategy1_mode,
            strategy2_mode=self.instance.strategy2_mode,
            strategy3_mode=self.instance.strategy3_mode,
            allocation_mode=self.instance.allocation_mode,
            show_transaction_details=self.instance.show_transaction_details,
            approach_multiplier=self.instance.approach_multiplier,
            allocation_detailing=self.instance.allocation_detailing,
            instruments=self.instance.instruments,
            portfolios=self.instance.portfolios,
            accounts=self.instance.accounts,
            strategies1=self.instance.strategies1,
            strategies2=self.instance.strategies2,
            strategies3=self.instance.strategies3,
            transaction_classes=self.instance.transaction_classes,
            date_field=self.instance.date_field,
            custom_fields=self.instance.custom_fields,
        )

        builder = self.__class__(report_on_pl_first_date)
        builder.build(full=False)

        if not report_on_pl_first_date.items:
            return

        def _item_key(item):
            return (
                item.type,
                getattr(item.prtfl, 'id', -1),
                getattr(item.acc, 'id', -1),
                getattr(item.str1, 'id', -1),
                getattr(item.str2, 'id', -1),
                getattr(item.str3, 'id', -1),
                getattr(item.alloc, 'id', -1),
                # getattr(item.alloc_bl, 'id', -1),
                # getattr(item.alloc_pl, 'id', -1),
                getattr(item.instr, 'id', -1),
                getattr(item.ccy, 'id', -1),
                # getattr(item.trn_ccy, 'id', -1),
                item.notes,
                getattr(item.detail_trn, 'id', -1),
            )

        items_on_rep_date = {_item_key(i): i for i in self.instance.items}
        # items_on_pl_start_date = {_item_key(i): i for i in report_on_pl_first_date.items}

        for item_plsd in report_on_pl_first_date.items:
            key = _item_key(item_plsd)
            item_rpd = items_on_rep_date.get(key, None)

            if item_rpd:
                item_rpd.pl_sub_item(item_plsd)

            else:
                item_rpd = ReportItem(self.instance, self.pricing_provider, self.fx_rate_provider, item_plsd.type)

                item_rpd.instr = item_plsd.instr
                item_rpd.ccy = item_plsd.ccy
                # item_rpd.trn_ccy = item_plsd.trn_ccy
                item_rpd.prtfl = item_plsd.prtfl
                item_rpd.instr = item_plsd.instr
                item_rpd.acc = item_plsd.acc
                item_rpd.str1 = item_plsd.str1
                item_rpd.str2 = item_plsd.str2
                item_rpd.str3 = item_plsd.str3
                item_rpd.notes = item_plsd.notes
                item_rpd.pricing_ccy = item_plsd.pricing_ccy
                item_rpd.trn = item_plsd.trn
                item_rpd.alloc = item_plsd.alloc
                item_rpd.alloc_bl = item_plsd.alloc_bl
                item_rpd.alloc_pl = item_plsd.alloc_pl
                item_rpd.mismatch_prtfl = item_plsd.mismatch_prtfl
                item_rpd.mismatch_acc = item_plsd.mismatch_acc

                item_rpd.pricing()
                item_rpd.pl_sub_item(item_plsd)

                self.instance.items.append(item_rpd)

        return report_on_pl_first_date

    # def _calc_pass2(self):
    #     _l.debug('transactions - pass 2')
    #
    #     items_map = {}
    #     for item in self._items:
    #         if item.type == ReportItem.TYPE_INSTRUMENT and item.instr:
    #             key = self._item_group_key_pass2(item=item)
    #             items_map[key] = item
    #
    #     for trn in self._transactions:
    #         if not trn.is_cloned and trn.trn_cls.id in [TransactionClass.BUY, TransactionClass.SELL]:
    #             key = self._item_group_key_pass2(trn=trn)
    #             item = items_map.get(key, None)
    #             if item:
    #                 trn.calc_pass2(balance_pos_size=item.pos_size)
    #                 item.add_pass2(trn)
    #             else:
    #                 raise RuntimeError('Oh error')
    #
    #     _l.debug('items - pass 2')
    #     for item in self._items:
    #         item.close_pass2()

    def _aggregate_summary(self):

        # print('settings.DEBUG %s' % settings.DEBUG)

        return

        # if not settings.DEBUG:
        #     return

        # _l.debug('aggregate summary')
        # # total = ReportItem(self.instance, self.pricing_provider, self.fx_rate_provider, ReportItem.TYPE_SUMMARY)
        # total = ReportItem.from_trn(self.instance, self.pricing_provider, self.fx_rate_provider,
        #                             ReportItem.TYPE_SUMMARY, trn)
        #
        # _l.debug('items len %s' % len(self._items))
        # _l.debug(repr(self._items[0]))
        #
        # for item in self._items:
        #     if item.type in [ReportItem.TYPE_INSTRUMENT, ReportItem.TYPE_CURRENCY, ReportItem.TYPE_TRANSACTION_PL,
        #                      ReportItem.TYPE_FX_TRADE, ReportItem.TYPE_CASH_IN_OUT]:
        #         total.add(item)
        # total.pricing()
        # total.close()
        # self._summaries.append(total)

    def _detect_mismatches(self):
        _l.debug('mismatches - detect')

        l = []
        for trn in self._transactions:
            if trn.is_mismatch and trn.link_instr and not isclose(trn.mismatch, 0.0):
                item = ReportItem.from_trn(self.instance, self.pricing_provider, self.fx_rate_provider,
                                           ReportItem.TYPE_MISMATCH, trn)
                l.append(item)

        # _l.debug('mismatches - raw.len=%s', len(l))

        if not l:
            return

        _l.debug('mismatches - aggregate')
        l = sorted(l, key=lambda x: self._item_mismatch_group_key(x))
        for k, g in groupby(l, key=lambda x: self._item_mismatch_group_key(x)):

            mismatch_item = None
            for item in g:
                if mismatch_item is None:
                    mismatch_item = ReportItem.from_item(item)
                mismatch_item.add(item)

            if mismatch_item:
                mismatch_item.pricing()
                mismatch_item.close()
                self._mismatch_items.append(mismatch_item)

        # _l.debug('mismatches - len=%s', len(self._mismatch_items))

    def _add_instr(self, trn, val=None):
        if trn.case == 0:
            item = ReportItem.from_trn(self.instance, self.pricing_provider, self.fx_rate_provider,
                                       ReportItem.TYPE_INSTRUMENT, trn, val=val)
            self._items.append(item)

        elif trn.case == 1:
            item = ReportItem.from_trn(self.instance, self.pricing_provider, self.fx_rate_provider,
                                       ReportItem.TYPE_INSTRUMENT, trn, val=val)
            self._items.append(item)

        elif trn.case == 2:
            pass

        else:
            raise RuntimeError('Invalid transaction case: %s' % trn.case)

    def _add_cash(self, trn, val, ccy, acc=None, acc_interim=None, str1=None, str2=None, str3=None):
        if trn.case == 0:
            item = ReportItem.from_trn(self.instance, self.pricing_provider, self.fx_rate_provider,
                                       ReportItem.TYPE_CURRENCY, trn, ccy=ccy, acc=acc,
                                       str1=str1, str2=str2, str3=str3,
                                       val=val)
            self._items.append(item)

        elif trn.case == 1:
            item = ReportItem.from_trn(self.instance, self.pricing_provider, self.fx_rate_provider,
                                       ReportItem.TYPE_CURRENCY, trn, ccy=ccy, acc=acc_interim or trn.acc_interim,
                                       str1=str1, str2=str2, str3=str3,
                                       val=val)
            self._items.append(item)

        elif trn.case == 2:
            item = ReportItem.from_trn(self.instance, self.pricing_provider, self.fx_rate_provider,
                                       ReportItem.TYPE_CURRENCY, trn, ccy=ccy, acc=acc,
                                       str1=str1, str2=str2, str3=str3,
                                       val=val)
            self._items.append(item)

            item = ReportItem.from_trn(self.instance, self.pricing_provider, self.fx_rate_provider,
                                       ReportItem.TYPE_CURRENCY, trn, ccy=ccy, acc=acc_interim or trn.acc_interim,
                                       str1=str1, str2=str2, str3=str3,
                                       val=-val)
            self._items.append(item)

        else:
            raise RuntimeError('Invalid transaction case: %s' % trn.case)

    def _get_member_permissions(self):

        result = []

        from poms.obj_perms.models import GenericObjectPermission
        result = GenericObjectPermission.objects.filter(member=self.instance.member)

        print('Member permissions %s ' % len(result))

        return result

    def _refresh_with_perms(self):
        # _l.debug('items - refresh all objects with permissions')

        # member_permissions = self._get_member_permissions()

        self.instance.portfolios = self._refresh_portfolios(
            master_user=self.instance.master_user,
            items=None,
            attrs=None,
            objects=self.instance.portfolios
        )
        self.instance.accounts = self._refresh_accounts(
            master_user=self.instance.master_user,
            items=None,
            attrs=None,
            objects=self.instance.accounts
        )
        self.instance.accounts_position = self._refresh_accounts(
            master_user=self.instance.master_user,
            items=None,
            attrs=None,
            objects=self.instance.accounts_position
        )
        self.instance.accounts_cash = self._refresh_accounts(
            master_user=self.instance.master_user,
            items=None,
            attrs=None,
            objects=self.instance.accounts_cash
        )
        self.instance.strategies1 = self._refresh_strategies1(
            master_user=self.instance.master_user,
            items=None,
            attrs=None,
            objects=self.instance.strategies1
        )
        self.instance.strategies2 = self._refresh_strategies2(
            master_user=self.instance.master_user,
            items=None,
            attrs=None,
            objects=self.instance.strategies2
        )
        self.instance.strategies3 = self._refresh_strategies3(
            master_user=self.instance.master_user,
            items=None,
            attrs=None,
            objects=self.instance.strategies3
        )

        self.instance.item_instruments = self._refresh_instruments(
            master_user=self.instance.master_user,
            items=self.instance.items,
            attrs=['instr', 'alloc']
        )
        self.instance.item_currencies = self._refresh_currencies(
            master_user=self.instance.master_user,
            items=self.instance.items,
            attrs=['ccy', 'pricing_ccy']
        )
        self.instance.item_portfolios = self._refresh_portfolios(
            master_user=self.instance.master_user,
            items=self.instance.items,
            attrs=['prtfl', 'mismatch_prtfl']
        )

        self.instance.item_accounts = self._refresh_accounts(
            master_user=self.instance.master_user,
            items=self.instance.items,
            attrs=['acc', 'mismatch_acc']
        )
        self.instance.item_strategies1 = self._refresh_strategies1(
            master_user=self.instance.master_user,
            items=self.instance.items,
            attrs=['str1']
        )
        self.instance.item_strategies2 = self._refresh_strategies2(
            master_user=self.instance.master_user,
            items=self.instance.items,
            attrs=['str2']
        )
        self.instance.item_strategies3 = self._refresh_strategies3(
            master_user=self.instance.master_user,
            items=self.instance.items,
            attrs=['str3']
        )
        self.instance.item_currency_fx_rates = self._refresh_currency_fx_rates(
            master_user=self.instance.master_user,
            items=self.instance.items,
            attrs=['report_ccy_cur', 'instr_pricing_ccy_cur', 'instr_accrued_ccy_cur', 'ccy_cur', 'pricing_ccy_cur']
        )
        self.instance.item_instrument_pricings = self._refresh_item_instrument_pricings(
            master_user=self.instance.master_user,
            items=self.instance.items,
            attrs=['instr_price_cur']
        )
        self.instance.item_instrument_accruals = self._refresh_item_instrument_accruals(
            master_user=self.instance.master_user,
            items=self.instance.items,
            attrs=['instr_accrual']
        )

        # instrs = set()
        # ccys = set()
        # prtfls = set()
        # accs = set()
        # strs1 = set()
        # strs2 = set()
        # strs3 = set()
        #
        # for i in self.instance.items:
        #     if i.instr:
        #         instrs.add(i.instr.id)
        #         if i.instr.pricing_currency_id:
        #             ccys.add(i.instr.pricing_currency_id)
        #         if i.instr.accrued_currency_id:
        #             ccys.add(i.instr.accrued_currency_id)
        #
        #     if i.ccy:
        #         ccys.add(i.ccy.id)
        #     # if i.trn_ccy:
        #     #     ccys.add(i.trn_ccy.id)
        #     if i.pricing_ccy:
        #         ccys.add(i.pricing_ccy.id)
        #
        #     if i.prtfl:
        #         prtfls.add(i.prtfl.id)
        #     if i.acc:
        #         accs.add(i.acc.id)
        #
        #     if i.str1:
        #         strs1.add(i.str1.id)
        #     if i.str2:
        #         strs2.add(i.str2.id)
        #     if i.str3:
        #         strs3.add(i.str3.id)
        #
        #     if i.mismatch_prtfl:
        #         prtfls.add(i.mismatch_prtfl.id)
        #     if i.mismatch_acc:
        #         accs.add(i.mismatch_acc.id)
        #
        #     if i.alloc:
        #         instrs.add(i.alloc.id)
        #         if i.alloc.pricing_currency_id:
        #             ccys.add(i.alloc.pricing_currency_id)
        #         if i.alloc.accrued_currency_id:
        #             ccys.add(i.alloc.accrued_currency_id)
        #
        #             # if i.alloc_bl:
        #             #     instrs.add(i.alloc_bl.id)
        #             #     if i.alloc_bl.pricing_currency_id:
        #             #         ccys.add(i.alloc_bl.pricing_currency_id)
        #             #     if i.alloc_bl.accrued_currency_id:
        #             #         ccys.add(i.alloc_bl.accrued_currency_id)
        #             #
        #             # if i.alloc_pl:
        #             #     instrs.add(i.alloc_pl.id)
        #             #     if i.alloc_pl.pricing_currency_id:
        #             #         ccys.add(i.alloc_pl.pricing_currency_id)
        #             #     if i.alloc_pl.accrued_currency_id:
        #             #         ccys.add(i.alloc_pl.accrued_currency_id)
        #
        # instrs = Instrument.objects.filter(master_user=self.instance.master_user).prefetch_related(
        #     'master_user',
        #     'instrument_type',
        #     'instrument_type__instrument_class',
        #     'pricing_currency',
        #     'accrued_currency',
        #     'payment_size_detail',
        #     'daily_pricing_model',
        #     'price_download_scheme',
        #     'price_download_scheme__provider',
        #     get_attributes_prefetch(),
        #     get_tag_prefetch(),
        #     *get_permissions_prefetch_lookups(
        #         (None, Instrument),
        #         ('instrument_type', InstrumentType),
        #     )
        # ).in_bulk(instrs)
        # _l.debug('instrs: %s', sorted(instrs.keys()))
        #
        # ccys = Currency.objects.filter(master_user=self.instance.master_user).prefetch_related(
        #     'master_user',
        #     'daily_pricing_model',
        #     'price_download_scheme',
        #     'price_download_scheme__provider',
        #     get_attributes_prefetch(),
        #     get_tag_prefetch()
        # ).in_bulk(ccys)
        # _l.debug('ccys: %s', sorted(ccys.keys()))
        #
        # prtfls = Portfolio.objects.filter(master_user=self.instance.master_user).prefetch_related(
        #     'master_user',
        #     get_attributes_prefetch(),
        #     get_tag_prefetch(),
        #     *get_permissions_prefetch_lookups(
        #         (None, Portfolio),
        #     )
        # ).in_bulk(prtfls)
        # _l.debug('prtfls: %s', sorted(prtfls.keys()))
        #
        # accs = Account.objects.filter(master_user=self.instance.master_user).prefetch_related(
        #     'master_user',
        #     'type',
        #     get_attributes_prefetch(),
        #     get_tag_prefetch(),
        #     *get_permissions_prefetch_lookups(
        #         (None, Account),
        #         ('type', AccountType),
        #     )
        # ).in_bulk(accs)
        # _l.debug('accs: %s', sorted(accs.keys()))
        #
        # strs1 = Strategy1.objects.filter(master_user=self.instance.master_user).prefetch_related(
        #     'master_user',
        #     'subgroup',
        #     'subgroup__group',
        #     get_tag_prefetch(),
        #     *get_permissions_prefetch_lookups(
        #         (None, Strategy1),
        #         ('subgroup', Strategy1Subgroup),
        #         ('subgroup__group', Strategy1Group),
        #     )
        # ).in_bulk(strs1)
        # _l.debug('strs1: %s', sorted(strs1.keys()))
        #
        # strs2 = Strategy2.objects.filter(master_user=self.instance.master_user).prefetch_related(
        #     'master_user',
        #     'subgroup',
        #     'subgroup__group',
        #     get_tag_prefetch(),
        #     *get_permissions_prefetch_lookups(
        #         (None, Strategy2),
        #         ('subgroup', Strategy2Subgroup),
        #         ('subgroup__group', Strategy2Group),
        #     )
        # ).in_bulk(strs2)
        # _l.debug('strs2: %s', sorted(strs2.keys()))
        #
        # strs3 = Strategy3.objects.filter(master_user=self.instance.master_user).prefetch_related(
        #     'master_user',
        #     'subgroup',
        #     'subgroup__group',
        #     get_tag_prefetch(),
        #     *get_permissions_prefetch_lookups(
        #         (None, Strategy3),
        #         ('subgroup', Strategy3Subgroup),
        #         ('subgroup__group', Strategy3Group),
        #     )
        # ).in_bulk(strs3)
        # _l.debug('strs3: %s', sorted(strs3.keys()))
        #
        # for i in self.instance.items:
        #     if i.instr:
        #         i.instr = instrs[i.instr.id]
        #         if i.instr.pricing_currency_id:
        #             i.instr.pricing_currency = ccys[i.instr.pricing_currency_id]
        #         if i.instr.accrued_currency_id:
        #             i.instr.accrued_currency = ccys[i.instr.accrued_currency_id]
        #
        #     if i.ccy:
        #         i.ccy = ccys[i.ccy.id]
        #     # if i.trn_ccy:
        #     #     i.trn_ccy = ccys[i.trn_ccy.id]
        #     if i.pricing_ccy:
        #         i.pricing_ccy = ccys[i.pricing_ccy.id]
        #
        #     if i.prtfl:
        #         i.prtfl = prtfls[i.prtfl.id]
        #     if i.acc:
        #         i.acc = accs[i.acc.id]
        #
        #     if i.str1:
        #         i.str1 = strs1[i.str1.id]
        #     if i.str2:
        #         i.str2 = strs2[i.str2.id]
        #     if i.str3:
        #         i.str3 = strs3[i.str3.id]
        #
        #     if i.mismatch_prtfl:
        #         i.mismatch_prtfl = prtfls[i.mismatch_prtfl.id]
        #     if i.mismatch_acc:
        #         i.mismatch_acc = accs[i.mismatch_acc.id]
        #
        #     if i.alloc:
        #         i.alloc = instrs[i.alloc.id]
        #         if i.alloc.pricing_currency_id:
        #             i.alloc.pricing_currency = ccys[i.alloc.pricing_currency_id]
        #         if i.alloc.accrued_currency_id:
        #             i.alloc.accrued_currency = ccys[i.alloc.accrued_currency_id]
        #
        #     # if i.alloc_bl:
        #     #     i.alloc_bl = instrs[i.alloc_bl.id]
        #     #     if i.alloc_bl.pricing_currency_id:
        #     #         i.alloc_bl.pricing_currency = ccys[i.alloc_bl.pricing_currency_id]
        #     #     if i.alloc_bl.accrued_currency_id:
        #     #         i.alloc_bl.accrued_currency = ccys[i.alloc_bl.accrued_currency_id]
        #     #
        #     # if i.alloc_pl:
        #     #     i.alloc_pl = instrs[i.alloc_pl.id]
        #     #     if i.alloc_pl.pricing_currency_id:
        #     #         i.alloc_pl.pricing_currency = ccys[i.alloc_pl.pricing_currency_id]
        #     #     if i.alloc_pl.accrued_currency_id:
        #     #         i.alloc_pl.accrued_currency = ccys[i.alloc_pl.accrued_currency_id]
        #     pass
        pass

    def _alloc_aggregation(self):
        _l.debug('aggregate by allocation: %s', self.instance.allocation_detailing)

        if self.instance.allocation_detailing:
            return

        def _group_key(x):
            return (
                x.alloc.id,
                # x.subtype,
            )

        no_alloc = self.instance.master_user.instrument

        res_items = []
        sorted_items = sorted(self.instance.items, key=_group_key)
        for k, g in groupby(sorted_items, key=_group_key):
            if k[0] == no_alloc.id:
                for item in g:
                    res_items.append(item)
            else:
                res_item = None
                for item in g:
                    if res_item is None:
                        res_item = ReportItem.alloc_from_item(item)
                        res_item.pricing()

                    res_item.add(item)

                if res_item:
                    res_item.set_pl_values(closed=0.0, opened=0.0)
                    res_item.close()
                    res_items.append(res_item)

        self.instance.items = res_items

    def _pl_regrouping(self):
        _l.debug('p&l regrouping')

        res_items = []
        for item in self.instance.items:
            if item.type in [ReportItem.TYPE_CURRENCY, ReportItem.TYPE_CASH_IN_OUT]:
                res_items.append(item)

            elif item.type in [ReportItem.TYPE_ALLOCATION]:
                res_items.append(item)

            elif item.type in [ReportItem.TYPE_INSTRUMENT]:
                if self.instance.pl_include_zero or not item.is_pl_is_zero(closed=True):
                    res_item = item.clone()
                    res_item.subtype = ReportItem.SUBTYPE_CLOSED
                    res_item.set_fields_by_subtype()
                    res_items.append(res_item)

                res_item = item.clone()
                res_item.subtype = ReportItem.SUBTYPE_OPENED
                res_item.set_fields_by_subtype()
                res_items.append(res_item)

            elif item.type in [ReportItem.TYPE_TRANSACTION_PL, ReportItem.TYPE_FX_TRADE, ReportItem.TYPE_CASH_IN_OUT,
                               ReportItem.TYPE_MISMATCH]:
                res_item = item.clone()
                res_item.subtype = ReportItem.SUBTYPE_CLOSED
                res_item.set_fields_by_subtype()
                res_item.subtype = ReportItem.SUBTYPE_DEFAULT
                res_items.append(res_item)

        self.instance.items = res_items
