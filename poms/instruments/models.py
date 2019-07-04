from __future__ import unicode_literals

import logging
from datetime import date, timedelta

from dateutil import relativedelta, rrule
from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.core import serializers
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import ugettext, ugettext_lazy
from mptt.models import MPTTModel

from poms.common import formula
from poms.common.formula_accruals import get_coupon
from poms.common.models import NamedModel, AbstractClassModel, FakeDeletableModel, EXPRESSION_FIELD_LENGTH
from poms.common.utils import date_now, isclose
from poms.common.wrapper_models import NamedModelAutoMapping
from poms.obj_attrs.models import GenericAttribute
from poms.obj_perms.models import GenericObjectPermission
from poms.tags.models import TagLink
from poms.users.models import MasterUser, Member

_l = logging.getLogger('poms.instruments')


class InstrumentClass(AbstractClassModel):
    GENERAL = 1
    EVENT_AT_MATURITY = 2
    REGULAR_EVENT_AT_MATURITY = 3
    PERPETUAL_REGULAR_EVENT = 4
    CONTRACT_FOR_DIFFERENCE = 5
    DEFAULT = 6

    CLASSES = (
        (GENERAL, 'GENERAL', ugettext_lazy("General Class")),
        (EVENT_AT_MATURITY, 'EVENT_AT_MATURITY', ugettext_lazy("Event at Maturity")),
        (REGULAR_EVENT_AT_MATURITY, 'REGULAR_EVENT_AT_MATURITY', ugettext_lazy("Regular Event with Maturity")),
        (PERPETUAL_REGULAR_EVENT, 'PERPETUAL_REGULAR_EVENT', ugettext_lazy("Perpetual Regular Event")),
        (CONTRACT_FOR_DIFFERENCE, 'CONTRACT_FOR_DIFFERENCE', ugettext_lazy("Contract for Difference")),
        (DEFAULT, '-', ugettext_lazy("Default"))
    )

    class Meta(AbstractClassModel.Meta):
        verbose_name = ugettext_lazy('instrument class')
        verbose_name_plural = ugettext_lazy('instrument classes')

    @property
    def has_one_off_event(self):
        return self.id in [self.EVENT_AT_MATURITY, self.REGULAR_EVENT_AT_MATURITY]

    @property
    def has_regular_event(self):
        return self.id in [self.REGULAR_EVENT_AT_MATURITY, self.PERPETUAL_REGULAR_EVENT]


class DailyPricingModel(AbstractClassModel):
    SKIP = 1
    FORMULA_ALWAYS = 2
    FORMULA_IF_OPEN = 3
    PROVIDER_ALWAYS = 4
    PROVIDER_IF_OPEN = 5
    DEFAULT = 6
    CLASSES = (
        (SKIP, 'SKIP', ugettext_lazy("No Pricing (no Price History)")),
        (FORMULA_ALWAYS, 'FORMULA_ALWAYS', ugettext_lazy("Don't download, just apply Formula / Pricing Policy (always)")),
        (FORMULA_IF_OPEN, 'FORMULA_IF_OPEN', ugettext_lazy("Download & apply Formula / Pricing Policy (if non-zero position)")),
        (PROVIDER_ALWAYS, 'PROVIDER_ALWAYS', ugettext_lazy("Download & apply Formula / Pricing Policy (always)")),
        (PROVIDER_IF_OPEN, 'PROVIDER_IF_OPEN', ugettext_lazy("Don't download, just apply Formula / Pricing Policy (if non-zero position)")),
        (DEFAULT, '-', ugettext_lazy("Use Default Price (no Price History)"))
    )

    class Meta(AbstractClassModel.Meta):
        verbose_name = ugettext_lazy('daily pricing model')
        verbose_name_plural = ugettext_lazy('daily pricing models')


class AccrualCalculationModel(AbstractClassModel):
    NONE = 1
    ACT_ACT = 2
    ACT_ACT_ISDA = 3
    ACT_360 = 4
    ACT_365 = 5
    ACT_365_25 = 6
    ACT_365_366 = 7
    ACT_1_365 = 8
    ACT_1_360 = 9
    # C_30_ACT = 10
    C_30_360 = 11
    C_30_360_NO_EOM = 12
    C_30E_P_360 = 24
    C_30E_P_360_ITL = 13
    NL_365 = 14
    NL_365_NO_EOM = 15
    ISMA_30_360 = 16
    ISMA_30_360_NO_EOM = 17
    US_MINI_30_360_EOM = 18
    US_MINI_30_360_NO_EOM = 19
    BUS_DAYS_252 = 20
    GERMAN_30_360_EOM = 21
    GERMAN_30_360_NO_EOM = 22
    REVERSED_ACT_365 = 23

    DEFAULT = 25

    CLASSES = (
        (NONE, 'NONE', ugettext_lazy("none")),
        (ACT_ACT, 'ACT_ACT', ugettext_lazy("ACT/ACT")),
        (ACT_ACT_ISDA, 'ACT_ACT_ISDA', ugettext_lazy("ACT/ACT - ISDA")),
        (ACT_360, 'ACT_360', ugettext_lazy("ACT/360")),
        (ACT_365, 'ACT_365', ugettext_lazy("ACT/365")),
        (ACT_365_25, 'ACT_365_25', ugettext_lazy("Act/365.25")),
        (ACT_365_366, 'ACT_365_366', ugettext_lazy("Act/365(366)")),
        (ACT_1_365, 'ACT_1_365', ugettext_lazy("Act+1/365")),
        (ACT_1_360, 'ACT_1_360', ugettext_lazy("Act+1/360")),
        # (C_30_ACT, 'C_30_ACT', ugettext_lazy("30/ACT")),
        (C_30_360, 'C_30_360', ugettext_lazy("30/360")),
        (C_30_360_NO_EOM, 'C_30_360_NO_EOM', ugettext_lazy("30/360 (NO EOM)")),
        (C_30E_P_360_ITL, 'C_30E_P_360_ITL', ugettext_lazy("30E+/360.ITL")),
        (NL_365, 'NL_365', ugettext_lazy("NL/365")),
        (NL_365_NO_EOM, 'NL_365_NO_EOM', ugettext_lazy("NL/365 (NO-EOM)")),
        (ISMA_30_360, 'ISMA_30_360', ugettext_lazy("ISMA-30/360")),
        (ISMA_30_360_NO_EOM, 'ISMA_30_360_NO_EOM', ugettext_lazy("ISMA-30/360 (NO EOM)")),
        (US_MINI_30_360_EOM, 'US_MINI_30_360_EOM', ugettext_lazy("US MUNI-30/360 (EOM)")),
        (US_MINI_30_360_NO_EOM, 'US_MINI_30_360_NO_EOM', ugettext_lazy("US MUNI-30/360 (NO EOM)")),
        (BUS_DAYS_252, 'BUS_DAYS_252', ugettext_lazy("BUS DAYS/252")),
        (GERMAN_30_360_EOM, 'GERMAN_30_360_EOM', ugettext_lazy("GERMAN-30/360 (EOM)")),
        (GERMAN_30_360_NO_EOM, 'GERMAN_30_360_NO_EOM', ugettext_lazy("GERMAN-30/360 (NO EOM)")),
        (REVERSED_ACT_365, 'REVERSED_ACT_365', ugettext_lazy("Reversed ACT/365")),
        (C_30E_P_360, 'C_30E_P_360', ugettext_lazy('30E+/360')),
        (DEFAULT, '-', ugettext_lazy('Default'))
    )

    class Meta(AbstractClassModel.Meta):
        verbose_name = ugettext_lazy('accrual calculation model')
        verbose_name_plural = ugettext_lazy('accrual calculation models')


