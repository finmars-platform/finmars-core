from __future__ import unicode_literals

import logging
import math
import time
from datetime import timedelta

from django.db import models
from django.utils.translation import gettext_lazy

from poms.common.models import NamedModel, EXPRESSION_FIELD_LENGTH, DataTimeStampedModel
from poms.instruments.models import PricingPolicy, CostMethod
from poms.users.models import MasterUser, Member, EcosystemDefault

_l = logging.getLogger('poms.reports')


class BalanceReportCustomField(models.Model):
    STRING = 10
    NUMBER = 20
    DATE = 40

    VALUE_TYPES = (
        (NUMBER, gettext_lazy('Number')),
        (STRING, gettext_lazy('String')),
        (DATE, gettext_lazy('Date')),
    )

    master_user = models.ForeignKey(MasterUser, related_name='balance_report_custom_fields',
                                    verbose_name=gettext_lazy('master user'), on_delete=models.CASCADE)
    name = models.CharField(max_length=255, verbose_name=gettext_lazy('name'))
    user_code = models.CharField(max_length=255, verbose_name=gettext_lazy('user code'))
    expr = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, verbose_name=gettext_lazy('expression'))
    value_type = models.PositiveSmallIntegerField(choices=VALUE_TYPES, default=STRING,
                                                  verbose_name=gettext_lazy('value type'))
    notes = models.TextField(blank=True, default='', verbose_name=gettext_lazy('notes'))

    class Meta:
        verbose_name = gettext_lazy('balance report custom field')
        verbose_name_plural = gettext_lazy('balance report custom fields')
        unique_together = [
            ['master_user', 'user_code']
        ]

    def __str__(self):
        return self.name


class PLReportCustomField(models.Model):
    STRING = 10
    NUMBER = 20
    DATE = 40

    VALUE_TYPES = (
        (NUMBER, gettext_lazy('Number')),
        (STRING, gettext_lazy('String')),
        (DATE, gettext_lazy('Date')),
    )

    master_user = models.ForeignKey(MasterUser, related_name='pl_report_custom_fields',
                                    verbose_name=gettext_lazy('master user'), on_delete=models.CASCADE)
    name = models.CharField(max_length=255, verbose_name=gettext_lazy('name'))
    user_code = models.CharField(max_length=255, verbose_name=gettext_lazy('user code'))
    expr = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, verbose_name=gettext_lazy('expression'))
    value_type = models.PositiveSmallIntegerField(choices=VALUE_TYPES, default=STRING,
                                                  verbose_name=gettext_lazy('value type'))
    notes = models.TextField(blank=True, default='', verbose_name=gettext_lazy('notes'))

    class Meta:
        verbose_name = gettext_lazy('pl report custom field')
        verbose_name_plural = gettext_lazy('pl report custom fields')
        unique_together = [
            ['master_user', 'user_code']
        ]

    def __str__(self):
        return self.name


class TransactionReportCustomField(models.Model):
    STRING = 10
    NUMBER = 20
    DATE = 40

    VALUE_TYPES = (
        (NUMBER, gettext_lazy('Number')),
        (STRING, gettext_lazy('String')),
        (DATE, gettext_lazy('Date')),
    )

    master_user = models.ForeignKey(MasterUser, related_name='transaction_report_custom_fields',
                                    verbose_name=gettext_lazy('master user'), on_delete=models.CASCADE)
    name = models.CharField(max_length=255, verbose_name=gettext_lazy('name'))
    user_code = models.CharField(max_length=255, verbose_name=gettext_lazy('user code'))
    expr = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, verbose_name=gettext_lazy('expression'))
    value_type = models.PositiveSmallIntegerField(choices=VALUE_TYPES, default=STRING,
                                                  verbose_name=gettext_lazy('value type'))
    notes = models.TextField(blank=True, default='', verbose_name=gettext_lazy('notes'))

    class Meta:
        verbose_name = gettext_lazy('transaction report custom field')
        verbose_name_plural = gettext_lazy('transaction report custom fields')
        unique_together = [
            ['master_user', 'user_code']
        ]

    def __str__(self):
        return self.name


