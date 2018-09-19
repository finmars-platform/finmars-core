import uuid
from collections import OrderedDict
from datetime import timedelta, date

from poms.common.utils import date_now, isclose
from poms.instruments.models import CostMethod
from poms.reports.builders.base_item import BaseReport, BaseReportItem


class PerformancePeriod:
    def __init__(self, report, period_begin=None, period_end=None, period_name=None, period_key=None):
        self.report = report
        self.period_begin = period_begin
        self.period_end = period_end
        self.period_name = period_name
        self.period_key = period_key

        self.local_trns = []
        self.trns = []

        self._items = OrderedDict()

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return 'Period({period_begin}/{period_end},local_trns={local_trns},trns={trns},items={items})'.format(
            period_begin=self.period_begin,
            period_end=self.period_end,
            local_trns=len(self.local_trns),
            trns=len(self.trns),
            items=len(self._items)
        )

    @property
    def items(self):
        return self._items.values()

    def get(self, portfolio: object = None, account: object = None, strategy1: object = None, strategy2: object = None,
            strategy3: object = None,
            create: object = None) -> object:
        if create is None:
            create = True
        key = PerformanceReportItem.make_item_key(
            self.report,
            period_key=self.period_key,
            portfolio=portfolio,
            account=account,
            strategy1=strategy1,
            strategy2=strategy2,
            strategy3=strategy3
        )
        try:
            return self._items[key]
        except KeyError:
            if create:
                item = PerformanceReportItem(
                    self.report,
                    id=str(uuid.uuid4()),
                    period_begin=self.period_begin,
                    period_end=self.period_end,
                    period_name=self.period_name,
                    period_key=self.period_key,
                    portfolio=portfolio,
                    account=account,
                    strategy1=strategy1,
                    strategy2=strategy2,
                    strategy3=strategy3
                )
                self._items[key] = item
                return item
            else:
                return None

    def get_by_trn_pos(self, trn, create=None):
        return self.get(
            portfolio=trn.prtfl,
            account=trn.acc_pos,
            strategy1=trn.str1_pos,
            strategy2=trn.str2_pos,
            strategy3=trn.str3_pos,
            create=create,
        )

    def get_by_trn_cash(self, trn, interim=False, create=None):
        return self.get(
            portfolio=trn.prtfl,
            account=trn.acc_cash if not interim else trn.acc_interim,
            strategy1=trn.str1_cash,
            strategy2=trn.str2_cash,
            strategy3=trn.str3_cash,
            create=create,
        )

    def mkt_val_add(self, trn):
        if trn.is_buy or trn.is_sell:
            # if trn.case == 0:
            #     if not isclose(trn.instr_mkt_val_res, 0):
            #         item = self.get_by_trn_pos(trn)
            #         if trn.period_key == self.period_key:
            #             item.mkt_val_res += trn.instr_mkt_val_res
            #
            # elif trn.case == 1:
            #     if not isclose(trn.instr_mkt_val_res, 0):
            #         item = self.get_by_trn_pos(trn)
            #         if trn.period_key == self.period_key:
            #             item.mkt_val_res += trn.instr_mkt_val_res
            #
            # elif trn.case == 2:
            #     pass

            item = self.get_by_trn_pos(trn)
            if trn.period_key == self.period_key:
                item.mkt_val_res += trn.instr_mkt_val_res
                item.add_src_trn(trn)

    def nav_add(self, trn):
        # is_nav_period_start = trn.period_key < self.period_key

        if trn.is_buy or trn.is_sell:
            # if trn.case == 0:
            #     if not isclose(trn.instr_mkt_val_res, 0):
            #         item = self.get_by_trn_pos(trn)
            #         if is_nav_period_start:
            #             item.nav_period_start += trn.instr_mkt_val_res
            #         item.nav_period_end += trn.instr_mkt_val_res
            #
            #     # if not isclose(trn.cash_mkt_val_res, 0):
            #     #     item = self.get_by_trn_cash(trn, interim=False)
            #     #     if is_nav_period_start:
            #     #         item.nav_period_start += trn.cash_mkt_val_res
            #     #     item.nav_period_end += trn.cash_mkt_val_res
            #     pass
            #
            # elif trn.case == 1:
            #     if not isclose(trn.instr_mkt_val_res, 0):
            #         item = self.get_by_trn_pos(trn)
            #         if is_nav_period_start:
            #             item.nav_period_start += trn.instr_mkt_val_res
            #         item.nav_period_end += trn.instr_mkt_val_res
            #
            #     # if not isclose(trn.cash_mkt_val_res, 0):
            #     #     item = self.get_by_trn_cash(trn, interim=True)
            #     #     if is_nav_period_start:
            #     #         item.nav_period_start += trn.cash_mkt_val_res
            #     #     item.nav_period_end += trn.cash_mkt_val_res
            #     pass
            #
            # elif trn.case == 2:
            #     # if not isclose(trn.instr_mkt_val_res, 0):
            #     #     pass
            #     pass
            #
            #     # if not isclose(trn.cash_mkt_val_res, 0):
            #     #     item = self.get_by_trn_cash(trn, interim=False)
            #     #     if is_nav_period_start:
            #     #         item.nav_period_start += trn.cash_mkt_val_res
            #     #     item.nav_period_end += trn.cash_mkt_val_res
            #     #
            #     #     item = self.get_by_trn_cash(trn, interim=True)
            #     #     if is_nav_period_start:
            #     #         item.nav_period_start += -trn.cash_mkt_val_res
            #     #     item.nav_period_end += -trn.cash_mkt_val_res
            #     pass
            item = self.get_by_trn_pos(trn)
            # if is_nav_period_start:
            #     item.nav_period_start += trn.instr_mkt_val_res
            item.nav_period_end += trn.instr_mkt_val_res
            item.add_src_trn(trn)

    def pl_add(self, trn):
        pos_item = self.get_by_trn_pos(trn)
        if trn.is_cash_inflow or trn.is_cash_outflow:
            # = [Cash Consideration] * Current FX ratre of the Sttlm Ccy  / Current FX rate of the Reporting Ccy -
            # [Cash Consideration]  * [Reference FX rate] * Hist FX  rate of the Transact Ccy / Hist FX rate of the Reportin Ccy
            pos_item.accumulated_pl += trn.cash_res - trn.cash * trn.ref_fx * trn.trn_ccy_cur_fx
            pos_item.add_src_trn(trn)

        else:
            # =( Principal + Carry + Overheads) * Current FX ratre of the Sttlm Ccy / Current FX  rate of the Reporting ccy
            pos_item.accumulated_pl += trn.total_res
            pos_item.add_src_trn(trn)

    def cash_in_out_add(self, trn):
        # cash_flow = trn.total_res

        # Cash flow in reporting Ccy =  [Cash Consideration]  * Reference FX rate * Hist FX  rate (accounting date, Trans Ccy -> Sys Ccy) / Hist FX Rate (accounting date, Reporting Ccy -> Sys Ccy)
        cash_flow = trn.cash * trn.ref_fx * trn.trn_ccy_cur_fx

        cash_cash_in = 0
        cash_cash_out = 0
        pos_cash_in = 0
        pos_cash_out = 0

        if isclose(cash_flow, 0):
            pass

        elif cash_flow > 0:
            cash_cash_in = cash_flow
            cash_cash_out = 0
            pos_cash_in = 0
            pos_cash_out = -cash_flow

        elif cash_flow < 0:
            cash_cash_in = 0
            cash_cash_out = cash_flow
            pos_cash_in = -cash_flow
            pos_cash_out = 0

        cash_item = self.get_by_trn_cash(trn, interim=False)
        cash_item.cash_inflows += cash_cash_in
        cash_item.cash_outflows += cash_cash_out
        cash_item.time_weighted_cash_inflows += cash_cash_in * trn.period_time_weight
        cash_item.time_weighted_cash_outflows += cash_cash_out * trn.period_time_weight
        cash_item.add_src_trn(trn)

        pos_item = self.get_by_trn_pos(trn)
        pos_item.cash_inflows += pos_cash_in
        pos_item.cash_outflows += pos_cash_out
        pos_item.time_weighted_cash_inflows += pos_cash_in * trn.period_time_weight
        pos_item.time_weighted_cash_outflows += pos_cash_out * trn.period_time_weight
        pos_item.add_src_trn(trn)

    def close(self, prev_periods):
        prev_period = prev_periods[-1] if prev_periods else None
        for item in self._items.values():
            if prev_period:
                prev_item = prev_period.get(
                    portfolio=item.portfolio,
                    account=item.account,
                    strategy1=item.strategy1,
                    strategy2=item.strategy2,
                    strategy3=item.strategy3,
                    create=False
                )
            else:
                prev_item = None

            # item.close()

            item.accumulated_pl += item.mkt_val_res

            item.pl_in_period = item.accumulated_pl - getattr(prev_item, 'accumulated_pl', 0)

            item.nav_period_start = getattr(prev_item, 'nav_period_end', 0)
            # item.nav_period_end = 0

            item.nav_change = (item.nav_period_end - item.nav_period_start) + \
                              (item.cash_outflows - item.cash_inflows)

            # item.cash_inflows = 0
            # item.cash_outflows = 0
            # item.time_weighted_cash_inflows = 0
            # item.time_weighted_cash_outflows = 0

            item.avg_nav_in_period = item.nav_period_start + \
                                     (item.time_weighted_cash_inflows - item.time_weighted_cash_outflows)

            try:
                item.return_pl = item.pl_in_period / item.avg_nav_in_period
            except ArithmeticError:
                item.return_pl = 0

            try:
                item.return_nav = item.nav_change / item.avg_nav_in_period
            except ArithmeticError:
                item.return_nav = 0

            # = ("Cummulative Return (P&L), %  of previous period" + 1) * (Return (P&L), % of the current period + 1) - 1
            item.cumulative_return_pl = (getattr(prev_item, 'cumulative_return_pl', 0) + 1) * (item.return_pl + 1) - 1

            # =  (Cummulative Return (NAV chng ex CF), %  of previous period + 1) * (Return (NAV chng ex CF), % of the current period + 1) - 1
            item.cumulative_return_nav = (getattr(prev_item, 'cumulative_return_nav', 0) + 1) * (item.return_nav + 1) - 1

    def same_item_key(self, current, prev):
        return PerformanceReportItem.make_item_key(
            self.report,
            period_key=prev.period_key,
            portfolio=current.portfolio,
            account=current.account,
            strategy1=current.strategy1,
            strategy2=current.strategy2,
            strategy3=current.strategy3
        )


