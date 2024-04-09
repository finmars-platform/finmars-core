import csv
import logging
import os

from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.functional import SimpleLazyObject
from django.utils.translation import gettext_lazy

from poms.common.exceptions import FinmarsBaseException
from poms.common.models import DataTimeStampedModel, FakeDeletableModel, NamedModel
from poms.common.utils import date_now
from poms.currencies.constants import MAIN_CURRENCIES
from poms.obj_attrs.models import GenericAttribute
from poms.users.models import MasterUser

_l = logging.getLogger("poms.currencies")


# Probably Deprecated
def _load_currencies_data():
    ccy_path = os.path.join(settings.BASE_DIR, "data", "currencies.csv")
    ret = {}
    with open(ccy_path) as csvfile:
        reader = csv.DictReader(csvfile, delimiter=";")
        for row in reader:
            ret[row["user_code"]] = row
    return ret


currencies_data = SimpleLazyObject(_load_currencies_data)


class Currency(NamedModel, FakeDeletableModel, DataTimeStampedModel):
    """
    Entity for Currency itself, e.g. USD, EUR, CHF
    Used in Transactions, in Reports, in Pricing,
    Very core Entity and very important
    """

    master_user = models.ForeignKey(
        MasterUser,
        related_name="currencies",
        verbose_name=gettext_lazy("master user"),
        on_delete=models.CASCADE,
    )
    reference_for_pricing = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name=gettext_lazy("reference for pricing"),
    )
    pricing_condition = models.ForeignKey(
        "instruments.PricingCondition",
        null=True,
        blank=True,
        verbose_name=gettext_lazy("pricing condition"),
        on_delete=models.CASCADE,
    )
    attributes = GenericRelation(
        GenericAttribute,
        verbose_name=gettext_lazy("attributes"),
    )
    default_fx_rate = models.FloatField(
        default=1,
        verbose_name=gettext_lazy("default fx rate"),
    )
    country = models.ForeignKey(
        "instruments.Country",
        null=True,
        blank=True,
        verbose_name=gettext_lazy("Country"),
        on_delete=models.SET_NULL,
    )

    class Meta(NamedModel.Meta, FakeDeletableModel.Meta):
        verbose_name = gettext_lazy("currency")
        verbose_name_plural = gettext_lazy("currencies")
        permissions = [
            ("manage_currency", "Can manage currency"),
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
            },
            {
                "key": "notes",
                "name": "Notes",
                "value_type": 10,
            },
            {
                "key": "reference_for_pricing",
                "name": "Reference for pricing",
                "value_type": 10,
            },
            {
                "key": "default_fx_rate",
                "name": "Default FX rate",
                "value_type": 20,
            },
            {
                "key": "pricing_condition",
                "name": "Pricing Condition",
                "value_content_type": "instruments.pricingcondition",
                "value_entity": "pricing-condition",
                "code": "user_code",
                "value_type": "field",
            },
        ]

    def fake_delete(self):
        if self.user_code not in MAIN_CURRENCIES:
            return super().fake_delete()


class CurrencyHistoryManager(models.Manager):
    def get_fx_rate(self, currency_id, pricing_policy, date) -> float:
        history = (
            super().get_queryset()
            .filter(
                currency_id=currency_id,
                pricing_policy=pricing_policy,
                date=date,
            )
            .first()
        )
        if not history:
            err_msg = (
                f"no fx_rate for currency {currency_id} date {date} "
                f"policy {pricing_policy} was found in currency history"
            )
            _l.error(err_msg)
            raise FinmarsBaseException(
                error_key="currency_fx_rate_lookup_error",
                message=err_msg,
            )

        return history.fx_rate


class CurrencyHistory(DataTimeStampedModel):
    """
    FX rate of Currencies for specific date
    Finmars is not bound to USD as base currency (Base Currency could be set in poms.users.EcosystemDefault)

    Example of currency history (ecosystem_default.currency = USD)
    EUR 2023-01-01 1.07
    """

    currency = models.ForeignKey(
        Currency,
        related_name="histories",
        verbose_name=gettext_lazy("currency"),
        on_delete=models.CASCADE,
    )
    pricing_policy = models.ForeignKey(
        "instruments.PricingPolicy",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("pricing policy"),
    )
    date = models.DateField(
        db_index=True,
        default=date_now,
        verbose_name=gettext_lazy("date"),
    )
    fx_rate = models.FloatField(
        default=1,
        verbose_name=gettext_lazy("fx rate"),
    )
    procedure_modified_datetime = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=gettext_lazy("procedure_modified_datetime"),
    )

    objects = CurrencyHistoryManager()

    class Meta:
        verbose_name = gettext_lazy("currency history")
        verbose_name_plural = gettext_lazy("currency histories")
        unique_together = (
            "currency",
            "pricing_policy",
            "date",
        )
        index_together = [["currency", "pricing_policy", "date"]]
        ordering = ["date"]

    def save(self, *args, **kwargs):
        cache.clear()

        if self.fx_rate == 0:
            raise ValidationError("FX rate must not be zero")

        if not self.procedure_modified_datetime:
            self.procedure_modified_datetime = date_now()

        if not self.created:
            self.created = date_now()

        super(CurrencyHistory, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.fx_rate} @{self.date}"
