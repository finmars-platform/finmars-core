import json
import logging

from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils.translation import gettext_lazy

from poms.common.models import EXPRESSION_FIELD_LENGTH, DataTimeStampedModel, NamedModel
from poms.common.utils import date_now
from poms.configuration.models import ConfigurationModel
from poms.integrations.models import DataProvider
from poms.schedules.models import ScheduleInstance
from poms.users.models import Member

_l = logging.getLogger("poms.procedures")


class BaseProcedure(NamedModel, DataTimeStampedModel, ConfigurationModel):
    master_user = models.ForeignKey(
        "users.MasterUser",
        verbose_name=gettext_lazy("master user"),
        on_delete=models.CASCADE,
    )

    notes_for_users = models.TextField(
        blank=True,
        default="",
        verbose_name=gettext_lazy("notes for user"),
    )

    class Meta(NamedModel.Meta):
        abstract = True
        unique_together = [["master_user", "user_code"]]
        ordering = ["user_code"]


class BaseProcedureInstance(DataTimeStampedModel):
    STATUS_INIT = "I"
    STATUS_PENDING = "P"
    STATUS_DONE = "D"
    STATUS_ERROR = "E"
    STATUS_CANCELED = "C"

    STATUS_CHOICES = (
        (STATUS_INIT, gettext_lazy("Init")),
        (STATUS_PENDING, gettext_lazy("Pending")),
        (STATUS_DONE, gettext_lazy("Done")),
        (STATUS_ERROR, gettext_lazy("Error")),
        (STATUS_CANCELED, gettext_lazy("Canceled")),
    )

    STARTED_BY_MEMBER = "M"
    STARTED_BY_SCHEDULE = "S"

    STARTED_BY_CHOICES = (
        (STARTED_BY_MEMBER, gettext_lazy("Member")),
        (STARTED_BY_SCHEDULE, gettext_lazy("Schedule")),
    )

    master_user = models.ForeignKey(
        "users.MasterUser",
        verbose_name=gettext_lazy("master user"),
        on_delete=models.CASCADE,
    )
    status = models.CharField(
        max_length=1,
        default=STATUS_INIT,
        choices=STATUS_CHOICES,
        verbose_name=gettext_lazy("status"),
    )
    started_by = models.CharField(
        max_length=1,
        default=STARTED_BY_MEMBER,
        choices=STARTED_BY_CHOICES,
        verbose_name=gettext_lazy("started by"),
    )
    member = models.ForeignKey(
        Member,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("member"),
        on_delete=models.SET_NULL,
    )
    schedule_instance = models.ForeignKey(
        ScheduleInstance,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("schedule instance"),
        on_delete=models.SET_NULL,
    )
    error_code = models.PositiveSmallIntegerField(
        null=True, blank=True, verbose_name=gettext_lazy("error code")
    )
    error_message = models.TextField(
        null=True, blank=True, verbose_name=gettext_lazy("error message")
    )
    action = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )
    provider = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )
    action_verbose = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )
    provider_verbose = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.provider}: {self.action} {self.started_by} by {self.member}"


