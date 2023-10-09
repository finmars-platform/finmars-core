import logging
import math
import time
from datetime import datetime, timedelta

from django.db import models
from django.utils.translation import gettext_lazy

from poms.common.models import EXPRESSION_FIELD_LENGTH, DataTimeStampedModel, NamedModel
from poms.common.utils import get_last_business_day
from poms.configuration.models import ConfigurationModel
from poms.instruments.models import CostMethod, PricingPolicy
from poms.users.models import EcosystemDefault, MasterUser, Member

_l = logging.getLogger("poms.reports")


class BalanceReportCustomField(ConfigurationModel):
    STRING = 10
    NUMBER = 20
    DATE = 40

    VALUE_TYPES = (
        (NUMBER, gettext_lazy("Number")),
        (STRING, gettext_lazy("String")),
        (DATE, gettext_lazy("Date")),
    )

    master_user = models.ForeignKey(
        MasterUser,
        related_name="balance_report_custom_fields",
        verbose_name=gettext_lazy("master user"),
        on_delete=models.CASCADE,
    )
    name = models.CharField(
        max_length=255,
        verbose_name=gettext_lazy("name"),
    )
    expr = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        verbose_name=gettext_lazy("expression"),
    )
    value_type = models.PositiveSmallIntegerField(
        choices=VALUE_TYPES,
        default=STRING,
        verbose_name=gettext_lazy("value type"),
    )
    notes = models.TextField(
        blank=True,
        default="",
        verbose_name=gettext_lazy("notes"),
    )

    class Meta:
        verbose_name = gettext_lazy("balance report custom field")
        verbose_name_plural = gettext_lazy("balance report custom fields")
        unique_together = [["master_user", "user_code"]]

    def __str__(self):
        return self.name


class PLReportCustomField(ConfigurationModel):
    STRING = 10
    NUMBER = 20
    DATE = 40

    VALUE_TYPES = (
        (NUMBER, gettext_lazy("Number")),
        (STRING, gettext_lazy("String")),
        (DATE, gettext_lazy("Date")),
    )

    master_user = models.ForeignKey(
        MasterUser,
        related_name="pl_report_custom_fields",
        verbose_name=gettext_lazy("master user"),
        on_delete=models.CASCADE,
    )
    name = models.CharField(
        max_length=255,
        verbose_name=gettext_lazy("name"),
    )
    user_code = models.CharField(
        max_length=255,
        verbose_name=gettext_lazy("user code"),
    )
    expr = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        verbose_name=gettext_lazy("expression"),
    )
    value_type = models.PositiveSmallIntegerField(
        choices=VALUE_TYPES,
        default=STRING,
        verbose_name=gettext_lazy("value type"),
    )
    notes = models.TextField(
        blank=True,
        default="",
        verbose_name=gettext_lazy("notes"),
    )

    class Meta:
        verbose_name = gettext_lazy("pl report custom field")
        verbose_name_plural = gettext_lazy("pl report custom fields")
        unique_together = [["master_user", "user_code"]]

    def __str__(self):
        return self.name


class TransactionReportCustomField(ConfigurationModel):
    STRING = 10
    NUMBER = 20
    DATE = 40

    VALUE_TYPES = (
        (NUMBER, gettext_lazy("Number")),
        (STRING, gettext_lazy("String")),
        (DATE, gettext_lazy("Date")),
    )

    master_user = models.ForeignKey(
        MasterUser,
        related_name="transaction_report_custom_fields",
        verbose_name=gettext_lazy("master user"),
        on_delete=models.CASCADE,
    )
    name = models.CharField(
        max_length=255,
        verbose_name=gettext_lazy("name"),
    )
    user_code = models.CharField(
        max_length=255,
        verbose_name=gettext_lazy("user code"),
    )
    expr = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        verbose_name=gettext_lazy("expression"),
    )
    value_type = models.PositiveSmallIntegerField(
        choices=VALUE_TYPES,
        default=STRING,
        verbose_name=gettext_lazy("value type"),
    )
    notes = models.TextField(
        blank=True,
        default="",
        verbose_name=gettext_lazy("notes"),
    )

    class Meta:
        verbose_name = gettext_lazy("transaction report custom field")
        verbose_name_plural = gettext_lazy("transaction report custom fields")
        unique_together = [["master_user", "user_code"]]

    def __str__(self):
        return self.name