class PerformanceReportItem(BaseReportItem):
    # TYPE_DEFAULT = 0
    # TYPE_MKT_VAL = 1
    # TYPE_PL = 2

    def __init__(self, report, id=None,
                 period_begin=None, period_end=None, period_name=None, period_key=None,
                 portfolio=None, account=None, strategy1=None, strategy2=None, strategy3=None):
        super(PerformanceReportItem, self).__init__(report, None, None)
        # self.report = report
        self.id = str(id) if id is not None else ''

        # self.item_type = item_type if item_type is not None else PerformanceReportItem.TYPE_DEFAULT

        self.period_begin = period_begin
        self.period_end = period_end
        self.period_name = period_name
        self.period_key = period_key
        self.portfolio = portfolio
        self.account = account
        self.strategy1 = strategy1
        self.strategy2 = strategy2
        self.strategy3 = strategy3
        self.src_trns_id = set()

        # temporal fields
        # self.acc_date = date.min
        # self.processing_date = date.min
        # self.instr_principal_res = 0
        # self.instr_accrued_res = 0
        # self.cash_res = 0
        # self.principal_res = 0
        # self.carry_res = 0
        # self.overheads_res = 0
        # self.total_res = 0
        self.mkt_val_res = 0
        # self.global_time_weight = 0
        # self.period_time_weight = 0

        # final fields
        self.return_pl = 0
        self.return_nav = 0
        self.accumulated_pl = 0
        self.pl_in_period = 0
        self.nav_change = 0
        self.nav_period_start = 0
        self.nav_period_end = 0
        self.cash_inflows = 0
        self.cash_outflows = 0
        self.time_weighted_cash_inflows = 0
        self.time_weighted_cash_outflows = 0
        self.avg_nav_in_period = 0
        self.cumulative_return_pl = 0
        self.cumulative_return_nav = 0

        self.custom_fields = []

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return 'PerfItem(' \
               '{period_begin}/{period_end},' \
               'portfolio={portfolio},' \
               'account={account},' \
               'strategy1={strategy1},' \
               'strategy2={strategy2},' \
               'strategy3={strategy3}' \
               ')'.format(
            period_begin=self.period_begin,
            period_end=self.period_end,
            portfolio=getattr(self.portfolio, 'id', -1),
            account=getattr(self.account, 'id', -1),
            strategy1=getattr(self.strategy1, 'id', -1),
            strategy2=getattr(self.strategy2, 'id', -1),
            strategy3=getattr(self.strategy3, 'id', -1),
        )

    @staticmethod
    def make_item_key(report, period_key=None, portfolio=None, account=None,
                      strategy1=None, strategy2=None, strategy3=None):
        # return (
        #     self.period_key,
        #     self.portfolio.id,
        #     self.account.id,
        #     self.strategy1.id,
        #     self.strategy2.id,
        #     self.strategy3.id
        # )
        # if report.portfolio_mode == PerformanceReport.MODE_INDEPENDENT:
        #     pass
        # else:
        #     portfolio = None
        #
        # if report.account_mode == PerformanceReport.MODE_INDEPENDENT:
        #     pass
        # else:
        #     account = None
        #
        # if report.strategy1_mode == PerformanceReport.MODE_INDEPENDENT:
        #     pass
        # else:
        #     strategy1 = None
        #
        # if report.strategy2_mode == PerformanceReport.MODE_INDEPENDENT:
        #     pass
        # else:
        #     strategy2 = None
        #
        # if report.strategy3_mode == PerformanceReport.MODE_INDEPENDENT:
        #     pass
        # else:
        #     strategy3 = None

        return (
            period_key,
            getattr(portfolio, 'id', -1),
            getattr(account, 'id', -1),
            getattr(strategy1, 'id', -1),
            getattr(strategy2, 'id', -1),
            getattr(strategy3, 'id', -1),
        )

    @property
    def item_key(self):
        return PerformanceReportItem.make_item_key(
            self.report,
            period_key=self.period_key,
            portfolio=self.portfolio,
            account=self.account,
            strategy1=self.strategy1,
            strategy2=self.strategy2,
            strategy3=self.strategy3
        )

    # def close(self):
    #     self.accumulated_pl += self.mkt_val_res
    #
    #     try:
    #         self.return_nav = self.nav_change / self.avg_nav_in_period
    #     except ArithmeticError:
    #         self.return_nav = 0
    #
    #     # self.pl_in_period = 0
    #
    #     self.nav_change = (self.nav_period_end - self.nav_period_start) + \
    #                       (self.cash_outflows - self.cash_inflows)
    #
    #     # self.nav_period_start = 0
    #
    #     # self.nav_period_end = 0
    #
    #     # self.cash_inflows = 0
    #
    #     # self.cash_outflows = 0
    #
    #     # self.time_weighted_cash_inflows = 0
    #
    #     # self.time_weighted_cash_outflows = 0
    #
    #     self.avg_nav_in_period = self.nav_period_start + \
    #                              (self.time_weighted_cash_inflows - self.time_weighted_cash_outflows)
    #
    #     try:
    #         self.return_pl = self.pl_in_period / self.avg_nav_in_period
    #     except ArithmeticError:
    #         self.return_pl = 0
    #     try:
    #         self.return_nav = self.nav_change / self.avg_nav_in_period
    #     except ArithmeticError:
    #         self.return_nav = 0
    #
    #     # self.cumulative_return_pl = 0
    #
    #     # self.cumulative_return_nav = 0
    #     pass

    def add_src_trn(self, trn):
        if trn.trn:
            self.src_trns_id.add(trn.trn.pk)

    def eval_custom_fields(self):
        # use optimization inside serialization
        res = []
        self.custom_fields = res