class PricingProcedure(BaseProcedure):
    CREATED_BY_USER = 1
    CREATED_BY_INSTRUMENT = 2
    CREATED_BY_CURRENCY = 3

    TYPES = (
        (CREATED_BY_USER, gettext_lazy("Created by User")),
        (CREATED_BY_INSTRUMENT, gettext_lazy("Created by Instrument")),
        (CREATED_BY_CURRENCY, gettext_lazy("Created by Currency")),
    )

    type = models.PositiveSmallIntegerField(
        default=CREATED_BY_USER,
        choices=TYPES,
        verbose_name=gettext_lazy("type"),
    )
    price_date_from = models.DateField(
        null=True,
        blank=True,
        verbose_name=gettext_lazy("price date from"),
    )
    price_date_from_expr = models.CharField(
        null=True,
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("price date from expr"),
    )
    price_date_to = models.DateField(
        null=True,
        blank=True,
        verbose_name=gettext_lazy("price date to"),
    )
    price_date_to_expr = models.CharField(
        null=True,
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("price date to expr"),
    )
    price_fill_days = models.PositiveSmallIntegerField(
        default=0,
        verbose_name=gettext_lazy("price fill days"),
    )
    price_get_principal_prices = models.BooleanField(
        default=False,
        verbose_name=gettext_lazy("price get principal prices"),
    )
    price_get_accrued_prices = models.BooleanField(
        default=False,
        verbose_name=gettext_lazy("price get accrued prices"),
    )
    price_get_fx_rates = models.BooleanField(
        default=False,
        verbose_name=gettext_lazy("price get fx rates"),
    )
    price_overwrite_principal_prices = models.BooleanField(
        default=False,
        verbose_name=gettext_lazy("price overwrite principal prices"),
    )
    price_overwrite_accrued_prices = models.BooleanField(
        default=False,
        verbose_name=gettext_lazy("price overwrite accrued prices"),
    )
    price_overwrite_fx_rates = models.BooleanField(
        default=False,
        verbose_name=gettext_lazy("price overwrite fx rates"),
    )
    pricing_policy_filters = models.TextField(
        blank=True,
        default="",
        verbose_name=gettext_lazy("pricing policy filters"),
    )
    portfolio_filters = models.TextField(
        blank=True,
        default="",
        verbose_name=gettext_lazy("portfolio filters"),
    )
    instrument_filters = models.TextField(
        blank=True,
        default="",
        verbose_name=gettext_lazy("instrument filters"),
    )
    currency_filters = models.TextField(
        blank=True,
        default="",
        verbose_name=gettext_lazy("currency filters"),
    )
    instrument_type_filters = models.TextField(
        blank=True,
        default="",
        verbose_name=gettext_lazy("instrument type filters"),
    )
    instrument_pricing_scheme_filters = models.TextField(
        blank=True,
        default="",
        verbose_name=gettext_lazy("instrument pricing scheme filters"),
    )
    instrument_pricing_condition_filters = models.TextField(
        blank=True,
        default="",
        verbose_name=gettext_lazy("instrument pricing condition filters"),
    )
    currency_pricing_scheme_filters = models.TextField(
        blank=True,
        default="",
        verbose_name=gettext_lazy("currency pricing scheme filters"),
    )
    currency_pricing_condition_filters = models.TextField(
        blank=True,
        default="",
        verbose_name=gettext_lazy("currency pricing condition filters"),
    )

    class Meta:
        unique_together = ("master_user", "user_code", "type")

    def save(self, *args, **kwargs):
        from poms.currencies.models import Currency
        from poms.expressions_engine import formula
        from poms.instruments.models import Instrument

        _l.info(f"self.instrument_filters {self.instrument_filters}")

        if self.type == PricingProcedure.CREATED_BY_INSTRUMENT:
            if self.instrument_filters and self.instrument_filters != "":
                user_code = self.instrument_filters

                print(f"save procedure {user_code}")

                instrument = Instrument.objects.get(
                    master_user=self.master_user, user_code=user_code
                )

                self.user_code = formula.safe_eval(
                    'generate_user_code("proc", "", 0)',
                    context={"master_user": self.master_user},
                )

                self.name = f"Instrument {instrument.name} Pricing"
                self.notes_for_users = (
                    f"Pricing Procedure - Instrument: {instrument.name} Date from:"
                    f" {self.price_date_from}. Date to: {self.price_date_to}"
                )
                self.notes = (
                    f"Pricing Procedure generated by instrument: {instrument.user_code}."
                    f" Master user: {self.master_user.name}. Created at {date_now()}"
                )

                self.price_fill_days = 0
                self.price_get_principal_prices = True
                self.price_get_accrued_prices = True
                self.price_get_fx_rates = False
                self.price_overwrite_fx_rates = False

                self.portfolio_filters = ""
                self.instrument_type_filters = ""
                self.instrument_pricing_scheme_filters = ""
                self.instrument_pricing_condition_filters = ""
                self.currency_pricing_scheme_filters = ""
                self.currency_pricing_condition_filters = ""

        elif self.type == PricingProcedure.CREATED_BY_CURRENCY:
            if self.currency_filters and self.currency_filters != "":
                user_code = self.currency_filters

                print(f"save procedure {user_code}")

                instrument = Instrument.objects.get(
                    master_user=self.master_user, user_code=user_code
                )
                currency = Currency.objects.get(
                    master_user=self.master_user, user_code=user_code
                )

                self.user_code = formula.safe_eval(
                    'generate_user_code("proc", "", 0)',
                    context={"master_user": self.master_user},
                )

                self.name = f"Currency {instrument.name} Pricing"
                self.notes_for_users = (
                    f"Pricing Procedure - Currency: {currency.name} Date from:"
                    f" {self.price_date_from}. Date to: {self.price_date_to}"
                )
                self.notes = (
                    f"Pricing Procedure generated by Currency: {currency.user_code}. "
                    f"Master user: {self.master_user.name}. Created at {date_now()}"
                )

                self.price_fill_days = 0
                self.price_get_principal_prices = True
                self.price_get_accrued_prices = True
                self.price_get_fx_rates = False
                self.price_overwrite_fx_rates = False

                self.portfolio_filters = ""
                self.instrument_type_filters = ""
                self.instrument_pricing_scheme_filters = ""
                self.instrument_pricing_condition_filters = ""
                self.currency_pricing_scheme_filters = ""
                self.currency_pricing_condition_filters = ""

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class PricingParentProcedureInstance(models.Model):
    created = models.DateTimeField(
        auto_now_add=True, editable=False, db_index=True, verbose_name="created"
    )
    modified = models.DateTimeField(auto_now=True, editable=False, db_index=True)

    master_user = models.ForeignKey(
        "users.MasterUser",
        verbose_name=gettext_lazy("master user"),
        on_delete=models.CASCADE,
    )

    procedure = models.ForeignKey(
        PricingProcedure,
        on_delete=models.CASCADE,
        verbose_name=gettext_lazy("procedure"),
    )

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return f"{self.procedure.user_code} [{str(self.id)}]"


