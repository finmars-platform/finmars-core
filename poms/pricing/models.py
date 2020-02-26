import json

from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy

from poms.common.models import EXPRESSION_FIELD_LENGTH, NamedModel
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


class InstrumentPricingScheme(NamedModel):

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

    notes_for_users = models.TextField(blank=True, default='', verbose_name=ugettext_lazy('notes for users'))

    notes_for_parameter = models.TextField(blank=True, default='', verbose_name=ugettext_lazy('notes for parameter'))

    error_handler = models.PositiveSmallIntegerField(default=SKIP, choices=ERROR_HANDLER_CHOICES,
                                                     verbose_name=ugettext_lazy('error handler'))

    type = models.ForeignKey(InstrumentPricingSchemeType, verbose_name=ugettext_lazy('type'), on_delete=models.CASCADE)

    class Meta:
        unique_together = (
            ('name', 'master_user')
        )

    def __str__(self):
        return self.name

    def get_parameters(self):

        result = None

        # print('self.type %s' % self.type)

        if self.type:

            if self.type.id == 2:  # manual pricing scheme

                try:

                    result = InstrumentPricingSchemeManualPricingParameters.objects.get(instrument_pricing_scheme=self)

                except InstrumentPricingSchemeManualPricingParameters.DoesNotExist:
                    pass

            if self.type.id == 3:  # single parameter formula

                try:

                    result = InstrumentPricingSchemeSingleParameterFormulaParameters.objects.get(instrument_pricing_scheme=self)

                # except InstrumentPricingSchemeSingleParameterFormulaParameters.DoesNotExist:
                except Exception as e:
                    print(e)

                    result = None

            if self.type.id == 4:  # multiple parameters formula

                try:

                    result = InstrumentPricingSchemeMultipleParametersFormulaParameters.objects.get(instrument_pricing_scheme=self)

                except (InstrumentPricingSchemeMultipleParametersFormulaParameters.DoesNotExist, Exception) as e:

                    print('Instrument Multiple Parameter Formula Parameters error %s' % e)

                    result = None

            if self.type.id == 5:  # bloomberg

                try:

                    result = InstrumentPricingSchemeBloombergParameters.objects.get(instrument_pricing_scheme=self)

                except InstrumentPricingSchemeBloombergParameters.DoesNotExist:

                    result = None

        # print('result %s' % result)

        return result


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


class CurrencyPricingScheme(NamedModel):
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

    notes_for_users = models.TextField(blank=True, default='', verbose_name=ugettext_lazy('notes for users'))

    notes_for_parameter = models.TextField(blank=True, default='', verbose_name=ugettext_lazy('notes for parameter'))

    error_handler = models.PositiveSmallIntegerField(default=SKIP, choices=ERROR_HANDLER_CHOICES,
                                                     verbose_name=ugettext_lazy('error handler'))

    type = models.ForeignKey(CurrencyPricingSchemeType, verbose_name=ugettext_lazy('type'), on_delete=models.CASCADE)

    class Meta:
        unique_together = (
            ('name', 'master_user')
        )

    def __str__(self):
        return self.name

    def get_parameters(self):

        result = None

        # print('self.type %s' % self.type)

        if self.type:

            if self.type.id == 2:  # manual pricing scheme

                try:

                    result = CurrencyPricingSchemeManualPricingParameters.objects.get(currency_pricing_scheme=self)

                except CurrencyPricingSchemeManualPricingParameters.DoesNotExist:
                    pass

            if self.type.id == 3:  # single parameter formula

                try:

                    result = CurrencyPricingSchemeSingleParameterFormulaParameters.objects.get(currency_pricing_scheme=self)

                except CurrencyPricingSchemeSingleParameterFormulaParameters.DoesNotExist:

                    result = None

            if self.type.id == 4:  # multiple parameters formula

                try:

                    result = CurrencyPricingSchemeMultipleParametersFormulaParameters.objects.get(currency_pricing_scheme=self)

                except CurrencyPricingSchemeMultipleParametersFormulaParameters.DoesNotExist:

                    result = None

            if self.type.id == 5:  # bloomberg

                try:

                    result = CurrencyPricingSchemeBloombergParameters.objects.get(currency_pricing_scheme=self)

                except CurrencyPricingSchemeBloombergParameters.DoesNotExist:

                    result = None

        # print('result %s' % result)

        return result


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

    bid_historical = models.CharField(max_length=50, blank=True, null=True, verbose_name=ugettext_lazy('bid historical'))
    bid_yesterday = models.CharField(max_length=50, blank=True, null=True, verbose_name=ugettext_lazy('bid yesterday'))

    ask_historical = models.CharField(max_length=50, blank=True, null=True, verbose_name=ugettext_lazy('ask historical'))
    ask_yesterday = models.CharField(max_length=50, blank=True, null=True, verbose_name=ugettext_lazy('ask yesterday'))

    last_historical = models.CharField(max_length=50, blank=True, null=True, verbose_name=ugettext_lazy('last historical'))
    last_yesterday = models.CharField(max_length=50, blank=True, null=True, verbose_name=ugettext_lazy('last yesterday'))



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