class PaymentSizeDetail(AbstractClassModel):
    PERCENT = 1
    PER_ANNUM = 2
    PER_QUARTER = 3
    PER_MONTH = 4
    PER_WEEK = 5
    PER_DAY = 6
    DEFAULT = 7
    CLASSES = (
        (PERCENT, 'PERCENT', ugettext_lazy("% per annum")),
        (PER_ANNUM, 'PER_ANNUM', ugettext_lazy("per annum")),
        (PER_QUARTER, 'PER_QUARTER', ugettext_lazy("per quarter")),
        (PER_MONTH, 'PER_MONTH', ugettext_lazy("per month")),
        (PER_WEEK, 'PER_WEEK', ugettext_lazy("per week")),
        (PER_DAY, 'PER_DAY', ugettext_lazy("per day")),
        (DEFAULT, '-', ugettext_lazy("Default")),
    )

    class Meta(AbstractClassModel.Meta):
        verbose_name = ugettext_lazy('payment size detail')
        verbose_name_plural = ugettext_lazy('payment size details')


class Periodicity(AbstractClassModel):
    N_DAY = 1
    N_WEEK_EOBW = 2
    N_MONTH_EOM = 3
    N_MONTH_SAME_DAY = 4
    N_YEAR_EOY = 5
    N_YEAR_SAME_DAY = 6

    WEEKLY = 7
    MONTHLY = 8
    QUARTERLY = 9
    SEMI_ANNUALLY = 10
    ANNUALLY = 11
    BIMONTHLY = 12

    DEFAULT = 13

    CLASSES = (
        (N_DAY, 'N_DAY', ugettext_lazy("N Days")),
        (N_WEEK_EOBW, 'N_WEEK_EOBW', ugettext_lazy("N Weeks (eobw)")),
        (N_MONTH_EOM, 'N_MONTH_EOM', ugettext_lazy("N Months (eom)")),
        (N_MONTH_SAME_DAY, 'N_MONTH_SAME_DAY', ugettext_lazy("N Months (same date)")),
        (N_YEAR_EOY, 'N_YEAR_EOY', ugettext_lazy("N Years (eoy)")),
        (N_YEAR_SAME_DAY, 'N_YEAR_SAME_DAY', ugettext_lazy("N Years (same date)")),

        (WEEKLY, 'WEEKLY', ugettext_lazy('Weekly')),
        (MONTHLY, 'MONTHLY', ugettext_lazy('Monthly')),
        (BIMONTHLY, 'BIMONTHLY', ugettext_lazy('Bimonthly')),
        (QUARTERLY, 'QUARTERLY', ugettext_lazy('Quarterly')),
        (SEMI_ANNUALLY, 'SEMI_ANNUALLY', ugettext_lazy('Semi-annually')),
        (ANNUALLY, 'ANNUALLY', ugettext_lazy('Annually')),

        (DEFAULT, '-', ugettext_lazy('-')),
    )

    class Meta(AbstractClassModel.Meta):
        verbose_name = ugettext_lazy('periodicity')
        verbose_name_plural = ugettext_lazy('periodicities')

    def to_timedelta(self, n=1, i=1, same_date=None):
        if self.id == Periodicity.N_DAY:
            if isclose(n, 0):
                raise ValueError("N_DAY: n can't be zero")
            return relativedelta.relativedelta(days=n * i)
        elif self.id == Periodicity.N_WEEK_EOBW:
            if isclose(n, 0):
                raise ValueError("N_WEEK_EOBW: n can't be zero")
            return relativedelta.relativedelta(weeks=n * i, weekday=relativedelta.FR)
        elif self.id == Periodicity.N_MONTH_EOM:
            if isclose(n, 0):
                raise ValueError("N_MONTH_EOM: n can't be zero")
            return relativedelta.relativedelta(months=n * i, day=31)
        elif self.id == Periodicity.N_MONTH_SAME_DAY:
            if isclose(n, 0):
                raise ValueError("N_MONTH_SAME_DAY: n can't be zero")
            return relativedelta.relativedelta(months=n * i, day=same_date.day)
        elif self.id == Periodicity.N_YEAR_EOY:
            if isclose(n, 0):
                raise ValueError("N_YEAR_EOY: n can't be zero")
            return relativedelta.relativedelta(years=n * i, month=12, day=31)
        elif self.id == Periodicity.N_YEAR_SAME_DAY:
            if isclose(n, 0):
                raise ValueError("N_YEAR_SAME_DAY: n can't be zero")
            return relativedelta.relativedelta(years=n * i, month=same_date.month, day=same_date.day)
        elif self.id == Periodicity.WEEKLY:
            return relativedelta.relativedelta(weeks=1 * i)
        elif self.id == Periodicity.MONTHLY:
            return relativedelta.relativedelta(months=1 * i)
        elif self.id == Periodicity.BIMONTHLY:
            return relativedelta.relativedelta(months=2 * i)
        elif self.id == Periodicity.QUARTERLY:
            return relativedelta.relativedelta(months=3 * i)
        elif self.id == Periodicity.SEMI_ANNUALLY:
            return relativedelta.relativedelta(months=6 * i)
        elif self.id == Periodicity.ANNUALLY:
            return relativedelta.relativedelta(years=1 * i)
        return None

    def to_freq(self):
        if self.id == Periodicity.N_DAY:
            return 0
        elif self.id == Periodicity.N_WEEK_EOBW:
            return 0
        elif self.id == Periodicity.N_MONTH_EOM:
            return 0
        elif self.id == Periodicity.N_MONTH_SAME_DAY:
            return 0
        elif self.id == Periodicity.N_YEAR_EOY:
            return 0
        elif self.id == Periodicity.N_YEAR_SAME_DAY:
            return 0
        elif self.id == Periodicity.WEEKLY:
            return 52
        elif self.id == Periodicity.MONTHLY:
            return 12
        elif self.id == Periodicity.BIMONTHLY:
            return 6
        elif self.id == Periodicity.QUARTERLY:
            return 4
        elif self.id == Periodicity.SEMI_ANNUALLY:
            return 2
        elif self.id == Periodicity.ANNUALLY:
            return 1
        return 0