class BalanceReport(models.Model):
    master_user = models.ForeignKey(
        MasterUser,
        related_name="balance_reports",
        verbose_name=gettext_lazy("master user"),
        on_delete=models.CASCADE,
    )

    class Meta:
        verbose_name = gettext_lazy("balance report")
        verbose_name_plural = gettext_lazy("balance reports")

    @staticmethod
    def get_system_attrs():
        """
        Returns attributes that front end uses
        """
        return [
            # region Balance report attributes
            {"key": "name", "name": "Name", "value_type": 10},
            {"key": "short_name", "name": "Short name", "value_type": 10},
            {"key": "user_code", "name": "User code", "value_type": 10},
            {"key": "item_type_name", "name": "Item Type", "value_type": 10},
            {"key": "position_size", "name": "Position size", "value_type": 20},
            {
                "key": "nominal_position_size",
                "name": "Nominal Position size",
                "value_type": 20,
            },
            {
                "key": "pricing_currency",
                "name": "Pricing Currency",
                "value_type": "field",
                "value_content_type": "currencies.currency",
                "code": "user_code",
            },
            {
                "key": "instrument_pricing_currency_fx_rate",
                "name": "Pricing currency fx rate",
                "value_type": 20,
            },
            {
                "key": "instrument_accrued_currency_fx_rate",
                "name": "Accrued currency fx rate",
                "value_type": 20,
            },
            {
                "key": "instrument_accrual_object_accrual_size",
                "name": "Current Payment Size",
                "value_type": 20,
            },
            {
                "key": "instrument_accrual_object_periodicity_object_name",
                "name": "Current Payment Frequency",
                "value_type": 20,
            },
            {
                "key": "instrument_accrual_object_periodicity_n",
                "name": "Current Payment Periodicity N",
                "value_type": 20,
            },
            {"key": "date", "name": "Date", "value_type": 40},
            {"key": "ytm", "name": "YTM", "value_type": 20},
            {"key": "modified_duration", "name": "Modified duration", "value_type": 20},
            {"key": "last_notes", "name": "Last notes", "value_type": 10},
            {
                "key": "gross_cost_price_loc",
                "name": "Gross cost price (Pricing Currency)",
                "value_type": 20,
            },
            {"key": "ytm_at_cost", "name": "YTM at cost", "value_type": 20},
            {"key": "time_invested", "name": "Time invested", "value_type": 20},
            {"key": "return_annually", "name": "Return annually", "value_type": 20},
            {
                "key": "net_cost_price_loc",
                "name": "Net cost price (Pricing Currency)",
                "value_type": 20,
            },
            {
                "key": "currency",
                "name": "Currency",
                "value_type": "field",
                "value_content_type": "currencies.currency",
                "code": "user_code",
            },
            {
                "key": "exposure_currency",
                "name": " Exposure Currency",
                "value_type": "field",
                "value_content_type": "currencies.currency",
                "code": "user_code",
            },
            {
                "key": "principal_invested",
                "name": "Principal invested",
                "value_type": 20,
            },
            {
                "key": "principal_invested_loc",
                "name": "Principal invested (Pricing Currency)",
                "value_type": 20,
            },
            {"key": "amount_invested", "name": "Amount invested", "value_type": 20},
            {
                "key": "amount_invested_loc",
                "name": "Amount invested (Pricing Currency)",
                "value_type": 20,
            },
            {"key": "market_value", "name": "Market value", "value_type": 20},
            {
                "key": "market_value_loc",
                "name": "Market value (Pricing Currency)",
                "value_type": 20,
            },
            {"key": "market_value_percent", "name": "Market value %", "value_type": 20},
            {"key": "exposure", "name": "Exposure", "value_type": 20},
            {"key": "exposure_percent", "name": "Exposure %", "value_type": 20},
            {
                "key": "exposure_loc",
                "name": "Exposure (Pricing Currency)",
                "value_type": 20,
            },
            {
                "key": "instrument_principal_price",
                "name": "Current Price",
                "value_type": 20,
            },
            {
                "key": "instrument_accrued_price",
                "name": "Current Accrued",
                "value_type": 20,
            },
            {"key": "instrument_factor", "name": "Factor", "value_type": 20},
            {"key": "detail", "name": "Transaction Detail", "value_type": 10},
            # endregion Balance report attributes
            # region Balance report performance attributes
            {
                "key": "net_position_return",
                "name": "Net position return",
                "value_type": 20,
            },
            {
                "key": "net_position_return_loc",
                "name": "Net position return (Pricing Currency)",
                "value_type": 20,
            },
            {"key": "position_return", "name": "Position return", "value_type": 20},
            {
                "key": "position_return_loc",
                "name": "Position return (Pricing Currency)",
                "value_type": 20,
            },
            {
                "key": "daily_price_change",
                "name": "Daily price change",
                "value_type": 20,
            },
            {"key": "mtd_price_change", "name": "MTD price change", "value_type": 20},
            {"key": "principal_fx", "name": "Principal FX", "value_type": 20},
            {
                "key": "principal_fx_loc",
                "name": "Principal FX (Pricing Currency)",
                "value_type": 20,
            },
            {"key": "principal_fixed", "name": "Principal fixed", "value_type": 20},
            {
                "key": "principal_fixed_loc",
                "name": "Principal fixed (Pricing Currency)",
                "value_type": 20,
            },
            {"key": "carry_fx", "name": "Carry FX", "value_type": 20},
            {
                "key": "carry_fx_loc",
                "name": "Carry FX (Pricing Currency)",
                "value_type": 20,
            },
            {"key": "carry_fixed", "name": "Carry fixed", "value_type": 20},
            {
                "key": "carry_fixed_loc",
                "name": "Carry fixed (Pricing Currency)",
                "value_type": 20,
            },
            {"key": "overheads_fx", "name": "Overheads FX", "value_type": 20},
            {
                "key": "overheads_fx_loc",
                "name": "Overheads FX (Pricing Currency)",
                "value_type": 20,
            },
            {"key": "overheads_fixed", "name": "Overheads fixed", "value_type": 20},
            {
                "key": "overheads_fixed_loc",
                "name": "Overheads fixed (Pricing Currency)",
                "value_type": 20,
            },
            {"key": "principal", "name": "Principal", "value_type": 20},
            {"key": "carry", "name": "Carry", "value_type": 20},
            {"key": "overheads", "name": "Overheads", "value_type": 20},
            {"key": "total", "name": "Total", "value_type": 20},
            {
                "key": "principal_loc",
                "name": "Pricnipal (Pricing Currency)",
                "value_type": 20,
            },
            {"key": "carry_loc", "name": "Carry (Pricing Currency)", "value_type": 20},
            {
                "key": "overheads_loc",
                "name": "Overheads (Pricing Currency)",
                "value_type": 20,
            },
            {"key": "total_loc", "name": "Total (Pricing Currency)", "value_type": 20},
            {"key": "total_fx", "name": "Total FX", "value_type": 20},
            {
                "key": "total_fx_loc",
                "name": "Total FX (Pricing Currency)",
                "value_type": 20,
            },
            {"key": "total_fixed", "name": "Total fixed", "value_type": 20},
            {
                "key": "total_fixed_loc",
                "name": "Total fixed (Pricing Currency)",
                "value_type": 20,
            },
            # endregion Balance report performance attributes
            # region Balance report mismatch attributes
            {"key": "mismatch", "name": "Mismatch", "value_type": 20},
            {
                "key": "mismatch_portfolio",
                "name": "Mismatch Portfolio",
                "value_type": "field",
            },
            {
                "key": "mismatch_account",
                "name": "Mismatch Account",
                "value_type": "field",
            }
            # endregion Balance report mismatch attributes
        ]


