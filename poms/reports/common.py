import logging
from datetime import date, timedelta

from poms.common.utils import date_now
from poms.instruments.models import CostMethod
from poms.users.models import EcosystemDefault

_l = logging.getLogger('poms.reports')


class BaseReport:
    # CONSOLIDATION = 1
    MODE_IGNORE = 0
    MODE_INDEPENDENT = 1
    MODE_INTERDEPENDENT = 2
    MODE_CHOICES = (
        (MODE_IGNORE, "Ignore"),
        (MODE_INDEPENDENT, "Independent"),
        (MODE_INTERDEPENDENT, "Offsetting (Interdependent - 0/100, 100/0, 50/50)"),
    )

    CALCULATION_GROUP_NO_GROUPING = 'no_grouping'
    CALCULATION_GROUP_PORTFOLIO = 'portfolio.id'
    CALCULATION_GROUP_ACCOUNT = 'account.id'
    CALCULATION_GROUP_STRATEGY1 = 'strategy1'
    CALCULATION_GROUP_STRATEGY2 = 'strategy2'
    CALCULATION_GROUP_STRATEGY3 = 'strategy3'
    CALCULATION_GROUP_CHOICES = (
        (CALCULATION_GROUP_NO_GROUPING, "No Grouping"),
        (CALCULATION_GROUP_PORTFOLIO, "Portfolio"),
        (CALCULATION_GROUP_ACCOUNT, "Account"),
        (CALCULATION_GROUP_STRATEGY1, "Strategy 1"),
        (CALCULATION_GROUP_STRATEGY2, "Strategy 2"),
        (CALCULATION_GROUP_STRATEGY3, "Strategy 3"),
    )

    def __init__(
            self, id=None, master_user=None, member=None, task_id=None, task_status=None
    ):
        self.id = id
        self.task_id = task_id
        self.task_status = task_status
        self.master_user = master_user
        self.member = member

        self.context = {
            "master_user": self.master_user,
            "member": self.member,
        }


class Report(BaseReport):
    TYPE_BALANCE = 1
    TYPE_PL = 2
    TYPE_CHOICES = (
        (TYPE_BALANCE, "Balance"),
        (TYPE_PL, "P&L"),
    )

    PERIOD_TYPE_DAILY = "daily"
    PERIOD_TYPE_MTD = "mtd"
    PERIOD_TYPE_QTD = "qtd"
    PERIOD_TYPE_YTD = "ytd"
    PERIOD_TYPE_INCEPTION = "inception"
    PERIOD_TYPE_CHOICES = (
        (PERIOD_TYPE_DAILY, "Daily"),
        (PERIOD_TYPE_MTD, "MTD"),
        (PERIOD_TYPE_QTD, "QTD"),
        (PERIOD_TYPE_YTD, "YTD"),
        (PERIOD_TYPE_INCEPTION, "Inception"),
    )

    def __init__(
            self,
            id=None,
            master_user=None,
            member=None,
            task_id=None,
            task_status=None,
            report_instance_name=None,
            save_report=False,
            ignore_cache=False,
            pl_first_date=None,
            report_type=TYPE_BALANCE,
            report_date=None,
            report_currency=None,
            pricing_policy=None,
            cost_method=None,
            calculation_group=BaseReport.CALCULATION_GROUP_NO_GROUPING,
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
            calculate_pl=False,
            only_numbers=False,
            items=None,
            execution_time=None,
            serialization_time=None,
            frontend_request_options=None,
            report_instance_id=None,

            page=1,
            page_size=40,
            count=0,

            period_type=None,

    ):
        super(Report, self).__init__(
            id=id,
            master_user=master_user,
            member=member,
            task_id=task_id,
            task_status=task_status,
        )

        self.ecosystem_default = EcosystemDefault.cache.get_cache(
            master_user_pk=master_user.pk
        )

        self.report_type = (
            report_type if report_type is not None else Report.TYPE_BALANCE
        )
        self.report_currency = report_currency or self.ecosystem_default.currency
        self.pricing_policy = pricing_policy or self.ecosystem_default.pricing_policy
        self.pl_first_date = pl_first_date
        self.report_date = report_date or (date_now() - timedelta(days=1))
        self.cost_method = cost_method or CostMethod.objects.get(pk=CostMethod.AVCO)
        self.calculation_group = calculation_group

        self.report_instance_name = report_instance_name
        self.save_report = save_report
        self.ignore_cache = ignore_cache
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
        self.only_numbers = (
            only_numbers  # do not add relations items when process report
        )

        self.instruments = instruments or []
        self.portfolios = portfolios or []
        self.accounts = accounts or []
        self.accounts_position = accounts_position or []
        self.accounts_cash = accounts_cash or []
        self.strategies1 = strategies1 or []
        self.strategies2 = strategies2 or []
        self.strategies3 = strategies3 or []

        self.transaction_classes = transaction_classes or []

        if date_field:
            self.date_field = date_field
        elif (
                self.report_type == Report.TYPE_BALANCE
                or self.report_type != Report.TYPE_PL
        ):
            self.date_field = "transaction_date"
        else:
            self.date_field = "accounting_date"

        self.custom_fields = custom_fields or []
        self.custom_fields_to_calculate = custom_fields_to_calculate or ""

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

        self.frontend_request_options = frontend_request_options  # For Backend Report Calculation
        self.report_instance_id = report_instance_id  # For Backend Report Calculation

        self.page = page
        self.page_size = page_size
        self.count = count

        self.period_type = period_type

    def __str__(self):
        return (
            f"{self.__class__.__name__} for {self.master_user}/{self.member}"
            f" @ {self.report_date}"
        )

    def close(self):
        for item in self.items:
            item.eval_custom_fields()

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
    def __init__(
            self,
            id=None,
            task_id=None,
            task_status=None,
            master_user=None,
            member=None,
            begin_date=None,
            end_date=None,
            period_type=None,
            portfolios=None,
            bundle=None,
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
            filters=None,
            report_instance_name=None,
            frontend_request_options=None,
            report_instance_id=None,

            page=1,
            page_size=40,
            count=0
    ):
        super().__init__(
            id=id,
            master_user=master_user,
            member=member,
            task_id=task_id,
            task_status=task_status,
        )

        self.has_errors = False
        self.begin_date = begin_date
        self.end_date = end_date
        self.period_type = period_type
        self.portfolios = portfolios or []
        self.bundle = bundle or None
        self.accounts = accounts or []
        self.accounts_position = accounts_position or []
        self.accounts_cash = accounts_cash or []
        self.strategies1 = strategies1 or []
        self.strategies2 = strategies2 or []
        self.strategies3 = strategies3 or []
        self.custom_fields = custom_fields or []
        self.custom_fields_to_calculate = custom_fields_to_calculate or ""
        self.complex_transaction_statuses_filter = (
                complex_transaction_statuses_filter or ""
        )

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

        self.date_field = date_field or "date"

        _l.debug(f"====depth_level {depth_level}")
        _l.debug(f"====filters {filters}")

        self.depth_level = depth_level or "base_transaction"

        self.expression_iterations_count = expression_iterations_count
        self.report_instance_name = report_instance_name
        self.frontend_request_options = frontend_request_options
        self.report_instance_id = report_instance_id

        _l.debug('TransactionReport.page %s' % page)

        self.page = page
        self.page_size = page_size
        self.count = count

    def __str__(self):
        return f"TransactionReport:{self.id}"

    def close(self):
        for item in self.items:
            item.eval_custom_fields()