class CostMethod(AbstractClassModel):
    AVCO = 1
    FIFO = 2
    LIFO = 3
    CLASSES = (
        (AVCO, 'AVCO', ugettext_lazy('AVCO')),
        (FIFO, 'FIFO', ugettext_lazy('FIFO')),
        # (LIFO, ugettext_lazy('LIFO')),
    )

    class Meta(AbstractClassModel.Meta):
        verbose_name = ugettext_lazy('cost method')
        verbose_name_plural = ugettext_lazy('cost methods')


class PricingPolicy(NamedModel):
    # DISABLED = 0
    # BLOOMBERG = 1
    # TYPES = (
    #     (DISABLED, ugettext_lazy('Disabled')),
    #     (BLOOMBERG, ugettext_lazy('Bloomberg')),
    # )

    master_user = models.ForeignKey(MasterUser, related_name='pricing_policies',
                                    verbose_name=ugettext_lazy('master user'))
    # type = models.PositiveIntegerField(default=DISABLED, choices=TYPES)
    expr = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, default='', blank=True,
                            verbose_name=ugettext_lazy('expression'))

    class Meta(AbstractClassModel.Meta):
        verbose_name = ugettext_lazy('pricing policy')
        verbose_name_plural = ugettext_lazy('pricing policies')


class InstrumentType(NamedModelAutoMapping, FakeDeletableModel):
    master_user = models.ForeignKey(MasterUser, related_name='instrument_types',
                                    verbose_name=ugettext_lazy('master user'))
    instrument_class = models.ForeignKey(InstrumentClass, related_name='instrument_types', on_delete=models.PROTECT,
                                         verbose_name=ugettext_lazy('instrument class'))

    one_off_event = models.ForeignKey('transactions.TransactionType', null=True, blank=True, on_delete=models.PROTECT,
                                      related_name='+', verbose_name=ugettext_lazy('one-off event'))
    regular_event = models.ForeignKey('transactions.TransactionType', null=True, blank=True, on_delete=models.PROTECT,
                                      related_name='+', verbose_name=ugettext_lazy('regular event'))

    factor_same = models.ForeignKey('transactions.TransactionType', null=True, blank=True, on_delete=models.PROTECT,
                                    related_name='+', verbose_name=ugettext_lazy('factor same'))
    factor_up = models.ForeignKey('transactions.TransactionType', null=True, blank=True, on_delete=models.PROTECT,
                                  related_name='+', verbose_name=ugettext_lazy('factor up'))
    factor_down = models.ForeignKey('transactions.TransactionType', null=True, blank=True, on_delete=models.PROTECT,
                                    related_name='+', verbose_name=ugettext_lazy('factor down'))

    attributes = GenericRelation(GenericAttribute, verbose_name=ugettext_lazy('attributes'))

    object_permissions = GenericRelation(GenericObjectPermission)
    tags = GenericRelation(TagLink)

    class Meta(NamedModel.Meta, FakeDeletableModel.Meta):
        verbose_name = ugettext_lazy('instrument type')
        verbose_name_plural = ugettext_lazy('instrument types')
        permissions = [
            ('view_instrumenttype', 'Can view instrument type'),
            ('manage_instrumenttype', 'Can manage instrument type'),
        ]

    def __str__(self):
        return self.user_code

    @property
    def is_default(self):
        return self.master_user.instrument_type_id == self.id if self.master_user_id else False