class PricingProcedureInstance(BaseProcedureInstance):
    procedure = models.ForeignKey(
        PricingProcedure,
        on_delete=models.CASCADE,
        verbose_name=gettext_lazy("procedure"),
    )

    parent_procedure_instance = models.ForeignKey(
        PricingParentProcedureInstance,
        on_delete=models.CASCADE,
        related_name="procedures",
        verbose_name=gettext_lazy("parent pricing procedure"),
        null=True,
        blank=True,
    )

    successful_prices_count = models.IntegerField(
        default=0, verbose_name=gettext_lazy("successful prices count")
    )
    error_prices_count = models.IntegerField(
        default=0, verbose_name=gettext_lazy("error prices count")
    )

    json_request_data = models.TextField(
        null=True, blank=True, verbose_name=gettext_lazy("json request data")
    )
    json_response_data = models.TextField(
        null=True, blank=True, verbose_name=gettext_lazy("response data")
    )

    @property
    def request_data(self):
        if not self.json_request_data:
            return None

        try:
            return json.loads(self.json_request_data)
        except (ValueError, TypeError):
            return None

    @request_data.setter
    def request_data(self, val):
        if val:
            self.json_request_data = json.dumps(
                val, cls=DjangoJSONEncoder, sort_keys=True
            )
        else:
            self.json_request_data = None

    @property
    def response_data(self):
        if not self.json_response_data:
            return None

        try:
            return json.loads(self.json_request_data)
        except (ValueError, TypeError):
            return self.json_response_data

    @response_data.setter
    def response_data(self, val):
        if val:
            try:
                self.json_response_data = json.dumps(
                    val, cls=DjangoJSONEncoder, sort_keys=True
                )
            except Exception as e:
                self.json_response_data = val
        else:
            self.json_response_data = None

    def save(self, *args, **kwargs):
        _l.debug(
            f"before PricingProcedureInstance save id {self.pk} "
            f"successful_prices_count {self.successful_prices_count} "
            f"error_prices_count {self.error_prices_count}"
        )

        super(PricingProcedureInstance, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.procedure} [{self.id}] by {self.member}"


SCHEME_TYPE_CHOICES = [
    ["transaction_import", "Transaction Import"],
    ["simple_import", "Simple Import"],
]


