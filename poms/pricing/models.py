import json

from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy

from poms.common.models import EXPRESSION_FIELD_LENGTH, NamedModel
from poms.common.utils import date_now
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

    def __str__(self):
        return self.name


class InstrumentPricingScheme(NamedModel):

    ADD_TO_ERROR_TABLE_AND_NOTIFY_IN_THE_END = 1
    ADD_TO_ERROR_TABLE_AND_NO_NOTIFICATION = 2
    ADD_TO_ERROR_TABLE_AND_NOTIFY_DIRECTLY = 3
    NOTIFY_DIRECTLY_AND_REQUEST_PRICES = 4

    ERROR_HANDLER_CHOICES = (
        (ADD_TO_ERROR_TABLE_AND_NOTIFY_IN_THE_END, ugettext_lazy('Add to Error Table and notify in the End')),
        (ADD_TO_ERROR_TABLE_AND_NO_NOTIFICATION, ugettext_lazy('Add to Error Table, no notification')),
        (ADD_TO_ERROR_TABLE_AND_NOTIFY_DIRECTLY, ugettext_lazy('Add to Error Table, notify directly')),
        (NOTIFY_DIRECTLY_AND_REQUEST_PRICES, ugettext_lazy('Notify Directly and request Prices')),
    )

    name = models.CharField(max_length=255)
    master_user = models.ForeignKey('users.MasterUser', verbose_name=ugettext_lazy('master user'),
                                    on_delete=models.CASCADE)
    notes = models.TextField(blank=True, default='', verbose_name=ugettext_lazy('notes'))

    notes_for_users = models.TextField(blank=True, default='', verbose_name=ugettext_lazy('notes for users'))

    notes_for_parameter = models.TextField(blank=True, default='', verbose_name=ugettext_lazy('notes for parameter'))

    error_handler = models.PositiveSmallIntegerField(default=ADD_TO_ERROR_TABLE_AND_NOTIFY_IN_THE_END, choices=ERROR_HANDLER_CHOICES,
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

                    result = InstrumentPricingSchemeSingleParameterFormulaParameters.objects.get(
                        instrument_pricing_scheme=self)

                # except InstrumentPricingSchemeSingleParameterFormulaParameters.DoesNotExist:
                except Exception as e:
                    print(e)

                    result = None

            if self.type.id == 4:  # multiple parameters formula

                try:

                    result = InstrumentPricingSchemeMultipleParametersFormulaParameters.objects.get(
                        instrument_pricing_scheme=self)

                except (InstrumentPricingSchemeMultipleParametersFormulaParameters.DoesNotExist, Exception) as e:

                    print('Instrument Multiple Parameter Formula Parameters error %s' % e)

                    result = None

            if self.type.id == 5:  # bloomberg

                try:

                    result = InstrumentPricingSchemeBloombergParameters.objects.get(instrument_pricing_scheme=self)

                except InstrumentPricingSchemeBloombergParameters.DoesNotExist:

                    result = None

            if self.type.id == 6:  # wtrade

                try:

                    result = InstrumentPricingSchemeWtradeParameters.objects.get(instrument_pricing_scheme=self)

                except InstrumentPricingSchemeWtradeParameters.DoesNotExist:

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

    def __str__(self):
        return self.name


class CurrencyPricingScheme(NamedModel):

    ADD_TO_ERROR_TABLE_AND_NOTIFY_IN_THE_END = 1
    ADD_TO_ERROR_TABLE_AND_NO_NOTIFICATION = 2
    ADD_TO_ERROR_TABLE_AND_NOTIFY_DIRECTLY = 3
    NOTIFY_DIRECTLY_AND_REQUEST_PRICES = 4

    ERROR_HANDLER_CHOICES = (
        (ADD_TO_ERROR_TABLE_AND_NOTIFY_IN_THE_END, ugettext_lazy('Add to Error Table and notify in the End')),
        (ADD_TO_ERROR_TABLE_AND_NO_NOTIFICATION, ugettext_lazy('Add to Error Table, no notification')),
        (ADD_TO_ERROR_TABLE_AND_NOTIFY_DIRECTLY, ugettext_lazy('Add to Error Table, notify directly')),
        (NOTIFY_DIRECTLY_AND_REQUEST_PRICES, ugettext_lazy('Notify Directly and request Prices')),
    )

    name = models.CharField(max_length=255)
    master_user = models.ForeignKey('users.MasterUser', verbose_name=ugettext_lazy('master user'),
                                    on_delete=models.CASCADE)
    notes = models.TextField(blank=True, default='', verbose_name=ugettext_lazy('notes'))

    notes_for_users = models.TextField(blank=True, default='', verbose_name=ugettext_lazy('notes for users'))

    notes_for_parameter = models.TextField(blank=True, default='', verbose_name=ugettext_lazy('notes for parameter'))

    error_handler = models.PositiveSmallIntegerField(default=ADD_TO_ERROR_TABLE_AND_NOTIFY_IN_THE_END, choices=ERROR_HANDLER_CHOICES,
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

                    result = CurrencyPricingSchemeSingleParameterFormulaParameters.objects.get(
                        currency_pricing_scheme=self)

                except CurrencyPricingSchemeSingleParameterFormulaParameters.DoesNotExist:

                    result = None

            if self.type.id == 4:  # multiple parameters formula

                try:

                    result = CurrencyPricingSchemeMultipleParametersFormulaParameters.objects.get(
                        currency_pricing_scheme=self)

                except CurrencyPricingSchemeMultipleParametersFormulaParameters.DoesNotExist:

                    result = None

            if self.type.id == 5:  # bloomberg

                try:

                    result = CurrencyPricingSchemeBloombergParameters.objects.get(currency_pricing_scheme=self)

                except CurrencyPricingSchemeBloombergParameters.DoesNotExist:

                    result = None

            # if self.type.id == 6:  # wtrade
            #
            #     try:
            #
            #         result = CurrencyPricingSchemeWtradeParameters.objects.get(currency_pricing_scheme=self)
            #
            #     except CurrencyPricingSchemeWtradeParameters.DoesNotExist:
            #
            #         result = None

            if self.type.id == 7:  # fixer

                try:

                    result = CurrencyPricingSchemeFixerParameters.objects.get(currency_pricing_scheme=self)

                except CurrencyPricingSchemeFixerParameters.DoesNotExist:

                    result = None

        # print('result %s' % result)

        return result


class InstrumentPricingSchemeManualPricingParameters(models.Model):
    instrument_pricing_scheme = models.ForeignKey(InstrumentPricingScheme,
                                                  verbose_name=ugettext_lazy('Instrument Pricing Scheme'),
                                                  on_delete=models.CASCADE)

    default_value = models.CharField(max_length=255, null=True, blank=True)
    attribute_key = models.CharField(max_length=255, null=True, blank=True)


class CurrencyPricingSchemeManualPricingParameters(models.Model):
    currency_pricing_scheme = models.ForeignKey(CurrencyPricingScheme,
                                                verbose_name=ugettext_lazy('Currency Pricing Scheme'),
                                                on_delete=models.CASCADE)

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

    ACCRUAL_NOT_APPLICABLE = 1
    ACCRUAL_PER_SCHEDULE = 2
    ACCRUAL_PER_FORMULA = 3

    ACCRUAL_METHODS = (
        (ACCRUAL_NOT_APPLICABLE, ugettext_lazy('Not applicable')),
        (ACCRUAL_PER_SCHEDULE, ugettext_lazy('As per Accrual Schedule')),
        (ACCRUAL_PER_FORMULA, ugettext_lazy('As per Formula')),

    )

    instrument_pricing_scheme = models.ForeignKey(InstrumentPricingScheme,
                                                  verbose_name=ugettext_lazy('Instrument Pricing Scheme'),
                                                  on_delete=models.CASCADE)

    expr = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                            verbose_name=ugettext_lazy('expr'))

    pricing_error_text_expr = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, null=True, blank=True, default='',
                                               verbose_name=ugettext_lazy('pricing error text'))

    accrual_calculation_method = models.PositiveSmallIntegerField(default=ACCRUAL_NOT_APPLICABLE,
                                                                  choices=ACCRUAL_METHODS,
                                                                  verbose_name=ugettext_lazy(
                                                                      'accrual calculation method'))

    accrual_expr = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, null=True, blank=True, default='',
                                    verbose_name=ugettext_lazy('accrual expr'))

    accrual_error_text_expr = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, null=True, blank=True, default='',
                                               verbose_name=ugettext_lazy('accrual error text expr'))

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

    currency_pricing_scheme = models.ForeignKey(CurrencyPricingScheme,
                                                verbose_name=ugettext_lazy('Currency Pricing Scheme'),
                                                on_delete=models.CASCADE)

    expr = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                            verbose_name=ugettext_lazy('expr'))

    error_text_expr = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, null=True, blank=True, default='',
                                       verbose_name=ugettext_lazy('error text expr'))

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

    ACCRUAL_NOT_APPLICABLE = 1
    ACCRUAL_PER_SCHEDULE = 2
    ACCRUAL_PER_FORMULA = 3

    ACCRUAL_METHODS = (
        (ACCRUAL_NOT_APPLICABLE, ugettext_lazy('Not applicable')),
        (ACCRUAL_PER_SCHEDULE, ugettext_lazy('As per Accrual Schedule')),
        (ACCRUAL_PER_FORMULA, ugettext_lazy('As per Formula')),

    )

    instrument_pricing_scheme = models.ForeignKey(InstrumentPricingScheme,
                                                  verbose_name=ugettext_lazy('Instrument Pricing Scheme'),
                                                  on_delete=models.CASCADE)

    expr = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                            verbose_name=ugettext_lazy('expr'))

    pricing_error_text_expr = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, null=True, blank=True, default='',
                                               verbose_name=ugettext_lazy('pricing error text'))

    accrual_calculation_method = models.PositiveSmallIntegerField(default=ACCRUAL_NOT_APPLICABLE,
                                                                  choices=ACCRUAL_METHODS,
                                                                  verbose_name=ugettext_lazy(
                                                                      'accrual calculation method'))

    accrual_expr = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, null=True, blank=True, default='',
                                    verbose_name=ugettext_lazy('accrual expr'))

    accrual_error_text_expr = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, null=True, blank=True, default='',
                                               verbose_name=ugettext_lazy('accrual error text expr'))

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

    currency_pricing_scheme = models.ForeignKey(CurrencyPricingScheme,
                                                verbose_name=ugettext_lazy('Currency Pricing Scheme'),
                                                on_delete=models.CASCADE)

    expr = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                            verbose_name=ugettext_lazy('expr'))

    error_text_expr = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, null=True, blank=True, default='',
                                       verbose_name=ugettext_lazy('error text expr'))

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

    ACCRUAL_NOT_APPLICABLE = 1
    ACCRUAL_PER_SCHEDULE = 2
    ACCRUAL_PER_FORMULA = 3

    ACCRUAL_METHODS = (
        (ACCRUAL_NOT_APPLICABLE, ugettext_lazy('Not applicable')),
        (ACCRUAL_PER_SCHEDULE, ugettext_lazy('As per Accrual Schedule')),
        (ACCRUAL_PER_FORMULA, ugettext_lazy('As per Formula')),

    )

    instrument_pricing_scheme = models.ForeignKey(InstrumentPricingScheme,
                                                  verbose_name=ugettext_lazy('Instrument Pricing Scheme'),
                                                  on_delete=models.CASCADE)

    expr = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                            verbose_name=ugettext_lazy('expr'))

    pricing_error_text_expr = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, null=True, blank=True, default='',
                                               verbose_name=ugettext_lazy('pricing error text expr'))

    accrual_calculation_method = models.PositiveSmallIntegerField(default=ACCRUAL_NOT_APPLICABLE,
                                                                  choices=ACCRUAL_METHODS,
                                                                  verbose_name=ugettext_lazy(
                                                                      'accrual calculation method'))

    accrual_expr = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, null=True, blank=True, default='',
                                    verbose_name=ugettext_lazy('accrual expr'))

    accrual_error_text_expr = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, null=True, blank=True, default='',
                                               verbose_name=ugettext_lazy('accrual error text expr'))

    default_value = models.CharField(max_length=255, null=True, blank=True)
    attribute_key = models.CharField(max_length=255, null=True, blank=True)
    value_type = models.PositiveSmallIntegerField(default=STRING, choices=TYPES,
                                                  verbose_name=ugettext_lazy('value type'))

    bid_historical = models.CharField(max_length=50, blank=True, null=True,
                                      verbose_name=ugettext_lazy('bid historical'))
    bid_yesterday = models.CharField(max_length=50, blank=True, null=True, verbose_name=ugettext_lazy('bid yesterday'))

    ask_historical = models.CharField(max_length=50, blank=True, null=True,
                                      verbose_name=ugettext_lazy('ask historical'))
    ask_yesterday = models.CharField(max_length=50, blank=True, null=True, verbose_name=ugettext_lazy('ask yesterday'))

    last_historical = models.CharField(max_length=50, blank=True, null=True,
                                       verbose_name=ugettext_lazy('last historical'))
    last_yesterday = models.CharField(max_length=50, blank=True, null=True,
                                      verbose_name=ugettext_lazy('last yesterday'))

    accrual_historical = models.CharField(max_length=50, blank=True, null=True,
                                          verbose_name=ugettext_lazy('accrual historical'))
    accrual_yesterday = models.CharField(max_length=50, blank=True, null=True,
                                         verbose_name=ugettext_lazy('accrual yesterday'))