class Instrument(NamedModelAutoMapping, FakeDeletableModel):
    master_user = models.ForeignKey(MasterUser, related_name='instruments', verbose_name=ugettext_lazy('master user'))

    instrument_type = models.ForeignKey(InstrumentType, on_delete=models.PROTECT,
                                        verbose_name=ugettext_lazy('instrument type'))
    is_active = models.BooleanField(default=True, verbose_name=ugettext_lazy('is active'))
    pricing_currency = models.ForeignKey('currencies.Currency', on_delete=models.PROTECT,
                                         verbose_name=ugettext_lazy('pricing currency'))
    price_multiplier = models.FloatField(default=1.0, verbose_name=ugettext_lazy('price multiplier'))
    accrued_currency = models.ForeignKey('currencies.Currency', related_name='instruments_accrued',
                                         on_delete=models.PROTECT, verbose_name=ugettext_lazy('accrued currency'))
    accrued_multiplier = models.FloatField(default=1.0, verbose_name=ugettext_lazy('accrued multiplier'))

    payment_size_detail = models.ForeignKey(PaymentSizeDetail, on_delete=models.PROTECT, null=True, blank=True,
                                            verbose_name=ugettext_lazy('payment size detail'))

    default_price = models.FloatField(default=0.0, verbose_name=ugettext_lazy('default price'))
    default_accrued = models.FloatField(default=0.0, verbose_name=ugettext_lazy('default accrued'))

    user_text_1 = models.CharField(max_length=255, null=True, blank=True, verbose_name=ugettext_lazy('user text 1'),
                                   help_text=ugettext_lazy('User specified field 1'))
    user_text_2 = models.CharField(max_length=255, null=True, blank=True, verbose_name=ugettext_lazy('user text 2'),
                                   help_text=ugettext_lazy('User specified field 2'))
    user_text_3 = models.CharField(max_length=255, null=True, blank=True, verbose_name=ugettext_lazy('user text 3'),
                                   help_text=ugettext_lazy('User specified field 3'))

    reference_for_pricing = models.CharField(max_length=100, blank=True, default='',
                                             verbose_name=ugettext_lazy('reference for pricing'))
    daily_pricing_model = models.ForeignKey(DailyPricingModel, null=True, blank=True,
                                            verbose_name=ugettext_lazy('daily pricing model'))
    price_download_scheme = models.ForeignKey('integrations.PriceDownloadScheme', on_delete=models.PROTECT, null=True,
                                              blank=True, verbose_name=ugettext_lazy('price download scheme'))
    maturity_date = models.DateField(default=date.max, verbose_name=ugettext_lazy('maturity date'))
    maturity_price = models.FloatField(default=0.0, verbose_name=ugettext_lazy('maturity price'))

    attributes = GenericRelation(GenericAttribute, verbose_name=ugettext_lazy('attributes'))
    object_permissions = GenericRelation(GenericObjectPermission, verbose_name=ugettext_lazy('object permissions'))
    tags = GenericRelation(TagLink, verbose_name=ugettext_lazy('tags'))

    class Meta(NamedModel.Meta, FakeDeletableModel.Meta):
        verbose_name = ugettext_lazy('instrument')
        verbose_name_plural = ugettext_lazy('instruments')
        permissions = [
            ('view_instrument', 'Can view instrument'),
            ('manage_instrument', 'Can manage instrument'),
        ]
        ordering = ['user_code']

    @property
    def is_default(self):
        return self.master_user.instrument_id == self.id if self.master_user_id else False

    def rebuild_event_schedules(self):
        from poms.transactions.models import EventClass, NotificationClass
        # TODO: add validate equality before process

        # self.event_schedules.filter(is_auto_generated=True).delete()

        master_user = self.master_user
        instrument_type = self.instrument_type
        instrument_class = instrument_type.instrument_class

        try:
            event_schedule_config = master_user.instrument_event_schedule_config
        except ObjectDoesNotExist:
            event_schedule_config = EventScheduleConfig.create_default(master_user=master_user)

        notification_class_id = event_schedule_config.notification_class_id
        if notification_class_id is None:
            notification_class_id = NotificationClass.DONT_REACT

        events = list(self.event_schedules.prefetch_related('actions').filter(is_auto_generated=True))
        events_by_accrual = {e.accrual_calculation_schedule_id: e
                             for e in events if e.accrual_calculation_schedule_id is not None}
        events_by_factor = {e.factor_schedule_id: e
                            for e in events if e.factor_schedule_id is not None}

        processed = []

        # process accruals
        # accruals = list(self.accrual_calculation_schedules.order_by('accrual_start_date'))
        accruals = self.get_accrual_calculation_schedules_all()
        for i, accrual in enumerate(accruals):
            try:
                accrual_next = accruals[i + 1]
            except IndexError:
                accrual_next = None

            if instrument_class.has_regular_event:
                if instrument_type.regular_event:
                    e = EventSchedule()
                    e.instrument = self
                    e.accrual_calculation_schedule = accrual
                    e.is_auto_generated = True
                    e.name = event_schedule_config.name
                    e.description = event_schedule_config.description
                    e.event_class_id = EventClass.REGULAR
                    e.notification_class_id = notification_class_id
                    e.effective_date = accrual.first_payment_date
                    e.notify_in_n_days = event_schedule_config.notify_in_n_days
                    e.periodicity = accrual.periodicity
                    e.periodicity_n = accrual.periodicity_n
                    e.final_date = accrual_next.accrual_start_date if accrual_next else self.maturity_date

                    a = EventScheduleAction()
                    a.text = event_schedule_config.action_text
                    a.transaction_type = instrument_type.regular_event
                    a.is_sent_to_pending = event_schedule_config.action_is_sent_to_pending
                    a.is_book_automatic = event_schedule_config.action_is_book_automatic
                    a.button_position = 1

                    eold = events_by_accrual.get(accrual.id, None)
                    self._event_save(processed, e, a, eold)
                else:
                    raise ValueError('Field regular event in instrument type "%s" must be set' % instrument_type)

        if instrument_class.has_one_off_event:
            if instrument_type.one_off_event:
                e = EventSchedule()
                e.instrument = self
                e.is_auto_generated = True
                e.name = event_schedule_config.name
                e.description = event_schedule_config.description
                e.event_class_id = EventClass.ONE_OFF
                e.notification_class_id = notification_class_id
                e.effective_date = self.maturity_date
                e.notify_in_n_days = event_schedule_config.notify_in_n_days
                e.final_date = self.maturity_date

                a = EventScheduleAction()
                a.text = event_schedule_config.action_text
                a.transaction_type = instrument_type.one_off_event
                a.is_sent_to_pending = event_schedule_config.action_is_sent_to_pending
                a.is_book_automatic = event_schedule_config.action_is_book_automatic
                a.button_position = 1

                eold = None
                for e0 in events:
                    if e0.is_auto_generated and e0.event_class_id == EventClass.ONE_OFF and \
                            e0.accrual_calculation_schedule_id is None and e0.factor_schedule_id is None:
                        eold = e0
                        break
                self._event_save(processed, e, a, eold)
            else:
                raise ValueError('Field one-off event in instrument type "%s" must be set' % instrument_type)

        # process factors
        factors = list(self.factor_schedules.all())
        for i, f in enumerate(factors):
            if i == 0:
                continue
            try:
                fprev = factors[i - 1]
            except IndexError:
                fprev = None

            if isclose(f.factor_value, fprev.factor_value):
                transaction_type = instrument_type.factor_same
                if transaction_type is None:
                    continue
                    # raise ValueError('Field "factor same"  in instrument type "%s" must be set' % instrument_type)
            elif f.factor_value > fprev.factor_value:
                transaction_type = instrument_type.factor_up
                if transaction_type is None:
                    continue
                    # raise ValueError('Fields "factor up" in instrument type "%s" must be set' % instrument_type)
            else:
                transaction_type = instrument_type.factor_down
                if transaction_type is None:
                    continue
                    # raise ValueError('Fields "factor down" in instrument type "%s" must be set' % instrument_type)

            e = EventSchedule()
            e.instrument = self
            e.is_auto_generated = True
            e.factor_schedule = f
            e.name = event_schedule_config.name
            e.description = event_schedule_config.description
            e.event_class_id = EventClass.ONE_OFF
            e.notification_class_id = notification_class_id
            e.effective_date = f.effective_date
            e.notify_in_n_days = event_schedule_config.notify_in_n_days
            e.final_date = f.effective_date

            a = EventScheduleAction()
            a.text = event_schedule_config.action_text
            a.transaction_type = transaction_type
            a.is_sent_to_pending = event_schedule_config.action_is_sent_to_pending
            a.is_book_automatic = event_schedule_config.action_is_book_automatic
            a.button_position = 1

            eold = events_by_factor.get(f.id, None)
            self._event_save(processed, e, a, eold)

        self.event_schedules.filter(is_auto_generated=True).exclude(pk__in=processed).delete()

    def _event_to_dict(self, event, event_actions=None):
        # build dict from attrs for compare its
        if event is None:
            return None
        event_values = serializers.serialize("python", [event])[0]
        if event_actions is None and hasattr(event, 'actions'):
            event_actions = event_actions or event.actions.all()
        event_values['fields']['actions'] = serializers.serialize("python", event_actions)
        event_values.pop('pk')
        for action_values in event_values['fields']['actions']:
            action_values.pop('pk')
            action_values['fields'].pop('event_schedule')
        return event_values

    def _event_is_equal(self, event, event_actions, old_event, old_event_actions):
        # compare action by all attrs
        es = self._event_to_dict(event, event_actions)
        eolds = self._event_to_dict(old_event, old_event_actions)
        return es == eolds

    def _event_save(self, processed, event, event_action, old_event):
        # compare action by all attrs
        if not self._event_is_equal(event, [event_action], old_event, None):
            event.save()
            event_action.event_schedule = event
            event_action.save()
            processed.append(event.id)
        else:
            if old_event:
                processed.append(old_event.id)

    def get_accrual_calculation_schedules_all(self):
        accruals = list(self.accrual_calculation_schedules.all())

        if not accruals:
            return accruals

        if getattr(accruals[0], 'accrual_end_date', None) is not None:
            # already configured
            return accruals

        accruals = sorted(accruals, key=lambda x: x.accrual_start_date)

        a = None
        for next_a in accruals:
            if a is not None:
                a.accrual_end_date = next_a.accrual_start_date
            a = next_a
        if a:
            a.accrual_end_date = self.maturity_date

        return accruals

    def find_accrual(self, d):
        if d >= self.maturity_date:
            return None

        accruals = self.get_accrual_calculation_schedules_all()
        accrual = None
        for a in accruals:
            if a.accrual_start_date <= d:
                accrual = a

        return accrual

    def calculate_prices_accrued_price(self, begin_date=None, end_date=None):
        accruals = self.get_accrual_calculation_schedules_all()

        if not accruals:
            return

        existed_prices = PriceHistory.objects.filter(instrument=self, date__range=(begin_date, end_date))

        if begin_date is None and end_date is None:
            # used from admin
            for price in existed_prices:
                if price.date >= self.maturity_date:
                    continue
                accrued_price = self.get_accrued_price(price.date)
                if accrued_price is None:
                    accrued_price = 0.0
                price.accrued_price = accrued_price
                price.save(update_fields=['accrued_price'])

        else:
            existed_prices = {(p.pricing_policy_id, p.date): p for p in existed_prices}
            for pp in PricingPolicy.objects.filter(master_user=self.master_user):
                for dt in rrule.rrule(rrule.DAILY, dtstart=begin_date, until=end_date):
                    d = dt.date()
                    if d >= self.maturity_date:
                        continue
                    price = existed_prices.get((pp.id, d), None)
                    accrued_price = self.get_accrued_price(d)
                    if price is None:
                        if accrued_price is not None:
                            price = PriceHistory()
                            price.instrument = self
                            price.pricing_policy = pp
                            price.date = d
                            price.accrued_price = accrued_price
                            price.save()
                    else:
                        if accrued_price is None:
                            accrued_price = 0.0
                        price.accrued_price = accrued_price
                        price.save(update_fields=['accrued_price'])

    def get_accrual_size(self, price_date):
        if price_date >= self.maturity_date:
            return 0.0

        accrual = self.find_accrual(price_date)
        if accrual is None:
            return 0.0

        return accrual.accrual_size

    def get_accrual_factor(self, price_date):
        from poms.common.formula_accruals import coupon_accrual_factor

        if price_date >= self.maturity_date:
            # return self.maturity_price
            return 0.0

        accrual = self.find_accrual(price_date)
        if accrual is None:
            return 0.0

        factor = coupon_accrual_factor(accrual_calculation_schedule=accrual,
                                       dt1=accrual.accrual_start_date,
                                       dt2=price_date,
                                       dt3=accrual.first_payment_date)

        return factor

    def get_accrued_price(self, price_date):
        from poms.common.formula_accruals import coupon_accrual_factor

        if price_date >= self.maturity_date:
            # return self.maturity_price
            return 0.0

        accrual = self.find_accrual(price_date)
        if accrual is None:
            return 0.0

        factor = coupon_accrual_factor(accrual_calculation_schedule=accrual,
                                       dt1=accrual.accrual_start_date,
                                       dt2=price_date,
                                       dt3=accrual.first_payment_date)

        return accrual.accrual_size * factor

    def get_coupon(self, cpn_date, with_maturity=False, factor=False):
        if cpn_date == self.maturity_date:
            if with_maturity:
                return self.maturity_price, True
            else:
                return 0.0, False

        elif cpn_date > self.maturity_date:
            return 0.0, False

        accruals = self.get_accrual_calculation_schedules_all()
        for accrual in accruals:
            if accrual.accrual_start_date <= cpn_date < accrual.accrual_end_date:
                prev_d = accrual.accrual_start_date
                for i in range(0, 3652058):
                    stop = False
                    if i == 0:
                        d = accrual.first_payment_date
                    else:
                        try:
                            d = accrual.first_payment_date + accrual.periodicity.to_timedelta(
                                n=accrual.periodicity_n, i=i, same_date=accrual.accrual_start_date)
                        except (OverflowError, ValueError):  # year is out of range
                            return 0.0, False

                    if d >= accrual.accrual_end_date:
                        d = accrual.accrual_end_date - timedelta(days=1)
                        stop = True

                    if d == cpn_date:
                        val_or_factor = get_coupon(accrual, prev_d, d, maturity_date=self.maturity_date, factor=factor)
                        return val_or_factor, True

                    if stop or d >= accrual.accrual_end_date:
                        break

                    prev_d = d

        return 0.0, False

    def get_future_coupons(self, begin_date=None, with_maturity=False, factor=False):
        res = []
        accruals = self.get_accrual_calculation_schedules_all()
        for accrual in accruals:
            if begin_date >= accrual.accrual_end_date:
                continue

            prev_d = accrual.accrual_start_date
            for i in range(0, 3652058):
                stop = False
                if i == 0:
                    d = accrual.first_payment_date
                else:
                    try:
                        d = accrual.first_payment_date + accrual.periodicity.to_timedelta(
                            n=accrual.periodicity_n, i=i, same_date=accrual.accrual_start_date)
                    except (OverflowError, ValueError):  # year is out of range
                        break

                if d < begin_date:
                    prev_d = d
                    continue

                if d >= accrual.accrual_end_date:
                    d = accrual.accrual_end_date - timedelta(days=1)
                    stop = True

                val_or_factor = get_coupon(accrual, prev_d, d, maturity_date=self.maturity_date, factor=factor)
                res.append((d, val_or_factor))

                if stop or d >= accrual.accrual_end_date:
                    break

                prev_d = d

        if with_maturity:
            if factor:
                val_or_factor = 1.0
            else:
                val_or_factor = self.maturity_price
            res.append((self.maturity_date, val_or_factor))

        return res

    def get_factors(self):
        factors = list(self.factor_schedules.all())
        factors.sort(key=lambda x: x.effective_date)
        return factors

    def get_factor(self, fdate):
        res = None
        factors = self.get_factors()
        for f in factors:
            if f.effective_date < fdate:
                res = f
        if res:
            return res.factor_value
        return 1.0


