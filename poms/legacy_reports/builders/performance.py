import logging
import time
from collections import OrderedDict
from datetime import date

from django.db import transaction
from django.db.models import Q
from django.utils.functional import cached_property, SimpleLazyObject
from poms.reports.builders.balance_pl import ReportBuilder
from poms.reports.builders.performance_item import PerformancePeriod
from poms.reports.builders.performance_virt_trn import PerformanceVirtualTransaction
from poms.reports.builders.pricing import FakeInstrumentPricingProvider, InstrumentPricingProvider, \
    FakeCurrencyFxRateProvider, CurrencyFxRateProvider

from poms.common import formula

_l = logging.getLogger('poms.reports')


class PerformanceReportBuilder(ReportBuilder):
    trn_cls = PerformanceVirtualTransaction

    def __init__(self, instance=None, queryset=None, transactions=None, pricing_provider=None, fx_rate_provider=None):
        super(PerformanceReportBuilder, self).__init__(
            instance=instance,
            queryset=queryset,
            transactions=transactions,
            pricing_provider=pricing_provider,
            fx_rate_provider=fx_rate_provider
        )

        # self._original_transactions = None

        self._periods = OrderedDict()

    def build_performance(self):
        st = time.perf_counter()
        _l.debug('build transaction')

        with transaction.atomic():
            try:
                self._load_transactions()
                # self._original_transactions = self.transactions.copy()
                self._process_periods()
                self._periods_init()
                self._periods_pricing()
                self._calc()
                self._make_items()

                if self.instance.has_errors:
                    self.instance.items = []

                self._refresh_from_db()
            finally:
                transaction.set_rollback(True)

        _l.debug('done: %s', (time.perf_counter() - st))
        return self.instance

    def _trn_qs_filter(self, qs):
        # qs = super(PerformanceReportBuilder, self)._trn_qs()

        filters = Q()

        if self.instance.begin_date:
            filters &= Q(accounting_date__gte=self.instance.begin_date)

        if self.instance.end_date:
            filters &= Q(accounting_date__lte=self.instance.end_date)

        qs = qs.filter(filters)

        qs = qs.order_by('accounting_date', 'transaction_code')

        return qs

    def _process_periods(self):
        _l.debug('> process periods')

        context = self.instance.context.copy()
        context['date_group_with_dates'] = True

        for trn in self._transactions:
            try:
                period = formula.safe_eval(self.instance.periods, names={'transaction': trn.trn}, context=context)
            except formula.InvalidExpression:
                self.instance.has_errors = True
                _l.debug('periods error', exc_info=True)
                return

            if isinstance(period, (tuple, list)):
                name, begin, end = period
                name = str(name)
                if not isinstance(begin, date) or not isinstance(end, date):
                    _l.debug('hacker detected on: trn=%s, period=%s', trn.pk, self.instance.periods)
                    name, begin, end = name, date.max, date.max
            else:
                name, begin, end = 'Default', date.max, date.max

            trn.set_period(name=name, begin=begin, end=end)

        _l.debug('< process periods')

    @cached_property
    def _instruments(self):
        assert self._transactions is not None
        instruments = {}
        for trn in self._transactions:
            if trn.instr:
                instruments[trn.instr.id] = trn.instr
        return list(instruments.values())

    @cached_property
    def _currencies(self):
        assert self._transactions is not None
        currencies = {self.instance.report_currency.id: self.instance.report_currency}
        for trn in self._transactions:
            if trn.trn_ccy:
                currencies[trn.trn_ccy.id] = trn.trn_ccy
            currencies[trn.stl_ccy.id] = trn.stl_ccy
        return list(currencies.values())

    @cached_property
    def _dates(self):
        assert self._transactions is not None
        dates = {t.period_end for t in self._transactions if t.period_end != date.min}
        return dates

    @property
    def pricing_provider(self):
        def _factory():
            assert self._transactions is not None

            if self._pricing_provider is None:
                if self.instance.pricing_policy is None:
                    p = FakeInstrumentPricingProvider(self.instance.master_user, None, None)
                else:
                    p = InstrumentPricingProvider(self.instance.master_user, self.instance.pricing_policy, None)
                    p.fill_using_instruments_and_dates(instruments=self._instruments, dates=self._dates)
                self._pricing_provider = p
            return self._pricing_provider

        return SimpleLazyObject(_factory)

    @property
    def fx_rate_provider(self):
        def _factory():
            assert self._transactions is not None

            if self._fx_rate_provider is None:
                if self.instance.pricing_policy is None:
                    p = FakeCurrencyFxRateProvider(self.instance.master_user, None, None)
                else:
                    p = CurrencyFxRateProvider(self.instance.master_user, self.instance.pricing_policy, None)
                    p.fill_using_currencies_and_dates(currencies=self._currencies, dates=self._dates)
                self._fx_rate_provider = p
            return self._fx_rate_provider

        return SimpleLazyObject(_factory)

    def _periods_init(self):
        _l.debug('> _periods_init')

        for trn in self._transactions:
            if trn.period_key not in self._periods:
                period = PerformancePeriod(
                    self.instance,
                    period_begin=trn.period_begin,
                    period_end=trn.period_end,
                    period_name=trn.period_name,
                    period_key=trn.period_key
                )
                self._periods[trn.period_key] = period

        _l.debug('count=%s', len(self._periods))
        _l.debug('periods=%s', ['%s' % p for p in self._periods.values()])

        _l.debug('fill period transaction list')
        for trn in self._transactions:
            # period_key = trn.period_key
            _l.debug('  trn: pk=%s, cls=%s, period_key=%s', trn.pk, trn.trn_cls, trn.period_key)

            if trn.is_hidden:
                _l.debug('    skip trn: is_hidden=%s', trn.is_hidden)
                continue

            for period in self._periods.values():
                if trn.period_key == period.period_key:
                    period.local_trns.append(trn.clone())
                if trn.period_key <= period.period_key:
                    period.trns.append(trn.clone())

        _l.debug('< _periods_init')

    def _periods_pricing(self):
        _l.debug('> _periods_pricing')

        for period in self._periods.values():
            _l.debug('%s', period)
            for trn in period.local_trns:
                trn.perf_pricing()

            for trn in period.trns:
                trn.set_processing_date(period.period_end)
                trn.perf_pricing()

        _l.debug('< _periods_pricing')

    def _calc(self):
        _l.debug('> calc')

        for period in self._periods.values():
            _l.debug('%s', period)

            self._transactions = period.trns

            self._transaction_multipliers()
            self._clone_transactions_if_need()

            self._transactions = [trn for trn in self._transactions if not trn.is_hidden]

            for trn in period.local_trns:
                trn.perf_calc()
                period.mkt_val_add(trn)
                period.cash_in_out_add(trn)

            for trn in self._transactions:
                trn.perf_calc()
                period.pl_add(trn)
                period.nav_add(trn)

        _l.debug('close periods')
        prev_periods = []
        for period in self._periods.values():
            period.close(prev_periods)
            prev_periods.append(period)

        _l.debug('< calc')

    def _make_items(self):
        _l.debug('> _make_items')

        self.instance.items = []
        for period in self._periods.values():
            self.instance.items.extend(period.items)

        _l.debug('< _make_items: %s', len(self.instance.items))

    # def _calc2(self):
    #     _l.debug('> calc')
    #
    #     periods = OrderedDict()
    #
    #     _l.debug('find periods')
    #     for trn in self._transactions:
    #         if trn.period_key not in periods:
    #             period = PerformancePeriod(
    #                 self.instance,
    #                 period_begin=trn.period_begin,
    #                 period_end=trn.period_end,
    #                 period_name=trn.period_name,
    #                 period_key=trn.period_key
    #             )
    #             _l.debug('  %s', period)
    #             periods[trn.period_key] = period
    #
    #     periods = list(periods.values())
    #     _l.debug('periods: %s', periods)
    #
    #     _l.debug('make periods')
    #     for trn in self._transactions:
    #         # period_key = trn.period_key
    #         _l.debug('  trn: pk=%s, cls=%s, period_key=%s', trn.pk, trn.trn_cls, trn.period_key)
    #
    #         if trn.is_hidden:
    #             _l.debug('    skip trn: is_hidden=%s', trn.is_hidden)
    #             continue
    #
    #         for period in periods:
    #             if trn.period_key == period.period_key:
    #                 period.local_trns.append(trn.clone())
    #             if trn.period_key <= period.period_key:
    #                 period.trns.append(trn.clone())
    #
    #     _l.debug('periods: %s', periods)
    #
    #     _l.debug('load pricing and first calculations')
    #     for period in periods:
    #         _l.debug('  %s', period)
    #         for trn in period.local_trns:
    #             trn.perf_pricing()
    #             trn.perf_calc()
    #
    #         for trn in period.trns:
    #             trn.processing_date = period.period_end
    #             trn.set_case()
    #             trn.perf_pricing()
    #             trn.perf_calc()
    #
    #     _l.debug('calculating')
    #     for period in periods:
    #         _l.debug('period: %s', period)
    #
    #         for trn in period.local_trns:
    #             period.cash_in_out_add(trn)
    #             pass
    #
    #         for trn in period.trns:
    #             period.nav_add(trn)
    #             # period.pl_add(trn)
    #             # period.cash_in_out_add(trn)
    #             pass
    #
    #         # # --------
    #         # _l.debug('items: local_trns=%s', len(period.trns))
    #         # for trn in period.local_trns:
    #         #     _l.debug('  pk=%s, cls=%s, period_key=%s', trn.pk, trn.trn_cls, trn.period_key)
    #         #     cash_item = self._create_cash_item(trn, interim=False)
    #         #     cash_item.set_as_cash(trn)
    #         #     period.items.append(cash_item)
    #         #
    #         #     pos_item = self._create_pos_item(trn)
    #         #     pos_item.set_as_pos(trn)
    #         #     period.items.append(pos_item)
    #
    #     _l.debug('periods: %s', periods)
    #
    #     _l.debug('aggregate: perids=%s', len(periods))
    #     prev_period = None
    #     for period in periods:
    #         period.close(prev_period)
    #         prev_period = period
    #
    #     _l.debug('periods: %s', periods)
    #
    #     items = []
    #     for period in periods:
    #         items.extend(period.items)
    #
    #     _l.debug('items: %s', items)
    #     self.instance.items = items
    #
    #     _l.debug('< calc')

    def _refresh_from_db(self):
        _l.debug('> refresh from db')

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

        self.instance.item_portfolios = self._refresh_portfolios(
            master_user=self.instance.master_user,
            items=self.instance.items,
            attrs=['portfolio']
        )
        self.instance.item_accounts = self._refresh_accounts(
            master_user=self.instance.master_user,
            items=self.instance.items,
            attrs=['account']
        )
        self.instance.item_strategies1 = self._refresh_strategies1(
            master_user=self.instance.master_user,
            items=self.instance.items,
            attrs=['strategy1']
        )
        self.instance.item_strategies2 = self._refresh_strategies2(
            master_user=self.instance.master_user,
            items=self.instance.items,
            attrs=['strategy2']
        )
        self.instance.item_strategies3 = self._refresh_strategies3(
            master_user=self.instance.master_user,
            items=self.instance.items,
            attrs=['strategy3']
        )

        _l.debug('< refresh from db')