class CurrencyPricingSchemeBloombergParameters(models.Model):
    STRING = 10
    NUMBER = 20
    DATE = 40

    TYPES = (
        (NUMBER, ugettext_lazy('Number')),
        (STRING, ugettext_lazy('String')),
        (DATE, ugettext_lazy('Date')),
    )

    currency_pricing_scheme = models.ForeignKey(CurrencyPricingScheme,
                                                verbose_name=ugettext_lazy('Currency Pricing Scheme'),
                                                on_delete=models.CASCADE)

    expr = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                            verbose_name=ugettext_lazy('expr'))

    error_text_expr = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, null=True, blank=True, default='',
                                       verbose_name=ugettext_lazy('error text expr'))

    default_value = models.CharField(max_length=255, null=True, blank=True)
    attribute_key = models.CharField(max_length=255, null=True, blank=True)
    value_type = models.PositiveSmallIntegerField(default=STRING, choices=TYPES,
                                                  verbose_name=ugettext_lazy('value type'))

    fx_rate = models.CharField(max_length=50, blank=True, verbose_name=ugettext_lazy('FX rate'))


class InstrumentPricingSchemeWtradeParameters(models.Model):
    STRING = 10
    NUMBER = 20
    DATE = 40

    TYPES = (
        (NUMBER, ugettext_lazy('Number')),
        (STRING, ugettext_lazy('String')),
        (DATE, ugettext_lazy('Date')),
    )

    ACCRUAL_NOT_APPLICABLE = 1
    ACCRUAL_PER_SCHEDULE = 2
    ACCRUAL_PER_FORMULA = 3

    ACCRUAL_METHODS = (
        (ACCRUAL_NOT_APPLICABLE, ugettext_lazy('Not applicable')),
        (ACCRUAL_PER_SCHEDULE, ugettext_lazy('As per Accrual Schedule')),
        (ACCRUAL_PER_FORMULA, ugettext_lazy('As per Formula')),

    )

    instrument_pricing_scheme = models.ForeignKey(InstrumentPricingScheme,
                                                  verbose_name=ugettext_lazy('Instrument Pricing Scheme'),
                                                  on_delete=models.CASCADE)

    expr = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                            verbose_name=ugettext_lazy('expr'))

    pricing_error_text_expr = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, null=True, blank=True, default='',
                                               verbose_name=ugettext_lazy('pricing error text expr'))

    accrual_calculation_method = models.PositiveSmallIntegerField(default=ACCRUAL_NOT_APPLICABLE,
                                                                  choices=ACCRUAL_METHODS,
                                                                  verbose_name=ugettext_lazy(
                                                                      'accrual calculation method'))

    accrual_expr = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, null=True, blank=True, default='',
                                    verbose_name=ugettext_lazy('accrual expr'))

    accrual_error_text_expr = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, null=True, blank=True, default='',
                                               verbose_name=ugettext_lazy('accrual error text expr'))


    default_value = models.CharField(max_length=255, null=True, blank=True)
    attribute_key = models.CharField(max_length=255, null=True, blank=True)
    value_type = models.PositiveSmallIntegerField(default=STRING, choices=TYPES,
                                                  verbose_name=ugettext_lazy('value type'))