class ManualPricingFormula(models.Model):
    instrument = models.ForeignKey(Instrument, related_name='manual_pricing_formulas',
                                   verbose_name=ugettext_lazy('instrument'))
    pricing_policy = models.ForeignKey(PricingPolicy, on_delete=models.PROTECT, related_name='manual_pricing_formulas',
                                       verbose_name=ugettext_lazy('pricing policy'))
    expr = models.CharField(max_length=255, blank=True, default='', verbose_name=ugettext_lazy('expression'))
    notes = models.TextField(blank=True, default='', verbose_name=ugettext_lazy('notes'))

    class Meta:
        verbose_name = ugettext_lazy('manual pricing formula')
        verbose_name_plural = ugettext_lazy('manual pricing formulas')
        unique_together = [
            ['instrument', 'pricing_policy']
        ]
        ordering = ['pricing_policy']

    def __str__(self):
        return self.expr


class PriceHistory(models.Model):
    instrument = models.ForeignKey(Instrument, related_name='prices', verbose_name=ugettext_lazy('instrument'))
    pricing_policy = models.ForeignKey(PricingPolicy, on_delete=models.PROTECT, null=True, blank=True,
                                       verbose_name=ugettext_lazy('pricing policy'))
    date = models.DateField(db_index=True, default=date_now, verbose_name=ugettext_lazy('date'))
    principal_price = models.FloatField(default=0.0, verbose_name=ugettext_lazy('principal price'))
    accrued_price = models.FloatField(default=0.0, verbose_name=ugettext_lazy('accrued price'))

    class Meta:
        verbose_name = ugettext_lazy('price history')
        verbose_name_plural = ugettext_lazy('price histories')
        unique_together = (
            ('instrument', 'pricing_policy', 'date',)
        )
        ordering = ['date']

    def __str__(self):
        # return '%s:%s:%s:%s:%s' % (
        #     self.instrument_id, self.pricing_policy_id, self.date, self.principal_price, self.accrued_price)
        return '%s;%s @%s' % (self.principal_price, self.accrued_price, self.date)