class PLReport(models.Model):
    master_user = models.ForeignKey(
        MasterUser,
        related_name="pl_reports",
        verbose_name=gettext_lazy("master user"),
        on_delete=models.CASCADE,
    )

    class Meta:
        verbose_name = gettext_lazy("p&l report")
        verbose_name_plural = gettext_lazy("p&l report")


class PerformanceReport(models.Model):
    master_user = models.ForeignKey(
        MasterUser,
        related_name="performance_reports",
        verbose_name=gettext_lazy("master user"),
        on_delete=models.CASCADE,
    )

    class Meta:
        verbose_name = gettext_lazy("performance report")
        verbose_name_plural = gettext_lazy("performance reports")


class CashFlowReport(models.Model):
    master_user = models.ForeignKey(
        MasterUser,
        related_name="cashflow_reports",
        verbose_name=gettext_lazy("master user"),
        on_delete=models.CASCADE,
    )

    class Meta:
        verbose_name = gettext_lazy("cash flow report")
        verbose_name_plural = gettext_lazy("cash flow reports")


class TransactionReport(models.Model):
    master_user = models.ForeignKey(
        MasterUser,
        related_name="transaction_reports",
        verbose_name=gettext_lazy("master user"),
        on_delete=models.CASCADE,
    )

    class Meta:
        verbose_name = gettext_lazy("transaction report")
        verbose_name_plural = gettext_lazy("transaction reports")

    @staticmethod
    def get_system_attrs():
        """
        Returns attributes that front end uses
        """
        return [
            {"key": "notes", "name": "Notes", "value_type": 10},
            {"key": "transaction_code", "name": "Transaction Code", "value_type": 20},
            {
                "key": "transaction_class",
                "name": "Transaction class",
                "value_type": "field",
                "code": "user_code",
                "value_content_type": "transactions.transactionclass",
                "allow_null": False,
            },
            {
                "key": "position_size_with_sign",
                "name": "Position Size with sign",
                "value_type": 20,
            },
            {
                "key": "cash_consideration",
                "name": "Cash consideration",
                "value_type": 20,
            },
            {
                "key": "principal_with_sign",
                "name": "Principal with sign",
                "value_type": 20,
            },
            {"key": "carry_with_sign", "name": "Carry with sign", "value_type": 20},
            {
                "key": "overheads_with_sign",
                "name": "Overheads with sign",
                "value_type": 20,
            },
            {"key": "accounting_date", "name": "Accounting date", "value_type": 40},
            {"key": "cash_date", "name": "Cash date", "value_type": 40},
            {"key": "reference_fx_rate", "name": "Reference fx rate", "value_type": 20},
            {"key": "is_locked", "name": "Is locked", "value_type": 50},
            {"key": "is_canceled", "name": "Is canceled", "value_type": 50},
            {"key": "factor", "name": "Factor", "value_type": 20},
            {"key": "trade_price", "name": "Trade price", "value_type": 20},
            # region Entry Part
            {
                "key": "entry_account",
                "name": "Entry Account",
                "value_content_type": "accounts.account",
                "value_entity": "account",
                "code": "user_code",
                "value_type": "field",
            },
            {
                "key": "entry_strategy",
                "name": "Entry Strategy",
                "value_content_type": "strategies.strategy1",
                "value_entity": "strategy-1",
                "code": "user_code",
                "value_type": "field",
            },
            {
                "key": "entry_currency",
                "name": "Entry Currency",
                "value_type": "field",
                "value_entity": "currency",
                "value_content_type": "currencies.currency",
                "code": "user_code",
            },
            {
                "key": "entry_instrument",
                "name": "Entry Instrument",
                "value_content_type": "instruments.instrument",
                "value_entity": "instrument",
                "code": "user_code",
                "value_type": "field",
            },
            {
                "key": "entry_item_short_name",
                "name": "Entry Item Short Name",
                "value_type": 10,
            },
            {"key": "entry_item_name", "name": "Entry Item Name", "value_type": 10},
            {
                "key": "entry_item_user_code",
                "name": "Entry Item User Code",
                "value_type": 10,
            },
            {
                "key": "entry_item_public_name",
                "name": "Entry Item Public Name",
                "value_type": 10,
            },
            {"key": "entry_amount", "name": "Entry Amount", "value_type": 20},
            {
                "key": "entry_item_type_name",
                "name": "Entry Item Type",
                "value_type": 10,
            },
            # endregion Entry Part
            {
                "key": "transaction_item_name",
                "name": "Transaction Item Name",
                "value_type": 10,
            },
            {
                "key": "transaction_item_short_name",
                "name": "Transaction Item Short Name",
                "value_type": 10,
            },
            {
                "key": "transaction_item_user_code",
                "name": "Transaction Item User Code",
                "value_type": 10,
            },
            {"key": "user_text_1", "name": "User Text 1", "value_type": 10},
            {"key": "user_text_2", "name": "User Text 2", "value_type": 10},
            {"key": "user_text_3", "name": "User Text 3", "value_type": 10},
            {"key": "user_number_1", "name": "User Number 1", "value_type": 10},
            {"key": "user_number_2", "name": "User Number 2", "value_type": 10},
            {"key": "user_number_3", "name": "User Number 3", "value_type": 10},
            {"key": "user_date_1", "name": "User Date 1", "value_type": 10},
            {"key": "user_date_2", "name": "User Date 2", "value_type": 10},
            {"key": "user_date_3", "name": "User Date 3", "value_type": 10},
        ]