# DEPRECATED since 09.03.2020
# class CurrencyPricingSchemeWtradeParameters(models.Model):
#     STRING = 10
#     NUMBER = 20
#     DATE = 40
#
#     TYPES = (
#         (NUMBER, ugettext_lazy('Number')),
#         (STRING, ugettext_lazy('String')),
#         (DATE, ugettext_lazy('Date')),
#     )
#
#     currency_pricing_scheme = models.ForeignKey(CurrencyPricingScheme,
#                                                 verbose_name=ugettext_lazy('Currency Pricing Scheme'),
#                                                 on_delete=models.CASCADE)
#
#     expr = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
#                             verbose_name=ugettext_lazy('expr'))
#
#     default_value = models.CharField(max_length=255, null=True, blank=True)
#     attribute_key = models.CharField(max_length=255, null=True, blank=True)
#     value_type = models.PositiveSmallIntegerField(default=STRING, choices=TYPES,
#                                                   verbose_name=ugettext_lazy('value type'))


class CurrencyPricingSchemeFixerParameters(models.Model):
    STRING = 10
    NUMBER = 20
    DATE = 40

    TYPES = (
        (NUMBER, ugettext_lazy('Number')),
        (STRING, ugettext_lazy('String')),
        (DATE, ugettext_lazy('Date')),
    )

    currency_pricing_scheme = models.ForeignKey(CurrencyPricingScheme,
                                                verbose_name=ugettext_lazy('Currency Pricing Scheme'),
                                                on_delete=models.CASCADE)

    expr = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                            verbose_name=ugettext_lazy('expr'))

    error_text_expr = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, null=True, blank=True, default='',
                                       verbose_name=ugettext_lazy('error text expr'))

    default_value = models.CharField(max_length=255, null=True, blank=True)
    attribute_key = models.CharField(max_length=255, null=True, blank=True)
    value_type = models.PositiveSmallIntegerField(default=STRING, choices=TYPES,
                                                  verbose_name=ugettext_lazy('value type'))


