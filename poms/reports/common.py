from datetime import timedelta, date

from poms.common.utils import date_now
from poms.instruments.models import CostMethod
from poms.users.models import EcosystemDefault


class BaseReport:
    # CONSOLIDATION = 1
    MODE_IGNORE = 0
    MODE_INDEPENDENT = 1
    MODE_INTERDEPENDENT = 2
    MODE_CHOICES = (
        (MODE_IGNORE, 'Ignore'),
        (MODE_INDEPENDENT, 'Independent'),
        (MODE_INTERDEPENDENT, 'Offsetting (Interdependent - 0/100, 100/0, 50/50)'),
    )

    def __init__(self, id=None, master_user=None, member=None, task_id=None, task_status=None):
        self.id = id
        self.task_id = task_id
        self.task_status = task_status
        self.master_user = master_user
        self.member = member

        self.context = {
            'master_user': self.master_user,
            'member': self.member,
        }


class Report(BaseReport):
    TYPE_BALANCE = 1
    TYPE_PL = 2
    TYPE_CHOICES = (
        (TYPE_BALANCE, 'Balance'),
        (TYPE_PL, 'P&L'),
    )

    def __init__(self,
                 id=None,
                 master_user=None,
                 member=None,
                 task_id=None,
                 task_status=None,
                 report_instance_name=None,
                 save_report=False,
                 pl_first_date=None,
                 report_type=TYPE_BALANCE,
                 report_date=None,
                 report_currency=None,
                 pricing_policy=None,
                 cost_method=None,
                 portfolio_mode=BaseReport.MODE_INDEPENDENT,
                 account_mode=BaseReport.MODE_INDEPENDENT,
                 strategy1_mode=BaseReport.MODE_INDEPENDENT,
                 strategy2_mode=BaseReport.MODE_INDEPENDENT,
                 strategy3_mode=BaseReport.MODE_INDEPENDENT,
                 allocation_mode=BaseReport.MODE_INDEPENDENT,
                 show_transaction_details=False,
                 show_balance_exposure_details=False,
                 approach_multiplier=0.5,
                 expression_iterations_count=1,
                 allocation_detailing=True,
                 pl_include_zero=True,
                 instruments=None,
                 portfolios=None,
                 accounts=None,
                 accounts_position=None,
                 accounts_cash=None,
                 strategies1=None,
                 strategies2=None,
                 strategies3=None,
                 transaction_classes=None,
                 date_field=None,
                 custom_fields=None,
                 custom_fields_to_calculate=None,
                 calculate_pl=True,
                 items=None,

                 execution_time=None,
                 serialization_time=None

                 ):
        super(Report, self).__init__(id=id, master_user=master_user, member=member,
                                     task_id=task_id, task_status=task_status)

        # self.id = id
        # self.task_id = task_id
        # self.task_status = task_status
        # self.master_user = master_user
        # self.member = member
        # self.context = {
        #     'master_user': self.master_user,
        #     'member': self.member,
        # }

        self.ecosystem_default = EcosystemDefault.objects.get(master_user=master_user)

        self.report_type = report_type if report_type is not None else Report.TYPE_BALANCE
        self.report_currency = report_currency or self.ecosystem_default.currency
        self.pricing_policy = pricing_policy or self.ecosystem_default.pricing_policy
        self.pl_first_date = pl_first_date
        self.report_date = report_date or (date_now() - timedelta(days=1))
        self.cost_method = cost_method or CostMethod.objects.get(pk=CostMethod.AVCO)

        self.report_instance_name = report_instance_name
        self.save_report = save_report
        self.portfolio_mode = portfolio_mode
        self.account_mode = account_mode
        self.strategy1_mode = strategy1_mode
        self.strategy2_mode = strategy2_mode
        self.strategy3_mode = strategy3_mode
        self.allocation_mode = allocation_mode
        self.show_transaction_details = show_transaction_details
        self.show_balance_exposure_details = show_balance_exposure_details
        self.approach_multiplier = approach_multiplier
        self.expression_iterations_count = expression_iterations_count
        self.allocation_detailing = allocation_detailing
        self.pl_include_zero = pl_include_zero

        self.instruments = instruments or []
        self.portfolios = portfolios or []
        self.accounts = accounts or []
        self.accounts_position = accounts_position or []
        self.accounts_cash = accounts_cash or []
        self.strategies1 = strategies1 or []
        self.strategies2 = strategies2 or []
        self.strategies3 = strategies3 or []

        self.transaction_classes = transaction_classes or []
        # self.date_field = date_field or 'transaction_date'
        if date_field:
            self.date_field = date_field
        else:
            if self.report_type == Report.TYPE_BALANCE:
                self.date_field = 'transaction_date'
            elif self.report_type == Report.TYPE_PL:
                self.date_field = 'accounting_date'
            else:
                self.date_field = 'transaction_date'

        self.custom_fields = custom_fields or []
        self.custom_fields_to_calculate = custom_fields_to_calculate or ''

        self.items = items or []
        self.transactions = []

        self.item_instruments = []
        self.item_currencies = []
        self.item_portfolios = []
        self.item_accounts = []
        self.item_strategies1 = []
        self.item_strategies2 = []
        self.item_strategies3 = []
        self.item_currency_fx_rates = []
        self.item_instrument_pricings = []
        self.item_instrument_accruals = []
        self.calculate_pl = calculate_pl

    def __str__(self):
        return "%s for %s/%s @ %s" % (self.__class__.__name__, self.master_user, self.member, self.report_date)

    def close(self):
        for item in self.items:
            item.eval_custom_fields()

            # item_instruments = {}
            # item_currencies = {}
            # item_portfolios = {}
            # item_accounts = {}
            # item_strategies1 = {}
            # item_strategies2 = {}
            # item_strategies3 = {}
            # item_currency_fx_rates = {}
            # item_instrument_pricings = {}
            # item_instrument_accruals = {}
            #
            # for item in self.items:
            #     if item.instr:
            #         item_instruments[item.instr.id] = item.instr
            #     if item.ccy:
            #         item_currencies[item.ccy.id] = item.ccy
            #     if item.prtfl:
            #         item_portfolios[item.prtfl.id] = item.prtfl
            #     if item.acc:
            #         item_accounts[item.acc.id] = item.acc
            #     if item.str1:
            #         item_strategies1[item.str1.id] = item.str1
            #     if item.str2:
            #         item_strategies2[item.str2.id] = item.str2
            #     if item.str3:
            #         item_strategies3[item.str3.id] = item.str3
            #     if item.mismatch_prtfl:
            #         item_portfolios[item.mismatch_prtfl.id] = item.mismatch_prtfl
            #     if item.mismatch_acc:
            #         item_accounts[item.mismatch_acc.id] = item.mismatch_acc
            #     if item.alloc:
            #         item_instruments[item.alloc.id] = item.alloc
            #     if item.report_ccy_cur:
            #         item_currency_fx_rates[item.report_ccy_cur.id] = item.report_ccy_cur
            #     if item.instr_price_cur:
            #         item_instrument_pricings[item.instr_price_cur.id] = item.instr_price_cur
            #     if item.instr_pricing_ccy_cur:
            #         item_currency_fx_rates[item.instr_pricing_ccy_cur.id] = item.instr_pricing_ccy_cur
            #     if item.instr_accrued_ccy_cur:
            #         item_currency_fx_rates[item.instr_accrued_ccy_cur.id] = item.instr_accrued_ccy_cur
            #     if item.ccy_cur:
            #         item_currency_fx_rates[item.ccy_cur.id] = item.ccy_cur
            #     if item.pricing_ccy_cur:
            #         item_currency_fx_rates[item.pricing_ccy_cur.id] = item.pricing_ccy_cur
            #     if item.instr_accrual:
            #         item_instrument_accruals[item.instr_accrual.id] = item.instr_accrual
            #
            # self.item_instruments = list(item_instruments.values())
            # self.item_currencies = list(item_currencies.values())
            # self.item_portfolios = list(item_portfolios.values())
            # self.item_accounts = list(item_accounts.values())
            # self.item_strategies1 = list(item_strategies1.values())
            # self.item_strategies2 = list(item_strategies2.values())
            # self.item_strategies3 = list(item_strategies3.values())
            # self.item_currency_fx_rates = list(item_currency_fx_rates.values())
            # self.item_instrument_pricings = list(item_instrument_pricings.values())
            # self.item_instrument_accruals = list(item_instrument_accruals.values())

    @property
    def report_type_str(self):
        if self.report_type == Report.TYPE_BALANCE:
            return "BALANCE"
        elif self.report_type == Report.TYPE_PL:
            return "P&L"
        return "<UNKNOWN>"

    @property
    def approach_begin_multiplier(self):
        return self.approach_multiplier

    @property
    def approach_end_multiplier(self):
        return 1.0 - self.approach_multiplier


