import json

from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy

from poms.common.models import EXPRESSION_FIELD_LENGTH
from poms.users.models import MasterUser

from django.core.serializers.json import DjangoJSONEncoder


class InstrumentPricingSchemeType(models.Model):

    NONE = 1
    SINGLE_PARAMETER = 2
    MULTIPLE_PARAMETERS = 3

    INPUT_TYPE_CHOICES = (
        (NONE, ugettext_lazy('None')),
        (SINGLE_PARAMETER, ugettext_lazy('Single Parameter')),
        (MULTIPLE_PARAMETERS, ugettext_lazy('Multiple Parameters')),
    )

    name = models.CharField(max_length=255)
    notes = models.TextField(blank=True, default='', verbose_name=ugettext_lazy('notes'))
    input_type = models.PositiveSmallIntegerField(default=NONE, choices=INPUT_TYPE_CHOICES,
                                                  verbose_name=ugettext_lazy('input type'))


class InstrumentPricingScheme(models.Model):

    SKIP = 1
    DEFAULT_PRICE = 2
    ASK_FOR_MANUAL_ENTRY = 3
    ADD_TO_PRICING_LOG = 4

    ERROR_HANDLER_CHOICES = (
        (SKIP, ugettext_lazy('Skip')),
        (DEFAULT_PRICE, ugettext_lazy('Default Price')),
        (ASK_FOR_MANUAL_ENTRY, ugettext_lazy('Ask For Manual Entry')),
        (ADD_TO_PRICING_LOG, ugettext_lazy('Add to Pricing Log')),
    )

    name = models.CharField(max_length=255)
    master_user = models.ForeignKey('users.MasterUser', verbose_name=ugettext_lazy('master user'),
                                    on_delete=models.CASCADE)
    notes = models.TextField(blank=True, default='', verbose_name=ugettext_lazy('notes'))

    notes_for_user = models.TextField(blank=True, default='', verbose_name=ugettext_lazy('notes for user'))

    error_handler = models.PositiveSmallIntegerField(default=SKIP, choices=ERROR_HANDLER_CHOICES,
                                                     verbose_name=ugettext_lazy('error handler'))

    type = models.ForeignKey(InstrumentPricingSchemeType, null=True, blank=True, verbose_name=ugettext_lazy('type'), on_delete=models.SET_NULL)

    class Meta:
        unique_together = (
            ('name', 'master_user')
        )

    def __str__(self):
        return self.name


class CurrencyPricingSchemeType(models.Model):

    NONE = 1
    SINGLE_PARAMETER = 2
    MULTIPLE_PARAMETERS = 3

    INPUT_TYPE_CHOICES = (
        (NONE, ugettext_lazy('None')),
        (SINGLE_PARAMETER, ugettext_lazy('Single Parameter')),
        (MULTIPLE_PARAMETERS, ugettext_lazy('Multiple Parameters')),
    )

    name = models.CharField(max_length=255)
    notes = models.TextField(blank=True, default='', verbose_name=ugettext_lazy('notes'))
    input_type = models.PositiveSmallIntegerField(default=NONE, choices=INPUT_TYPE_CHOICES,
                                                  verbose_name=ugettext_lazy('input type'))


class CurrencyPricingScheme(models.Model):
    SKIP = 1
    DEFAULT_PRICE = 2
    ASK_FOR_MANUAL_ENTRY = 3
    ADD_TO_PRICING_LOG = 4

    ERROR_HANDLER_CHOICES = (
        (SKIP, ugettext_lazy('Skip')),
        (DEFAULT_PRICE, ugettext_lazy('Default Price')),
        (ASK_FOR_MANUAL_ENTRY, ugettext_lazy('Ask For Manual Entry')),
        (ADD_TO_PRICING_LOG, ugettext_lazy('Add to Pricing Log')),
    )

    name = models.CharField(max_length=255)
    master_user = models.ForeignKey('users.MasterUser', verbose_name=ugettext_lazy('master user'),
                                    on_delete=models.CASCADE)
    notes = models.TextField(blank=True, default='', verbose_name=ugettext_lazy('notes'))

    notes_for_user = models.TextField(blank=True, default='', verbose_name=ugettext_lazy('notes for user'))

    error_handler = models.PositiveSmallIntegerField(default=SKIP, choices=ERROR_HANDLER_CHOICES,
                                                     verbose_name=ugettext_lazy('error handler'))

    type = models.ForeignKey(CurrencyPricingSchemeType, null=True, blank=True, verbose_name=ugettext_lazy('type'), on_delete=models.CASCADE)

    class Meta:
        unique_together = (
            ('name', 'master_user')
        )

    def __str__(self):
        return self.name


