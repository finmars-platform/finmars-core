import json
from datetime import date
from logging import getLogger

from django.contrib.contenttypes.fields import GenericRelation
from django.core.cache import cache
from django.db import models
from django.utils.timezone import now
from django.utils.translation import gettext_lazy

from poms.clients.models import Client
from poms.common.fields import ResourceGroupsField
from poms.common.models import (
    AbstractClassModel,
    ComputedModel,
    FakeDeletableModel,
    NamedModel,
    ObjectStateModel,
    TimeStampedModel,
)
from poms.common.utils import date_now, str_to_date
from poms.configuration.models import ConfigurationModel
from poms.currencies.models import Currency
from poms.file_reports.models import FileReport
from poms.iam.models import ResourceGroupAssignment
from poms.instruments.models import CostMethod, Instrument, PricingPolicy
from poms.obj_attrs.models import GenericAttribute
from poms.users.models import EcosystemDefault, MasterUser
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


class PortfolioType(NamedModel, FakeDeletableModel, TimeStampedModel, ConfigurationModel):
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
            },
        ]


# noinspection PyUnresolvedReferences
class Portfolio(NamedModel, FakeDeletableModel, TimeStampedModel, ObjectStateModel):
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
        GenericAttribute,
        verbose_name=gettext_lazy("attributes"),
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
    resource_groups = ResourceGroupsField()
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="portfolios",
        verbose_name=gettext_lazy("client"),
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
            {
                "key": "client",
                "name": "Сlient",
                "value_content_type": "clients.client",
                "value_entity": "client",
                "code": "user_code",
                "value_type": "mc_field",
            },
        ]

    @property
    def is_default(self):
        return self.master_user.portfolio_id == self.id if self.master_user_id else False

    def save(self, *args, **kwargs):
        self.calculate_first_transactions_dates()

        cache_key = f"{self.master_user.space_code}_serialized_report_portfolio_{self.id}"
        cache.delete(cache_key)

        super().save(*args, **kwargs)

    def calculate_first_transactions_dates(self):
        from poms.transactions.models import Transaction, TransactionClass

        first_transaction = (
            Transaction.objects.filter(portfolio=self, is_deleted=False)
            .order_by(
                "accounting_date",
            )
            .first()
        )
        self.first_transaction_date = first_transaction.accounting_date if first_transaction else None

        first_cash_flow_transaction = (
            Transaction.objects.filter(
                portfolio=self,
                is_deleted=False,
                transaction_class_id__in=[
                    TransactionClass.CASH_INFLOW,
                    TransactionClass.CASH_OUTFLOW,
                ],
            )
            .order_by("accounting_date")
            .first()
        )
        self.first_cash_flow_date = (
            first_cash_flow_transaction.accounting_date if first_cash_flow_transaction else None
        )

        _l.info(
            f"calculate_first_transactions_dates succeed: "
            f"first_transaction_date={self.first_transaction_date} "
            f"first_cash_flow_date={self.first_cash_flow_date}"
        )

    def get_first_portfolio_register_record_accounting_date(
        self,
        date_field: str = "accounting_date",
    ) -> date:
        """
        DEPRECATED: Try to return the 1st accounting date from PortfolioRegisterRecord
        """
        param = f"transaction__{date_field}"
        return self.portfolioregisterrecord_set.aggregate(models.Min(param))[f"{param}__min"]

    def destroy_reconcile_histories(self):
        """
        As portfolio's set of transactions has changed, so all reconcile history objects are not valid anymore,
        and has to be removed.
        """
        groups = PortfolioReconcileGroup.objects.filter(portfolios=self)
        histories = PortfolioReconcileHistory.objects.filter(portfolio_reconcile_group__in=groups).select_related(
            "file_report"
        )
        for history in histories:
            if history.file_report:
                history.file_report.delete()

            history.delete()

        _l.info(f"destroy_reconcile_histories of portfolio {self.user_code} succeed")