class RequestDataFileProcedure(BaseProcedure):
    provider = models.ForeignKey(
        DataProvider, verbose_name=gettext_lazy("provider"), on_delete=models.CASCADE
    )

    scheme_type = models.CharField(
        max_length=255, choices=SCHEME_TYPE_CHOICES, default="transaction_import"
    )

    scheme_user_code = models.CharField(max_length=1024)

    date_from = models.DateField(
        null=True, blank=True, verbose_name=gettext_lazy("price date from")
    )

    date_from_expr = models.CharField(
        null=True,
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("price date from expr"),
    )

    date_to = models.DateField(
        null=True, blank=True, verbose_name=gettext_lazy("price date to")
    )

    date_to_expr = models.CharField(
        null=True,
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("price date to expr"),
    )

    json_data = models.TextField(
        null=True, blank=True, verbose_name=gettext_lazy("json data")
    )

    @property
    def data(self):
        if not self.json_data:
            return None

        try:
            return json.loads(self.json_data)
        except (ValueError, TypeError):
            return None

    @data.setter
    def data(self, val):
        if val:
            self.json_data = json.dumps(val, cls=DjangoJSONEncoder, sort_keys=True)
        else:
            self.json_data = None


class RequestDataFileProcedureInstance(BaseProcedureInstance):
    procedure = models.ForeignKey(
        RequestDataFileProcedure,
        on_delete=models.CASCADE,
        verbose_name=gettext_lazy("procedure"),
    )

    private_key = models.TextField(
        null=True, blank=True, verbose_name=gettext_lazy("private key")
    )
    public_key = models.TextField(
        null=True, blank=True, verbose_name=gettext_lazy("public key")
    )
    symmetric_key = models.TextField(
        null=True, blank=True, verbose_name=gettext_lazy("symmetric key")
    )

    date_from = models.DateField(
        null=True, blank=True, verbose_name=gettext_lazy("date from")
    )
    date_to = models.DateField(
        null=True, blank=True, verbose_name=gettext_lazy("date to")
    )

    json_request_data = models.TextField(
        null=True, blank=True, verbose_name=gettext_lazy("json data")
    )
    response_data = models.TextField(
        null=True, blank=True, verbose_name=gettext_lazy("response data")
    )

    linked_import_task = models.ForeignKey(
        "celery_tasks.CeleryTask",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("linked import task"),
    )

    class Meta:
        ordering = ["-created"]

    @property
    def request_data(self):
        if not self.json_request_data:
            return None

        try:
            return json.loads(self.json_request_data)
        except (ValueError, TypeError):
            return None

    @request_data.setter
    def request_data(self, val):
        if val:
            self.json_request_data = json.dumps(
                val, cls=DjangoJSONEncoder, sort_keys=True
            )
        else:
            self.json_request_data = None

    def __str__(self):
        return f"{self.procedure} [{self.id}] by {self.member}"

    def save(self, *args, **kwargs):
        super(RequestDataFileProcedureInstance, self).save(*args, **kwargs)

        count = RequestDataFileProcedureInstance.objects.all().count()

        if count > 1000:
            RequestDataFileProcedureInstance.objects.all().order_by("id")[0].delete()


class ExpressionProcedure(BaseProcedure):
    code = models.TextField(null=True, blank=True, verbose_name=gettext_lazy("code"))

    json_data = models.TextField(
        null=True, blank=True, verbose_name=gettext_lazy("json data")
    )

    @property
    def data(self):
        if not self.json_data:
            return None

        try:
            return json.loads(self.json_data)
        except (ValueError, TypeError):
            return None

    @data.setter
    def data(self, val):
        if val:
            self.json_data = json.dumps(val, cls=DjangoJSONEncoder, sort_keys=True)
        else:
            self.json_data = None


class ExpressionProcedureContextVariable(models.Model):
    procedure = models.ForeignKey(
        ExpressionProcedure,
        on_delete=models.CASCADE,
        related_name="context_variables",
        verbose_name=gettext_lazy("procedure"),
    )
    order = models.IntegerField(default=0, verbose_name=gettext_lazy("order"))
    name = models.CharField(max_length=255)
    expression = models.CharField(
        null=True,
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("expression"),
    )
    notes = models.TextField(null=True, blank=True, verbose_name=gettext_lazy("notes"))

    def __str__(self):
        return self.name or ""
