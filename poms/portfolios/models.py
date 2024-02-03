import traceback
from datetime import date
from logging import getLogger

from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.utils.translation import gettext_lazy

from poms.common.models import DataTimeStampedModel, FakeDeletableModel, NamedModel, AbstractClassModel
from poms.common.utils import date_now, str_to_date
from poms.configuration.models import ConfigurationModel
from poms.currencies.models import Currency
from poms.instruments.models import Instrument, PricingPolicy, CostMethod
from poms.obj_attrs.models import GenericAttribute
from poms.users.models import MasterUser
from poms_app import settings

_l = getLogger("poms.portfolios")


class PortfolioClass(AbstractClassModel):
    GENERAL = 1
    POSITION = 2
    MANUAL = 3

    CLASSES = (
        (
            GENERAL,
            "general",
            gettext_lazy("General Portfolio"),
        ),
        (
            POSITION,
            "position",
            gettext_lazy("Position Only Portfolio"),
        ),
        (
            MANUAL,
            "manual",
            gettext_lazy("Manual Managed Portfolio"),
        ),

    )

    class Meta(AbstractClassModel.Meta):
        verbose_name = gettext_lazy("portfolio class")
        verbose_name_plural = gettext_lazy("portfolio classes")


class PortfolioType(
    NamedModel, FakeDeletableModel, DataTimeStampedModel, ConfigurationModel
):
    """
    Meta Entity, part of Finmars Configuration
    Mostly used for extra fragmentation of Reports
    Maybe in future would have extra logic
    """

    master_user = models.ForeignKey(
        MasterUser,
        related_name="portfolio_types",
        verbose_name=gettext_lazy("master user"),
        on_delete=models.CASCADE,
    )

    attributes = GenericRelation(
        GenericAttribute,
        verbose_name=gettext_lazy("attributes"),
    )

    portfolio_class = models.ForeignKey(
        PortfolioClass,
        related_name="portfolio_types",
        on_delete=models.PROTECT,
        verbose_name=gettext_lazy("portfolio class"),
    )

    class Meta(NamedModel.Meta, FakeDeletableModel.Meta):
        verbose_name = gettext_lazy("portfolio type")
        verbose_name_plural = gettext_lazy("portfolio types")
        permissions = [
            ("manage_portfoliotype", "Can manage portfolio type"),
        ]

    @staticmethod
    def get_system_attrs():
        """
        Returns attributes that front end uses
        """
        return [
            {
                "key": "name",
                "name": "Name",
                "value_type": 10,
                "allow_null": True,
            },
            {
                "key": "short_name",
                "name": "Short name",
                "value_type": 10,
                "allow_null": True,
            },
            {
                "key": "user_code",
                "name": "User code",
                "value_type": 10,
            },
            {
                "key": "configuration_code",
                "name": "Configuration code",
                "value_type": 10,
            },
            {
                "key": "public_name",
                "name": "Public name",
                "value_type": 10,
                "allow_null": True,
            },
            {
                "key": "notes",
                "name": "Notes",
                "value_type": 10,
                "allow_null": True,
            }
        ]