class PortfolioRegister(NamedModel, FakeDeletableModel, TimeStampedModel, ObjectStateModel):
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
            ),
        )
        if created:
            _l.info(f"PortfolioRegister.save - self={self.id} bundle={bundle.id} created")
            bundle.registers.set([self])
            bundle.save()

    def __str__(self):
        return f"Portfolio Register {self.portfolio.user_code}. " f"Linked Instrument {self.linked_instrument}"


class PortfolioRegisterRecord(TimeStampedModel, ComputedModel):
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
        return f"{self.portfolio_register} {self.transaction_date} " f"{self.transaction_class} {self.cash_amount}"


class PortfolioBundle(NamedModel, TimeStampedModel, ObjectStateModel):
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


class PortfolioHistory(NamedModel, TimeStampedModel, ComputedModel):
    PERIOD_DAILY = "daily"
    PERIOD_YTD = "ytd"
    PERIOD_MTD = "mtd"
    PERIOD_QTD = "qtd"
    PERIOD_INCEPTION = "inception"

    PERIOD_CHOICES = (
        (PERIOD_DAILY, "daily"),
        (PERIOD_YTD, "YTD"),
        (PERIOD_MTD, "MTD"),
        (PERIOD_QTD, "QTD"),
        (PERIOD_INCEPTION, "Inception"),
    )

    PERFORMANCE_METHOD_MODIFIED_DIETZ = "modified_dietz"
    PERFORMANCE_METHOD_TIME_WEIGHTED = "time_weighted"

    PERFORMANCE_METHOD_CHOICES = (
        (PERFORMANCE_METHOD_MODIFIED_DIETZ, "Modified Dietz"),
        (PERFORMANCE_METHOD_TIME_WEIGHTED, "Time Weighted"),
    )

    STATUS_OK = "ok"
    STATUS_ERROR = "error"

    STATUS_CHOICES = (
        (STATUS_OK, "Ok"),
        (STATUS_ERROR, "error"),
    )

    master_user = models.ForeignKey(
        MasterUser,
        verbose_name=gettext_lazy("master user"),
        on_delete=models.CASCADE,
    )
    user_code = models.CharField(
        max_length=1024,
        unique=True,
        verbose_name=gettext_lazy("user code"),
        help_text=gettext_lazy("Unique Code for this object. Used in Configuration and Permissions Logic"),
    )
    date = models.DateField(
        db_index=True,
        default=date_now,
        verbose_name=gettext_lazy("date"),
    )
    date_from = models.DateField(
        db_index=True,
        default=date_now,
        verbose_name=gettext_lazy("date from"),
    )
    period_type = models.CharField(
        max_length=255,
        default=PERIOD_YTD,
        choices=PERIOD_CHOICES,
        verbose_name="period_type",
    )
    portfolio = models.ForeignKey(
        Portfolio,
        on_delete=models.CASCADE,
        verbose_name=gettext_lazy("portfolio"),
    )
    currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        verbose_name=gettext_lazy("currency"),
    )
    pricing_policy = models.ForeignKey(
        PricingPolicy,
        on_delete=models.CASCADE,
        verbose_name=gettext_lazy("pricing policy"),
    )
    cost_method = models.ForeignKey(
        CostMethod,
        on_delete=models.CASCADE,
        verbose_name=gettext_lazy("cost method"),
        help_text="AVCO / FIFO",
    )
    performance_method = models.CharField(
        max_length=255,
        default=PERFORMANCE_METHOD_MODIFIED_DIETZ,
        choices=PERFORMANCE_METHOD_CHOICES,
        verbose_name="performance method",
    )
    benchmark = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name=gettext_lazy("benchmark"),
    )
    nav = models.FloatField(
        default=0.0,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("nav"),
        help_text="Net Asset Value",
    )
    gav = models.FloatField(
        default=0.0,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("gav"),
        help_text="Gross Asset Value",
    )
    cash_flow = models.FloatField(
        default=0.0,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("cash flow"),
    )
    cash_inflow = models.FloatField(
        default=0.0,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("cash inflow"),
    )
    cash_outflow = models.FloatField(
        default=0.0,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("cash outflow"),
    )
    total = models.FloatField(
        default=0.0,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("total"),
        help_text="Total Value of the Portfolio from P&L Report",
    )
    cumulative_return = models.FloatField(
        default=0.0,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("cumulative return"),
    )
    annualized_return = models.FloatField(
        default=0.0,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("annualized return"),
    )
    portfolio_volatility = models.FloatField(
        default=0.0,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("portfolio volatility"),
    )
    annualized_portfolio_volatility = models.FloatField(
        default=0.0,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("annualized portfolio volatility"),
    )
    sharpe_ratio = models.FloatField(
        default=0.0,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("sharpe_ratio"),
    )
    max_annualized_drawdown = models.FloatField(
        default=0.0,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("max_annualized_drawdown"),
    )
    betta = models.FloatField(
        default=0.0,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("betta"),
    )
    alpha = models.FloatField(
        default=0.0,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("alpha"),
    )
    correlation = models.FloatField(
        default=0.0,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("correlation"),
    )
    weighted_duration = models.FloatField(
        default=0.0,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("weighted_duration"),
    )
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
            ["master_user", "user_code"],
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
            strategy3_mode=0,
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
            strategy3_mode=0,
        )

        builder = PLReportBuilderSql(instance=instance)
        instance = builder.build_pl_sync()

        return instance

    def get_performance_report(self):
        from poms.reports.common import PerformanceReport

        try:
            portfolio_register = PortfolioRegister.objects.filter(portfolio=self.portfolio)[0]

            instance = PerformanceReport(
                master_user=self.master_user,
                member=self.owner,
                report_currency=self.currency,
                begin_date=str_to_date(self.date_from),
                end_date=str_to_date(self.date),
                calculation_type=self.performance_method,
                segmentation_type="months",
                registers=[portfolio_register],
            )

            from poms.reports.performance_report import PerformanceReportBuilder

            builder = PerformanceReportBuilder(instance=instance)
            instance = builder.build_report()
        except Exception as e:
            instance = None

        return instance

    def get_annualized_return(self):
        _delta = self.date - str_to_date(self.portfolio.first_transaction_date)
        days_from_first_transaction = _delta.days

        if days_from_first_transaction == 0:
            return 0

        _l.info(f"get_annualized_return.years_from_first_transaction {days_from_first_transaction}")

        annualized_return = round(
            (1 + self.cumulative_return) ** (365 / days_from_first_transaction) - 1,
            settings.ROUND_NDIGITS,
        )

        return annualized_return

    def calculate(self):
        self.error_message = ""

        self.balance_report = self.get_balance_report()
        self.pl_report = self.get_pl_report()

        # _l.info('balance_report.items %s' % len(balance_report.items))
        # if len(balance_report.items):
        #     _l.info('balance_report.items %s' % balance_report.items[0])

        has_nav_error = False
        has_total_error = False

        nav = 0
        gav = 0
        for item in self.balance_report.items:
            if item["market_value"] is not None and round(item["position_size"], settings.ROUND_NDIGITS):
                nav = nav + item["market_value"]

                if item["market_value"] > 0:
                    gav = gav + item["market_value"]
            else:
                self.error_message = f'{self.error_message} {item["name"]} has no market_value\n'
                has_nav_error = True

        if has_nav_error:
            _l.info("PortfolioHistory.calculate has_nav_error")
            self.error_message = self.error_message + " NAV is wrong, some positions has no market value\n"

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
            self.error_message = self.error_message + "Total is wrong, some positions has no total value\n"

        self.nav = nav
        self.gav = gav
        self.total = total

        # Performance Part
        performance_report = self.get_performance_report()
        if performance_report:
            try:
                self.performance_report = performance_report

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
                self.error_message = self.error_message + str(e) + "\n"
        else:
            self.error_message = f"{self.error_message}Calculate error. Portfolio has not Portfolio Register\n"

        _l.info(f"error_message {self.error_message}")

        self.status = self.STATUS_ERROR if self.error_message else self.STATUS_OK

        self.save()