class ReportItem:
    TYPE_UNKNOWN = 0
    TYPE_INSTRUMENT = 1
    TYPE_CURRENCY = 2
    TYPE_TRANSACTION_PL = 3
    TYPE_FX_TRADE = 4
    TYPE_CASH_IN_OUT = 5
    TYPE_MISMATCH = 100  # Linked instrument
    TYPE_SUMMARY = 200
    TYPE_ALLOCATION = 400


class TransactionReport(BaseReport):
    def __init__(self,
                 id=None,
                 task_id=None,
                 task_status=None,
                 master_user=None,
                 member=None,
                 begin_date=None,
                 end_date=None,
                 portfolios=None,
                 accounts=None,
                 accounts_position=None,
                 accounts_cash=None,
                 strategies1=None,
                 strategies2=None,
                 strategies3=None,
                 custom_fields=None,
                 custom_fields_to_calculate=None,
                 complex_transaction_statuses_filter=None,
                 items=None,
                 date_field=None,
                 depth_level=None,
                 expression_iterations_count=1,
                 filters=None):
        super(TransactionReport, self).__init__(id=id, master_user=master_user, member=member,
                                                task_id=task_id, task_status=task_status)

        self.has_errors = False

        # self.id = id
        # self.task_id = task_id
        # self.task_status = task_status
        # self.master_user = master_user
        # self.member = member

        self.begin_date = begin_date
        self.end_date = end_date
        self.portfolios = portfolios or []
        self.accounts = accounts or []
        self.accounts_position = accounts_position or []
        self.accounts_cash = accounts_cash or []
        self.strategies1 = strategies1 or []
        self.strategies2 = strategies2 or []
        self.strategies3 = strategies3 or []
        self.custom_fields = custom_fields or []
        self.custom_fields_to_calculate = custom_fields_to_calculate or ''
        self.complex_transaction_statuses_filter = complex_transaction_statuses_filter or ''

        # self.context = {
        #     'master_user': self.master_user,
        #     'member': self.member,
        # }

        self.items = items

        self.item_transaction_classes = []
        self.item_complex_transactions = []
        self.item_transaction_types = []
        self.item_instruments = []
        self.item_currencies = []
        self.item_portfolios = []
        self.item_accounts = []
        self.item_strategies1 = []
        self.item_strategies2 = []
        self.item_strategies3 = []
        self.item_responsibles = []
        self.item_counterparties = []
        self.filters = filters

        if date_field:
            self.date_field = date_field
        else:
            self.date_field = 'date'

        print('====depth_level %s' % depth_level)
        print('====filters %s' % filters)

        if depth_level:
            self.depth_level = depth_level
        else:
            self.depth_level = 'base_transaction'

        self.expression_iterations_count = expression_iterations_count

    def __str__(self):
        return 'TransactionReport:%s' % self.id

    def close(self):
        for item in self.items:
            item.eval_custom_fields()