# noinspection PyUnresolvedReferences
class Portfolio(NamedModel, FakeDeletableModel, DataTimeStampedModel):
    """
    Portfolio Entity - Way of grouping transactions in user-defined way.
    """

    master_user = models.ForeignKey(
        MasterUser,
        related_name="portfolios",
        verbose_name=gettext_lazy("master user"),
        on_delete=models.CASCADE,
    )
    accounts = models.ManyToManyField(
        "accounts.Account",
        related_name="portfolios",
        blank=True,
        verbose_name=gettext_lazy("accounts"),
    )
    responsibles = models.ManyToManyField(
        "counterparties.Responsible",
        related_name="portfolios",
        blank=True,
        verbose_name=gettext_lazy("responsibles"),
    )
    counterparties = models.ManyToManyField(
        "counterparties.Counterparty",
        related_name="portfolios",
        blank=True,
        verbose_name=gettext_lazy("counterparties"),
    )
    transaction_types = models.ManyToManyField(
        "transactions.TransactionType",
        related_name="portfolios",
        blank=True,
        verbose_name=gettext_lazy("transaction types"),
    )
    attributes = GenericRelation(
        GenericAttribute, verbose_name=gettext_lazy("attributes")
    )

    portfolio_type = models.ForeignKey(
        PortfolioType,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("portfolio type"),
    )

    first_transaction_date = models.DateField(
        null=True,
        verbose_name=gettext_lazy("first transaction date"),
    )

    first_cash_flow_date = models.DateField(
        null=True,
        verbose_name=gettext_lazy("first cash flow date"),
    )

    class Meta(NamedModel.Meta, FakeDeletableModel.Meta):
        verbose_name = gettext_lazy("portfolio")
        verbose_name_plural = gettext_lazy("portfolios")
        permissions = (("manage_portfolio", "Can manage portfolio"),)

    def fake_delete(self):
        super().fake_delete()

        # falsely delete corresponding PortfolioRegister objects
        for register in self.registers.all():
            register.fake_delete()

    @staticmethod
    def get_system_attrs():
        """
        Returns attributes that front end uses
        """
        return [
            {
                "key": "name",
                "name": "Name",
                "value_type": 10,
            },
            {
                "key": "short_name",
                "name": "Short name",
                "value_type": 10,
            },
            {
                "key": "user_code",
                "name": "User code",
                "value_type": 10,
            },
            {
                "key": "public_name",
                "name": "Public name",
                "value_type": 10,
                "allow_null": True,
            },
            {
                "key": "notes",
                "name": "Notes",
                "value_type": 10,
            },
            {
                "key": "accounts",
                "name": "Accounts",
                "value_content_type": "accounts.account",
                "value_entity": "account",
                "code": "user_code",
                "value_type": "mc_field",
            },
            {
                "key": "responsibles",
                "name": "Responsibles",
                "value_content_type": "counterparties.responsible",
                "value_entity": "responsible",
                "code": "user_code",
                "value_type": "mc_field",
            },
            {
                "key": "counterparties",
                "name": "Counterparties",
                "value_content_type": "counterparties.counterparty",
                "value_entity": "counterparty",
                "code": "user_code",
                "value_type": "mc_field",
            },
            {
                "key": "transaction_types",
                "name": "Transaction types",
                "value_content_type": "transactions.transactiontype",
                "value_entity": "transaction-type",
                "code": "user_code",
                "value_type": "mc_field",
            },
        ]

    @property
    def is_default(self):
        return (
            self.master_user.portfolio_id == self.id if self.master_user_id else False
        )

    def save(self, *args, **kwargs):

        _l.info("Here???")
        self.calculate_first_transactions_dates()

        super().save(*args, **kwargs)

    def calculate_first_transactions_dates(self):

        try:

            from poms.transactions.models import Transaction, TransactionClass

            first_transaction = Transaction.objects.filter(portfolio=self).order_by("accounting_date").first()

            if first_transaction:
                self.first_transaction_date = first_transaction.accounting_date

            first_cash_flow_transaction = Transaction.objects.filter(portfolio=self, transaction_class_id__in=[
                TransactionClass.CASH_INFLOW, TransactionClass.CASH_OUTFLOW]).order_by("accounting_date").first()

            if first_cash_flow_transaction:
                self.first_cash_flow_date = first_cash_flow_transaction.accounting_date

            _l.info("calculate_first_transactions_dates success")

        except Exception as e:
            _l.error("calculate_first_transactions_dates.error %s" % e)
            _l.error("calculate_first_transactions_dates.traceback %s" % traceback.print_exc())

    def get_first_transaction_date(self, date_field: str = 'accounting_date') -> date:
        """
        Try to return the 1st transaction date for the portfolio
        """
        param = f"transaction__{date_field}"
        return self.portfolioregisterrecord_set.aggregate(models.Min(param))[
            f"{param}__min"
        ]