class BalanceReportInstance(DataTimeStampedModel, NamedModel):
    master_user = models.ForeignKey(
        MasterUser,
        verbose_name=gettext_lazy("master user"),
        on_delete=models.CASCADE,
    )
    member = models.ForeignKey(
        Member,
        verbose_name=gettext_lazy("member"),
        on_delete=models.CASCADE,
    )
    report_date = models.DateField(
        db_index=True, verbose_name=gettext_lazy("report date")
    )
    report_currency = models.ForeignKey(
        "currencies.Currency",
        on_delete=models.CASCADE,
        verbose_name=gettext_lazy("report currency"),
    )
    pricing_policy = models.ForeignKey(
        PricingPolicy,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("pricing policy"),
    )
    cost_method = models.ForeignKey(
        CostMethod,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("cost method"),
    )
    report_uuid = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("report uuid"),
    )
    report_settings_data = models.TextField(
        null=True,
        blank=True,
        verbose_name=gettext_lazy("report settings data"),
    )
    data = models.JSONField(
        null=True,
        blank=True,
        verbose_name=gettext_lazy("Data"),
        help_text="Content of whole report representation",
    )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if BalanceReportInstance.objects.all().count() > 512:
            _l.warning(
                "BalanceReportInstance amount > 512, "
                "delete oldest BalanceReportInstance"
            )
            BalanceReportInstance.objects.all().order_by("id")[0].delete()


class PLReportInstance(DataTimeStampedModel, NamedModel):
    master_user = models.ForeignKey(
        MasterUser,
        verbose_name=gettext_lazy("master user"),
        on_delete=models.CASCADE,
    )
    member = models.ForeignKey(
        Member,
        verbose_name=gettext_lazy("member"),
        on_delete=models.CASCADE,
    )
    report_date = models.DateField(
        db_index=True,
        verbose_name=gettext_lazy("report date"),
    )
    pl_first_date = models.DateField(
        db_index=True,
        verbose_name=gettext_lazy("pl first date"),
    )
    report_currency = models.ForeignKey(
        "currencies.Currency",
        on_delete=models.CASCADE,
        verbose_name=gettext_lazy("report currency"),
    )
    pricing_policy = models.ForeignKey(
        PricingPolicy,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("pricing policy"),
    )
    cost_method = models.ForeignKey(
        CostMethod,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("cost method"),
    )
    report_settings_data = models.TextField(
        null=True,
        blank=True,
        verbose_name=gettext_lazy("report settings data"),
    )
    report_uuid = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("report uuid"),
    )
    data = models.JSONField(
        null=True,
        blank=True,
        verbose_name=gettext_lazy("Data"),
        help_text="Content of whole report representation",
    )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if PLReportInstance.objects.all().count() > 512:
            _l.warning("PLReportInstance amount > 512, delete oldest PLReportInstance")
            PLReportInstance.objects.all().order_by("id")[0].delete()


class TransactionReportInstance(DataTimeStampedModel, NamedModel):
    master_user = models.ForeignKey(
        MasterUser,
        verbose_name=gettext_lazy("master user"),
        on_delete=models.CASCADE,
    )
    member = models.ForeignKey(
        Member,
        verbose_name=gettext_lazy("member"),
        on_delete=models.CASCADE,
    )
    begin_date = models.DateField(
        db_index=True,
        verbose_name=gettext_lazy("begin date"),
    )
    end_date = models.DateField(
        db_index=True,
        verbose_name=gettext_lazy("end date"),
    )
    report_settings_data = models.TextField(
        null=True,
        blank=True,
        verbose_name=gettext_lazy("report settings data"),
    )
    report_uuid = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("report uuid"),
    )
    data = models.JSONField(
        null=True,
        blank=True,
        verbose_name=gettext_lazy("Data"),
        help_text="Content of whole report representation",
    )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if TransactionReportInstance.objects.all().count() > 512:
            _l.warning(
                "TransactionReportInstance amount > 512, "
                "delete oldest PLReportInstance"
            )
            TransactionReportInstance.objects.all().order_by("id")[0].delete()