class BalanceReport(models.Model):
    master_user = models.ForeignKey(MasterUser, related_name='balance_reports',
                                    verbose_name=gettext_lazy('master user'), on_delete=models.CASCADE)

    class Meta:
        verbose_name = gettext_lazy('balance report')
        verbose_name_plural = gettext_lazy('balance reports')

    @staticmethod
    def get_system_attrs():
        """
        Returns attributes that front end uses
        """
        return [
            # region Balance report attributes
            {
                "key": "name",
                "name": "Name",
                "value_type": 10
            },
            {
                "key": "short_name",
                "name": "Short name",
                "value_type": 10
            },
            {
                "key": "user_code",
                "name": "User code",
                "value_type": 10
            },
            {
                "key": "item_type_name",
                "name": "Item Type",
                "value_type": 10
            },
            {
                "key": "position_size",
                "name": "Position size",
                "value_type": 20
            },
            {
                "key": "nominal_position_size",
                "name": "Nominal Position size",
                "value_type": 20
            },
            {
                "key": "pricing_currency",
                "name": "Pricing Currency",
                "value_type": "field",
                "value_content_type": "currencies.currency",
                "code": "user_code"
            },
            {
                "key": "instrument_pricing_currency_fx_rate",
                "name": "Pricing currency fx rate",
                "value_type": 20
            },
            {
                "key": "instrument_accrued_currency_fx_rate",
                "name": "Accrued currency fx rate",
                "value_type": 20
            },

            {
                "key": "instrument_accrual_object_accrual_size",
                "name": "Current Payment Size",
                "value_type": 20
            },
            {
                "key": "instrument_accrual_object_periodicity_object_name",
                "name": "Current Payment Frequency",
                "value_type": 20
            },
            {
                "key": "instrument_accrual_object_periodicity_n",
                "name": "Current Payment Periodicity N",
                "value_type": 20
            },
            {
                "key": "date",
                "name": "Date",
                "value_type": 40
            },
            {
                "key": "ytm",
                "name": "YTM",
                "value_type": 20
            },
            {
                "key": "modified_duration",
                "name": "Modified duration",
                "value_type": 20
            },

            {
                "key": "last_notes",
                "name": "Last notes",
                "value_type": 10
            },
            {
                "key": "gross_cost_price_loc",
                "name": "Gross cost price (Pricing Currency)",
                "value_type": 20
            },
            {
                "key": "ytm_at_cost",
                "name": "YTM at cost",
                "value_type": 20
            },
            {
                "key": "time_invested",
                "name": "Time invested",
                "value_type": 20
            },

            {
                "key": "return_annually",
                "name": "Return annually",
                "value_type": 20
            },
            {
                "key": "net_cost_price_loc",
                "name": "Net cost price (Pricing Currency)",
                "value_type": 20
            },
            {
                "key": "currency",
                "name": "Currency",
                "value_type": "field",
                "value_content_type": "currencies.currency",
                "code": "user_code"
            },
            {
                "key": "exposure_currency",
                "name": " Exposure Currency",
                "value_type": "field",
                "value_content_type": "currencies.currency",
                "code": "user_code"
            },
            {
                "key": "principal_invested",
                "name": "Principal invested",
                "value_type": 20
            },
            {
                "key": "principal_invested_loc",
                "name": "Principal invested (Pricing Currency)",
                "value_type": 20
            },
            {
                "key": "amount_invested",
                "name": "Amount invested",
                "value_type": 20
            },
            {
                "key": "amount_invested_loc",
                "name": "Amount invested (Pricing Currency)",
                "value_type": 20
            },

            {
                "key": "market_value",
                "name": "Market value",
                "value_type": 20
            },
            {
                "key": "market_value_loc",
                "name": "Market value (Pricing Currency)",
                "value_type": 20
            },
            {
                "key": "market_value_percent",
                "name": "Market value %",
                "value_type": 20
            },
            {
                "key": "exposure",
                "name": "Exposure",
                "value_type": 20
            },
            {
                "key": "exposure_percent",
                "name": "Exposure %",
                "value_type": 20
            },
            {
                "key": "exposure_loc",
                "name": "Exposure (Pricing Currency)",
                "value_type": 20
            },
            {
                "key": "instrument_principal_price",
                "name": "Current Price",
                "value_type": 20
            },
            {
                "key": "instrument_accrued_price",
                "name": "Current Accrued",
                "value_type": 20
            },
            {
                "key": "instrument_factor",
                "name": "Factor",
                "value_type": 20
            },
            {
                "key": "detail",
                "name": "Transaction Detail",
                "value_type": 10
            },
            # endregion Balance report attributes

            # region Balance report performance attributes
            {
                "key": "net_position_return",
                "name": "Net position return",
                "value_type": 20
            },
            {
                "key": "net_position_return_loc",
                "name": "Net position return (Pricing Currency)",
                "value_type": 20
            },
            {
                "key": "position_return",
                "name": "Position return",
                "value_type": 20
            },
            {
                "key": "position_return_loc",
                "name": "Position return (Pricing Currency)",
                "value_type": 20
            },
            {
                "key": "daily_price_change",
                "name": "Daily price change",
                "value_type": 20
            },
            {
                "key": "mtd_price_change",
                "name": "MTD price change",
                "value_type": 20
            },
            {
                "key": "principal_fx",
                "name": "Principal FX",
                "value_type": 20
            },
            {
                "key": "principal_fx_loc",
                "name": "Principal FX (Pricing Currency)",
                "value_type": 20
            },
            {
                "key": "principal_fixed",
                "name": "Principal fixed",
                "value_type": 20
            },
            {
                "key": "principal_fixed_loc",
                "name": "Principal fixed (Pricing Currency)",
                "value_type": 20
            },
            {
                "key": "carry_fx",
                "name": "Carry FX",
                "value_type": 20
            },
            {
                "key": "carry_fx_loc",
                "name": "Carry FX (Pricing Currency)",
                "value_type": 20
            },
            {
                "key": "carry_fixed",
                "name": "Carry fixed",
                "value_type": 20
            },
            {
                "key": "carry_fixed_loc",
                "name": "Carry fixed (Pricing Currency)",
                "value_type": 20
            },
            {
                "key": "overheads_fx",
                "name": "Overheads FX",
                "value_type": 20
            },
            {
                "key": "overheads_fx_loc",
                "name": "Overheads FX (Pricing Currency)",
                "value_type": 20
            },
            {
                "key": "overheads_fixed",
                "name": "Overheads fixed",
                "value_type": 20
            },
            {
                "key": "overheads_fixed_loc",
                "name": "Overheads fixed (Pricing Currency)",
                "value_type": 20
            },
            {
                "key": "principal",
                "name": "Principal",
                "value_type": 20
            },
            {
                "key": "carry",
                "name": "Carry",
                "value_type": 20
            },
            {
                "key": "overheads",
                "name": "Overheads",
                "value_type": 20
            },
            {
                "key": "total",
                "name": "Total",
                "value_type": 20
            },
            {
                "key": "principal_loc",
                "name": "Pricnipal (Pricing Currency)",
                "value_type": 20
            },
            {
                "key": "carry_loc",
                "name": "Carry (Pricing Currency)",
                "value_type": 20
            },
            {
                "key": "overheads_loc",
                "name": "Overheads (Pricing Currency)",
                "value_type": 20
            },
            {
                "key": "total_loc",
                "name": "Total (Pricing Currency)",
                "value_type": 20
            },
            {
                "key": "total_fx",
                "name": "Total FX",
                "value_type": 20
            },
            {
                "key": "total_fx_loc",
                "name": "Total FX (Pricing Currency)",
                "value_type": 20
            },

            {
                "key": "total_fixed",
                "name": "Total fixed",
                "value_type": 20
            },
            {
                "key": "total_fixed_loc",
                "name": "Total fixed (Pricing Currency)",
                "value_type": 20
            },

            # endregion Balance report performance attributes

            # region Balance report mismatch attributes
            {
                "key": "mismatch",
                "name": "Mismatch",
                "value_type": 20
            },
            {
                "key": "mismatch_portfolio",
                "name": "Mismatch Portfolio",
                "value_type": "field"
            },
            {
                "key": "mismatch_account",
                "name": "Mismatch Account",
                "value_type": "field"
            }
            # endregion Balance report mismatch attributes
        ]