class PortfolioReconcileGroup(NamedModel, FakeDeletableModel, TimeStampedModel):
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
    params = models.JSONField(
        default=dict,
        verbose_name=gettext_lazy("calculation & reporting parameters"),
    )
    last_calculated_at = models.DateTimeField(
        null=True,
        default=None,
        verbose_name=gettext_lazy("last time calculation was done"),
    )

    class Meta(NamedModel.Meta, FakeDeletableModel.Meta):
        verbose_name = gettext_lazy("portfolio reconcile group")
        verbose_name_plural = gettext_lazy("portfolio reconcile groups")
        index_together = [["master_user", "user_code"]]


class PortfolioReconcileHistory(NamedModel, TimeStampedModel, ComputedModel):
    STATUS_OK = "ok"
    STATUS_ERROR = "error"

    STATUS_CHOICES = (
        (STATUS_OK, "Ok"),
        (STATUS_ERROR, "error"),
    )

    master_user = models.ForeignKey(
        MasterUser,
        verbose_name=gettext_lazy("master user"),
        on_delete=models.CASCADE,
    )
    user_code = models.CharField(
        max_length=1024,
        unique=True,
        verbose_name=gettext_lazy("user code"),
        help_text=gettext_lazy("Unique Code for this object. Used in Configuration and Permissions Logic"),
    )
    date = models.DateField(
        db_index=True,
        default=date_now,
        verbose_name=gettext_lazy("date"),
    )
    portfolio_reconcile_group = models.ForeignKey(
        PortfolioReconcileGroup,
        on_delete=models.CASCADE,
        verbose_name=gettext_lazy("portfolio reconcile group"),
    )
    error_message = models.TextField(
        null=True,
        blank=True,
        verbose_name=gettext_lazy("error_message"),
        help_text="Error message if any",
    )
    verbose_result = models.TextField(
        null=True,
        blank=True,
        verbose_name=gettext_lazy("verbose result"),
    )
    status = models.CharField(
        max_length=255,
        default=STATUS_OK,
        choices=STATUS_CHOICES,
        verbose_name="status",
    )
    linked_task = models.ForeignKey(
        "celery_tasks.CeleryTask",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("linked task"),
    )
    file_report = models.ForeignKey(
        FileReport,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name=gettext_lazy("file report"),
    )
    report_ttl = models.PositiveIntegerField(
        default=90,
        verbose_name=gettext_lazy("number of days until report expires"),
    )

    class Meta:
        unique_together = [
            ["master_user", "user_code"],
        ]

    @staticmethod
    def compare_portfolios(reference_portfolio, portfolios, params: dict):
        report = []
        has_reconcile_error = False
        reference_items = reference_portfolio["items"]
        precision = params.get("precision", 1)
        only_errors = params.get("only_errors", False)
        round_digits = params.get("round_digits", 2)

        for portfolio_id, portfolio in portfolios.items():
            if portfolio_id == reference_portfolio["portfolio"]:
                continue

            for user_code, position_size in portfolio["items"].items():
                # Initialize with reference position size; default to 0 if not found
                reference_size = reference_items.get(user_code, 0)

                # Prepare report entry
                # "Position Portfolio": reference_size,
                # "General Portfolio": position_size,
                report_entry = {
                    "user_code": user_code,
                    "status": "ok",
                    "message": "ok",
                    "diff": 0,
                    reference_portfolio["portfolio_object"]["user_code"]: reference_size,
                    portfolio["portfolio_object"]["user_code"]: position_size,
                }
                # Check for discrepancies
                if position_size != reference_size:
                    discrepancy = round(abs(reference_size - position_size), round_digits)
                    equal_with_precision = discrepancy <= precision

                    if equal_with_precision:
                        message = (
                            f"{portfolio['portfolio_object']['user_code']} is "
                            f"{position_size} is equal to {reference_size} "
                            f"with precision {precision} ({discrepancy} units)"
                        )
                        report_entry["message"] = message
                        report_entry["diff"] = discrepancy
                    else:
                        message = (
                            f"{portfolio['portfolio_object']['user_code']} is "
                            f"{'missing' if position_size < reference_size else 'over by'} "
                            f"{discrepancy} units"
                        )
                        report_entry["status"] = "error"
                        report_entry["diff"] = discrepancy
                        report_entry["message"] = message
                        has_reconcile_error = True

                if not only_errors:
                    report.append(report_entry)

        return report, has_reconcile_error

    def calculate(self):
        from poms.reports.common import Report
        from poms.reports.sql_builders.balance import BalanceReportBuilderSql

        ecosystem_defaults = EcosystemDefault.objects.filter(master_user=self.master_user).first()

        report = Report(master_user=self.master_user)
        report.master_user = self.master_user
        report.member = self.owner
        report.report_date = self.date
        report.pricing_policy = ecosystem_defaults.pricing_policy
        report.portfolios = self.portfolio_reconcile_group.portfolios.all()
        report.report_currency = ecosystem_defaults.currency

        builder_instance = BalanceReportBuilderSql(instance=report)
        builder = builder_instance.build_balance_sync()

        _l.info(f"instance.items[0] {builder.items[0]}")

        portfolio_map = {}
        reconcile_result = {}
        position_portfolio_id = None

        for portfolio in self.portfolio_reconcile_group.portfolios.all():
            portfolio_map[portfolio.id] = portfolio

            if portfolio.portfolio_type.portfolio_class_id == PortfolioClass.POSITION:
                position_portfolio_id = portfolio.id

        if not position_portfolio_id:
            raise RuntimeError("Could not reconcile. Position Portfolio is not Set in Portfolio Reconcile Group")

        for item in builder.items:
            if "portfolio_id" not in item:
                _l.warning(f"missing portfolio_id item {item}")
                continue

            pid = item["portfolio_id"]
            if pid not in reconcile_result:
                portfolio = portfolio_map[pid]
                reconcile_result[pid] = {
                    "portfolio": pid,
                    "portfolio_object": {
                        "name": portfolio.name,
                        "user_code": portfolio.user_code,
                        "portfolio_type": portfolio.portfolio_type_id,
                        "portfolio_type_object": {
                            "name": portfolio.portfolio_type.name,
                            "user_code": portfolio.portfolio_type.user_code,
                            "portfolio_class": portfolio.portfolio_type.portfolio_class_id,
                            "portfolio_class_object": {
                                "id": portfolio.portfolio_type.portfolio_class.id,
                                "name": portfolio.portfolio_type.portfolio_class.name,
                                "user_code": portfolio.portfolio_type.portfolio_class.user_code,
                            },
                        },
                    },
                    "position_size": 0,
                    "items": {},
                }

            reconcile_result[pid]["items"][item["user_code"]] = item["position_size"]
            reconcile_result[pid]["position_size"] += item["position_size"]

        _l.info(f"reconcile_result {reconcile_result}")

        reference_portfolio = reconcile_result[position_portfolio_id]
        params = self.portfolio_reconcile_group.params
        report, has_reconcile_error = self.compare_portfolios(
            reference_portfolio,
            reconcile_result,
            params,
        )

        if has_reconcile_error:
            self.status = self.STATUS_ERROR
            self.error_message = "Reconciliation Error. Please check the report for details"

        self.file_report = self.generate_json_report(report)
        self.save()

        emails = params.get("emails")
        if emails:
            self.file_report.send_emails(emails)

        _l.info(f"report {report}")

    def generate_json_report(self, content) -> FileReport:
        current_date_time = now().strftime("%Y-%m-%d-%H-%M")
        file_name = f"reconciliation_report_{current_date_time}_task_{self.linked_task_id}.json"

        file_report = FileReport()
        file_report.upload_file(
            file_name=file_name,
            text=json.dumps(content, indent=4, default=str),
            master_user=self.master_user,
        )
        file_report.master_user = self.master_user
        file_report.name = f"Reconciliation {current_date_time} (Task {self.linked_task_id}).json"
        file_report.file_name = file_name
        file_report.type = "simple_import.import"
        file_report.notes = "System File"
        file_report.content_type = "application/json"

        file_report.save()

        _l.info(f"SimpleImportProcess.json_report {file_report} {file_report.file_url}")

        return file_report