class AccrualCalculationSchedule(models.Model):
    instrument = models.ForeignKey(Instrument, related_name='accrual_calculation_schedules',
                                   verbose_name=ugettext_lazy('instrument'))
    accrual_start_date = models.DateField(default=date_now, verbose_name=ugettext_lazy('accrual start date'))
    accrual_end_date = None  # excluded date
    first_payment_date = models.DateField(default=date_now, verbose_name=ugettext_lazy('first payment date'))
    # TODO: is %
    accrual_size = models.FloatField(default=0.0, verbose_name=ugettext_lazy('accrual size'))
    accrual_calculation_model = models.ForeignKey(AccrualCalculationModel, on_delete=models.PROTECT,
                                                  verbose_name=ugettext_lazy('accrual calculation model'))
    periodicity = models.ForeignKey(Periodicity, on_delete=models.PROTECT, null=True, blank=True,
                                    verbose_name=ugettext_lazy('periodicity'))
    periodicity_n = models.IntegerField(default=0, verbose_name=ugettext_lazy('periodicity n'))
    notes = models.TextField(blank=True, default='', verbose_name=ugettext_lazy('notes'))

    class Meta:
        verbose_name = ugettext_lazy('accrual calculation schedule')
        verbose_name_plural = ugettext_lazy('accrual calculation schedules')
        ordering = ['accrual_start_date']

    def __str__(self):
        return '%s' % self.accrual_start_date


class InstrumentFactorSchedule(models.Model):
    instrument = models.ForeignKey(Instrument, related_name='factor_schedules',
                                   verbose_name=ugettext_lazy('instrument'))
    effective_date = models.DateField(default=date_now, verbose_name=ugettext_lazy('effective date'))
    factor_value = models.FloatField(default=0., verbose_name=ugettext_lazy('factor value'))

    class Meta:
        verbose_name = ugettext_lazy('instrument factor schedule')
        verbose_name_plural = ugettext_lazy('instrument factor schedules')
        ordering = ['effective_date']

    def __str__(self):
        return '%s' % self.effective_date


class EventSchedule(models.Model):
    instrument = models.ForeignKey(Instrument, related_name='event_schedules', verbose_name=ugettext_lazy('instrument'))

    # T O D O: name & description is expression
    # T O D O: default settings.POMS_EVENT_*
    name = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, verbose_name=ugettext_lazy('name'))
    description = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                   verbose_name=ugettext_lazy('description'))

    event_class = models.ForeignKey('transactions.EventClass', on_delete=models.PROTECT,
                                    verbose_name=ugettext_lazy('event class'))

    # T O D O: add to MasterUser defaults
    notification_class = models.ForeignKey('transactions.NotificationClass', on_delete=models.PROTECT,
                                           verbose_name=ugettext_lazy('notification class'))

    # TODO: is first_payment_date for regular
    # TODO: is instrument.maturity for one-off
    effective_date = models.DateField(null=True, blank=True, verbose_name=ugettext_lazy('effective date'))
    notify_in_n_days = models.PositiveIntegerField(default=0, verbose_name=ugettext_lazy('notify in N days'))

    periodicity = models.ForeignKey(Periodicity, null=True, blank=True, on_delete=models.PROTECT,
                                    verbose_name=ugettext_lazy('periodicity'))
    periodicity_n = models.IntegerField(default=0, verbose_name=ugettext_lazy('N'))
    # TODO: =see next accrual_calculation_schedule.accrual_start_date or instrument.maturity_date (if last)
    final_date = models.DateField(default=date.max, verbose_name=ugettext_lazy('final date'))  # excluded date

    is_auto_generated = models.BooleanField(default=False, verbose_name=ugettext_lazy('is auto generated'))
    accrual_calculation_schedule = models.ForeignKey(AccrualCalculationSchedule, null=True, blank=True, editable=False,
                                                     related_name='event_schedules',
                                                     verbose_name=ugettext_lazy('accrual calculation schedule'),
                                                     help_text=ugettext_lazy(
                                                         'Used for store link when is_auto_generated is True'))
    factor_schedule = models.ForeignKey(InstrumentFactorSchedule, null=True, blank=True, editable=False,
                                        related_name='event_schedules', verbose_name=ugettext_lazy('factor schedule'),
                                        help_text=ugettext_lazy('Used for store link when is_auto_generated is True'))

    class Meta:
        verbose_name = ugettext_lazy('event schedule')
        verbose_name_plural = ugettext_lazy('event schedules')
        ordering = ['effective_date']

    def __str__(self):
        return '#%s/#%s' % (self.id, self.instrument_id)

    @cached_property
    def all_dates(self):
        from poms.transactions.models import EventClass

        notify_in_n_days = timedelta(days=self.notify_in_n_days)

        # sdate = self.effective_date
        # edate = self.final_date

        dates = []

        def add_date(edate):
            ndate = edate - notify_in_n_days
            # if self.effective_date <= ndate < self.final_date or self.effective_date <= edate < self.final_date:
            #     dates.append((edate, ndate))
            dates.append((edate, ndate))

        if self.event_class_id == EventClass.ONE_OFF:
            # effective_date = self.effective_date
            # notification_date = effective_date - notify_in_n_days
            # if self.effective_date <= notification_date <= self.final_date or self.effective_date <= effective_date <= self.final_date:
            #     dates.append((effective_date, notification_date))
            add_date(self.effective_date)

        elif self.event_class_id == EventClass.REGULAR:
            for i in range(0, 3652058):
                stop = False
                try:
                    effective_date = self.effective_date + self.periodicity.to_timedelta(
                        n=self.periodicity_n, i=i, same_date=self.effective_date)
                except (OverflowError, ValueError):  # year is out of range
                    # effective_date = date.max
                    # stop = True
                    break

                if self.accrual_calculation_schedule_id is not None:
                    if effective_date >= self.final_date:
                        # magic date
                        effective_date = self.final_date - timedelta(days=1)
                        stop = True

                # notification_date = effective_date - notify_in_n_days
                # if self.effective_date <= notification_date <= self.final_date or self.effective_date <= effective_date <= self.final_date:
                #     dates.append((effective_date, notification_date))
                add_date(effective_date)

                if stop or effective_date >= self.final_date:
                    break

        return dates

    def check_date(self, now):
        # from poms.transactions.models import EventClass
        #
        # notification_date_correction = timedelta(days=self.notify_in_n_days)
        #
        # if self.event_class_id == EventClass.ONE_OFF:
        #     effective_date = self.effective_date
        #     notification_date = effective_date - notification_date_correction
        #     # _l.debug('effective_date=%s, notification_date=%s', effective_date, notification_date)
        #
        #     if notification_date == now or effective_date == now:
        #         return True, effective_date, notification_date
        #
        # elif self.event_class_id == EventClass.REGULAR:
        #     for i in range(0, settings.INSTRUMENT_EVENTS_REGULAR_MAX_INTERVALS):
        #         try:
        #             effective_date = self.effective_date + self.periodicity.to_timedelta(
        #                 n=self.periodicity_n, i=i, same_date=self.effective_date)
        #         except (OverflowError, ValueError):  # year is out of range
        #             effective_date = date.max
        #
        #         if self.accrual_calculation_schedule_id is not None:
        #             if effective_date > self.final_date:
        #                 # magic date
        #                 effective_date = self.final_date - timedelta(days=1)
        #
        #         notification_date = effective_date - notification_date_correction
        #
        #         if notification_date == now or effective_date == now:
        #             return True, effective_date, notification_date
        #
        #         if notification_date > now and effective_date > now:
        #             break
        #
        # return False, None, None
        for edate, ndate in self.all_dates:
            if edate == now or ndate == now:
                return True, edate, ndate
        return False, None, None

    def check_effective_date(self, now):
        for edate, ndate in self.all_dates:
            if edate == now:
                return True, edate, ndate
        return False, None, None

    def check_notification_date(self, now):
        for edate, ndate in self.all_dates:
            if ndate == now:
                return True, edate, ndate
        return False, None, None