class PricingProcedure(NamedModel):

    CREATED_BY_USER = 1
    CREATED_BY_INSTRUMENT = 2

    TYPES = (
        (CREATED_BY_USER, ugettext_lazy('Created by User')),
        (CREATED_BY_INSTRUMENT, ugettext_lazy('Created by Instrument')),
    )

    name = models.CharField(max_length=255)
    master_user = models.ForeignKey('users.MasterUser', verbose_name=ugettext_lazy('master user'),
                                    on_delete=models.CASCADE)
    notes = models.TextField(blank=True, default='', verbose_name=ugettext_lazy('notes'))

    notes_for_users = models.TextField(blank=True, default='', verbose_name=ugettext_lazy('notes for user'))

    type = models.PositiveSmallIntegerField(default=CREATED_BY_USER, choices=TYPES,
                                            verbose_name=ugettext_lazy('type'))

    # DEPRECATED since 21.02.2020
    # price_is_active = models.BooleanField(default=False, verbose_name=ugettext_lazy('price is active'))

    price_date_from = models.DateField(null=True, blank=True, verbose_name=ugettext_lazy('price date from'))

    price_date_from_expr = models.CharField(null=True, max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                            verbose_name=ugettext_lazy('price date from expr'))

    price_date_to = models.DateField(null=True, blank=True, verbose_name=ugettext_lazy('price date to'))

    price_date_to_expr = models.CharField(null=True, max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                          verbose_name=ugettext_lazy('price date to expr'))

    # DEPRECATED since 27.04.2020
    # price_balance_date = models.DateField(null=True, blank=True, verbose_name=ugettext_lazy('price balance date'))
    #
    # price_balance_date_expr = models.CharField(null=True, max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
    #                                            verbose_name=ugettext_lazy('price balance date expr'))

    price_fill_days = models.PositiveSmallIntegerField(default=0, verbose_name=ugettext_lazy('price fill days'))

    # DEPRECATED since 27.04.2020
    # price_override_existed = models.BooleanField(default=True, verbose_name=ugettext_lazy('price override existed'))

    price_get_principal_prices = models.BooleanField(default=False, verbose_name=ugettext_lazy('price get principal prices'))
    price_get_accrued_prices = models.BooleanField(default=False, verbose_name=ugettext_lazy('price get accrued prices'))
    price_get_fx_rates = models.BooleanField(default=False, verbose_name=ugettext_lazy('price get fx rates'))

    price_overwrite_principal_prices = models.BooleanField(default=False, verbose_name=ugettext_lazy('price overwrite principal prices'))
    price_overwrite_accrued_prices = models.BooleanField(default=False, verbose_name=ugettext_lazy('price overwrite accrued prices'))
    price_overwrite_fx_rates = models.BooleanField(default=False, verbose_name=ugettext_lazy('price overwrite fx rates'))

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

    pricing_policy_filters = models.TextField(blank=True, default='',
                                              verbose_name=ugettext_lazy('pricing policy filters'))

    portfolio_filters = models.TextField(blank=True, default='',
                                              verbose_name=ugettext_lazy('portfolio filters'))

    instrument_filters = models.TextField(blank=True, default='', verbose_name=ugettext_lazy('instrument filters'))

    instrument_type_filters = models.TextField(blank=True, default='', verbose_name=ugettext_lazy('instrument type filters'))

    instrument_pricing_scheme_filters = models.TextField(blank=True, default='', verbose_name=ugettext_lazy('instrument pricing scheme filters'))

    instrument_pricing_condition_filters = models.TextField(blank=True, default='', verbose_name=ugettext_lazy('instrument pricing condition filters'))

    currency_pricing_scheme_filters = models.TextField(blank=True, default='', verbose_name=ugettext_lazy('currency pricing scheme filters'))

    currency_pricing_condition_filters = models.TextField(blank=True, default='', verbose_name=ugettext_lazy('currency pricing condition filters'))

    class Meta:
        unique_together = (
            ('master_user', 'user_code', 'type')
        )

    def save(self, *args, **kwargs):
        if self.type == PricingProcedure.CREATED_BY_INSTRUMENT:

            if self.instrument_filters:

                user_code = self.instrument_filters

                print('save procedure %s' % user_code)

                from poms.instruments.models import Instrument
                from poms.common import formula
                instrument = Instrument.objects.get(master_user=self.master_user, user_code=user_code)

                self.user_code = formula.safe_eval('generate_user_code("proc", "", 0)', context={'master_user': self.master_user})
                self.name = 'Instrument %s Pricing' % instrument.name
                self.notes_for_users = 'Pricing Procedure - Instrument: %s Date from: %s. Date to: %s' % (instrument.name, self.price_date_from, self.price_date_to)

                self.notes = 'Pricing Procedure generated by instrument: %s. Master user: %s. Created at %s' % (instrument.user_code, self.master_user.name, date_now())

                self.price_fill_days = 0
                self.price_get_principal_prices = True
                self.price_get_accrued_prices = True
                self.price_get_fx_rates = False
                self.price_overwrite_fx_rates = False

                self.portfolio_filters = ''
                self.instrument_type_filters = ''
                self.instrument_pricing_scheme_filters = ''
                self.instrument_pricing_condition_filters = ''
                self.currency_pricing_scheme_filters = ''
                self.currency_pricing_condition_filters = ''


        super(PricingProcedure, self).save(*args, **kwargs)

    def __str__(self):
        return self.name


