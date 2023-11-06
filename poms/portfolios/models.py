from datetime import date

from logging import getLogger

from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.utils.translation import gettext_lazy

from poms.common.models import DataTimeStampedModel, FakeDeletableModel, NamedModel
from poms.common.utils import date_now
from poms.common.wrapper_models import NamedModelAutoMapping
from poms.currencies.models import Currency
from poms.instruments.models import Instrument, PricingPolicy
from poms.obj_attrs.models import GenericAttribute
from poms.users.models import MasterUser

_l = getLogger("poms.portfolios")


# noinspection PyUnresolvedReferences
class Portfolio(NamedModelAutoMapping, FakeDeletableModel, DataTimeStampedModel):
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

    def first_transaction_date(self, date_field: str) -> date:
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

        if self.linked_instrument:
            self.linked_instrument.has_linked_with_portfolio = True
            self.linked_instrument.save()

        try:
            PortfolioBundle.objects.get(
                master_user=self.master_user,
                user_code=self.user_code,
            )
            _l.info("Bundle already exists")

        except PortfolioBundle.DoesNotExist:
            bundle = PortfolioBundle.objects.create(
                master_user=self.master_user,
                owner=self.owner,
                user_code=self.user_code,
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
    nav_previous_day_valuation_currency = models.FloatField(
        default=0.0,
        verbose_name=gettext_lazy("nav previous day valuation currency"),
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