class PricingProcedure(NamedModel):

    name = models.CharField(max_length=255)
    master_user = models.ForeignKey('users.MasterUser', verbose_name=ugettext_lazy('master user'),
                                    on_delete=models.CASCADE)
    notes = models.TextField(blank=True, default='', verbose_name=ugettext_lazy('notes'))

    notes_for_users = models.TextField(blank=True, default='', verbose_name=ugettext_lazy('notes for user'))

    # DEPRECATED since 21.02.2020
    # price_is_active = models.BooleanField(default=False, verbose_name=ugettext_lazy('price is active'))

    price_date_from = models.DateField(null=True, blank=True, verbose_name=ugettext_lazy('price date from'))

    price_date_from_expr = models.CharField(null=True, max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                            verbose_name=ugettext_lazy('price date from expr'))

    price_date_to = models.DateField(null=True, blank=True, verbose_name=ugettext_lazy('price date to'))

    price_date_to_expr = models.CharField(null=True, max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                            verbose_name=ugettext_lazy('price date to expr'))

    price_balance_date = models.DateField(null=True, blank=True, verbose_name=ugettext_lazy('price balance date'))

    price_balance_date_expr = models.CharField(null=True, max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                          verbose_name=ugettext_lazy('price balance date expr'))

    price_fill_days = models.PositiveSmallIntegerField(default=0, verbose_name=ugettext_lazy('price fill days'))
    price_override_existed = models.BooleanField(default=True, verbose_name=ugettext_lazy('price override existed'))

    # DEPRECATED since 21.02.2020
    # accrual_is_active = models.BooleanField(default=False, verbose_name=ugettext_lazy('accrual is active'))
    #
    # accrual_date_from = models.DateField(null=True, blank=True, verbose_name=ugettext_lazy('accrual date from'))
    # accrual_date_from_expr = models.CharField(null=True, max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
    #                                            verbose_name=ugettext_lazy('accrual date from expr'))
    #
    # accrual_date_to = models.DateField(null=True, blank=True, verbose_name=ugettext_lazy('accrual date to'))
    # accrual_date_to_expr = models.CharField(null=True, max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
    #                                           verbose_name=ugettext_lazy('accrual date to expr'))

    pricing_policy_filters = models.TextField(blank=True, default='', verbose_name=ugettext_lazy('pricing policy filters'))

    instrument_filters = models.TextField(blank=True, default='', verbose_name=ugettext_lazy('instrument filters'))

    class Meta:
        unique_together = (
            ('name', 'master_user')
        )

    def __str__(self):
        return self.name


class CurrencyPricingPolicy(models.Model):

    currency = models.ForeignKey('currencies.Currency', on_delete=models.CASCADE, verbose_name=ugettext_lazy('currency'), related_name='pricing_policies')

    pricing_policy = models.ForeignKey('instruments.PricingPolicy', on_delete=models.CASCADE, verbose_name=ugettext_lazy('pricing policy'))

    pricing_scheme = models.ForeignKey(CurrencyPricingScheme, null=True, blank=True, on_delete=models.SET_NULL, verbose_name=ugettext_lazy('pricing scheme'))

    notes = models.TextField(blank=True, default='', verbose_name=ugettext_lazy('notes'))

    default_value = models.CharField(max_length=255, null=True, blank=True)
    attribute_key = models.CharField(max_length=255, null=True, blank=True)

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

    class Meta:
        unique_together = (
            ('currency', 'pricing_policy')
        )