class PLReport(models.Model):
    master_user = models.ForeignKey(MasterUser, related_name='pl_reports', verbose_name=gettext_lazy('master user'),
                                    on_delete=models.CASCADE)

    class Meta:
        verbose_name = gettext_lazy('p&l report')
        verbose_name_plural = gettext_lazy('p&l report')


class PerformanceReport(models.Model):
    master_user = models.ForeignKey(MasterUser, related_name='performance_reports',
                                    verbose_name=gettext_lazy('master user'), on_delete=models.CASCADE)

    class Meta:
        verbose_name = gettext_lazy('performance report')
        verbose_name_plural = gettext_lazy('performance reports')


class CashFlowReport(models.Model):
    master_user = models.ForeignKey(MasterUser, related_name='cashflow_reports',
                                    verbose_name=gettext_lazy('master user'), on_delete=models.CASCADE)

    class Meta:
        verbose_name = gettext_lazy('cash flow report')
        verbose_name_plural = gettext_lazy('cash flow reports')


class TransactionReport(models.Model):
    master_user = models.ForeignKey(MasterUser, related_name='transaction_reports',
                                    verbose_name=gettext_lazy('master user'), on_delete=models.CASCADE)

    class Meta:
        verbose_name = gettext_lazy('transaction report')
        verbose_name_plural = gettext_lazy('transaction reports')


class BalanceReportInstance(DataTimeStampedModel, NamedModel):
    master_user = models.ForeignKey(MasterUser,
                                    verbose_name=gettext_lazy('master user'), on_delete=models.CASCADE)

    member = models.ForeignKey(Member,
                               verbose_name=gettext_lazy('member'), on_delete=models.CASCADE)

    report_date = models.DateField(db_index=True, verbose_name=gettext_lazy('report date'))

    report_currency = models.ForeignKey('currencies.Currency', on_delete=models.CASCADE,
                                        verbose_name=gettext_lazy('report currency'))

    pricing_policy = models.ForeignKey(PricingPolicy, on_delete=models.CASCADE, null=True, blank=True,
                                       verbose_name=gettext_lazy('pricing policy'))

    cost_method = models.ForeignKey(CostMethod, on_delete=models.CASCADE, null=True, blank=True,
                                    verbose_name=gettext_lazy('cost method'))

    report_uuid = models.CharField(max_length=255, null=True, blank=True, verbose_name=gettext_lazy('report uuid'))

    report_settings_data = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('report settings data'))


