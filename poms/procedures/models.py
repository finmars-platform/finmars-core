from django.db import models
from django.utils.translation import ugettext_lazy

from poms.common.models import NamedModel, DataTimeStampedModel
from poms.integrations.models import DataProvider
from poms.schedules.models import Schedule, ScheduleInstance
from poms.users.models import MasterUser, Member

from poms.common.models import EXPRESSION_FIELD_LENGTH

from poms.common.utils import date_now

import logging

_l = logging.getLogger('poms.procedures')


class BaseProcedure(NamedModel, DataTimeStampedModel):

    master_user = models.ForeignKey('users.MasterUser', verbose_name=ugettext_lazy('master user'),
                                    on_delete=models.CASCADE)

    notes_for_users = models.TextField(blank=True, default='', verbose_name=ugettext_lazy('notes for user'))

    class Meta(NamedModel.Meta):
        abstract = True
        unique_together = [
            ['master_user', 'user_code']
        ]
        ordering = ['user_code']


class BaseProcedureInstance(DataTimeStampedModel):

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

    STARTED_BY_MEMBER = 'M'
    STARTED_BY_SCHEDULE = 'S'

    STARTED_BY_CHOICES = (
        (STARTED_BY_MEMBER, ugettext_lazy('Member')),
        (STARTED_BY_SCHEDULE, ugettext_lazy('Schedule')),
    )

    master_user = models.ForeignKey('users.MasterUser', verbose_name=ugettext_lazy('master user'),
                                    on_delete=models.CASCADE)

    status = models.CharField(max_length=1, default=STATUS_INIT, choices=STATUS_CHOICES,
                              verbose_name=ugettext_lazy('status'))

    started_by = models.CharField(max_length=1, default=STARTED_BY_MEMBER, choices=STARTED_BY_CHOICES,
                                  verbose_name=ugettext_lazy('started by'))

    member = models.ForeignKey(Member, null=True, blank=True, verbose_name=ugettext_lazy('member'), on_delete=models.SET_NULL)
    schedule_instance = models.ForeignKey(ScheduleInstance, null=True, blank=True,  verbose_name=ugettext_lazy('schedule instance'), on_delete=models.SET_NULL)

    error_code = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name=ugettext_lazy('error code'))
    error_message = models.TextField(null=True, blank=True, verbose_name=ugettext_lazy('error message'))

    class Meta:
        abstract = True


class PricingProcedure(BaseProcedure):

    CREATED_BY_USER = 1
    CREATED_BY_INSTRUMENT = 2
    CREATED_BY_CURRENCY = 3

    TYPES = (
        (CREATED_BY_USER, ugettext_lazy('Created by User')),
        (CREATED_BY_INSTRUMENT, ugettext_lazy('Created by Instrument')),
        (CREATED_BY_CURRENCY, ugettext_lazy('Created by Currency')),
    )

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

    currency_filters = models.TextField(blank=True, default='', verbose_name=ugettext_lazy('currency filters'))


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

        if self.type == PricingProcedure.CREATED_BY_CURRENCY:

            if self.currency_filters:

                user_code = self.currency_filters

                print('save procedure %s' % user_code)

                from poms.currencies.models import Currency
                from poms.common import formula
                currency = Currency.objects.get(master_user=self.master_user, user_code=user_code)

                self.user_code = formula.safe_eval('generate_user_code("proc", "", 0)', context={'master_user': self.master_user})
                self.name = 'Currency %s Pricing' % instrument.name
                self.notes_for_users = 'Pricing Procedure - Currency: %s Date from: %s. Date to: %s' % (currency.name, self.price_date_from, self.price_date_to)

                self.notes = 'Pricing Procedure generated by Currency: %s. Master user: %s. Created at %s' % (currency.user_code, self.master_user.name, date_now())

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


class PricingParentProcedureInstance(models.Model):

    created = models.DateTimeField(auto_now_add=True, editable=False, db_index=True,
                                   verbose_name='created')
    modified = models.DateTimeField(auto_now=True, editable=False, db_index=True)

    master_user = models.ForeignKey('users.MasterUser', verbose_name=ugettext_lazy('master user'),
                                    on_delete=models.CASCADE)

    procedure = models.ForeignKey(PricingProcedure, on_delete=models.CASCADE,
                                          verbose_name=ugettext_lazy('procedure'))

    class Meta:
        ordering = ['-created']


class PricingProcedureInstance(BaseProcedureInstance):

    procedure = models.ForeignKey(PricingProcedure, on_delete=models.CASCADE,
                                          verbose_name=ugettext_lazy('procedure'))

    parent_procedure_instance = models.ForeignKey(PricingParentProcedureInstance, on_delete=models.CASCADE,
                                                  related_name='procedures',
                                                  verbose_name=ugettext_lazy('parent pricing procedure'), null=True, blank=True)

    action = models.CharField(max_length=255, null=True, blank=True)
    provider = models.CharField(max_length=255, null=True, blank=True)

    action_verbose = models.CharField(max_length=255, null=True, blank=True)
    provider_verbose = models.CharField(max_length=255, null=True, blank=True)

    successful_prices_count = models.IntegerField(default=0, verbose_name=ugettext_lazy('successful prices count'))
    error_prices_count = models.IntegerField(default=0, verbose_name=ugettext_lazy('error prices count'))


    def save(self, *args, **kwargs):

        _l.info("before PricingProcedureInstance save id %s"  % self.pk)
        _l.info("before PricingProcedureInstance save successful_prices_count %s" % self.successful_prices_count)
        _l.info("before PricingProcedureInstance save error_prices_count %s" %  self.error_prices_count)

        super(PricingProcedureInstance, self).save(*args, **kwargs)


class RequestDataFileProcedure(BaseProcedure):

    provider = models.ForeignKey(DataProvider, verbose_name=ugettext_lazy('provider'), on_delete=models.CASCADE)

    scheme_name = models.CharField(max_length=255)

    price_date_from = models.DateField(null=True, blank=True, verbose_name=ugettext_lazy('price date from'))

    price_date_from_expr = models.CharField(null=True, max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                            verbose_name=ugettext_lazy('price date from expr'))

    price_date_to = models.DateField(null=True, blank=True, verbose_name=ugettext_lazy('price date to'))

    price_date_to_expr = models.CharField(null=True, max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                          verbose_name=ugettext_lazy('price date to expr'))


class RequestDataFileProcedureInstance(BaseProcedureInstance):

    procedure = models.ForeignKey(RequestDataFileProcedure, on_delete=models.CASCADE,
                                          verbose_name=ugettext_lazy('procedure'))