class PortfolioRegister(NamedModel, FakeDeletableModel, DataTimeStampedModel):
    """
    Portfolio Register

    Entity that creates a link between portfolio and instrument - That allows us
    to treat portfolio as an instrument
    It means it appears as a position in reports, and also we could calculate
    the performance of that instrument
    """

    master_user = models.ForeignKey(
        MasterUser,
        related_name="portfolio_registers",
        verbose_name=gettext_lazy("master user"),
        on_delete=models.CASCADE,
    )
    portfolio = models.ForeignKey(
        Portfolio,
        related_name="registers",
        verbose_name=gettext_lazy("portfolio"),
        on_delete=models.CASCADE,
    )
    linked_instrument = models.ForeignKey(
        Instrument,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("linked instrument"),
        on_delete=models.SET_NULL,
    )
    valuation_pricing_policy = models.ForeignKey(
        PricingPolicy,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("pricing policy"),
    )
    valuation_currency = models.ForeignKey(
        "currencies.Currency",
        on_delete=models.PROTECT,
        verbose_name=gettext_lazy("valuation currency"),
    )
    attributes = GenericRelation(
        GenericAttribute,
        verbose_name=gettext_lazy("attributes"),
    )
    default_price = models.FloatField(
        default=1.0,
        verbose_name=gettext_lazy("default price"),
    )

    class Meta(NamedModel.Meta, FakeDeletableModel.Meta):
        verbose_name = gettext_lazy("portfolio register")
        verbose_name_plural = gettext_lazy("portfolio registers")

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if self.linked_instrument and not self.linked_instrument.has_linked_with_portfolio:
            self.linked_instrument.has_linked_with_portfolio = True
            self.linked_instrument.save()

        bundle, created = PortfolioBundle.objects.using(settings.DB_DEFAULT).get_or_create(
            master_user=self.master_user,
            user_code=self.user_code,
            defaults=dict(
                owner=self.owner,
                name=self.user_code,
            )
        )
        if created:
            _l.info(
                f"PortfolioRegister.save - self={self.id} bundle={bundle.id} created"
            )
            bundle.registers.set([self])
            bundle.save()

    def __str__(self):
        return (
            f"Portfolio Register {self.portfolio.user_code}. "
            f"Linked Instrument {self.linked_instrument}"
        )


class PortfolioRegisterRecord(DataTimeStampedModel):
    """
    Portfolio Register RECORD

    Basically it is a copy of transactions.BaseTransaction, but with few extra features
    For Calculate Performance Report we need only Cash In/Cash Out Transactions,
    so we filter them out and save as Register Record

    Its also contains NAV of the portfolio in previous date
    And we're also counting number of shares. In portfolio share it is position_size
    """

    AUTOMATIC = "Automatic"
    MANUAL = "Manual"

    master_user = models.ForeignKey(
        MasterUser,
        related_name="portfolio_register_records",
        verbose_name=gettext_lazy("master user"),
        on_delete=models.CASCADE,
    )
    portfolio = models.ForeignKey(
        Portfolio,
        verbose_name=gettext_lazy("portfolio"),
        on_delete=models.CASCADE,
    )
    instrument = models.ForeignKey(
        Instrument,
        verbose_name=gettext_lazy("instrument"),
        on_delete=models.CASCADE,
    )
    transaction_class = models.ForeignKey(
        "transactions.TransactionClass",
        related_name="register_record_transaction_class",
        on_delete=models.CASCADE,
        verbose_name=gettext_lazy("transaction class"),
    )
    transaction_code = models.IntegerField(
        default=0,
        verbose_name=gettext_lazy("transaction code"),
    )
    transaction_date = models.DateField(
        default=date_now,
        db_index=True,
        verbose_name=gettext_lazy("transaction date"),
    )
    cash_amount = models.FloatField(
        default=0.0,
        verbose_name=gettext_lazy("cash amount"),
        help_text=gettext_lazy("Cash amount"),
    )
    cash_currency = models.ForeignKey(
        Currency,
        related_name="register_record_cash_currency",
        on_delete=models.PROTECT,
        verbose_name=gettext_lazy("cash currency"),
    )
    fx_rate = models.FloatField(
        default=0.0,
        verbose_name=gettext_lazy("fx rate"),
    )
    cash_amount_valuation_currency = models.FloatField(
        default=0.0,
        verbose_name=gettext_lazy("cash amount valuation currency"),
        help_text=gettext_lazy("Cash amount valuation currency"),
    )
    valuation_currency = models.ForeignKey(
        Currency,
        related_name="register_record_valuation_currency",
        on_delete=models.PROTECT,
        verbose_name=gettext_lazy("valuation currency"),
    )
    nav_valuation_currency = models.FloatField(
        default=0.0,
        verbose_name=gettext_lazy("nav valuation currency"),
    )
    # Should be rename to previous record date
    nav_previous_register_record_day_valuation_currency = models.FloatField(
        default=0.0,
        verbose_name=gettext_lazy("nav previous register record day valuation currency"),
    )
    nav_previous_business_day_valuation_currency = models.FloatField(
        default=0.0,
        verbose_name=gettext_lazy("nav previous business day valuation currency"),
    )
    n_shares_previous_day = models.FloatField(
        default=0.0,
        verbose_name=gettext_lazy("n shares previous day"),
    )
    n_shares_added = models.FloatField(
        default=0.0,
        verbose_name=gettext_lazy("n shares added"),
    )
    dealing_price_valuation_currency = models.FloatField(
        default=0.0,
        verbose_name=gettext_lazy("dealing price valuation currency"),
        help_text=gettext_lazy("Dealing price valuation currency"),
    )
    rolling_shares_of_the_day = models.FloatField(
        default=0.0,
        verbose_name=gettext_lazy("rolling shares  of the day"),
    )
    previous_date_record = models.ForeignKey(
        "portfolios.PortfolioRegisterRecord",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name=gettext_lazy("previous date record"),
    )
    transaction = models.ForeignKey(
        "transactions.Transaction",
        on_delete=models.CASCADE,
        related_name="register_record_transaction",
        verbose_name=gettext_lazy("transaction"),
    )
    complex_transaction = models.ForeignKey(
        "transactions.ComplexTransaction",
        related_name="register_record_complex_transaction",
        on_delete=models.CASCADE,
        verbose_name=gettext_lazy("complex transaction"),
    )
    portfolio_register = models.ForeignKey(
        PortfolioRegister,
        on_delete=models.CASCADE,
        verbose_name=gettext_lazy("portfolio register"),
    )
    share_price_calculation_type = models.CharField(
        max_length=255,
        default=AUTOMATIC,
        blank=False,
        verbose_name=gettext_lazy("price calculation type"),
    )

    class Meta:
        verbose_name = gettext_lazy("portfolio register record")
        verbose_name_plural = gettext_lazy("portfolio registers record")

    # def save(self, *args, **kwargs):
    #     if self.pk:  # check if instance already exists in database
    #         original_instance = PortfolioRegisterRecord.objects.get(pk=self.pk)
    #         if (
    #             self.dealing_price_valuation_currency
    #             != original_instance.dealing_price_valuation_currency
    #         ):
    #             # dealing_price_valuation_currency field value has changed,
    #             # update share_price_calculation_type to manual type
    #             self.share_price_calculation_type = PortfolioRegisterRecord.MANUAL
    #
    #     super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.portfolio_register} {self.transaction_date} "
            f"{self.transaction_class} {self.cash_amount}"
        )