class CurrencyPricingPolicy(models.Model):
    currency = models.ForeignKey('currencies.Currency', on_delete=models.CASCADE,
                                 verbose_name=ugettext_lazy('currency'), related_name='pricing_policies')

    pricing_policy = models.ForeignKey('instruments.PricingPolicy', on_delete=models.CASCADE,
                                       verbose_name=ugettext_lazy('pricing policy'))

    pricing_scheme = models.ForeignKey(CurrencyPricingScheme, null=True, blank=True, on_delete=models.SET_NULL,
                                       verbose_name=ugettext_lazy('pricing scheme'))

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
    instrument_type = models.ForeignKey('instruments.InstrumentType', on_delete=models.CASCADE,
                                        verbose_name=ugettext_lazy('instrument type'), related_name='pricing_policies')

    pricing_policy = models.ForeignKey('instruments.PricingPolicy', on_delete=models.CASCADE,
                                       verbose_name=ugettext_lazy('pricing policy'))

    pricing_scheme = models.ForeignKey(InstrumentPricingScheme, null=True, blank=True, on_delete=models.SET_NULL,
                                       verbose_name=ugettext_lazy('pricing scheme'))

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
    instrument = models.ForeignKey('instruments.Instrument', on_delete=models.CASCADE,
                                   verbose_name=ugettext_lazy('instrument'), related_name='pricing_policies')

    pricing_policy = models.ForeignKey('instruments.PricingPolicy', on_delete=models.CASCADE,
                                       verbose_name=ugettext_lazy('pricing policy'))

    pricing_scheme = models.ForeignKey(InstrumentPricingScheme, null=True, blank=True, on_delete=models.SET_NULL,
                                       verbose_name=ugettext_lazy('pricing scheme'))

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