class InstrumentTypePricingPolicy(models.Model):

    instrument_type = models.ForeignKey('instruments.InstrumentType', on_delete=models.CASCADE, verbose_name=ugettext_lazy('instrument type'), related_name='pricing_policies')

    pricing_policy = models.ForeignKey('instruments.PricingPolicy', on_delete=models.CASCADE, verbose_name=ugettext_lazy('pricing policy'))

    pricing_scheme = models.ForeignKey(InstrumentPricingScheme, null=True, blank=True, on_delete=models.SET_NULL, verbose_name=ugettext_lazy('pricing scheme'))

    notes = models.TextField(blank=True, default='', verbose_name=ugettext_lazy('notes'))

    default_value = models.CharField(max_length=255, null=True, blank=True)
    attribute_key = models.CharField(max_length=255, null=True, blank=True)

    json_data = models.TextField(null=True, blank=True, verbose_name=ugettext_lazy('json data'))

    overwrite_default_parameters = models.BooleanField(default=False, verbose_name=ugettext_lazy('is default'))

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

    class Meta:
        unique_together = (
            ('instrument_type', 'pricing_policy')
        )

class InstrumentPricingPolicy(models.Model):

    instrument = models.ForeignKey('instruments.Instrument', on_delete=models.CASCADE, verbose_name=ugettext_lazy('instrument'), related_name='pricing_policies')

    pricing_policy = models.ForeignKey('instruments.PricingPolicy', on_delete=models.CASCADE, verbose_name=ugettext_lazy('pricing policy'))

    pricing_scheme = models.ForeignKey(InstrumentPricingScheme, null=True, blank=True, on_delete=models.SET_NULL, verbose_name=ugettext_lazy('pricing scheme'))

    notes = models.TextField(blank=True, default='', verbose_name=ugettext_lazy('notes'))

    default_value = models.CharField(max_length=255, null=True, blank=True)
    attribute_key = models.CharField(max_length=255, null=True, blank=True)

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

    class Meta:
        unique_together = (
            ('instrument', 'pricing_policy')
        )

class PricingProcedureInstance(models.Model):

    STATUS_INIT = 'I'
    STATUS_PENDING = 'P'
    STATUS_DONE = 'D'
    STATUS_ERROR = 'E'

    STATUS_CHOICES = (
        (STATUS_INIT, ugettext_lazy('Init')),
        (STATUS_PENDING, ugettext_lazy('Pending')),
        (STATUS_DONE, ugettext_lazy('Done')),
        (STATUS_ERROR, ugettext_lazy('Error')),
    )

    pricing_procedure = models.ForeignKey(PricingProcedure, on_delete=models.CASCADE, verbose_name=ugettext_lazy('pricing procedure'))

    created = models.DateTimeField(auto_now_add=True, editable=False, db_index=True,
                                   verbose_name='created')
    modified = models.DateTimeField(auto_now=True, editable=False, db_index=True)

    master_user = models.ForeignKey('users.MasterUser', verbose_name=ugettext_lazy('master user'),
                                    on_delete=models.CASCADE)

    status = models.CharField(max_length=1,  default=STATUS_INIT, choices=STATUS_CHOICES, verbose_name=ugettext_lazy('status'))



class PricingProcedureBloombergResult(models.Model):

    master_user = models.ForeignKey('users.MasterUser', verbose_name=ugettext_lazy('master user'),
                                    on_delete=models.CASCADE)

    procedure = models.ForeignKey(PricingProcedureInstance, on_delete=models.CASCADE, verbose_name=ugettext_lazy('procedure'))

    instrument = models.ForeignKey('instruments.Instrument', on_delete=models.CASCADE, verbose_name=ugettext_lazy('instrument'))
    pricing_policy = models.ForeignKey('instruments.PricingPolicy', on_delete=models.CASCADE, verbose_name=ugettext_lazy('pricing policy'))

    reference = models.CharField(max_length=255, null=True, blank=True)

    date = models.DateField(null=True, blank=True, verbose_name=ugettext_lazy('date'))

    instrument_parameters = models.CharField(max_length=255, null=True, blank=True)

    ask_parameters = models.CharField(max_length=255, null=True, blank=True, verbose_name=ugettext_lazy('ask parameters'))
    ask_value = models.FloatField(null=True, blank=True, verbose_name=ugettext_lazy('ask value'))

    bid_parameters = models.CharField(max_length=255, null=True, blank=True, verbose_name=ugettext_lazy('bid parameters'))
    bid_value = models.FloatField(null=True, blank=True, verbose_name=ugettext_lazy('bid value'))

    last_parameters = models.CharField(max_length=255, null=True, blank=True, verbose_name=ugettext_lazy('last parameters'))
    last_value = models.FloatField(null=True, blank=True,  verbose_name=ugettext_lazy('last value'))

    class Meta:
        unique_together = (
            ('master_user', 'instrument', 'date', 'pricing_policy')
        )