class PortfolioBundle(NamedModel, DataTimeStampedModel):
    master_user = models.ForeignKey(
        MasterUser,
        related_name="portfolio_bundles",
        verbose_name=gettext_lazy("master user"),
        on_delete=models.CASCADE,
    )
    registers = models.ManyToManyField(
        PortfolioRegister,
        verbose_name=gettext_lazy("registers"),
        blank=True,
        related_name="portfolio_bundles",
        related_query_name="bundle",
    )

    class Meta(NamedModel.Meta, FakeDeletableModel.Meta):
        verbose_name = gettext_lazy("portfolio bundle")
        verbose_name_plural = gettext_lazy("portfolio bundles")
        index_together = [["master_user", "user_code"]]


class PortfolioHistory(NamedModel, DataTimeStampedModel):
    PERIOD_DAILY = 'daily'
    PERIOD_YTD = 'ytd'
    PERIOD_MTD = 'mtd'
    PERIOD_QTD = 'qtd'
    PERIOD_INCEPTION = 'inception'

    PERIOD_CHOICES = (
        (PERIOD_DAILY, "daily"),
        (PERIOD_YTD, "YTD"),
        (PERIOD_MTD, "MTD"),
        (PERIOD_QTD, "QTD"),
        (PERIOD_INCEPTION, "Inception"),
    )

    PERFORMANCE_METHOD_MODIFIED_DIETZ = 'modified_dietz'
    PERFORMANCE_METHOD_TIME_WEIGHTED = 'time_weighted'

    PERFORMANCE_METHOD_CHOICES = (
        (PERFORMANCE_METHOD_MODIFIED_DIETZ, "Modified Dietz"),
        (PERFORMANCE_METHOD_TIME_WEIGHTED, "Time Weighted"),
    )

    STATUS_OK = 'ok'
    STATUS_ERROR = 'error'

    STATUS_CHOICES = (
        (STATUS_OK, "Ok"),
        (STATUS_ERROR, "error"),
    )

    master_user = models.ForeignKey(MasterUser,
                                    verbose_name=gettext_lazy('master user'), on_delete=models.CASCADE)

    user_code = models.CharField(
        max_length=1024,
        unique=True,
        verbose_name=gettext_lazy("user code"),
        help_text=gettext_lazy(
            "Unique Code for this object. Used in Configuration and Permissions Logic"
        ),
    )

    date = models.DateField(db_index=True, default=date_now, verbose_name=gettext_lazy('date'))
    date_from = models.DateField(db_index=True, default=date_now, verbose_name=gettext_lazy('date from'))

    period_type = models.CharField(
        max_length=255,
        default=PERIOD_YTD,
        choices=PERIOD_CHOICES,
        verbose_name="period_type",
    )

    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE,
                                  verbose_name=gettext_lazy('portfolio'))

    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, verbose_name=gettext_lazy('currency'))
    pricing_policy = models.ForeignKey(PricingPolicy, on_delete=models.CASCADE,
                                       verbose_name=gettext_lazy('pricing policy'))

    cost_method = models.ForeignKey(CostMethod, on_delete=models.CASCADE, verbose_name=gettext_lazy('cost method'),
                                    help_text="AVCO / FIFO")
    performance_method = models.CharField(
        max_length=255,
        default=PERFORMANCE_METHOD_MODIFIED_DIETZ,
        choices=PERFORMANCE_METHOD_CHOICES,
        verbose_name="performance method",
    )

    benchmark = models.CharField(max_length=255, blank=True, default='', verbose_name=gettext_lazy('benchmark'))

    nav = models.FloatField(default=0.0, null=True, blank=True, verbose_name=gettext_lazy('nav'),
                            help_text="Net Asset Value")
    cash_flow = models.FloatField(default=0.0, null=True, blank=True, verbose_name=gettext_lazy('cash flow'))
    cash_inflow = models.FloatField(default=0.0, null=True, blank=True, verbose_name=gettext_lazy('cash inflow'))
    cash_outflow = models.FloatField(default=0.0, null=True, blank=True, verbose_name=gettext_lazy('cash outflow'))

    total = models.FloatField(default=0.0, null=True, blank=True, verbose_name=gettext_lazy('total'),
                              help_text="Total Value of the Portfolio from P&L Report")

    cumulative_return = models.FloatField(default=0.0, null=True, blank=True,
                                          verbose_name=gettext_lazy('cumulative return'))
    annualized_return = models.FloatField(default=0.0, null=True, blank=True,
                                          verbose_name=gettext_lazy('annualized return'))
    portfolio_volatility = models.FloatField(default=0.0, null=True, blank=True,
                                             verbose_name=gettext_lazy('portfolio volatility'))
    annualized_portfolio_volatility = models.FloatField(default=0.0, null=True, blank=True,
                                                        verbose_name=gettext_lazy('annualized portfolio volatility'))
    sharpe_ratio = models.FloatField(default=0.0, null=True, blank=True, verbose_name=gettext_lazy('sharpe_ratio'))
    max_annualized_drawdown = models.FloatField(default=0.0, null=True, blank=True,
                                                verbose_name=gettext_lazy('max_annualized_drawdown'))
    betta = models.FloatField(default=0.0, null=True, blank=True, verbose_name=gettext_lazy('betta'))
    alpha = models.FloatField(default=0.0, null=True, blank=True, verbose_name=gettext_lazy('alpha'))
    correlation = models.FloatField(default=0.0, null=True, blank=True, verbose_name=gettext_lazy('correlation'))
    weighted_duration = models.FloatField(default=0.0, null=True, blank=True,
                                          verbose_name=gettext_lazy('weighted_duration'))

    error_message = models.TextField(
        null=True,
        blank=True,
        verbose_name=gettext_lazy("error_message"),
        help_text="Error message if any",
    )

    status = models.CharField(
        max_length=255,
        default=STATUS_OK,
        choices=STATUS_CHOICES,
        verbose_name="status",
    )

    class Meta:
        unique_together = [
            ['master_user', 'user_code'],
        ]

    def get_balance_report(self):

        from poms.reports.common import Report
        from poms.reports.sql_builders.balance import BalanceReportBuilderSql

        instance = Report(
            master_user=self.master_user,
            member=self.owner,
            report_currency=self.currency,
            report_date=self.date,
            cost_method=self.cost_method,
            portfolios=[self.portfolio],
            pricing_policy=self.pricing_policy,
            portfolio_mode=1,
            account_mode=1,
            strategy1_mode=0,
            strategy2_mode=0,
            strategy3_mode=0
        )

        builder = BalanceReportBuilderSql(instance=instance)
        instance = builder.build_balance_sync()

        return instance

    def get_pl_report(self):

        from poms.reports.common import Report
        from poms.reports.sql_builders.pl import PLReportBuilderSql

        instance = Report(
            master_user=self.master_user,
            member=self.owner,
            report_currency=self.currency,
            pl_first_date=self.date_from,
            report_date=self.date,
            cost_method=self.cost_method,
            portfolios=[self.portfolio],
            pricing_policy=self.pricing_policy,
            portfolio_mode=1,
            account_mode=1,
            strategy1_mode=0,
            strategy2_mode=0,
            strategy3_mode=0
        )

        builder = PLReportBuilderSql(instance=instance)
        instance = builder.build_pl_sync()

        return instance

    def get_performance_report(self):

        from poms.reports.common import PerformanceReport

        portfolio_register = PortfolioRegister.objects.get(portfolio=self.portfolio)

        instance = PerformanceReport(
            master_user=self.master_user,
            member=self.owner,
            report_currency=self.currency,
            begin_date=str_to_date(self.date_from),
            end_date=str_to_date(self.date),
            calculation_type=self.performance_method,
            segmentation_type='months',
            registers=[portfolio_register]
        )

        from poms.reports.performance_report import PerformanceReportBuilder
        builder = PerformanceReportBuilder(instance=instance)
        instance = builder.build_report()

        return instance

    def get_annualized_return(self):

        _delta = self.date - str_to_date(self.portfolio.get_first_transaction_date('accounting_date'))
        days_from_first_transaction = _delta.days

        if days_from_first_transaction == 0:
            return 0

        _l.info('get_annualized_return.years_from_first_transaction %s' % days_from_first_transaction)

        annualized_return = round((1 + self.cumulative_return) ** (365 / days_from_first_transaction) - 1,
                                  settings.ROUND_NDIGITS)

        return annualized_return

    def calculate(self):

        self.error_message = ''

        self.balance_report = self.get_balance_report()
        self.pl_report = self.get_pl_report()

        # _l.info('balance_report.items %s' % len(balance_report.items))
        # if len(balance_report.items):
        #     _l.info('balance_report.items %s' % balance_report.items[0])

        has_nav_error = False
        has_total_error = False

        nav = 0
        for item in self.balance_report.items:
            if item["market_value"] is not None and round(item["position_size"], settings.ROUND_NDIGITS):
                nav = nav + item["market_value"]
            else:
                self.error_message = self.error_message + f'{item["name"]} has no market_value\n'
                has_nav_error = True

        if has_nav_error:
            _l.info("PortfolioHistory.calculate has_nav_error")
            self.error_message = self.error_message + 'NAV is wrong, some positions has no market value\n'

        total = 0
        for item in self.pl_report.items:

            # Check position_size aswell?
            if item["total"] is not None:
                total = total + item["total"]
            else:
                self.error_message = self.error_message + f'{item["name"]} has no total value\n'
                _l.info("PortfolioHistory.calculate has_total_error")
                has_total_error = True

        if has_total_error:
            self.error_message = self.error_message + 'Total is wrong, some positions has no total value\n'

        self.nav = nav
        self.total = total

        # Performance Part

        try:
            self.performance_report = self.get_performance_report()

            self.cumulative_return = round(self.performance_report.grand_return, settings.ROUND_NDIGITS)
            self.cash_flow = self.performance_report.grand_cash_flow
            self.cash_inflow = self.performance_report.grand_cash_inflow
            self.cash_outflow = self.performance_report.grand_cash_outflow
            self.annualized_return = self.get_annualized_return()

            # TODO implement portoflio_volatility
            # TODO implement annualized_portoflio_volatility
            # TODO implement max_annualized_drawdown
            # TODO implement betta
            # TODO implement alpha
            # TODO implement correltaion

        except Exception as e:
            self.error_message = self.error_message + str(e) + '\n'

        _l.info('error_message %s' % self.error_message)

        if self.error_message:
            self.status = self.STATUS_ERROR
        else:
            self.status = self.STATUS_OK

        self.save()


class PortfolioReconcileGroup(NamedModel, FakeDeletableModel, DataTimeStampedModel):

    master_user = models.ForeignKey(
        MasterUser,
        related_name="portfolio_reconcile_groups",
        verbose_name=gettext_lazy("master user"),
        on_delete=models.CASCADE,
    )
    
    portfolios = models.ManyToManyField(
        Portfolio,
        verbose_name=gettext_lazy("portfolios"),
        blank=True,
        related_name="portfolio_reconcile_groups",
    )

    class Meta(NamedModel.Meta, FakeDeletableModel.Meta):
        verbose_name = gettext_lazy("portfolio reconcile group")
        verbose_name_plural = gettext_lazy("portfolio reconcile groups")
        index_together = [["master_user", "user_code"]]