class PricingParentProcedureInstance(models.Model):

    created = models.DateTimeField(auto_now_add=True, editable=False, db_index=True,
                                   verbose_name='created')
    modified = models.DateTimeField(auto_now=True, editable=False, db_index=True)

    master_user = models.ForeignKey('users.MasterUser', verbose_name=ugettext_lazy('master user'),
                                    on_delete=models.CASCADE)

    pricing_procedure = models.ForeignKey(PricingProcedure, on_delete=models.CASCADE,
                                          verbose_name=ugettext_lazy('pricing procedure'))

    class Meta:
        ordering = ['-created']


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

    pricing_procedure = models.ForeignKey(PricingProcedure, on_delete=models.CASCADE,
                                          verbose_name=ugettext_lazy('pricing procedure'))

    parent_procedure_instance = models.ForeignKey(PricingParentProcedureInstance, on_delete=models.CASCADE,
                                                  related_name='procedures',
                                                  verbose_name=ugettext_lazy('parent pricing procedure'), null=True, blank=True)

    created = models.DateTimeField(auto_now_add=True, editable=False, db_index=True,
                                   verbose_name='created')
    modified = models.DateTimeField(auto_now=True, editable=False, db_index=True)

    master_user = models.ForeignKey('users.MasterUser', verbose_name=ugettext_lazy('master user'),
                                    on_delete=models.CASCADE)

    status = models.CharField(max_length=1, default=STATUS_INIT, choices=STATUS_CHOICES,
                              verbose_name=ugettext_lazy('status'))

    action = models.CharField(max_length=255, null=True, blank=True)
    provider = models.CharField(max_length=255, null=True, blank=True)

    action_verbose = models.CharField(max_length=255, null=True, blank=True)
    provider_verbose = models.CharField(max_length=255, null=True, blank=True)


class PriceHistoryError(models.Model):

    STATUS_ERROR = 'E'
    STATUS_SKIP = 'S'

    STATUS_CHOICES = (
        (STATUS_ERROR, ugettext_lazy('Error')),
        (STATUS_SKIP, ugettext_lazy('Skip')),
    )

    master_user = models.ForeignKey('users.MasterUser', verbose_name=ugettext_lazy('master user'),
                                    on_delete=models.CASCADE)

    instrument = models.ForeignKey('instruments.Instrument', on_delete=models.CASCADE,
                                   verbose_name=ugettext_lazy('instrument'))

    pricing_policy = models.ForeignKey('instruments.PricingPolicy', on_delete=models.CASCADE,
                                       verbose_name=ugettext_lazy('pricing policy'))

    pricing_scheme = models.ForeignKey(InstrumentPricingScheme, null=True, blank=True, on_delete=models.SET_NULL,
                                       verbose_name=ugettext_lazy('pricing scheme'))

    date = models.DateField(db_index=True, default=date_now, verbose_name=ugettext_lazy('date'))

    principal_price = models.FloatField(default=0.0, verbose_name=ugettext_lazy('principal price'))
    accrued_price = models.FloatField(default=0.0, verbose_name=ugettext_lazy('accrued price'))

    price_error_text = models.TextField(blank=True, default='', verbose_name=ugettext_lazy('price error text'))

    accrual_error_text = models.TextField(blank=True, default='', verbose_name=ugettext_lazy('accrual error text'))

    procedure_instance = models.ForeignKey(PricingProcedureInstance, on_delete=models.CASCADE,
                                           verbose_name=ugettext_lazy('pricing procedure instance'))

    status = models.CharField(max_length=1, default=STATUS_ERROR, choices=STATUS_CHOICES,
                              verbose_name=ugettext_lazy('status'))


