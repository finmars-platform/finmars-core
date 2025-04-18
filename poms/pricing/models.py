import logging

from django.db import models
from django.utils.translation import gettext_lazy

from poms.common.models import NamedModel, TimeStampedModel
from poms.common.utils import date_now
from poms.configuration.models import ConfigurationModel
from poms.procedures.models import PricingProcedureInstance

_l = logging.getLogger("poms.pricing")


class CurrencyPricingScheme(models.Model):
    class Meta:
        abstract = True


class InstrumentPricingScheme(models.Model):
    class Meta:
        abstract = True


class PriceHistoryError(TimeStampedModel):
    STATUS_ERROR = "E"
    STATUS_SKIP = "S"
    STATUS_CREATED = "C"
    STATUS_OVERWRITTEN = "O"
    STATUS_REQUESTED = "R"

    STATUS_CHOICES = (
        (STATUS_ERROR, gettext_lazy("Error")),
        (STATUS_SKIP, gettext_lazy("Skip")),
        (STATUS_CREATED, gettext_lazy("Created")),
        (STATUS_OVERWRITTEN, gettext_lazy("Overwritten")),
        (STATUS_REQUESTED, gettext_lazy("Requested")),
    )

    master_user = models.ForeignKey(
        "users.MasterUser",
        verbose_name=gettext_lazy("master user"),
        on_delete=models.CASCADE,
    )
    instrument = models.ForeignKey(
        "instruments.Instrument",
        on_delete=models.CASCADE,
        verbose_name=gettext_lazy("instrument"),
    )
    pricing_policy = models.ForeignKey(
        "instruments.PricingPolicy",
        on_delete=models.CASCADE,
        verbose_name=gettext_lazy("pricing policy"),
    )
    date = models.DateField(
        db_index=True,
        default=date_now,
        verbose_name=gettext_lazy("date"),
    )
    principal_price = models.FloatField(
        default=None,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("principal price"),
    )
    accrued_price = models.FloatField(
        default=None,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("accrued price"),
    )
    status = models.CharField(
        max_length=1,
        default=STATUS_ERROR,
        choices=STATUS_CHOICES,
        verbose_name=gettext_lazy("status"),
    )
    error_text = models.TextField(
        blank=True,
        default="",
        verbose_name=gettext_lazy("error text"),
    )

    def __str__(self):
        return f"{self.date}: @{self.error_text}"


class CurrencyHistoryError(TimeStampedModel):
    STATUS_ERROR = "E"
    STATUS_SKIP = "S"
    STATUS_CREATED = "C"
    STATUS_OVERWRITTEN = "O"
    STATUS_REQUESTED = "R"

    STATUS_CHOICES = (
        (STATUS_ERROR, gettext_lazy("Error")),
        (STATUS_SKIP, gettext_lazy("Skip")),
        (STATUS_CREATED, gettext_lazy("Created")),
        (STATUS_OVERWRITTEN, gettext_lazy("Overwritten")),
        (STATUS_REQUESTED, gettext_lazy("Requested")),
    )

    master_user = models.ForeignKey(
        "users.MasterUser",
        verbose_name=gettext_lazy("master user"),
        on_delete=models.CASCADE,
    )
    currency = models.ForeignKey(
        "currencies.Currency",
        on_delete=models.CASCADE,
        verbose_name=gettext_lazy("currency"),
    )
    pricing_policy = models.ForeignKey(
        "instruments.PricingPolicy",
        on_delete=models.CASCADE,
        verbose_name=gettext_lazy("pricing policy"),
    )
    date = models.DateField(
        db_index=True,
        default=date_now,
        verbose_name=gettext_lazy("date"),
    )
    fx_rate = models.FloatField(
        default=None,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("fx rate"),
    )
    error_text = models.TextField(
        blank=True,
        default="",
        verbose_name=gettext_lazy("error text"),
    )
    status = models.CharField(
        max_length=1,
        default=STATUS_ERROR,
        choices=STATUS_CHOICES,
        verbose_name=gettext_lazy("status"),
    )

    def __str__(self):
        return f"{self.date}: @{self.error_text}"