class InstrumentPricingSchemeManualPricingParameters(models.Model):

    instrument_pricing_scheme = models.ForeignKey(InstrumentPricingScheme, verbose_name=ugettext_lazy('Instrument Pricing Scheme'), on_delete=models.CASCADE)

    default_value = models.CharField(max_length=255, null=True, blank=True)
    attribute_key = models.CharField(max_length=255, null=True, blank=True)


class CurrencyPricingSchemeManualPricingParameters(models.Model):

    currency_pricing_scheme = models.ForeignKey(CurrencyPricingScheme, verbose_name=ugettext_lazy('Currency Pricing Scheme'), on_delete=models.CASCADE)

    default_value = models.CharField(max_length=255, null=True, blank=True)

    attribute_key = models.CharField(max_length=255, null=True, blank=True)


class InstrumentPricingSchemeSingleParameterFormulaParameters(models.Model):

    STRING = 10
    NUMBER = 20
    DATE = 40

    TYPES = (
        (NUMBER, ugettext_lazy('Number')),
        (STRING, ugettext_lazy('String')),
        (DATE, ugettext_lazy('Date')),
    )

    instrument_pricing_scheme = models.ForeignKey(InstrumentPricingScheme, verbose_name=ugettext_lazy('Instrument Pricing Scheme'), on_delete=models.CASCADE)

    expr = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                            verbose_name=ugettext_lazy('expr'))

    default_value = models.CharField(max_length=255, null=True, blank=True)
    attribute_key = models.CharField(max_length=255, null=True, blank=True)
    value_type = models.PositiveSmallIntegerField(default=STRING, choices=TYPES,
                                                  verbose_name=ugettext_lazy('value type'))


class CurrencyPricingSchemeSingleParameterFormulaParameters(models.Model):

    STRING = 10
    NUMBER = 20
    DATE = 40

    TYPES = (
        (NUMBER, ugettext_lazy('Number')),
        (STRING, ugettext_lazy('String')),
        (DATE, ugettext_lazy('Date')),
    )

    currency_pricing_scheme = models.ForeignKey(CurrencyPricingScheme, verbose_name=ugettext_lazy('Currency Pricing Scheme'), on_delete=models.CASCADE)

    expr = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                            verbose_name=ugettext_lazy('expr'))

    default_value = models.CharField(max_length=255, null=True, blank=True)
    attribute_key = models.CharField(max_length=255, null=True, blank=True)
    value_type = models.PositiveSmallIntegerField(default=STRING, choices=TYPES,
                                                  verbose_name=ugettext_lazy('value type'))


class InstrumentPricingSchemeMultipleParametersFormulaParameters(models.Model):

    instrument_pricing_scheme = models.ForeignKey(InstrumentPricingScheme, verbose_name=ugettext_lazy('Instrument Pricing Scheme'), on_delete=models.CASCADE)

    expr = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                            verbose_name=ugettext_lazy('expr'))

    json_data = models.TextField(null=True, blank=True, verbose_name=ugettext_lazy('json data'))

    @property
    def data(self):
        if self.json_data:
            try:
                return json.loads(self.json_data)
            except (ValueError, TypeError):
                return None
        else:
            return None

    @data.setter
    def data(self, val):
        if val:
            self.json_data = json.dumps(val, cls=DjangoJSONEncoder, sort_keys=True)
        else:
            self.json_data = None


class CurrencyPricingSchemeMultipleParametersFormulaParameters(models.Model):

    currency_pricing_scheme = models.ForeignKey(CurrencyPricingScheme, verbose_name=ugettext_lazy('Currency Pricing Scheme'), on_delete=models.CASCADE)

    expr = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                            verbose_name=ugettext_lazy('expr'))

    json_data = models.TextField(null=True, blank=True, verbose_name=ugettext_lazy('json data'))

    @property
    def data(self):
        if self.json_data:
            try:
                return json.loads(self.json_data)
            except (ValueError, TypeError):
                return None
        else:
            return None

    @data.setter
    def data(self, val):
        if val:
            self.json_data = json.dumps(val, cls=DjangoJSONEncoder, sort_keys=True)
        else:
            self.json_data = None