class BalanceReportInstanceItem(models.Model):
    report_instance = models.ForeignKey(BalanceReportInstance, related_name="items",
                                        verbose_name=gettext_lazy('report instance'), on_delete=models.CASCADE)

    master_user = models.ForeignKey(MasterUser,
                                    verbose_name=gettext_lazy('master user'), on_delete=models.CASCADE)

    member = models.ForeignKey(Member,
                               verbose_name=gettext_lazy('member'), on_delete=models.CASCADE)

    report_date = models.DateField(db_index=True, verbose_name=gettext_lazy('report date'))

    report_currency = models.ForeignKey('currencies.Currency', on_delete=models.CASCADE,
                                        verbose_name=gettext_lazy('report currency'))

    pricing_policy = models.ForeignKey(PricingPolicy, on_delete=models.CASCADE, null=True, blank=True,
                                       verbose_name=gettext_lazy('pricing policy'))

    cost_method = models.ForeignKey(CostMethod, on_delete=models.CASCADE, null=True, blank=True,
                                    verbose_name=gettext_lazy('cost method'))

    report_settings_data = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('report settings data'))

    name = models.CharField(max_length=255, null=True, blank=True, verbose_name=gettext_lazy('name'))
    short_name = models.CharField(max_length=255, null=True, blank=True, verbose_name=gettext_lazy('short name'))
    user_code = models.CharField(max_length=255, null=True, blank=True, verbose_name=gettext_lazy('user code'))

    portfolio = models.ForeignKey('portfolios.Portfolio', null=True, blank=True, on_delete=models.SET_NULL,
                                  verbose_name=gettext_lazy('portfolio'))

    instrument = models.ForeignKey('instruments.Instrument', null=True, blank=True, on_delete=models.SET_NULL,
                                   verbose_name=gettext_lazy('instrument'))

    currency = models.ForeignKey('currencies.Currency', null=True, blank=True, on_delete=models.SET_NULL,
                                 related_name="balance_report_instance_item_currency",
                                 verbose_name=gettext_lazy('currency'))
    pricing_currency = models.ForeignKey('currencies.Currency', null=True, blank=True, on_delete=models.SET_NULL,
                                         related_name="balance_report_instance_item_pricing_currency",
                                         verbose_name=gettext_lazy('pricing currency'))
    exposure_currency = models.ForeignKey('currencies.Currency', null=True, blank=True, on_delete=models.SET_NULL,
                                          related_name="balance_report_instance_item_exposure_currency",
                                          verbose_name=gettext_lazy('exposure currency'))
    account = models.ForeignKey('accounts.Account', null=True, blank=True, on_delete=models.SET_NULL,
                                verbose_name=gettext_lazy('account'))
    strategy1 = models.ForeignKey('strategies.Strategy1', null=True, blank=True, on_delete=models.SET_NULL,
                                  verbose_name=gettext_lazy('strategy1'))
    strategy2 = models.ForeignKey('strategies.Strategy2', null=True, blank=True, on_delete=models.SET_NULL,
                                  verbose_name=gettext_lazy('strategy2'))
    strategy3 = models.ForeignKey('strategies.Strategy3', null=True, blank=True, on_delete=models.SET_NULL,
                                  verbose_name=gettext_lazy('strategy3'))

    item_id = models.CharField(max_length=255, null=True, blank=True, verbose_name=gettext_lazy('item id'))
    item_type = models.IntegerField(default=0, verbose_name=gettext_lazy('portfolio'))
    item_type_name = models.CharField(max_length=255, null=True, blank=True,
                                      verbose_name=gettext_lazy('item type name'))

    instrument_pricing_currency_fx_rate = models.FloatField(default=0.0, null=True, blank=True,
                                                            verbose_name=gettext_lazy(
                                                                'instrument_pricing_currency_fx_rate'))
    instrument_accrued_currency_fx_rate = models.FloatField(default=0.0, null=True, blank=True,
                                                            verbose_name=gettext_lazy(
                                                                'instrument_accrued_currency_fx_rate'))
    instrument_principal_price = models.FloatField(default=0.0, null=True, blank=True,
                                                   verbose_name=gettext_lazy('instrument_principal_price'))
    instrument_accrued_price = models.FloatField(default=0.0, null=True, blank=True,
                                                 verbose_name=gettext_lazy('instrument_accrued_price'))

    position_size = models.FloatField(default=0.0, null=True, blank=True, verbose_name=gettext_lazy('position_size'))
    market_value = models.FloatField(default=0.0, null=True, blank=True, verbose_name=gettext_lazy('market_value'))
    market_value_loc = models.FloatField(default=0.0, null=True, blank=True,
                                         verbose_name=gettext_lazy('market_value_loc'))
    exposure = models.FloatField(default=0.0, null=True, blank=True, verbose_name=gettext_lazy('exposure'))
    exposure_loc = models.FloatField(default=0.0, null=True, blank=True, verbose_name=gettext_lazy('exposure_loc'))

    ytm = models.FloatField(default=0.0, null=True, blank=True, verbose_name=gettext_lazy('ytm'))
    ytm_at_cost = models.FloatField(default=0.0, null=True, blank=True, verbose_name=gettext_lazy('ytm_at_cost'))
    modified_duration = models.FloatField(default=0.0, null=True, blank=True,
                                          verbose_name=gettext_lazy('modified_duration'))
    return_annually = models.FloatField(default=0.0, null=True, blank=True,
                                        verbose_name=gettext_lazy('return_annually'))

    position_return = models.FloatField(default=0.0, null=True, blank=True,
                                        verbose_name=gettext_lazy('position_return'))
    position_return_loc = models.FloatField(default=0.0, null=True, blank=True,
                                            verbose_name=gettext_lazy('position_return_loc'))
    net_position_return = models.FloatField(default=0.0, null=True, blank=True,
                                            verbose_name=gettext_lazy('net_position_return'))
    net_position_return_loc = models.FloatField(default=0.0, null=True, blank=True,
                                                verbose_name=gettext_lazy('net_position_return_loc'))

    net_cost_price = models.FloatField(default=0.0, null=True, blank=True, verbose_name=gettext_lazy('net_cost_price'))
    net_cost_price_loc = models.FloatField(default=0.0, null=True, blank=True,
                                           verbose_name=gettext_lazy('net_cost_price_loc'))
    gross_cost_price = models.FloatField(default=0.0, null=True, blank=True,
                                         verbose_name=gettext_lazy('gross_cost_price'))
    gross_cost_price_loc = models.FloatField(default=0.0, null=True, blank=True,
                                             verbose_name=gettext_lazy('gross_cost_price_loc'))

    principal_invested = models.FloatField(default=0.0, null=True, blank=True,
                                           verbose_name=gettext_lazy('principal_invested'))
    principal_invested_loc = models.FloatField(default=0.0, null=True, blank=True,
                                               verbose_name=gettext_lazy('principal_invested_loc'))

    amount_invested = models.FloatField(default=0.0, null=True, blank=True,
                                        verbose_name=gettext_lazy('amount_invested'))
    amount_invested_loc = models.FloatField(default=0.0, null=True, blank=True,
                                            verbose_name=gettext_lazy('amount_invested_loc'))

    time_invested = models.FloatField(default=0.0, null=True, blank=True, verbose_name=gettext_lazy('time_invested'))

    principal = models.FloatField(default=0.0, null=True, blank=True, verbose_name=gettext_lazy('principal'))
    carry = models.FloatField(default=0.0, null=True, blank=True, verbose_name=gettext_lazy('carry'))
    overheads = models.FloatField(default=0.0, null=True, blank=True, verbose_name=gettext_lazy('overheads'))
    total = models.FloatField(default=0.0, null=True, blank=True, verbose_name=gettext_lazy('total'))

    principal_fx = models.FloatField(default=0.0, null=True, blank=True, verbose_name=gettext_lazy('principal_fx'))
    carry_fx = models.FloatField(default=0.0, null=True, blank=True, verbose_name=gettext_lazy('carry_fx'))
    overheads_fx = models.FloatField(default=0.0, null=True, blank=True, verbose_name=gettext_lazy('overheads_fx'))
    total_fx = models.FloatField(default=0.0, null=True, blank=True, verbose_name=gettext_lazy('total_fx'))

    principal_fixed = models.FloatField(default=0.0, null=True, blank=True,
                                        verbose_name=gettext_lazy('principal_fixed'))
    carry_fixed = models.FloatField(default=0.0, null=True, blank=True, verbose_name=gettext_lazy('carry_fixed'))
    overheads_fixed = models.FloatField(default=0.0, null=True, blank=True,
                                        verbose_name=gettext_lazy('overheads_fixed'))
    total_fixed = models.FloatField(default=0.0, null=True, blank=True, verbose_name=gettext_lazy('total_fixed'))

    principal_loc = models.FloatField(default=0.0, null=True, blank=True, verbose_name=gettext_lazy('principal_loc'))
    carry_loc = models.FloatField(default=0.0, null=True, blank=True, verbose_name=gettext_lazy('carry_loc'))
    overheads_loc = models.FloatField(default=0.0, null=True, blank=True, verbose_name=gettext_lazy('overheads_loc'))
    total_loc = models.FloatField(default=0.0, null=True, blank=True, verbose_name=gettext_lazy('total_loc'))

    principal_fx_loc = models.FloatField(default=0.0, null=True, blank=True,
                                         verbose_name=gettext_lazy('principal_fx_loc'))
    carry_fx_loc = models.FloatField(default=0.0, null=True, blank=True, verbose_name=gettext_lazy('carry_fx_loc'))
    overheads_fx_loc = models.FloatField(default=0.0, null=True, blank=True,
                                         verbose_name=gettext_lazy('overheads_fx_loc'))
    total_fx_loc = models.FloatField(default=0.0, null=True, blank=True, verbose_name=gettext_lazy('total_fx_loc'))

    principal_fixed_loc = models.FloatField(default=0.0, null=True, blank=True,
                                            verbose_name=gettext_lazy('principal_fixed_loc'))
    carry_fixed_loc = models.FloatField(default=0.0, null=True, blank=True,
                                        verbose_name=gettext_lazy('carry_fixed_loc'))
    overheads_fixed_loc = models.FloatField(default=0.0, null=True, blank=True,
                                            verbose_name=gettext_lazy('overheads_fixed_loc'))
    total_fixed_loc = models.FloatField(default=0.0, null=True, blank=True,
                                        verbose_name=gettext_lazy('total_fixed_loc'))

    custom_field_text_1 = models.CharField(max_length=255, null=True, blank=True,
                                           verbose_name=gettext_lazy('custom_field_text_1'))
    custom_field_text_2 = models.CharField(max_length=255, null=True, blank=True,
                                           verbose_name=gettext_lazy('custom_field_text_2'))
    custom_field_text_3 = models.CharField(max_length=255, null=True, blank=True,
                                           verbose_name=gettext_lazy('custom_field_text_3'))
    custom_field_text_4 = models.CharField(max_length=255, null=True, blank=True,
                                           verbose_name=gettext_lazy('custom_field_text_4'))
    custom_field_text_5 = models.CharField(max_length=255, null=True, blank=True,
                                           verbose_name=gettext_lazy('custom_field_text_5'))

    custom_field_number_1 = models.FloatField(default=0.0, null=True, blank=True,
                                              verbose_name=gettext_lazy('custom_field_number_1'))
    custom_field_number_2 = models.FloatField(default=0.0, null=True, blank=True,
                                              verbose_name=gettext_lazy('custom_field_number_2'))
    custom_field_number_3 = models.FloatField(default=0.0, null=True, blank=True,
                                              verbose_name=gettext_lazy('custom_field_number_3'))
    custom_field_number_4 = models.FloatField(default=0.0, null=True, blank=True,
                                              verbose_name=gettext_lazy('custom_field_number_4'))
    custom_field_number_5 = models.FloatField(default=0.0, null=True, blank=True,
                                              verbose_name=gettext_lazy('custom_field_number_5'))

    custom_field_date_1 = models.DateField(null=True, blank=True, verbose_name=gettext_lazy('custom_field_date_1'))
    custom_field_date_2 = models.DateField(null=True, blank=True, verbose_name=gettext_lazy('custom_field_date_2'))
    custom_field_date_3 = models.DateField(null=True, blank=True, verbose_name=gettext_lazy('custom_field_date_3'))
    custom_field_date_4 = models.DateField(null=True, blank=True, verbose_name=gettext_lazy('custom_field_date_4'))
    custom_field_date_5 = models.DateField(null=True, blank=True, verbose_name=gettext_lazy('custom_field_date_5'))

    class Meta:
        verbose_name = gettext_lazy('balance report instance item')
        verbose_name_plural = gettext_lazy('balance reports instance item')