class PerformanceReportInstance(DataTimeStampedModel, NamedModel):
    master_user = models.ForeignKey(
        MasterUser,
        verbose_name=gettext_lazy("master user"),
        on_delete=models.CASCADE,
    )
    member = models.ForeignKey(
        Member,
        verbose_name=gettext_lazy("member"),
        on_delete=models.CASCADE,
    )
    begin_date = models.DateField(
        db_index=True, verbose_name=gettext_lazy("begin date")
    )
    end_date = models.DateField(
        db_index=True,
        verbose_name=gettext_lazy("end date"),
    )
    report_currency = models.ForeignKey(
        "currencies.Currency",
        on_delete=models.CASCADE,
        verbose_name=gettext_lazy("report currency"),
    )
    calculation_type = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("calculation type"),
    )
    segmentation_type = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("segmentation type"),
    )
    registers = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("registers"),
    )
    registers_names = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("registers names"),
    )
    report_settings_data = models.TextField(
        null=True,
        blank=True,
        verbose_name=gettext_lazy("report settings data"),
    )
    report_uuid = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("report uuid"),
    )
    begin_nav = models.FloatField(
        default=0.0,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("begin nav"),
    )
    end_nav = models.FloatField(
        default=0.0,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("end nav"),
    )
    grand_return = models.FloatField(
        default=0.0,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("grand return"),
    )
    grand_cash_flow = models.FloatField(
        default=0.0,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("grand cash flow"),
    )
    grand_cash_inflow = models.FloatField(
        default=0.0,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("grand cash inflow"),
    )
    grand_cash_outflow = models.FloatField(
        default=0.0,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("grand cash outflow"),
    )
    grand_nav = models.FloatField(
        default=0.0,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("grand nav"),
    )


