from logging import getLogger

from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.utils.translation import gettext_lazy
from poms.common.models import (
    DataTimeStampedModel,
    FakeDeletableModel,
    NamedModel,
)
from poms.common.utils import date_now
from poms.common.wrapper_models import NamedModelAutoMapping
from poms.currencies.models import Currency
from poms.instruments.models import Instrument, PricingPolicy
from poms.obj_attrs.models import GenericAttribute
from poms.obj_perms.models import GenericObjectPermission
from poms.users.models import MasterUser

_l = getLogger("poms.portfolios")


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
    object_permissions = GenericRelation(
        GenericObjectPermission, verbose_name=gettext_lazy("object permissions")
    )

    class Meta(NamedModel.Meta, FakeDeletableModel.Meta):
        verbose_name = gettext_lazy("portfolio")
        verbose_name_plural = gettext_lazy("portfolios")
        permissions = (
            # ('view_portfolio', 'Can view portfolio'),
            ("manage_portfolio", "Can manage portfolio"),
        )

    @property
    def is_default(self):
        return (
            self.master_user.portfolio_id == self.id if self.master_user_id else False
        )


class PortfolioRegister(NamedModel, FakeDeletableModel, DataTimeStampedModel):
    """
    Portfolio Register

    Entity that create link between portfolio and instrument - That allow us
    to treat portfolio as an instrument
    It means it appears as a position in reports, and also we could calculate
    performance of that instrument
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
    object_permissions = GenericRelation(
        GenericObjectPermission,
        verbose_name=gettext_lazy("object permissions"),
    )
    default_price = models.FloatField(
        default=1.0,
        verbose_name=gettext_lazy("default price"),
    )

    class Meta(NamedModel.Meta, FakeDeletableModel.Meta):
        verbose_name = gettext_lazy("portfolio register")
        verbose_name_plural = gettext_lazy("portfolio registers")

    def save(self, *args, **kwargs):
        super(PortfolioRegister, self).save(*args, **kwargs)

        if self.linked_instrument:
            self.linked_instrument.has_linked_with_portfolio = True
            self.linked_instrument.save()

        try:
            PortfolioBundle.objects.get(
                master_user=self.master_user,
                user_code=self.user_code,
            )
            _l.info("Bundle already exists")

        except Exception:
            bundle = PortfolioBundle.objects.create(
                master_user=self.master_user,
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
    And we also counting number of shares. In portfolio share it is position_size
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
        default=0.0, verbose_name=gettext_lazy("nav previous day valuation currency")
    )
    n_shares_previous_day = models.FloatField(
        default=0.0, verbose_name=gettext_lazy("n shares previous day")
    )
    n_shares_added = models.FloatField(
        default=0.0, verbose_name=gettext_lazy("n shares added")
    )
    dealing_price_valuation_currency = models.FloatField(
        default=0.0,
        verbose_name=gettext_lazy("dealing price valuation currency"),
        help_text=gettext_lazy("Dealing price valuation currency"),
    )

    # n_shares_end_of_the_day = models.FloatField(default=0.0, verbose_name=gettext_lazy("n shares end of the day"))

    rolling_shares_of_the_day = models.FloatField(
        default=0.0,
        verbose_name=gettext_lazy("rolling shares  of the day"),
    )
    previous_date_record = models.ForeignKey(
        "portfolios.PortfolioRegisterRecord",
        null=True,
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
    object_permissions = GenericRelation(
        GenericObjectPermission,
        verbose_name=gettext_lazy("object permissions"),
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
    #
    #     try:
    #
    #         previous = PortfolioRegisterRecord.objects.exclude(transaction_date=self.transaction_date).filter(
    #             portfolio_register=self.portfolio_register).order_by('-transaction_date')[0]
    #
    #         date = self.transaction_date - timedelta(days=1)
    #
    #         price_history = None
    #         try:
    #             price_history = PriceHistory.objecst.get(instrument=self.instrument, date=date)
    #         except Exception as e:
    #             price_history = PriceHistory.objecst.create(instrument=self.instrument, date=date)
    #
    #
    #         portfolio_share_price =  price_history.nav / previous.n_shares_end_of_the_day
    #         nav = 123
    #
    #         price_history.portfolio_share_price = portfolio_share_price
    #         price_history.nav = nav
    #
    #         price_history.save()
    #
    #         self.dealing_price_valuation_currency = portfolio_share_price
    #
    #     except Exception as e:
    #
    #         # ROOT RECORD
    #
    #         self.dealing_price_valuation_currency = self.portfolio.default_price
    #
    #     super(PortfolioRegisterRecord, self).save(*args, **kwargs)

    def save(self, *args, **kwargs):
        if self.pk:  # check if instance already exists in database
            original_instance = PortfolioRegisterRecord.objects.get(pk=self.pk)
            if (
                self.dealing_price_valuation_currency
                != original_instance.dealing_price_valuation_currency
            ):
                # dealing_price_valuation_currency field value has changed,
                # update share_price_calculation_type to manual type
                self.share_price_calculation_type = PortfolioRegisterRecord.MANUAL

        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.portfolio_register} {self.transaction_date} "
            f"{self.transaction_class} {self.cash_amount}"
        )


class PortfolioBundle(NamedModel, FakeDeletableModel, DataTimeStampedModel):
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


# from django.db.models.signals import pre_save
# from django.dispatch import receiver
#
#
# @receiver(pre_save, sender=PortfolioRegisterRecord)
# def check_required_field(sender, instance, **kwargs):
#     if instance.pk:  # check if instance already exists in database
#         original_instance = PortfolioRegisterRecord.objects.get(pk=instance.pk)
#         if instance.required_field != original_instance.required_field:
#             # Required field has changed, do something here
#             pass
#
# from django.core.exceptions import ValidationError
# from django.db import models
#
# class MyModel(models.Model):
#     required_field = models.CharField(max_length=100)
#