class CurrencyHistoryError(models.Model):

    STATUS_ERROR = 'E'
    STATUS_SKIP = 'S'

    STATUS_CHOICES = (
        (STATUS_ERROR, ugettext_lazy('Error')),
        (STATUS_SKIP, ugettext_lazy('Skip')),
    )

    master_user = models.ForeignKey('users.MasterUser', verbose_name=ugettext_lazy('master user'),
                                    on_delete=models.CASCADE)

    currency = models.ForeignKey('currencies.Currency', on_delete=models.CASCADE,
                                   verbose_name=ugettext_lazy('currency'))

    pricing_policy = models.ForeignKey('instruments.PricingPolicy', on_delete=models.CASCADE,
                                       verbose_name=ugettext_lazy('pricing policy'))

    pricing_scheme = models.ForeignKey(CurrencyPricingScheme, null=True, blank=True, on_delete=models.SET_NULL,
                                       verbose_name=ugettext_lazy('pricing scheme'))

    date = models.DateField(db_index=True, default=date_now, verbose_name=ugettext_lazy('date'))

    fx_rate = models.FloatField(default=0.0, verbose_name=ugettext_lazy('fx rate'))

    error_text = models.TextField(blank=True, default='', verbose_name=ugettext_lazy('error text'))

    procedure_instance = models.ForeignKey(PricingProcedureInstance, on_delete=models.CASCADE,
                                           verbose_name=ugettext_lazy('pricing procedure instance'))

    status = models.CharField(max_length=1, default=STATUS_ERROR, choices=STATUS_CHOICES,
                              verbose_name=ugettext_lazy('status'))


class PricingProcedureBloombergInstrumentResult(models.Model):
    master_user = models.ForeignKey('users.MasterUser', verbose_name=ugettext_lazy('master user'),
                                    on_delete=models.CASCADE)

    procedure = models.ForeignKey(PricingProcedureInstance, on_delete=models.CASCADE,
                                  verbose_name=ugettext_lazy('procedure'))

    instrument = models.ForeignKey('instruments.Instrument', on_delete=models.CASCADE,
                                   verbose_name=ugettext_lazy('instrument'))
    pricing_policy = models.ForeignKey('instruments.PricingPolicy', on_delete=models.CASCADE,
                                       verbose_name=ugettext_lazy('pricing policy'))

    pricing_scheme = models.ForeignKey(InstrumentPricingScheme, null=True, blank=True, on_delete=models.SET_NULL,
                                       verbose_name=ugettext_lazy('pricing scheme'))

    reference = models.CharField(max_length=255, null=True, blank=True)

    date = models.DateField(null=True, blank=True, verbose_name=ugettext_lazy('date'))

    instrument_parameters = models.CharField(max_length=255, null=True, blank=True)

    ask_parameters = models.CharField(max_length=255, null=True, blank=True,
                                      verbose_name=ugettext_lazy('ask parameters'))
    ask_value = models.FloatField(null=True, blank=True, verbose_name=ugettext_lazy('ask value'))

    bid_parameters = models.CharField(max_length=255, null=True, blank=True,
                                      verbose_name=ugettext_lazy('bid parameters'))
    bid_value = models.FloatField(null=True, blank=True, verbose_name=ugettext_lazy('bid value'))

    last_parameters = models.CharField(max_length=255, null=True, blank=True,
                                       verbose_name=ugettext_lazy('last parameters'))
    last_value = models.FloatField(null=True, blank=True, verbose_name=ugettext_lazy('last value'))

    accrual_parameters = models.CharField(max_length=255, null=True, blank=True,
                                          verbose_name=ugettext_lazy('accrual parameters'))
    accrual_value = models.FloatField(null=True, blank=True, verbose_name=ugettext_lazy('accrual value'))

    class Meta:
        unique_together = (
            ('master_user', 'instrument', 'date', 'pricing_policy', 'procedure')
        )
        ordering = ['date']


class PricingProcedureBloombergCurrencyResult(models.Model):
    master_user = models.ForeignKey('users.MasterUser', verbose_name=ugettext_lazy('master user'),
                                    on_delete=models.CASCADE)

    procedure = models.ForeignKey(PricingProcedureInstance, on_delete=models.CASCADE,
                                  verbose_name=ugettext_lazy('procedure'))

    currency = models.ForeignKey('currencies.Currency', on_delete=models.CASCADE,
                                 verbose_name=ugettext_lazy('currency'))
    pricing_policy = models.ForeignKey('instruments.PricingPolicy', on_delete=models.CASCADE,
                                       verbose_name=ugettext_lazy('pricing policy'))

    pricing_scheme = models.ForeignKey(CurrencyPricingScheme, null=True, blank=True, on_delete=models.SET_NULL,
                                       verbose_name=ugettext_lazy('pricing scheme'))

    reference = models.CharField(max_length=255, null=True, blank=True)

    date = models.DateField(null=True, blank=True, verbose_name=ugettext_lazy('date'))

    currency_parameters = models.CharField(max_length=255, null=True, blank=True)

    fx_rate_parameters = models.CharField(max_length=255, null=True, blank=True,
                                          verbose_name=ugettext_lazy('fx rate parameters'))
    fx_rate_value = models.FloatField(null=True, blank=True, verbose_name=ugettext_lazy('fx rate value'))

    class Meta:
        unique_together = (
            ('master_user', 'currency', 'date', 'pricing_policy', 'procedure')
        )
        ordering = ['date']