class PLReportInstance(DataTimeStampedModel, NamedModel):
    master_user = models.ForeignKey(MasterUser,
                                    verbose_name=gettext_lazy('master user'), on_delete=models.CASCADE)

    member = models.ForeignKey(Member,
                               verbose_name=gettext_lazy('member'), on_delete=models.CASCADE)

    report_date = models.DateField(db_index=True, verbose_name=gettext_lazy('report date'))
    pl_first_date = models.DateField(db_index=True, verbose_name=gettext_lazy('pl first date'))

    report_currency = models.ForeignKey('currencies.Currency', on_delete=models.CASCADE,
                                        verbose_name=gettext_lazy('report currency'))

    pricing_policy = models.ForeignKey(PricingPolicy, on_delete=models.CASCADE, null=True, blank=True,
                                       verbose_name=gettext_lazy('pricing policy'))

    cost_method = models.ForeignKey(CostMethod, on_delete=models.CASCADE, null=True, blank=True,
                                    verbose_name=gettext_lazy('cost method'))

    report_settings_data = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('report settings data'))

    report_uuid = models.CharField(max_length=255, null=True, blank=True, verbose_name=gettext_lazy('report uuid'))


class PLReportInstanceItem(models.Model):
    report_instance = models.ForeignKey(PLReportInstance, related_name="items",
                                        verbose_name=gettext_lazy('report instance'), on_delete=models.CASCADE)

    master_user = models.ForeignKey(MasterUser,
                                    verbose_name=gettext_lazy('master user'), on_delete=models.CASCADE)

    member = models.ForeignKey(Member,
                               verbose_name=gettext_lazy('member'), on_delete=models.CASCADE)

    report_date = models.DateField(db_index=True, verbose_name=gettext_lazy('report date'))
    pl_first_date = models.DateField(db_index=True, verbose_name=gettext_lazy('pl first date'))

    report_currency = models.ForeignKey('currencies.Currency', on_delete=models.CASCADE,
                                        verbose_name=gettext_lazy('report currency'))

    pricing_policy = models.ForeignKey(PricingPolicy, on_delete=models.CASCADE, null=True, blank=True,
                                       verbose_name=gettext_lazy('pricing policy'))

    cost_method = models.ForeignKey(CostMethod, on_delete=models.CASCADE, null=True, blank=True,
                                    verbose_name=gettext_lazy('cost method'))

    report_settings_data = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('report settings data'))

    name = models.CharField(max_length=255, null=True, blank=True, verbose_name=gettext_lazy('name'))
    short_name = models.CharField(max_length=255, null=True, blank=True, verbose_name=gettext_lazy('short name'))
    user_code = models.CharField(max_length=255, null=True, blank=True, verbose_name=gettext_lazy('user code'))

    portfolio = models.ForeignKey('portfolios.Portfolio', null=True, blank=True, on_delete=models.SET_NULL,
                                  verbose_name=gettext_lazy('portfolio'))

    instrument = models.ForeignKey('instruments.Instrument', null=True, blank=True, on_delete=models.SET_NULL,
                                   verbose_name=gettext_lazy('instrument'))

    currency = models.ForeignKey('currencies.Currency', null=True, blank=True, on_delete=models.SET_NULL,
                                 related_name="pl_report_instance_item_currency",
                                 verbose_name=gettext_lazy('currency'))
    pricing_currency = models.ForeignKey('currencies.Currency', null=True, blank=True, on_delete=models.SET_NULL,
                                         related_name="pl_report_instance_item_pricing_currency",
                                         verbose_name=gettext_lazy('pricing currency'))
    exposure_currency = models.ForeignKey('currencies.Currency', null=True, blank=True, on_delete=models.SET_NULL,
                                          related_name="pl_report_instance_item_exposure_currency",
                                          verbose_name=gettext_lazy('exposure currency'))
    account = models.ForeignKey('accounts.Account', null=True, blank=True, on_delete=models.SET_NULL,
                                verbose_name=gettext_lazy('account'))
    strategy1 = models.ForeignKey('strategies.Strategy1', null=True, blank=True, on_delete=models.SET_NULL,
                                  verbose_name=gettext_lazy('strategy1'))
    strategy2 = models.ForeignKey('strategies.Strategy2', null=True, blank=True, on_delete=models.SET_NULL,
                                  verbose_name=gettext_lazy('strategy2'))
    strategy3 = models.ForeignKey('strategies.Strategy3', null=True, blank=True, on_delete=models.SET_NULL,
                                  verbose_name=gettext_lazy('strategy3'))

    item_id = models.CharField(max_length=255, null=True, blank=True, verbose_name=gettext_lazy('item id'))
    item_type = models.IntegerField(default=0, verbose_name=gettext_lazy('portfolio'))
    item_type_name = models.CharField(max_length=255, null=True, blank=True,
                                      verbose_name=gettext_lazy('item type name'))

    custom_field_text_1 = models.CharField(max_length=255, null=True, blank=True,
                                           verbose_name=gettext_lazy('custom_field_text_1'))
    custom_field_text_2 = models.CharField(max_length=255, null=True, blank=True,
                                           verbose_name=gettext_lazy('custom_field_text_2'))
    custom_field_text_3 = models.CharField(max_length=255, null=True, blank=True,
                                           verbose_name=gettext_lazy('custom_field_text_3'))
    custom_field_text_4 = models.CharField(max_length=255, null=True, blank=True,
                                           verbose_name=gettext_lazy('custom_field_text_4'))
    custom_field_text_5 = models.CharField(max_length=255, null=True, blank=True,
                                           verbose_name=gettext_lazy('custom_field_text_5'))

    custom_field_number_1 = models.FloatField(default=0.0, null=True, blank=True,
                                              verbose_name=gettext_lazy('custom_field_number_1'))
    custom_field_number_2 = models.FloatField(default=0.0, null=True, blank=True,
                                              verbose_name=gettext_lazy('custom_field_number_2'))
    custom_field_number_3 = models.FloatField(default=0.0, null=True, blank=True,
                                              verbose_name=gettext_lazy('custom_field_number_3'))
    custom_field_number_4 = models.FloatField(default=0.0, null=True, blank=True,
                                              verbose_name=gettext_lazy('custom_field_number_4'))
    custom_field_number_5 = models.FloatField(default=0.0, null=True, blank=True,
                                              verbose_name=gettext_lazy('custom_field_number_5'))

    custom_field_date_1 = models.DateField(null=True, blank=True, verbose_name=gettext_lazy('custom_field_date_1'))
    custom_field_date_2 = models.DateField(null=True, blank=True, verbose_name=gettext_lazy('custom_field_date_2'))
    custom_field_date_3 = models.DateField(null=True, blank=True, verbose_name=gettext_lazy('custom_field_date_3'))
    custom_field_date_4 = models.DateField(null=True, blank=True, verbose_name=gettext_lazy('custom_field_date_4'))
    custom_field_date_5 = models.DateField(null=True, blank=True, verbose_name=gettext_lazy('custom_field_date_5'))

    class Meta:
        verbose_name = gettext_lazy('pl report instance item')
        verbose_name_plural = gettext_lazy('pl reports instance item')


