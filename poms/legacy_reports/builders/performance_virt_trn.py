from datetime import date

from poms.reports.builders.balance_virt_trn import VirtualTransaction


class PerformanceVirtualTransaction(VirtualTransaction):
    period_key = None
    period_begin = None
    period_end = None
    period_name = None

    processing_date = None

    # global_time_weight = 0
    period_time_weight = 0

    instr_mkt_val_res = 0
    cash_mkt_val_res = 0

    # cash_flow_cash_res = 0
    # cash_flow_pos_res = 0

    # time_weight_cash_flow_cash_res = 0
    # time_weight_cash_flow_pos_res = 0

    def __init__(self, report, pricing_provider, fx_rate_provider, trn, overrides=None):
        super(PerformanceVirtualTransaction, self).__init__(
            report=report,
            pricing_provider=pricing_provider,
            fx_rate_provider=fx_rate_provider,
            trn=trn,
            overrides=overrides
        )
        self.report_ccy = self.report.report_currency

    def __repr__(self):
        return 'PVT(%s)' % self.trn_code

    def set_case(self):
        if self.processing_date:
            if self.acc_date <= self.processing_date < self.cash_date:
                self.case = 1
            elif self.cash_date <= self.processing_date < self.acc_date:
                self.case = 2
            else:
                self.case = 0
        else:
            self.case = 0

    def set_period(self, name, begin, end):
        if name is None:
            name = ''
        if begin is None:
            begin = date.min
        if end is None:
            end = date.min
        self.period_name = name
        self.period_begin = begin
        self.period_end = end

        # self.period_key = (str(self.period_begin), str(self.period_end), self.period_name)
        self.period_key = (str(self.period_end), str(self.period_begin), self.period_name)

        self.set_processing_date(self.period_end)

    def set_processing_date(self, processing_date):
        self.processing_date = processing_date
        self.set_case()

    def pricing(self):
        pass

    def calc(self):
        pass

    def perf_pricing(self):
        # report ccy
        self.report_ccy_cur = self.fx_rate_provider[self.report.report_currency, self.processing_date]
        self.report_ccy_cur_fx = self.report_ccy_cur.fx_rate

        try:
            report_ccy_cur_fx = 1.0 / self.report_ccy_cur_fx
        except ArithmeticError:
            report_ccy_cur_fx = 0.0

        # instr
        if self.instr:
            self.instr_price_cur = self.pricing_provider[self.instr, self.processing_date]
            self.instr_price_cur_principal_price = self.instr_price_cur.principal_price
            self.instr_price_cur_accrued_price = self.instr_price_cur.accrued_price

            self.instr_pricing_ccy_cur = self.fx_rate_provider[self.instr.pricing_currency, self.processing_date]
            self.instr_pricing_ccy_cur_fx = self.instr_pricing_ccy_cur.fx_rate * report_ccy_cur_fx

            self.instr_accrued_ccy_cur = self.fx_rate_provider[self.instr.accrued_currency, self.processing_date]
            self.instr_accrued_ccy_cur_fx = self.instr_accrued_ccy_cur.fx_rate * report_ccy_cur_fx

        # trn ccy
        if self.trn_ccy:
            self.trn_ccy_cur = self.fx_rate_provider[self.trn_ccy, self.processing_date]
            self.trn_ccy_cur_fx = self.trn_ccy_cur.fx_rate * report_ccy_cur_fx

        # stl ccy
        if self.stl_ccy:
            self.stl_ccy_cur = self.fx_rate_provider[self.stl_ccy, self.processing_date]
            self.stl_ccy_cur_fx = self.stl_ccy_cur.fx_rate * report_ccy_cur_fx

    def perf_calc(self):
        # if self.trn_cls.id in [TransactionClass.BUY, TransactionClass.SELL, TransactionClass.TRANSACTION_PL,
        #                        TransactionClass.INSTRUMENT_PL, TransactionClass.FX_TRADE]:
        if self.is_buy or self.is_sell or self.is_transaction_pl or self.is_instrument_pl or self.is_fx_trade:
            if self.instr:
                self.instr_principal = self.pos_size * self.instr.price_multiplier * self.instr_price_cur_principal_price
                self.instr_principal_res = self.instr_principal * self.instr_pricing_ccy_cur_fx

                self.instr_accrued = self.pos_size * self.instr.accrued_multiplier * self.instr_price_cur_accrued_price
                self.instr_accrued_res = self.instr_accrued * self.instr_accrued_ccy_cur_fx

            self.total = self.principal + self.carry + self.overheads

            self.cash_res = self.cash * self.stl_ccy_cur_fx

            self.principal_res = self.principal * self.stl_ccy_cur_fx
            self.carry_res = self.carry * self.stl_ccy_cur_fx
            self.overheads_res = self.overheads * self.stl_ccy_cur_fx
            self.total_res = self.total * self.stl_ccy_cur_fx

        # try:
        #     self.global_time_weight = (self.report.end_date - self.acc_date).days / \
        #                               (self.report.end_date - self.report.begin_date).days
        # except ArithmeticError:
        #     self.global_time_weight = 0

        try:
            # self.period_time_weight = (self.processing_date - self.acc_date).days / \
            #                           (self.processing_date - self.period_begin).days
            self.period_time_weight = (self.period_end - self.acc_date).days / \
                                      (self.period_end - self.period_begin).days
        except ArithmeticError:
            self.period_time_weight = 0

        # self.cash_flow_cash_res = self.total_res
        # self.cash_flow_pos_res = -self.total_res
        #
        # self.time_weight_cash_flow_cash_res = self.cash_flow_cash_res * self.period_time_weight
        # self.time_weight_cash_flow_pos_res = self.cash_flow_pos_res * self.period_time_weight

        # mkt_val
        if self.is_buy or self.is_sell:
            self.instr_mkt_val_res = self.instr_principal_res + self.instr_accrued_res
            self.cash_mkt_val_res = self.cash_res

        elif self.is_cash_inflow or self.is_cash_outflow:
            self.cash_mkt_val_res = self.cash_res

        elif self.is_instrument_pl:
            self.cash_mkt_val_res = self.cash_res

        elif self.is_transaction_pl:
            self.cash_mkt_val_res = self.cash_res

        elif self.is_fx_trade:
            self.cash_mkt_val_res = self.principal_res

        elif self.is_transfer:
            pass

        elif self.is_fx_transfer:
            pass

        else:
            pass