class PricingProcedureWtradeInstrumentResult(models.Model):
    master_user = models.ForeignKey('users.MasterUser', verbose_name=ugettext_lazy('master user'),
                                    on_delete=models.CASCADE)

    procedure = models.ForeignKey(PricingProcedureInstance, on_delete=models.CASCADE,
                                  verbose_name=ugettext_lazy('procedure'))

    instrument = models.ForeignKey('instruments.Instrument', on_delete=models.CASCADE,
                                   verbose_name=ugettext_lazy('instrument'))
    pricing_policy = models.ForeignKey('instruments.PricingPolicy', on_delete=models.CASCADE,
                                       verbose_name=ugettext_lazy('pricing policy'))

    pricing_scheme = models.ForeignKey(InstrumentPricingScheme, null=True, blank=True, on_delete=models.SET_NULL,
                                       verbose_name=ugettext_lazy('pricing scheme'))

    reference = models.CharField(max_length=255, null=True, blank=True)

    date = models.DateField(null=True, blank=True, verbose_name=ugettext_lazy('date'))

    instrument_parameters = models.CharField(max_length=255, null=True, blank=True)

    open_value = models.FloatField(null=True, blank=True, verbose_name=ugettext_lazy('open value'))
    close_value = models.FloatField(null=True, blank=True, verbose_name=ugettext_lazy('close value'))
    high_value = models.FloatField(null=True, blank=True, verbose_name=ugettext_lazy('high value'))
    low_value = models.FloatField(null=True, blank=True, verbose_name=ugettext_lazy('low value'))
    volume_value = models.FloatField(null=True, blank=True, verbose_name=ugettext_lazy('volume value'))

    class Meta:
        unique_together = (
            ('master_user', 'instrument', 'date', 'pricing_policy', 'procedure')
        )
        ordering = ['date']


# DEPRECATED since 09.03.2020
# class PricingProcedureWtradeCurrencyResult(models.Model):
#     master_user = models.ForeignKey('users.MasterUser', verbose_name=ugettext_lazy('master user'),
#                                     on_delete=models.CASCADE)
#
#     procedure = models.ForeignKey(PricingProcedureInstance, on_delete=models.CASCADE,
#                                   verbose_name=ugettext_lazy('procedure'))
#
#     currency = models.ForeignKey('currencies.Currency', on_delete=models.CASCADE,
#                                  verbose_name=ugettext_lazy('currency'))
#     pricing_policy = models.ForeignKey('instruments.PricingPolicy', on_delete=models.CASCADE,
#                                        verbose_name=ugettext_lazy('pricing policy'))
#
#     pricing_scheme = models.ForeignKey(CurrencyPricingScheme, null=True, blank=True, on_delete=models.SET_NULL,
#                                        verbose_name=ugettext_lazy('pricing scheme'))
#
#     reference = models.CharField(max_length=255, null=True, blank=True)
#
#     date = models.DateField(null=True, blank=True, verbose_name=ugettext_lazy('date'))
#
#     currency_parameters = models.CharField(max_length=255, null=True, blank=True)
#
#     open_value = models.FloatField(null=True, blank=True, verbose_name=ugettext_lazy('open value'))
#     close_value = models.FloatField(null=True, blank=True, verbose_name=ugettext_lazy('close value'))
#     high_value = models.FloatField(null=True, blank=True, verbose_name=ugettext_lazy('high value'))
#     low_value = models.FloatField(null=True, blank=True, verbose_name=ugettext_lazy('low value'))
#     volume_value = models.FloatField(null=True, blank=True, verbose_name=ugettext_lazy('volume value'))
#
#     class Meta:
#         unique_together = (
#             ('master_user', 'currency', 'date', 'pricing_policy', 'procedure')
#         )


class PricingProcedureFixerCurrencyResult(models.Model):
    master_user = models.ForeignKey('users.MasterUser', verbose_name=ugettext_lazy('master user'),
                                    on_delete=models.CASCADE)

    procedure = models.ForeignKey(PricingProcedureInstance, on_delete=models.CASCADE,
                                  verbose_name=ugettext_lazy('procedure'))

    currency = models.ForeignKey('currencies.Currency', on_delete=models.CASCADE,
                                 verbose_name=ugettext_lazy('currency'))
    pricing_policy = models.ForeignKey('instruments.PricingPolicy', on_delete=models.CASCADE,
                                       verbose_name=ugettext_lazy('pricing policy'))

    pricing_scheme = models.ForeignKey(CurrencyPricingScheme, null=True, blank=True, on_delete=models.SET_NULL,
                                       verbose_name=ugettext_lazy('pricing scheme'))

    reference = models.CharField(max_length=255, null=True, blank=True)

    date = models.DateField(null=True, blank=True, verbose_name=ugettext_lazy('date'))

    currency_parameters = models.CharField(max_length=255, null=True, blank=True)

    close_value = models.FloatField(null=True, blank=True, verbose_name=ugettext_lazy('close value'))

    class Meta:
        unique_together = (
            ('master_user', 'currency', 'date', 'pricing_policy', 'procedure')
        )
        ordering = ['date']