class PerformanceReportInstance(DataTimeStampedModel, NamedModel):
    master_user = models.ForeignKey(MasterUser,
                                    verbose_name=gettext_lazy('master user'), on_delete=models.CASCADE)

    member = models.ForeignKey(Member,
                               verbose_name=gettext_lazy('member'), on_delete=models.CASCADE)

    begin_date = models.DateField(db_index=True, verbose_name=gettext_lazy('begin date'))
    end_date = models.DateField(db_index=True, verbose_name=gettext_lazy('end date'))

    report_currency = models.ForeignKey('currencies.Currency', on_delete=models.CASCADE,
                                        verbose_name=gettext_lazy('report currency'))

    calculation_type = models.CharField(max_length=255, null=True, blank=True,
                                        verbose_name=gettext_lazy('calculation type'))
    segmentation_type = models.CharField(max_length=255, null=True, blank=True,
                                         verbose_name=gettext_lazy('segmentation type'))
    registers = models.CharField(max_length=255, null=True, blank=True, verbose_name=gettext_lazy('registers'))
    registers_names = models.CharField(max_length=255, null=True, blank=True,
                                       verbose_name=gettext_lazy('registers names'))

    report_settings_data = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('report settings data'))

    report_uuid = models.CharField(max_length=255, null=True, blank=True, verbose_name=gettext_lazy('report uuid'))

    begin_nav = models.FloatField(default=0.0, null=True, blank=True, verbose_name=gettext_lazy('begin nav'))
    end_nav = models.FloatField(default=0.0, null=True, blank=True, verbose_name=gettext_lazy('end nav'))
    grand_return = models.FloatField(default=0.0, null=True, blank=True, verbose_name=gettext_lazy('grand return'))
    grand_cash_flow = models.FloatField(default=0.0, null=True, blank=True,
                                        verbose_name=gettext_lazy('grand cash flow'))
    grand_cash_inflow = models.FloatField(default=0.0, null=True, blank=True,
                                          verbose_name=gettext_lazy('grand cash inflow'))
    grand_cash_outflow = models.FloatField(default=0.0, null=True, blank=True,
                                           verbose_name=gettext_lazy('grand cash outflow'))
    grand_nav = models.FloatField(default=0.0, null=True, blank=True, verbose_name=gettext_lazy('grand nav'))