class EventScheduleAction(models.Model):
    # TODO: for auto generated always one
    event_schedule = models.ForeignKey(EventSchedule, related_name='actions',
                                       verbose_name=ugettext_lazy('event schedule'))
    transaction_type = models.ForeignKey('transactions.TransactionType', on_delete=models.PROTECT,
                                         verbose_name=ugettext_lazy('transaction type'))
    # T O D O: on auto generate fill 'Book: ' + transaction_type
    text = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                            verbose_name=ugettext_lazy('text'))
    # T O D O: add to MasterUser defaults
    is_sent_to_pending = models.BooleanField(default=True, verbose_name=ugettext_lazy('is sent to pending'))
    # T O D O: add to MasterUser defaults
    # T O D O: rename to: is_book_automatic (used when now notification)
    is_book_automatic = models.BooleanField(default=True, verbose_name=ugettext_lazy('is book automatic'))
    button_position = models.IntegerField(default=0, verbose_name=ugettext_lazy('button position'))

    class Meta:
        verbose_name = ugettext_lazy('event schedule action')
        verbose_name_plural = ugettext_lazy('event schedule actions')
        ordering = ['is_book_automatic', 'button_position']

    def __str__(self):
        return self.text


class GeneratedEvent(models.Model):
    NEW = 1
    INFORMED = 2
    BOOKED_SYSTEM_DEFAULT = 3
    BOOKED_USER_ACTIONS = 4
    BOOKED_USER_DEFAULT = 5

    BOOKED_PENDING_SYSTEM_DEFAULT = 6
    BOOKED_PENDING_USER_ACTIONS = 7
    BOOKED_PENDING_USER_DEFAULT = 8

    ERROR = 9

    STATUS_CHOICES = (
        (NEW, ugettext_lazy('New')),
        (INFORMED, ugettext_lazy('Informed')),
        (BOOKED_SYSTEM_DEFAULT, ugettext_lazy('Booked (system, default)')),
        (BOOKED_USER_ACTIONS, ugettext_lazy('Booked (user, actions)')),
        (BOOKED_USER_DEFAULT, ugettext_lazy('Booked (user, default)')),

        (BOOKED_PENDING_SYSTEM_DEFAULT, ugettext_lazy('Booked, pending (system, default)')),
        (BOOKED_PENDING_USER_ACTIONS, ugettext_lazy('Booked, pending (user, actions)')),
        (BOOKED_PENDING_USER_DEFAULT, ugettext_lazy('Booked, pending (user, default)')),
        (ERROR, ugettext_lazy('Error')),
    )

    master_user = models.ForeignKey(MasterUser, related_name='generated_events',
                                    verbose_name=ugettext_lazy('master user'))

    effective_date = models.DateField(default=date_now, db_index=True, verbose_name=ugettext_lazy('effective date'))
    effective_date_notified = models.BooleanField(default=False, db_index=True,
                                                  verbose_name=ugettext_lazy('effective date notified'))
    notification_date = models.DateField(default=date_now, db_index=True,
                                         verbose_name=ugettext_lazy('notification date'))
    notification_date_notified = models.BooleanField(default=False, db_index=True,
                                                     verbose_name=ugettext_lazy('notification date notified'))

    status = models.PositiveSmallIntegerField(default=NEW, choices=STATUS_CHOICES, db_index=True,
                                              verbose_name=ugettext_lazy('status'))
    status_date = models.DateTimeField(default=timezone.now, db_index=True, verbose_name=ugettext_lazy('status date'))

    event_schedule = models.ForeignKey(EventSchedule, null=True, blank=True, on_delete=models.SET_NULL,
                                       related_name='generated_events', verbose_name=ugettext_lazy('event schedule'))

    instrument = models.ForeignKey('instruments.Instrument', null=True, blank=True, on_delete=models.PROTECT,
                                   related_name='generated_events', verbose_name=ugettext_lazy('instrument'))
    portfolio = models.ForeignKey('portfolios.Portfolio', null=True, blank=True, on_delete=models.PROTECT,
                                  related_name='generated_events', verbose_name=ugettext_lazy('portfolio'))
    account = models.ForeignKey('accounts.Account', null=True, blank=True, on_delete=models.PROTECT,
                                related_name='generated_events', verbose_name=ugettext_lazy('account'))
    strategy1 = models.ForeignKey('strategies.Strategy1', null=True, blank=True, on_delete=models.PROTECT,
                                  related_name='generated_events', verbose_name=ugettext_lazy('strategy1'))
    strategy2 = models.ForeignKey('strategies.Strategy2', null=True, blank=True, on_delete=models.PROTECT,
                                  related_name='generated_events', verbose_name=ugettext_lazy('strategy2'))
    strategy3 = models.ForeignKey('strategies.Strategy3', null=True, blank=True, on_delete=models.PROTECT,
                                  related_name='generated_events', verbose_name=ugettext_lazy('strategy3'))
    position = models.FloatField(default=0.0, verbose_name=ugettext_lazy('position'))

    action = models.ForeignKey(EventScheduleAction, null=True, blank=True, on_delete=models.SET_NULL,
                               related_name='generated_events', verbose_name=ugettext_lazy('action'))
    transaction_type = models.ForeignKey('transactions.TransactionType', null=True, blank=True,
                                         on_delete=models.PROTECT, related_name='generated_events',
                                         verbose_name=ugettext_lazy('transaction type'))
    complex_transaction = models.ForeignKey('transactions.ComplexTransaction', null=True, blank=True,
                                            on_delete=models.PROTECT, related_name='generated_events',
                                            verbose_name=ugettext_lazy('complex transaction'))
    member = models.ForeignKey('users.Member', null=True, blank=True, on_delete=models.SET_NULL,
                               verbose_name=ugettext_lazy('member'))

    class Meta:
        verbose_name = ugettext_lazy('generated event')
        verbose_name_plural = ugettext_lazy('generated events')
        ordering = ['effective_date']

    def __str__(self):
        return 'Event #%s' % self.id

    def processed(self, member, action, complex_transaction, status=BOOKED_SYSTEM_DEFAULT):
        self.member = member
        self.action = action

        self.status = status

        self.status_date = timezone.now()
        self.transaction_type = action.transaction_type
        self.complex_transaction = complex_transaction

    def is_notify_on_effective_date(self, now=None):
        from poms.transactions.models import NotificationClass
        if not self.effective_date_notified:
            now = now or date_now()
            notification_class = self.event_schedule.notification_class

            print('self event %s ' % self)
            print('self.event_schedule %s ' % self.event_schedule)
            print('self.now %s ' % now)
            print('self.effective_date %s ' % self.effective_date)
            print(
                'self.notification_class.is_notify_on_effective_date %s ' % notification_class.is_notify_on_effective_date)

            return self.effective_date == now and notification_class.is_notify_on_effective_date
        return False

    def is_notify_on_notification_date(self, now=None):
        from poms.transactions.models import NotificationClass
        if not self.effective_date_notified:
            now = now or date_now()

            notification_class = self.event_schedule.notification_class

            print('self event %s ' % self)
            print('self.event_schedule %s ' % self.event_schedule)
            print('self.now %s ' % now)
            print('self.notification_date %s ' % self.notification_date)
            print(
                'self.notification_class.is_notify_on_notification_date %s ' % notification_class.is_notify_on_notification_date)

            return self.notification_date == now and notification_class.is_notify_on_notification_date
        return False

    def is_notify_on_date(self, now=None):
        return self.is_notify_on_effective_date(now) or self.is_notify_on_notification_date(now)

    def is_apply_default_on_effective_date(self, now=None):
        from poms.transactions.models import NotificationClass
        if self.status == GeneratedEvent.NEW:
            now = now or date_now()
            notification_class = self.event_schedule.notification_class
            return self.effective_date == now and notification_class.is_apply_default_on_effective_date
        return False

    def is_apply_default_on_notification_date(self, now=None):
        from poms.transactions.models import NotificationClass
        if self.status == GeneratedEvent.NEW:
            now = now or date_now()
            notification_class = self.event_schedule.notification_class
            return self.notification_date == now and notification_class.is_apply_default_on_notification_date
        return False

    def is_apply_default_on_date(self, now=None):
        return self.is_apply_default_on_effective_date(now) or self.is_apply_default_on_notification_date(now)

    def is_need_reaction_on_effective_date(self, now=None):
        from poms.transactions.models import NotificationClass
        if self.status == GeneratedEvent.NEW:
            now = now or date_now()
            notification_class = self.event_schedule.notification_class
            return self.effective_date == now and notification_class.is_need_reaction_on_effective_date
        return False

    def is_need_reaction_on_notification_date(self, now=None):
        from poms.transactions.models import NotificationClass
        if self.status == GeneratedEvent.NEW:
            now = now or date_now()
            notification_class = self.event_schedule.notification_class
            return self.notification_date == now and notification_class.is_need_reaction_on_notification_date
        return False

    def is_need_reaction_on_date(self, now=None):
        return self.is_need_reaction_on_effective_date(now) or self.is_need_reaction_on_notification_date(now)

    def get_default_action(self, actions=None):
        if actions is None:
            actions = self.event_schedule.actions.all()
        for a in actions:
            if a.is_book_automatic:
                return a
        return None

    def generate_text(self, exr, names=None, context=None):
        names = names or {}
        names.update({
            'effective_date': self.effective_date,
            'notification_date': self.notification_date,
            'instrument': self.instrument,
            'portfolio': self.portfolio,
            'account': self.account,
            'strategy1': self.strategy1,
            'strategy2': self.strategy2,
            'strategy3': self.strategy3,
            'position': self.position,
        })
        # import json
        # print(json.dumps(names, indent=2))
        try:
            return formula.safe_eval(exr, names=names, context=context)
        except formula.InvalidExpression as e:
            return '<InvalidExpression>'