class PerformanceReportInstanceItem(models.Model):
    report_instance = models.ForeignKey(
        PerformanceReportInstance,
        related_name="items",
        verbose_name=gettext_lazy("report instance"),
        on_delete=models.CASCADE,
    )
    master_user = models.ForeignKey(
        MasterUser,
        verbose_name=gettext_lazy("master user"),
        on_delete=models.CASCADE,
    )
    member = models.ForeignKey(
        Member,
        verbose_name=gettext_lazy("member"),
        on_delete=models.CASCADE,
    )

    begin_date = models.DateField(
        db_index=True,
        verbose_name=gettext_lazy("begin date"),
    )
    end_date = models.DateField(
        db_index=True,
        verbose_name=gettext_lazy("end date"),
    )
    report_currency = models.ForeignKey(
        "currencies.Currency",
        on_delete=models.CASCADE,
        verbose_name=gettext_lazy("report currency"),
    )
    calculation_type = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("calculation type"),
    )
    segmentation_type = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("segmentation type"),
    )
    registers = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("registers"),
    )
    registers_names = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("registers names"),
    )
    report_settings_data = models.TextField(
        null=True,
        blank=True,
        verbose_name=gettext_lazy("report settings data"),
    )
    date_from = models.DateField(
        db_index=True,
        verbose_name=gettext_lazy("date from"),
    )
    date_to = models.DateField(
        db_index=True,
        verbose_name=gettext_lazy("date to"),
    )

    begin_nav = models.FloatField(
        default=0.0,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("begin nav"),
    )
    end_nav = models.FloatField(
        default=0.0,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("end nav"),
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
    nav = models.FloatField(
        default=0.0,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("nav"),
    )
    instrument_return = models.FloatField(
        default=0.0,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("instrument return"),
    )
    cumulative_return = models.FloatField(
        default=0.0,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("cumulative return"),
    )

    class Meta:
        verbose_name = gettext_lazy("performance report instance item")
        verbose_name_plural = gettext_lazy("performance reports instance item")


class ReportSummary:
    def __init__(
        self,
        date_from,
        date_to,
        portfolios,
        bundles,
        currency,
        pricing_policy,
        master_user,
        member,
        context,
    ):
        self.ecosystem_defaults = EcosystemDefault.objects.get(master_user=master_user)

        self.context = context
        self.master_user = master_user
        self.member = member

        self.date_from = date_from
        self.date_to = date_to

        self.currency = currency
        self.pricing_policy = pricing_policy
        self.portfolios = portfolios
        self.bundles = bundles

        self.portfolio_ids = []
        self.portfolio_user_codes = []

        self.portfolio_ids.extend(portfolio.id for portfolio in self.portfolios)
        self.portfolio_user_codes.extend(portfolio.user_code for portfolio in self.portfolios)

    def build_balance(self):
        st = time.perf_counter()

        from poms.reports.serializers import BalanceReportSerializer

        serializer = BalanceReportSerializer(
            data={
                "report_date": self.date_to,
                "pricing_policy": self.pricing_policy.id,
                "report_currency": self.currency.id,
                "portfolios": self.portfolio_ids,
                "cost_method": CostMethod.AVCO,
                "only_numbers": True,
            },
            context=self.context,
        )

        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        from poms.reports.sql_builders.balance import BalanceReportBuilderSql

        self.balance_report = BalanceReportBuilderSql(instance=instance).build_balance()

        _l.info(
            "ReportSummary.build_balance done: %s"
            % "{:3.3f}".format(time.perf_counter() - st)
        )

    def build_pl_range(self):
        st = time.perf_counter()

        from poms.reports.serializers import PLReportSerializer

        serializer = PLReportSerializer(
            data={
                "pl_first_date": self.date_from,
                "report_date": self.date_to,
                "pricing_policy": self.pricing_policy.id,
                "report_currency": self.currency.id,
                "portfolios": self.portfolio_ids,
                "cost_method": CostMethod.AVCO,
            },
            context=self.context,
        )

        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        from poms.reports.sql_builders.pl import PLReportBuilderSql

        self.pl_report_range = PLReportBuilderSql(instance=instance).build_report()

        _l.info(
            "ReportSummary.build_pl_daily done: %s"
            % "{:3.3f}".format(time.perf_counter() - st)
        )

    def build_pl_daily(self):
        st = time.perf_counter()

        from poms.reports.serializers import PLReportSerializer

        pl_first_date = get_last_business_day(self.date_to - timedelta(days=1))

        _l.info('build_pl_daily %s' % pl_first_date)

        serializer = PLReportSerializer(
            data={
                "pl_first_date": pl_first_date,
                "report_date": self.date_to,
                "pricing_policy": self.pricing_policy.id,
                "report_currency": self.currency.id,
                "portfolios": self.portfolio_ids,
                "cost_method": CostMethod.AVCO,
            },
            context=self.context,
        )

        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        from poms.reports.sql_builders.pl import PLReportBuilderSql

        self.pl_report_daily = PLReportBuilderSql(instance=instance).build_report()

        _l.info(
            "ReportSummary.build_pl_daily done: %s"
            % "{:3.3f}".format(time.perf_counter() - st)
        )
    @property
    def pl_first_date_for_mtd(self):

        # If self.date_to is the first day of the month, we subtract one day to get the last day of the previous month.
        # Otherwise, we set the date to the last day of the previous month.
        if self.date_to.day == 1:
            last_day_of_prev_month = self.date_to - timedelta(days=1)
        else:
            # Subtract enough days to get to the first day of the current month and then subtract one more day
            last_day_of_prev_month = self.date_to - timedelta(days=self.date_to.day-1) - timedelta(days=1)

        # Check if it's a weekend and adjust accordingly
        while last_day_of_prev_month.weekday() > 4:  # 0 = Monday, 1 = Tuesday, ..., 6 = Sunday
            last_day_of_prev_month -= timedelta(days=1)

        return last_day_of_prev_month.strftime('%Y-%m-%d')

    def build_pl_mtd(self):
        st = time.perf_counter()

        from poms.reports.serializers import PLReportSerializer

        _l.info('pl_first_date_for_mtd %s' % self.pl_first_date_for_mtd)


        serializer = PLReportSerializer(
            data={
                "pl_first_date": self.pl_first_date_for_mtd,
                "report_date": self.date_to,
                "pricing_policy": self.pricing_policy.id,
                "report_currency": self.currency.id,
                "portfolios": self.portfolio_ids,
                "cost_method": CostMethod.AVCO,
            },
            context=self.context,
        )

        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        _l.info(
            f"build_pl_mtd.instance.pl_first_date {instance.pl_first_date} "
            f"report_date {instance.report_date}"
        )

        from poms.reports.sql_builders.pl import PLReportBuilderSql

        self.pl_report_mtd = PLReportBuilderSql(instance=instance).build_report()

        _l.info(
            "ReportSummary.build_pl_mtd done: %s"
            % "{:3.3f}".format(time.perf_counter() - st)
        )

    @property
    def pl_first_date_for_ytd(self):

        # If self.date_to is January 1st, we subtract one day to get the last day of the previous year.
        # Otherwise, we set the date to December 31st of the previous year.
        if self.date_to.month == 1 and self.date_to.day == 1:
            last_day_of_prev_year = self.date_to - timedelta(days=1)
        else:
            last_day_of_prev_year = self.date_to.replace(year=self.date_to.year-1, month=12, day=31)

        # Check if it's a weekend or holiday and adjust accordingly
        while last_day_of_prev_year.weekday() > 4:  # 0 = Monday, 1 = Tuesday, ..., 6 = Sunday
            last_day_of_prev_year -= timedelta(days=1)

        return last_day_of_prev_year.strftime('%Y-%m-%d')

    def build_pl_ytd(self):
        st = time.perf_counter()

        from poms.reports.serializers import PLReportSerializer

        _l.info('pl_first_date_for_ytd %s' % self.pl_first_date_for_ytd)

        serializer = PLReportSerializer(
            data={
                "pl_first_date": self.pl_first_date_for_ytd,
                "report_date": self.date_to,
                "pricing_policy": self.pricing_policy.id,
                "report_currency": self.currency.id,
                "portfolios": self.portfolio_ids,
                "cost_method": CostMethod.AVCO,
            },
            context=self.context,
        )

        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        from poms.reports.sql_builders.pl import PLReportBuilderSql

        self.pl_report_ytd = PLReportBuilderSql(instance=instance).build_report()

        _l.info(
            "ReportSummary.build_pl_ytd done: %s"
            % "{:3.3f}".format(time.perf_counter() - st)
        )

    def build_pl_inception_to_date(self):
        from poms.reports.sql_builders.pl import PLReportBuilderSql

        st = time.perf_counter()

        from poms.reports.serializers import PLReportSerializer

        serializer = PLReportSerializer(
            data={
                "pl_first_date": self.date_to - timedelta(days=365000),
                "report_date": self.date_to,
                "pricing_policy": self.pricing_policy.id,
                "report_currency": self.currency.id,
                "portfolios": self.portfolio_ids,
                "cost_method": CostMethod.AVCO,
            },
            context=self.context,
        )

        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        self.pl_report_inception_to_date = PLReportBuilderSql(
            instance=instance
        ).build_report()

        _l.info(
            "ReportSummary.build_pl_inception_to_date done: %s"
            % "{:3.3f}".format(time.perf_counter() - st)
        )

    def get_nav(self, portfolio_id=None):
        nav = 0

        for item in self.balance_report.items:
            if (
                portfolio_id
                and item["portfolio_id"] == portfolio_id
                and item["market_value"]
                or not portfolio_id
                and item["market_value"]
            ):
                nav = nav + item["market_value"]

        return nav

    def get_total_pl_range(self, portfolio_id=None):
        total = 0

        for item in self.pl_report_range.items:
            if (
                    portfolio_id
                    and item["portfolio_id"] == portfolio_id
                    and item["total"]
                    or not portfolio_id
                    and item["total"]
            ):
                total = total + item["total"]

        return total

    def get_total_position_return_pl_range(self, portfolio_id=None):
        total = 0
        market_value = 0

        for item in self.pl_report_range.items:
            if portfolio_id:
                if item["portfolio_id"] == portfolio_id:
                    if item["total"]:
                        total = total + item["total"]

                    if item["market_value"]:
                        total = market_value + item["market_value"]

            else:
                if item["total"]:
                    total = total + item["total"]

                if item["market_value"]:
                    market_value = market_value + item["market_value"]

        return math.floor(total / market_value * 10000) / 100 if market_value else 0

    def get_total_pl_daily(self, portfolio_id=None):
        total = 0

        for item in self.pl_report_daily.items:
            if (
                portfolio_id
                and item["portfolio_id"] == portfolio_id
                and item["total"]
                or not portfolio_id
                and item["total"]
            ):
                total = total + item["total"]

        return total

    def get_total_position_return_pl_daily(self, portfolio_id=None):
        total = 0
        market_value = 0

        for item in self.pl_report_daily.items:
            if portfolio_id:
                if item["portfolio_id"] == portfolio_id:
                    if item["total"]:
                        total = total + item["total"]

                    if item["market_value"]:
                        total = market_value + item["market_value"]

            else:
                if item["total"]:
                    total = total + item["total"]

                if item["market_value"]:
                    market_value = market_value + item["market_value"]

        return math.floor(total / market_value * 10000) / 100 if market_value else 0

    def get_total_pl_mtd(self, portfolio_id=None):
        total = 0

        for item in self.pl_report_mtd.items:
            if (
                portfolio_id
                and item["portfolio_id"] == portfolio_id
                and item["total"]
                or not portfolio_id
                and item["total"]
            ):
                total = total + item["total"]

        return total

    def get_total_position_return_pl_mtd(self, portfolio_id=None):
        total = 0
        market_value = 0

        for item in self.pl_report_mtd.items:
            if (
                portfolio_id
                and item["portfolio_id"] == portfolio_id
                or not portfolio_id
            ):
                if item["total"]:
                    total = total + item["total"]

                if item["market_value"]:
                    market_value = market_value + item["market_value"]

        return math.floor(total / market_value * 10000) / 100 if market_value else 0

    def get_total_pl_ytd(self, portfolio_id=None):
        total = 0

        for item in self.pl_report_ytd.items:
            if (
                portfolio_id
                and item["portfolio_id"] == portfolio_id
                and item["total"]
                or not portfolio_id
                and item["total"]
            ):
                total = total + item["total"]

        return total

    def get_total_position_return_pl_ytd(self, portfolio_id=None):
        total = 0
        market_value = 0

        for item in self.pl_report_ytd.items:
            if (
                portfolio_id
                and item["portfolio_id"] == portfolio_id
                or not portfolio_id
            ):
                if item["total"]:
                    total = total + item["total"]

                if item["market_value"]:
                    market_value = market_value + item["market_value"]

        return math.floor(total / market_value * 10000) / 100 if market_value else 0

    def get_total_pl_inception_to_date(self, portfolio_id=None):
        total = 0

        for item in self.pl_report_inception_to_date.items:
            if (
                portfolio_id
                and item["portfolio_id"] == portfolio_id
                and item["total"]
                or not portfolio_id
                and item["total"]
            ):
                total = total + item["total"]

        return total

    def get_total_position_return_pl_inception_to_date(self, portfolio_id=None):
        position_return = 0

        for item in self.pl_report_inception_to_date.items:
            if (
                portfolio_id
                and item["portfolio_id"] == portfolio_id
                and item["position_return"]
                or not portfolio_id
                and item["position_return"]
            ):
                position_return = position_return + item["position_return"]

        return position_return


    def get_daily_performance(self):

        from poms.reports.serializers import PerformanceReportSerializer
        serializer = PerformanceReportSerializer(data={
            "begin_date": get_last_business_day(self.date_to - timedelta(days=1)),
            "end_date": self.date_to,
            "calculation_type": "time_weighted",
            "segmentation_type": "days",
            "registers": self.portfolio_user_codes,
            "report_currency": self.currency.user_code,
        }, context=self.context)

        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        from poms.reports.performance_report import PerformanceReportBuilder
        builder = PerformanceReportBuilder(instance=instance)
        performance_report = builder.build_report()

        return performance_report.grand_return

    def get_mtd_performance(self):

        from poms.reports.serializers import PerformanceReportSerializer

        _l.info('get_mtd_performance self.pl_first_date_for_mtd %s' % self.pl_first_date_for_mtd)

        serializer = PerformanceReportSerializer(data={
            "begin_date": self.pl_first_date_for_mtd,
            "end_date": self.date_to,
            "calculation_type": "time_weighted",
            "segmentation_type": "months",
            "registers": self.portfolio_user_codes,
            "report_currency": self.currency.user_code,
        }, context=self.context)

        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        from poms.reports.performance_report import PerformanceReportBuilder
        builder = PerformanceReportBuilder(instance=instance)
        performance_report = builder.build_report()

        return performance_report.grand_return

    def get_ytd_performance(self):

        from poms.reports.serializers import PerformanceReportSerializer
        serializer = PerformanceReportSerializer(data={
            "begin_date": self.pl_first_date_for_ytd,
            "end_date": self.date_to,
            "calculation_type": "time_weighted",
            "segmentation_type": "months",
            "registers": self.portfolio_user_codes,
            "report_currency": self.currency.user_code,
        }, context=self.context)

        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        from poms.reports.performance_report import PerformanceReportBuilder
        builder = PerformanceReportBuilder(instance=instance)
        performance_report = builder.build_report()

        return performance_report.grand_return


class ReportInstanceModel:
    def __init__(self, **kwargs):
        from poms.accounts.models import Account
        from poms.currencies.models import Currency
        from poms.portfolios.models import Portfolio
        from poms.strategies.models import Strategy1, Strategy2, Strategy3

        # _l.info('ReportInstanceModel.kwargs %s' % kwargs)

        self.report_date = datetime.strptime(kwargs["report_date"], "%Y-%m-%d")

        if kwargs.get("pl_first_date", None):
            self.pl_first_date = datetime.strptime(kwargs["pl_first_date"], "%Y-%m-%d")

        if kwargs.get("bday_yesterday_of_report_date", None):
            self.bday_yesterday_of_report_date = datetime.strptime(
                kwargs["bday_yesterday_of_report_date"], "%Y-%m-%d"
            )

        self.report_currency = Currency.objects.get(id=kwargs["report_currency_id"])
        self.pricing_policy = PricingPolicy.objects.get(id=kwargs["pricing_policy_id"])
        self.cost_method = CostMethod.objects.get(id=kwargs["cost_method_id"])

        self.portfolios = Portfolio.objects.filter(id__in=kwargs["portfolios_ids"])

        self.accounts = Account.objects.filter(id__in=kwargs["accounts_ids"])

        self.strategies1 = Strategy1.objects.filter(id__in=kwargs["strategies1_ids"])
        self.strategies2 = Strategy2.objects.filter(id__in=kwargs["strategies2_ids"])
        self.strategies3 = Strategy3.objects.filter(id__in=kwargs["strategies3_ids"])

        self.show_balance_exposure_details = kwargs["show_balance_exposure_details"]

        self.portfolio_mode = kwargs["portfolio_mode"]
        self.account_mode = kwargs["account_mode"]
        self.strategy1_mode = kwargs["strategy1_mode"]
        self.strategy2_mode = kwargs["strategy2_mode"]
        self.strategy3_mode = kwargs["strategy3_mode"]
        self.allocation_mode = kwargs["allocation_mode"]

        self.master_user = kwargs["master_user"]


class ReportSummaryInstance(DataTimeStampedModel, NamedModel):
    master_user = models.ForeignKey(
        MasterUser,
        verbose_name=gettext_lazy("master user"),
        on_delete=models.CASCADE,
    )
    member = models.ForeignKey(
        Member,
        verbose_name=gettext_lazy("member"),
        on_delete=models.CASCADE,
    )
    date_from = models.DateField(
        null=True,
        db_index=True, verbose_name=gettext_lazy("date from")
    )
    date_to = models.DateField(
        null=True,
        db_index=True,
        verbose_name=gettext_lazy("date to"),
    )

    portfolios = models.TextField(
        null=True,
        blank=True,
        verbose_name=gettext_lazy("portfolios user_codes"),
    )

    currency = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("currency user_code"),
    )

    pricing_policy = models.CharField(
        max_length=1024,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("pricing policy user_code"),
    )

    data = models.JSONField(
        null=True,
        blank=True,
        verbose_name=gettext_lazy("Data"),
        help_text="Content of whole report representation",
    )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if ReportSummaryInstance.objects.all().count() > 512:
            _l.warning(
                "BalanceReportInstance amount > 512, "
                "delete oldest BalanceReportInstance"
            )
            ReportSummaryInstance.objects.all().order_by("id")[0].delete()