class PerformanceReportInstanceItem(models.Model):
    report_instance = models.ForeignKey(PerformanceReportInstance, related_name="items",
                                        verbose_name=gettext_lazy('report instance'), on_delete=models.CASCADE)

    master_user = models.ForeignKey(MasterUser,
                                    verbose_name=gettext_lazy('master user'), on_delete=models.CASCADE)

    member = models.ForeignKey(Member,
                               verbose_name=gettext_lazy('member'), on_delete=models.CASCADE)

    begin_date = models.DateField(db_index=True, verbose_name=gettext_lazy('begin date'))
    end_date = models.DateField(db_index=True, verbose_name=gettext_lazy('end date'))

    report_currency = models.ForeignKey('currencies.Currency', on_delete=models.CASCADE,
                                        verbose_name=gettext_lazy('report currency'))

    calculation_type = models.CharField(max_length=255, null=True, blank=True,
                                        verbose_name=gettext_lazy('calculation type'))
    segmentation_type = models.CharField(max_length=255, null=True, blank=True,
                                         verbose_name=gettext_lazy('segmentation type'))

    registers = models.CharField(max_length=255, null=True, blank=True, verbose_name=gettext_lazy('registers'))
    registers_names = models.CharField(max_length=255, null=True, blank=True,
                                       verbose_name=gettext_lazy('registers names'))

    report_settings_data = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('report settings data'))

    date_from = models.DateField(db_index=True, verbose_name=gettext_lazy('date from'))
    date_to = models.DateField(db_index=True, verbose_name=gettext_lazy('date to'))

    begin_nav = models.FloatField(default=0.0, null=True, blank=True, verbose_name=gettext_lazy('begin nav'))
    end_nav = models.FloatField(default=0.0, null=True, blank=True, verbose_name=gettext_lazy('end nav'))
    cash_flow = models.FloatField(default=0.0, null=True, blank=True, verbose_name=gettext_lazy('cash flow'))
    cash_inflow = models.FloatField(default=0.0, null=True, blank=True, verbose_name=gettext_lazy('cash inflow'))
    cash_outflow = models.FloatField(default=0.0, null=True, blank=True, verbose_name=gettext_lazy('cash outflow'))
    nav = models.FloatField(default=0.0, null=True, blank=True, verbose_name=gettext_lazy('nav'))
    instrument_return = models.FloatField(default=0.0, null=True, blank=True,
                                          verbose_name=gettext_lazy('instrument return'))
    cumulative_return = models.FloatField(default=0.0, null=True, blank=True,
                                          verbose_name=gettext_lazy('cumulative return'))

    class Meta:
        verbose_name = gettext_lazy('performance report instance item')
        verbose_name_plural = gettext_lazy('performance reports instance item')