class EventScheduleConfig(models.Model):
    master_user = models.OneToOneField('users.MasterUser', related_name='instrument_event_schedule_config',
                                       verbose_name=ugettext_lazy('master user'))

    name = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                            verbose_name=ugettext_lazy('name'))
    description = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                   verbose_name=ugettext_lazy('description'))
    notification_class = models.ForeignKey('transactions.NotificationClass', null=True, blank=True,
                                           on_delete=models.PROTECT, verbose_name=ugettext_lazy('notification class'))
    notify_in_n_days = models.PositiveSmallIntegerField(default=0, verbose_name=ugettext_lazy('notify in N days'))
    action_text = models.CharField(max_length=255, blank=True, default='', verbose_name=ugettext_lazy('action text'))
    action_is_sent_to_pending = models.BooleanField(default=True,
                                                    verbose_name=ugettext_lazy('action is sent to pending'))
    action_is_book_automatic = models.BooleanField(default=True, verbose_name=ugettext_lazy('action is book automatic'))

    class Meta:
        verbose_name = ugettext_lazy('event schedule config')
        verbose_name_plural = ugettext_lazy('event schedule configs')

    def __str__(self):
        return ugettext('event schedule config')

    @staticmethod
    def create_default(master_user):
        from poms.transactions.models import NotificationClass

        return EventScheduleConfig.objects.create(
            master_user=master_user,
            name='""',
            description='""',
            # notification_class=NotificationClass.objects.get(pk=NotificationClass.DONT_REACT),
            notification_class_id=NotificationClass.DONT_REACT,
            notify_in_n_days=0,
            action_text='""',
            action_is_sent_to_pending=False,
            action_is_book_automatic=True
        )