class PerformanceReport(BaseReport):
    report_type = 0  # VirtualTransaction
    report_date = date.min  # VirtualTransaction

    PERIOD_TYPE_DAILY = "daily"
    PERIOD_TYPE_MTD = "mtd"
    PERIOD_TYPE_QTD = "qtd"
    PERIOD_TYPE_YTD = "ytd"
    PERIOD_TYPE_INCEPTION = "inception"
    PERIOD_TYPE_CHOICES = (
        (PERIOD_TYPE_DAILY, "Daily"),
        (PERIOD_TYPE_MTD, "MTD"),
        (PERIOD_TYPE_QTD, "QTD"),
        (PERIOD_TYPE_YTD, "YTD"),
        (PERIOD_TYPE_INCEPTION, "Inception"),
    )

    CALCULATION_TYPE_TIME_WEIGHTED = "time_weighted"
    CALCULATION_TYPE_MODIFIED_DIETZ = "modified_dietz"
    CALCULATION_TYPE_CHOICES = (
        (CALCULATION_TYPE_TIME_WEIGHTED, "Time Weighted"),
        (CALCULATION_TYPE_MODIFIED_DIETZ, "Modified Dietz"),
    )

    SEGMENTATION_TYPE_DAYS = "days"
    SEGMENTATION_TYPE_MONTHS = "months"
    SEGMENTATION_TYPE_CHOICES = (
        (SEGMENTATION_TYPE_DAYS, "Days"),
        (SEGMENTATION_TYPE_MONTHS, "Months"),
    )

    ADJUSTMENT_TYPE_ORIGINAL = "original"
    ADJUSTMENT_TYPE_ANNUALIZED = "annualized"
    ADJUSTMENT_TYPE_CHOICES = (
        (ADJUSTMENT_TYPE_ORIGINAL, "Original"),
        (ADJUSTMENT_TYPE_ANNUALIZED, "Annualized")
    )

    def __init__(
            self,
            id=None,
            task_id=None,
            task_status=None,
            name=None,
            report_instance_name=None,
            save_report=False,
            calculation_type=None,
            segmentation_type=None,
            adjustment_type=None,
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
            items=None,
            period_type=PERIOD_TYPE_YTD
    ):
        super().__init__(
            id=id,
            master_user=master_user,
            member=member,
            task_id=task_id,
            task_status=task_status,
        )

        self.has_errors = False

        d = date_now() - timedelta(days=1)
        self.begin_date = begin_date
        self.end_date = end_date or d

        self.ecosystem_default = EcosystemDefault.cache.get_cache(
            master_user_pk=master_user.pk
        )

        self.report_currency = report_currency or self.ecosystem_default.currency
        self.pricing_policy = pricing_policy
        self.calculation_type = calculation_type
        self.segmentation_type = segmentation_type
        self.adjustment_type = adjustment_type
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

        self.period_type = period_type

        if not self.begin_date and not self.period_type:
            self.period_type = 'ytd'

    def __str__(self):
        return f"PerformanceReport:{self.id}"

    def close(self):
        for item in self.items:
            item.eval_custom_fields()