class ReportSummary():

    def __init__(self, date_from, date_to, portfolios, bundles, currency, master_user, member, context):

        self.ecosystem_defaults = EcosystemDefault.objects.get(master_user=master_user)

        self.context = context
        self.master_user = master_user
        self.member = member

        self.date_from = date_from
        self.date_to = date_to

        self.currency = currency
        self.portfolios = portfolios
        self.bundles = bundles

        self.portfolio_ids = []

        for portfolio in self.portfolios:
            self.portfolio_ids.append(portfolio.id)

    def build_balance(self):

        st = time.perf_counter()

        from poms.reports.serializers import BalanceReportSerializer

        serializer = BalanceReportSerializer(data={
            "report_date": self.date_to,
            "pricing_policy": self.ecosystem_defaults.pricing_policy_id,
            "report_currency": self.currency.id,
            "portfolios": self.portfolio_ids,
            "cost_method": CostMethod.AVCO,
            "only_numbers": True
        }, context=self.context)

        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        from poms.reports.sql_builders.balance import BalanceReportBuilderSql
        self.balance_report = BalanceReportBuilderSql(instance=instance).build_balance()

        _l.info('ReportSummary.build_balance done: %s' % "{:3.3f}".format(time.perf_counter() - st))

    def build_pl_daily(self):

        st = time.perf_counter()

        from poms.reports.serializers import PLReportSerializer

        serializer = PLReportSerializer(data={
            "pl_first_date": self.date_to - timedelta(days=1),
            "report_date": self.date_to,
            "pricing_policy": self.ecosystem_defaults.pricing_policy_id,
            "report_currency": self.currency.id,
            "portfolios": self.portfolio_ids,
            "cost_method": CostMethod.AVCO
        }, context=self.context)

        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        from poms.reports.sql_builders.pl import PLReportBuilderSql
        self.pl_report_daily = PLReportBuilderSql(instance=instance).build_report()

        _l.info('ReportSummary.build_pl_daily done: %s' % "{:3.3f}".format(time.perf_counter() - st))

    def build_pl_mtd(self):

        st = time.perf_counter()

        from poms.reports.serializers import PLReportSerializer

        serializer = PLReportSerializer(data={
            "pl_first_date": self.date_to - timedelta(days=30),
            "report_date": self.date_to,
            "pricing_policy": self.ecosystem_defaults.pricing_policy_id,
            "report_currency": self.currency.id,
            "portfolios": self.portfolio_ids,
            "cost_method": CostMethod.AVCO
        }, context=self.context)

        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        _l.info('build_pl_mtd.instance.pl_first_date %s' % instance.pl_first_date)
        _l.info('build_pl_mtd.instance.report_date %s' % instance.report_date)

        from poms.reports.sql_builders.pl import PLReportBuilderSql
        self.pl_report_mtd = PLReportBuilderSql(instance=instance).build_report()

        _l.info('ReportSummary.build_pl_mtd done: %s' % "{:3.3f}".format(time.perf_counter() - st))

    def build_pl_ytd(self):

        st = time.perf_counter()

        from poms.reports.serializers import PLReportSerializer

        serializer = PLReportSerializer(data={
            "pl_first_date": self.date_to - timedelta(days=365),
            "report_date": self.date_to,
            "pricing_policy": self.ecosystem_defaults.pricing_policy_id,
            "report_currency": self.currency.id,
            "portfolios": self.portfolio_ids,
            "cost_method": CostMethod.AVCO
        }, context=self.context)

        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        from poms.reports.sql_builders.pl import PLReportBuilderSql
        self.pl_report_ytd = PLReportBuilderSql(instance=instance).build_report()

        _l.info('ReportSummary.build_pl_ytd done: %s' % "{:3.3f}".format(time.perf_counter() - st))

    def build_pl_inception_to_date(self):

        st = time.perf_counter()

        from poms.reports.serializers import PLReportSerializer

        serializer = PLReportSerializer(data={
            "pl_first_date": self.date_to - timedelta(days=365000),
            "report_date": self.date_to,
            "pricing_policy": self.ecosystem_defaults.pricing_policy_id,
            "report_currency": self.currency.id,
            "portfolios": self.portfolio_ids,
            "cost_method": CostMethod.AVCO
        }, context=self.context)

        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        from poms.reports.sql_builders.pl import PLReportBuilderSql
        self.pl_report_inception_to_date = PLReportBuilderSql(instance=instance).build_report()

        _l.info('ReportSummary.build_pl_inception_to_date done: %s' % "{:3.3f}".format(time.perf_counter() - st))

    def get_nav(self, portfolio_id=None):

        nav = 0

        if portfolio_id:

            for item in self.balance_report.items:
                if item['portfolio_id'] == portfolio_id:
                    if item['market_value']:
                        nav = nav + item['market_value']

        else:

            for item in self.balance_report.items:
                if item['market_value']:
                    nav = nav + item['market_value']

        return nav

    def get_total_pl_daily(self, portfolio_id=None):

        total = 0

        if portfolio_id:

            for item in self.pl_report_daily.items:
                if item['portfolio_id'] == portfolio_id:
                    if item['total']:
                        total = total + item['total']

        else:

            for item in self.pl_report_daily.items:
                if item['total']:
                    total = total + item['total']

        return total

    def get_total_position_return_pl_daily(self, portfolio_id=None):

        total = 0
        market_value = 0

        if portfolio_id:

            for item in self.pl_report_daily.items:
                if item['portfolio_id'] == portfolio_id:
                    if item['total']:
                        total = total + item['total']

                    if item['market_value']:
                        total = market_value + item['market_value']

        else:

            for item in self.pl_report_daily.items:
                if item['total']:
                    total = total + item['total']

                if item['market_value']:
                    market_value = market_value + item['market_value']

        if market_value:
            return math.floor(total / market_value * 10000) / 100 # TODO refactor
        return 0

    def get_total_pl_mtd(self, portfolio_id=None):

        total = 0

        if portfolio_id:

            for item in self.pl_report_mtd.items:
                if item['portfolio_id'] == portfolio_id:
                    if item['total']:
                        total = total + item['total']

        else:

            for item in self.pl_report_mtd.items:
                if item['total']:
                    total = total + item['total']

        return total

    def get_total_position_return_pl_mtd(self, portfolio_id=None):
        # position_return = 0

        total = 0
        market_value = 0

        if portfolio_id:

            for item in self.pl_report_mtd.items:
                if item['portfolio_id'] == portfolio_id:
                    if item['total']:
                        total = total + item['total']

                    if item['market_value']:
                        market_value = market_value + item['market_value']

        else:

            for item in self.pl_report_mtd.items:
                if item['total']:
                    total = total + item['total']

                if item['market_value']:
                    market_value = market_value + item['market_value']

        if market_value:
            return math.floor(total / market_value * 10000) / 100 # TODO refactor
        return 0

    def get_total_pl_ytd(self, portfolio_id=None):

        total = 0

        if portfolio_id:

            for item in self.pl_report_ytd.items:

                if item['portfolio_id'] == portfolio_id:
                    if item['total']:
                        total = total + item['total']

        else:

            for item in self.pl_report_ytd.items:
                if item['total']:
                    total = total + item['total']

        return total

    def get_total_position_return_pl_ytd(self, portfolio_id=None):
        # position_return = 0

        total = 0
        market_value = 0

        if portfolio_id:

            for item in self.pl_report_ytd.items:
                if item['portfolio_id'] == portfolio_id:
                    if item['total']:
                        total = total + item['total']

                    if item['market_value']:
                        market_value = market_value + item['market_value']

        else:

            for item in self.pl_report_ytd.items:

                if item['total']:
                    total = total + item['total']

                if item['market_value']:
                    market_value = market_value + item['market_value']

        if market_value:
            return math.floor(total / market_value * 10000) / 100 # TODO refactor
        return 0

    def get_total_pl_inception_to_date(self, portfolio_id=None):

        total = 0

        if portfolio_id:

            for item in self.pl_report_inception_to_date.items:

                if item['portfolio_id'] == portfolio_id:
                    if item['total']:
                        total = total + item['total']

        else:

            for item in self.pl_report_inception_to_date.items:
                if item['total']:
                    total = total + item['total']

        return total

    def get_total_position_return_pl_inception_to_date(self, portfolio_id=None):
        position_return = 0

        if portfolio_id:

            for item in self.pl_report_inception_to_date.items:
                if item['portfolio_id'] == portfolio_id:
                    if item['position_return']:
                        position_return = position_return + item['position_return']

        else:

            for item in self.pl_report_inception_to_date.items:
                if item['position_return']:
                    position_return = position_return + item['position_return']

        return position_return