class PerformanceReport(BaseReport):
    report_type = 0  # VirtualTransaction
    report_date = date.min  # VirtualTransaction

    def __init__(self,
                 id=None,
                 task_id=None,
                 task_status=None,
                 master_user=None,
                 member=None,
                 begin_date=None,
                 end_date=None,
                 report_currency=None,
                 pricing_policy=None,
                 periods=None,
                 portfolio_mode=BaseReport.MODE_INDEPENDENT,
                 account_mode=BaseReport.MODE_INDEPENDENT,
                 strategy1_mode=BaseReport.MODE_INDEPENDENT,
                 strategy2_mode=BaseReport.MODE_INDEPENDENT,
                 strategy3_mode=BaseReport.MODE_INDEPENDENT,
                 cost_method=None,
                 approach_multiplier=0.5,
                 portfolios=None,
                 accounts=None,
                 accounts_position=None,
                 accounts_cash=None,
                 strategies1=None,
                 strategies2=None,
                 strategies3=None,
                 custom_fields=None,
                 items=None):
        super(PerformanceReport, self).__init__(id=id, master_user=master_user, member=member,
                                                task_id=task_id, task_status=task_status)

        self.has_errors = False

        d = date_now() - timedelta(days=1)
        self.begin_date = begin_date or date(d.year, 1, 1)
        # self.begin_date = date.min
        self.end_date = end_date or d
        self.report_currency = report_currency or master_user.system_currency
        self.pricing_policy = pricing_policy
        self.periods = periods
        self.portfolio_mode = portfolio_mode
        self.account_mode = account_mode
        self.strategy1_mode = strategy1_mode
        self.strategy2_mode = strategy2_mode
        self.strategy3_mode = strategy3_mode
        self.allocation_mode = PerformanceReport.MODE_IGNORE
        self.cost_method = cost_method or CostMethod.objects.get(pk=CostMethod.AVCO)
        self.approach_multiplier = approach_multiplier
        self.approach_begin_multiplier = self.approach_multiplier
        self.approach_end_multiplier = 1.0 - self.approach_multiplier
        self.portfolios = portfolios or []
        self.accounts = accounts or []
        self.accounts_position = accounts_position or []
        self.accounts_cash = accounts_cash or []
        self.strategies1 = strategies1 or []
        self.strategies2 = strategies2 or []
        self.strategies3 = strategies3 or []
        self.custom_fields = custom_fields or []

        self.items = items
        self.item_portfolios = []
        self.item_accounts = []
        self.item_strategies1 = []
        self.item_strategies2 = []
        self.item_strategies3 = []

    def __str__(self):
        return 'PerformanceReport:%s' % self.id

    def close(self):
        for item in self.items:
            item.eval_custom_fields()