class PerformanceReport(BaseReport):
    report_type = 0  # VirtualTransaction
    report_date = date.min  # VirtualTransaction

    CALCULATION_TYPE_TIME_WEIGHTED = 'time_weighted'
    CALCULATION_TYPE_MONEY_WEIGHTED = 'money_weighted'
    CALCULATION_TYPE_CHOICES = (
        (CALCULATION_TYPE_TIME_WEIGHTED, 'Time Weighted'),
        (CALCULATION_TYPE_MONEY_WEIGHTED, 'Money Weighted'),
    )

    SEGMENTATION_TYPE_DAYS = 'days'
    SEGMENTATION_TYPE_MONTHS = 'months'
    SEGMENTATION_TYPE_CHOICES = (
        (SEGMENTATION_TYPE_DAYS, 'Days'),
        (SEGMENTATION_TYPE_MONTHS, 'Months'),
    )

    def __init__(self,
                 id=None,
                 task_id=None,
                 task_status=None,
                 name=None,
                 report_instance_name=None,
                 save_report=False,
                 calculation_type=None,
                 segmentation_type=None,
                 registers=None,
                 bundle=None,
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

        self.ecosystem_default = EcosystemDefault.objects.get(master_user=master_user)

        self.report_currency = report_currency or self.ecosystem_default.currency
        self.pricing_policy = pricing_policy
        self.calculation_type = calculation_type
        self.segmentation_type = segmentation_type
        self.registers = registers
        self.bundle = bundle
        self.periods = periods
        self.name = name
        self.report_instance_name = report_instance_name
        self.save_report = save_report
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