class InstrumentPricingSchemeBloombergParameters(models.Model):

    STRING = 10
    NUMBER = 20
    DATE = 40

    TYPES = (
        (NUMBER, ugettext_lazy('Number')),
        (STRING, ugettext_lazy('String')),
        (DATE, ugettext_lazy('Date')),
    )

    instrument_pricing_scheme = models.ForeignKey(InstrumentPricingScheme, verbose_name=ugettext_lazy('Instrument Pricing Scheme'), on_delete=models.CASCADE)

    expr = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                            verbose_name=ugettext_lazy('expr'))

    default_value = models.CharField(max_length=255, null=True, blank=True)
    attribute_key = models.CharField(max_length=255, null=True, blank=True)
    value_type = models.PositiveSmallIntegerField(default=STRING, choices=TYPES,
                                                  verbose_name=ugettext_lazy('value type'))

    bid0 = models.CharField(max_length=50, blank=True, null=True, verbose_name=ugettext_lazy('bid0'))
    bid1 = models.CharField(max_length=50, blank=True, null=True, verbose_name=ugettext_lazy('bid1'))
    bid0_multiplier = models.FloatField(default=1.0, null=True, verbose_name=ugettext_lazy('bid 0 multiplier'))
    bid1_multiplier = models.FloatField(default=1.0, null=True, verbose_name=ugettext_lazy('bid 1 multiplier'))

    ask0 = models.CharField(max_length=50, blank=True, null=True, verbose_name=ugettext_lazy('ask0'))
    ask1 = models.CharField(max_length=50, blank=True, null=True, verbose_name=ugettext_lazy('ask1'))
    ask0_multiplier = models.FloatField(default=1.0, null=True, verbose_name=ugettext_lazy('ask 0 multiplier'))
    ask1_multiplier = models.FloatField(default=1.0, null=True, verbose_name=ugettext_lazy('ask 1 multiplier'))

    last0 = models.CharField(max_length=50, blank=True, null=True, verbose_name=ugettext_lazy('last0'))
    last1 = models.CharField(max_length=50, blank=True, null=True, verbose_name=ugettext_lazy('last1'))
    last0_multiplier = models.FloatField(default=1.0, null=True, verbose_name=ugettext_lazy('last 0 multiplier'))
    last1_multiplier = models.FloatField(default=1.0, null=True, verbose_name=ugettext_lazy('last 1 multiplier'))


class CurrencyPricingSchemeBloombergParameters(models.Model):

    STRING = 10
    NUMBER = 20
    DATE = 40

    TYPES = (
        (NUMBER, ugettext_lazy('Number')),
        (STRING, ugettext_lazy('String')),
        (DATE, ugettext_lazy('Date')),
    )

    currency_pricing_scheme = models.ForeignKey(CurrencyPricingScheme, verbose_name=ugettext_lazy('Currency Pricing Scheme'), on_delete=models.CASCADE)

    expr = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                            verbose_name=ugettext_lazy('expr'))

    default_value = models.CharField(max_length=255, null=True, blank=True)
    attribute_key = models.CharField(max_length=255, null=True, blank=True)
    value_type = models.PositiveSmallIntegerField(default=STRING, choices=TYPES,
                                                  verbose_name=ugettext_lazy('value type'))

    fxrate = models.CharField(max_length=50, blank=True, verbose_name=ugettext_lazy('FX-rate'))
    fxrate_multiplier = models.FloatField(default=1.0,
                                                   verbose_name=ugettext_lazy('FX-rate multiplier'))


class PricingProcedure(models.Model):

    name = models.CharField(max_length=255)
    master_user = models.ForeignKey('users.MasterUser', verbose_name=ugettext_lazy('master user'),
                                    on_delete=models.CASCADE)
    notes = models.TextField(blank=True, default='', verbose_name=ugettext_lazy('notes'))

    notes_for_users = models.TextField(blank=True, default='', verbose_name=ugettext_lazy('notes for user'))

    price_date_from = models.DateField(null=True, blank=True, verbose_name=ugettext_lazy('price date from'))
    price_date_to = models.DateField(null=True, blank=True, verbose_name=ugettext_lazy('price date to'))

    price_balance_date = models.DateField(null=True, blank=True, verbose_name=ugettext_lazy('price balance date'))

    price_fill_days = models.PositiveSmallIntegerField(default=0, verbose_name=ugettext_lazy('price fill days'))
    price_override_existed = models.BooleanField(default=True, verbose_name=ugettext_lazy('price override existed'))

    accrual_date_from = models.DateField(null=True, blank=True, verbose_name=ugettext_lazy('accrual date from'))
    accrual_date_to = models.DateField(null=True, blank=True, verbose_name=ugettext_lazy('accrual date to'))

    class Meta:
        unique_together = (
            ('name', 'master_user')
        )

    def __str__(self):
        return self.name
