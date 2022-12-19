from __future__ import unicode_literals

import json
import logging
import traceback
from datetime import date, timedelta, datetime

from dateutil import relativedelta, rrule
from django.contrib.contenttypes.fields import GenericRelation
from django.core import serializers
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy
from math import isnan

from poms.common import formula
from poms.common.constants import SYSTEM_VALUE_TYPES, SystemValueType
from poms.common.formula_accruals import get_coupon, f_duration, f_xirr
from poms.common.models import NamedModel, AbstractClassModel, FakeDeletableModel, EXPRESSION_FIELD_LENGTH, \
    DataTimeStampedModel
from poms.common.utils import date_now, isclose
from poms.common.wrapper_models import NamedModelAutoMapping
from poms.currencies.models import CurrencyHistory
from poms.obj_attrs.models import GenericAttribute, GenericAttributeType
from poms.obj_perms.models import GenericObjectPermission
from poms.pricing.models import InstrumentPricingScheme, CurrencyPricingScheme, InstrumentPricingPolicy
from poms.users.models import MasterUser, EcosystemDefault

_l = logging.getLogger('poms.instruments')


class InstrumentClass(AbstractClassModel):
    GENERAL = 1
    EVENT_AT_MATURITY = 2
    REGULAR_EVENT_AT_MATURITY = 3
    PERPETUAL_REGULAR_EVENT = 4
    CONTRACT_FOR_DIFFERENCE = 5
    DEFAULT = 6

    CLASSES = (
        (GENERAL, 'GENERAL', gettext_lazy("General Class")),
        (EVENT_AT_MATURITY, 'EVENT_AT_MATURITY', gettext_lazy("Event at Maturity")),
        (REGULAR_EVENT_AT_MATURITY, 'REGULAR_EVENT_AT_MATURITY', gettext_lazy("Regular Event with Maturity")),
        (PERPETUAL_REGULAR_EVENT, 'PERPETUAL_REGULAR_EVENT', gettext_lazy("Perpetual Regular Event")),
        (CONTRACT_FOR_DIFFERENCE, 'CONTRACT_FOR_DIFFERENCE', gettext_lazy("Contract for Difference")),
        (DEFAULT, '-', gettext_lazy("Default"))
    )

    class Meta(AbstractClassModel.Meta):
        verbose_name = gettext_lazy('instrument class')
        verbose_name_plural = gettext_lazy('instrument classes')

    @property
    def has_one_off_event(self):
        return self.id in [self.EVENT_AT_MATURITY, self.REGULAR_EVENT_AT_MATURITY]

    @property
    def has_regular_event(self):
        return self.id in [self.REGULAR_EVENT_AT_MATURITY, self.PERPETUAL_REGULAR_EVENT]


# DEPRECATED (25.05.2020), delete soon
class DailyPricingModel(AbstractClassModel):
    SKIP = 1
    FORMULA_ALWAYS = 2
    FORMULA_IF_OPEN = 3
    PROVIDER_ALWAYS = 4
    PROVIDER_IF_OPEN = 5
    DEFAULT = 6
    CLASSES = (
        (SKIP, 'SKIP', gettext_lazy("No Pricing (no Price History)")),
        (FORMULA_ALWAYS, 'FORMULA_ALWAYS',
         gettext_lazy("Don't download, just apply Formula / Pricing Policy (always)")),
        (FORMULA_IF_OPEN, 'FORMULA_IF_OPEN',
         gettext_lazy("Download & apply Formula / Pricing Policy (if non-zero position)")),
        (PROVIDER_ALWAYS, 'PROVIDER_ALWAYS', gettext_lazy("Download & apply Formula / Pricing Policy (always)")),
        (PROVIDER_IF_OPEN, 'PROVIDER_IF_OPEN',
         gettext_lazy("Don't download, just apply Formula / Pricing Policy (if non-zero position)")),
        (DEFAULT, '-', gettext_lazy("Use Default Price (no Price History)"))
    )

    class Meta(AbstractClassModel.Meta):
        verbose_name = gettext_lazy('daily pricing model')
        verbose_name_plural = gettext_lazy('daily pricing models')


class PricingCondition(AbstractClassModel):
    NO_VALUATION = 1
    RUN_VALUATION_IF_NON_ZERO = 2
    RUN_VALUATION_ALWAYS = 3

    CLASSES = (
        (NO_VALUATION, 'NO_VALUATION', gettext_lazy("Don't Run Valuation")),
        (RUN_VALUATION_IF_NON_ZERO, 'RUN_VALUATION_IF_OPEN', gettext_lazy("Run Valuation: if non-zero position")),
        (RUN_VALUATION_ALWAYS, 'RUN_VALUATION_ALWAYS', gettext_lazy("Run Valuation: always"))
    )

    class Meta(AbstractClassModel.Meta):
        verbose_name = gettext_lazy('pricing condition')
        verbose_name_plural = gettext_lazy('pricing conditions ')

        base_manager_name = 'objects'


class ExposureCalculationModel(AbstractClassModel):
    MARKET_VALUE = 1
    PRICE_EXPOSURE = 2
    DELTA_ADJUSTED_PRICE_EXPOSURE = 3
    UNDERLYING_LONG_SHORT_EXPOSURE_NET = 4
    UNDERLYING_LONG_SHORT_EXPOSURE_SPLIT = 5

    CLASSES = (
        (MARKET_VALUE, 'MARKET_VALUE', gettext_lazy("Market value")),
        (PRICE_EXPOSURE, 'PRICE_EXPOSURE', gettext_lazy("Price exposure")),
        (DELTA_ADJUSTED_PRICE_EXPOSURE, 'DELTA_ADJUSTED_PRICE_EXPOSURE', gettext_lazy("Delta adjusted price exposure")),
        (UNDERLYING_LONG_SHORT_EXPOSURE_NET, 'UNDERLYING_LONG_SHORT_EXPOSURE_NET',
         gettext_lazy("Underlying long short exposure net")),
        (UNDERLYING_LONG_SHORT_EXPOSURE_SPLIT, 'UNDERLYING_LONG_SHORT_EXPOSURE_SPLIT',
         gettext_lazy("Underlying long short exposure split"))
    )

    class Meta(AbstractClassModel.Meta):
        verbose_name = gettext_lazy('Exposure calculation model')
        verbose_name_plural = gettext_lazy('Exposure calculation models ')


# <select id="u948_input" class="u948_input">
#           <option class="u948_input_option" value="Zero">Zero</option>
#           <option class="u948_input_option" value="Long Underlying Instrument Price Exposure">Long Underlying Instrument Price Exposure</option>
#           <option class="u948_input_option" value="Long Underlying Instrument Price Delta-adjusted Exposure">Long Underlying Instrument Price Delta-adjusted Exposure</option>
#           <option class="u948_input_option" value="Long Underlying Currency FX Rate Exposure">Long Underlying Currency FX Rate Exposure</option>
#           <option class="u948_input_option" value="Long Underlying Currency FX Rate Delta-adjusted Exposure">Long Underlying Currency FX Rate Delta-adjusted Exposure</option>
#         </select>

class LongUnderlyingExposure(AbstractClassModel):
    ZERO = 1
    LONG_UNDERLYING_INSTRUMENT_PRICE_EXPOSURE = 2
    LONG_UNDERLYING_INSTRUMENT_PRICE_DELTA = 3
    LONG_UNDERLYING_CURRENCY_FX_RATE_EXPOSURE = 4
    LONG_UNDERLYING_CURRENCY_FX_RATE_DELTA_ADJUSTED_EXPOSURE = 5

    CLASSES = (
        (ZERO, 'ZERO', gettext_lazy("Zero")),
        (LONG_UNDERLYING_INSTRUMENT_PRICE_EXPOSURE, 'LONG_UNDERLYING_INSTRUMENT_PRICE_EXPOSURE',
         gettext_lazy("Long Underlying Instrument Price Exposure")),
        (LONG_UNDERLYING_INSTRUMENT_PRICE_DELTA, 'LONG_UNDERLYING_INSTRUMENT_PRICE_DELTA',
         gettext_lazy("Long Underlying Instrument Price Delta")),
        (LONG_UNDERLYING_CURRENCY_FX_RATE_EXPOSURE, 'LONG_UNDERLYING_CURRENCY_FX_RATE_EXPOSURE',
         gettext_lazy("Long Underlying Currency FX Rate Exposure")),
        (LONG_UNDERLYING_CURRENCY_FX_RATE_DELTA_ADJUSTED_EXPOSURE,
         'LONG_UNDERLYING_CURRENCY_FX_RATE_DELTA_ADJUSTED_EXPOSURE',
         gettext_lazy("Long Underlying Currency FX Rate Delta-adjusted Exposure"))
    )

    class Meta(AbstractClassModel.Meta):
        verbose_name = gettext_lazy('Long underlying exposure')
        verbose_name_plural = gettext_lazy('Long underlying exposure ')


class ShortUnderlyingExposure(AbstractClassModel):
    ZERO = 1
    SHORT_UNDERLYING_INSTRUMENT_PRICE_EXPOSURE = 2
    SHORT_UNDERLYING_INSTRUMENT_PRICE_DELTA = 3
    SHORT_UNDERLYING_CURRENCY_FX_RATE_EXPOSURE = 4
    SHORT_UNDERLYING_CURRENCY_FX_RATE_DELTA_ADJUSTED_EXPOSURE = 5

    CLASSES = (
        (ZERO, 'ZERO', gettext_lazy("Zero")),
        (SHORT_UNDERLYING_INSTRUMENT_PRICE_EXPOSURE, 'SHORT_UNDERLYING_INSTRUMENT_PRICE_EXPOSURE',
         gettext_lazy("Short Underlying Instrument Price Exposure")),
        (SHORT_UNDERLYING_INSTRUMENT_PRICE_DELTA, 'SHORT_UNDERLYING_INSTRUMENT_PRICE_DELTA',
         gettext_lazy("Short Underlying Instrument Price Delta")),
        (SHORT_UNDERLYING_CURRENCY_FX_RATE_EXPOSURE, 'SHORT_UNDERLYING_CURRENCY_FX_RATE_EXPOSURE',
         gettext_lazy("Short Underlying Currency FX Rate Exposure")),
        (SHORT_UNDERLYING_CURRENCY_FX_RATE_DELTA_ADJUSTED_EXPOSURE,
         'SHORT_UNDERLYING_CURRENCY_FX_RATE_DELTA_ADJUSTED_EXPOSURE',
         gettext_lazy("Short Underlying Currency FX Rate Delta-adjusted Exposure"))
    )

    class Meta(AbstractClassModel.Meta):
        verbose_name = gettext_lazy('Short underlying exposure')
        verbose_name_plural = gettext_lazy('Short underlying exposure ')


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
        (NONE, 'NONE', gettext_lazy("none")),
        (ACT_ACT, 'ACT_ACT', gettext_lazy("ACT/ACT")),
        (ACT_ACT_ISDA, 'ACT_ACT_ISDA', gettext_lazy("ACT/ACT - ISDA")),
        (ACT_360, 'ACT_360', gettext_lazy("ACT/360")),
        (ACT_365, 'ACT_365', gettext_lazy("ACT/365")),
        (ACT_365_25, 'ACT_365_25', gettext_lazy("Act/365.25")),
        (ACT_365_366, 'ACT_365_366', gettext_lazy("Act/365(366)")),
        (ACT_1_365, 'ACT_1_365', gettext_lazy("Act+1/365")),
        (ACT_1_360, 'ACT_1_360', gettext_lazy("Act+1/360")),
        # (C_30_ACT, 'C_30_ACT', gettext_lazy("30/ACT")),
        (C_30_360, 'C_30_360', gettext_lazy("30/360")),
        (C_30_360_NO_EOM, 'C_30_360_NO_EOM', gettext_lazy("30/360 (NO EOM)")),
        (C_30E_P_360_ITL, 'C_30E_P_360_ITL', gettext_lazy("30E+/360.ITL")),
        (NL_365, 'NL_365', gettext_lazy("NL/365")),
        (NL_365_NO_EOM, 'NL_365_NO_EOM', gettext_lazy("NL/365 (NO-EOM)")),
        (ISMA_30_360, 'ISMA_30_360', gettext_lazy("ISMA-30/360")),
        (ISMA_30_360_NO_EOM, 'ISMA_30_360_NO_EOM', gettext_lazy("ISMA-30/360 (NO EOM)")),
        (US_MINI_30_360_EOM, 'US_MINI_30_360_EOM', gettext_lazy("US MUNI-30/360 (EOM)")),
        (US_MINI_30_360_NO_EOM, 'US_MINI_30_360_NO_EOM', gettext_lazy("US MUNI-30/360 (NO EOM)")),
        (BUS_DAYS_252, 'BUS_DAYS_252', gettext_lazy("BUS DAYS/252")),
        (GERMAN_30_360_EOM, 'GERMAN_30_360_EOM', gettext_lazy("GERMAN-30/360 (EOM)")),
        (GERMAN_30_360_NO_EOM, 'GERMAN_30_360_NO_EOM', gettext_lazy("GERMAN-30/360 (NO EOM)")),
        (REVERSED_ACT_365, 'REVERSED_ACT_365', gettext_lazy("Reversed ACT/365")),
        (C_30E_P_360, 'C_30E_P_360', gettext_lazy('30E+/360')),
        (DEFAULT, '-', gettext_lazy('Default'))
    )

    class Meta(AbstractClassModel.Meta):
        verbose_name = gettext_lazy('accrual calculation model')
        verbose_name_plural = gettext_lazy('accrual calculation models')


class PaymentSizeDetail(AbstractClassModel):
    PERCENT = 1
    PER_ANNUM = 2
    PER_QUARTER = 3
    PER_MONTH = 4
    PER_WEEK = 5
    PER_DAY = 6
    DEFAULT = 7
    CLASSES = (
        (PERCENT, 'PERCENT', gettext_lazy("% per annum")),
        (PER_ANNUM, 'PER_ANNUM', gettext_lazy("per annum")),
        (PER_QUARTER, 'PER_QUARTER', gettext_lazy("per quarter")),
        (PER_MONTH, 'PER_MONTH', gettext_lazy("per month")),
        (PER_WEEK, 'PER_WEEK', gettext_lazy("per week")),
        (PER_DAY, 'PER_DAY', gettext_lazy("per day")),
        (DEFAULT, '-', gettext_lazy("Default")),
    )

    class Meta(AbstractClassModel.Meta):
        verbose_name = gettext_lazy('payment size detail')
        verbose_name_plural = gettext_lazy('payment size details')


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
        (N_DAY, 'N_DAY', gettext_lazy("N Days")),
        (N_WEEK_EOBW, 'N_WEEK_EOBW', gettext_lazy("N Weeks (eobw)")),
        (N_MONTH_EOM, 'N_MONTH_EOM', gettext_lazy("N Months (eom)")),
        (N_MONTH_SAME_DAY, 'N_MONTH_SAME_DAY', gettext_lazy("N Months (same date)")),
        (N_YEAR_EOY, 'N_YEAR_EOY', gettext_lazy("N Years (eoy)")),
        (N_YEAR_SAME_DAY, 'N_YEAR_SAME_DAY', gettext_lazy("N Years (same date)")),

        (WEEKLY, 'WEEKLY', gettext_lazy('Weekly')),
        (MONTHLY, 'MONTHLY', gettext_lazy('Monthly')),
        (BIMONTHLY, 'BIMONTHLY', gettext_lazy('Bimonthly')),
        (QUARTERLY, 'QUARTERLY', gettext_lazy('Quarterly')),
        (SEMI_ANNUALLY, 'SEMI_ANNUALLY', gettext_lazy('Semi-annually')),
        (ANNUALLY, 'ANNUALLY', gettext_lazy('Annually')),

        (DEFAULT, '-', gettext_lazy('-')),
    )

    class Meta(AbstractClassModel.Meta):
        verbose_name = gettext_lazy('periodicity')
        verbose_name_plural = gettext_lazy('periodicities')

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
        (AVCO, 'AVCO', gettext_lazy('AVCO')),
        (FIFO, 'FIFO', gettext_lazy('FIFO')),
        # (LIFO, gettext_lazy('LIFO')),
    )

    class Meta(AbstractClassModel.Meta):
        verbose_name = gettext_lazy('cost method')
        verbose_name_plural = gettext_lazy('cost methods')


class Country(DataTimeStampedModel):
    name = models.CharField(max_length=255, verbose_name=gettext_lazy('name'))
    user_code = models.CharField(max_length=255, blank=True, default='', verbose_name=gettext_lazy('user code'))
    short_name = models.CharField(max_length=255, blank=True, default='', verbose_name=gettext_lazy('short name'))
    description = models.TextField(blank=True, default='', verbose_name=gettext_lazy('description'))

    alpha_2 = models.CharField(max_length=255, null=True, blank=True, verbose_name=gettext_lazy('alpha 2'))
    alpha_3 = models.CharField(max_length=255, null=True, blank=True, verbose_name=gettext_lazy('alpha 3'))
    country_code = models.CharField(max_length=255, null=True, blank=True, verbose_name=gettext_lazy('country code'))
    iso_3166_2 = models.CharField(max_length=255, null=True, blank=True, verbose_name=gettext_lazy('iso_3166_2'))
    region = models.CharField(max_length=255, null=True, blank=True, verbose_name=gettext_lazy('region'))
    sub_region = models.CharField(max_length=255, null=True, blank=True, verbose_name=gettext_lazy('sub region'))
    intermediate_region = models.CharField(max_length=255, null=True, blank=True,
                                           verbose_name=gettext_lazy('intermediate region'))
    region_code = models.CharField(max_length=255, null=True, blank=True, verbose_name=gettext_lazy('region code'))
    sub_region_code = models.CharField(max_length=255, null=True, blank=True,
                                       verbose_name=gettext_lazy('sub region code'))
    intermediate_region_code = models.CharField(max_length=255, null=True, blank=True,
                                                verbose_name=gettext_lazy('intermediate region code'))


class PricingPolicy(NamedModel, DataTimeStampedModel):
    # DISABLED = 0
    # BLOOMBERG = 1
    # TYPES = (
    #     (DISABLED, gettext_lazy('Disabled')),
    #     (BLOOMBERG, gettext_lazy('Bloomberg')),
    # )

    master_user = models.ForeignKey(MasterUser, related_name='pricing_policies',
                                    verbose_name=gettext_lazy('master user'), on_delete=models.CASCADE)
    # type = models.PositiveIntegerField(default=DISABLED, choices=TYPES)

    # expr - DEPRECATED
    expr = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, default='', blank=True, null=True,
                            verbose_name=gettext_lazy('expression'))

    default_instrument_pricing_scheme = models.ForeignKey(InstrumentPricingScheme, null=True, blank=True,
                                                          verbose_name=gettext_lazy(
                                                              'default instrument pricing scheme'),
                                                          on_delete=models.SET_NULL)
    default_currency_pricing_scheme = models.ForeignKey(CurrencyPricingScheme, null=True, blank=True,
                                                        verbose_name=gettext_lazy('default currency pricing scheme'),
                                                        on_delete=models.SET_NULL)

    class Meta(AbstractClassModel.Meta):
        verbose_name = gettext_lazy('pricing policy')
        verbose_name_plural = gettext_lazy('pricing policies')
        unique_together = [
            ['master_user', 'user_code']
        ]
        ordering = ['user_code']

        base_manager_name = 'objects'

    # def delete(self, *args, **kwargs):
    #
    #     CurrencyPricingPolicy.objects.filter(pricing_policy=self).delete()
    #     InstrumentTypePricingPolicy.objects.filter(pricing_policy=self).delete()
    #     InstrumentPricingPolicy.objects.filter(pricing_policy=self).delete()
    #
    #     super(PricingPolicy, self).delete(*args, **kwargs)


class InstrumentType(NamedModelAutoMapping, FakeDeletableModel, DataTimeStampedModel):
    master_user = models.ForeignKey(MasterUser, related_name='instrument_types',
                                    verbose_name=gettext_lazy('master user'), on_delete=models.CASCADE)
    instrument_class = models.ForeignKey(InstrumentClass, related_name='instrument_types', on_delete=models.PROTECT,
                                         verbose_name=gettext_lazy('instrument class'))

    one_off_event = models.ForeignKey('transactions.TransactionType', null=True, blank=True, on_delete=models.PROTECT,
                                      related_name='+', verbose_name=gettext_lazy('one-off event'))
    regular_event = models.ForeignKey('transactions.TransactionType', null=True, blank=True, on_delete=models.PROTECT,
                                      related_name='+', verbose_name=gettext_lazy('regular event'))

    factor_same = models.ForeignKey('transactions.TransactionType', null=True, blank=True, on_delete=models.PROTECT,
                                    related_name='+', verbose_name=gettext_lazy('factor same'))
    factor_up = models.ForeignKey('transactions.TransactionType', null=True, blank=True, on_delete=models.PROTECT,
                                  related_name='+', verbose_name=gettext_lazy('factor up'))
    factor_down = models.ForeignKey('transactions.TransactionType', null=True, blank=True, on_delete=models.PROTECT,
                                    related_name='+', verbose_name=gettext_lazy('factor down'))

    attributes = GenericRelation(GenericAttribute, verbose_name=gettext_lazy('attributes'))

    has_second_exposure_currency = models.BooleanField(default=False,
                                                       verbose_name=gettext_lazy('has second exposure currency'))

    object_permissions = GenericRelation(GenericObjectPermission)

    instrument_form_layouts = models.TextField(null=True, blank=True,
                                               verbose_name=gettext_lazy('instrument form layouts'))

    payment_size_detail = models.ForeignKey(PaymentSizeDetail, on_delete=models.PROTECT, null=True, blank=True,
                                            verbose_name=gettext_lazy('payment size detail'))

    accrued_currency = models.ForeignKey('currencies.Currency', null=True, blank=True,
                                         related_name='instrument_types_accrued',
                                         on_delete=models.PROTECT, verbose_name=gettext_lazy('accrued currency'))
    accrued_multiplier = models.FloatField(default=1.0, verbose_name=gettext_lazy('accrued multiplier'))

    default_accrued = models.FloatField(default=0.0, verbose_name=gettext_lazy('default accrued'))

    instrument_factor_schedule_json_data = models.TextField(null=True, blank=True, verbose_name=gettext_lazy(
        'instrument factor schedule json data'))

    exposure_calculation_model = models.ForeignKey(ExposureCalculationModel, null=True, blank=True,
                                                   verbose_name=gettext_lazy('exposure calculation model'),
                                                   on_delete=models.SET_NULL)

    long_underlying_instrument = models.CharField(max_length=255, null=True, blank=True,
                                                  verbose_name=gettext_lazy('long underlying instrument'))

    underlying_long_multiplier = models.FloatField(default=1.0, verbose_name=gettext_lazy('underlying long multiplier'))

    short_underlying_instrument = models.CharField(max_length=255, null=True, blank=True,
                                                   verbose_name=gettext_lazy('short underlying instrument'))

    underlying_short_multiplier = models.FloatField(default=1.0,
                                                    verbose_name=gettext_lazy('underlying short multiplier'))

    long_underlying_exposure = models.ForeignKey(LongUnderlyingExposure, null=True, blank=True,
                                                 related_name="instrument_type_long_instruments",
                                                 verbose_name=gettext_lazy('long underlying exposure'),
                                                 on_delete=models.SET_NULL)

    short_underlying_exposure = models.ForeignKey(ShortUnderlyingExposure, null=True, blank=True,
                                                  related_name="instrument_type_short_instruments",
                                                  verbose_name=gettext_lazy('short underlying exposure'),
                                                  on_delete=models.SET_NULL)

    co_directional_exposure_currency = models.CharField(max_length=255, null=True, blank=True,
                                                        verbose_name=gettext_lazy('co directional exposure currency'))
    co_directional_exposure_currency_value_type = models.PositiveSmallIntegerField(choices=SYSTEM_VALUE_TYPES,
                                                                                   default=SystemValueType.RELATION,
                                                                                   verbose_name=gettext_lazy(
                                                                                       'co directional exposure currency value type'))

    counter_directional_exposure_currency = models.CharField(max_length=255, null=True, blank=True,
                                                             verbose_name=gettext_lazy(
                                                                 'counter directional exposure currency'))
    counter_directional_exposure_currency_value_type = models.PositiveSmallIntegerField(choices=SYSTEM_VALUE_TYPES,
                                                                                        default=SystemValueType.RELATION,
                                                                                        verbose_name=gettext_lazy(
                                                                                            'counter directional exposure currency value type'))

    default_price = models.FloatField(default=0.0, verbose_name=gettext_lazy('default price'))
    maturity_date = models.DateField(default=date.max, null=True, verbose_name=gettext_lazy('maturity date'))
    maturity_price = models.FloatField(default=0.0, verbose_name=gettext_lazy('maturity price'))

    DIRECT_POSITION = 1
    FACTOR_ADJUSTED_POSITION = 2
    DO_NOT_SHOW = 3

    VALUE_TYPES = (
        (DIRECT_POSITION, gettext_lazy('Direct Position')),
        (FACTOR_ADJUSTED_POSITION, gettext_lazy('Factor Adjusted Position')),
        (DO_NOT_SHOW, gettext_lazy('Do not show')),
    )

    pricing_currency = models.ForeignKey('currencies.Currency', null=True, blank=True,
                                         related_name='instrument_types_pricing',
                                         on_delete=models.PROTECT, verbose_name=gettext_lazy('pricing currency'))
    price_multiplier = models.FloatField(default=1.0, verbose_name=gettext_lazy('price multiplier'))

    position_reporting = models.PositiveSmallIntegerField(choices=VALUE_TYPES, default=DIRECT_POSITION,
                                                          verbose_name=gettext_lazy('position reporting'))

    pricing_condition = models.ForeignKey(PricingCondition, null=True, blank=True,
                                          verbose_name=gettext_lazy('pricing condition'),
                                          on_delete=models.SET_NULL)

    reference_for_pricing = models.CharField(max_length=100, blank=True, default='',
                                             verbose_name=gettext_lazy('reference for pricing'))

    @property
    def instrument_factor_schedule_data(self):
        if self.instrument_factor_schedule_json_data:
            try:
                return json.loads(self.instrument_factor_schedule_json_data)
            except (ValueError, TypeError):
                return None
        else:
            return None

    @instrument_factor_schedule_data.setter
    def instrument_factor_schedule_data(self, val):
        if val:
            self.instrument_factor_schedule_json_data = json.dumps(val, cls=DjangoJSONEncoder, sort_keys=True)
        else:
            self.instrument_factor_schedule_json_data = None

    class Meta(NamedModel.Meta, FakeDeletableModel.Meta):
        verbose_name = gettext_lazy('instrument type')
        verbose_name_plural = gettext_lazy('instrument types')
        permissions = [
            # ('view_instrumenttype', 'Can view instrument type'),
            ('manage_instrumenttype', 'Can manage instrument type'),
        ]

    def __str__(self):
        return self.user_code

    @property
    def is_default(self):
        return self.master_user.instrument_type_id == self.id if self.master_user_id else False


class InstrumentTypeAccrual(models.Model):
    instrument_type = models.ForeignKey(InstrumentType, on_delete=models.CASCADE,
                                        related_name='accruals',
                                        verbose_name=gettext_lazy('instrument type'))

    name = models.CharField(max_length=255, verbose_name=gettext_lazy('name'))

    order = models.IntegerField(default=0, verbose_name=gettext_lazy('order'))

    autogenerate = models.BooleanField(default=True, verbose_name=gettext_lazy('autogenerate'))

    json_data = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('json data'))

    class Meta:

        ordering = ['order']

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


class InstrumentTypeEvent(models.Model):
    instrument_type = models.ForeignKey(InstrumentType, on_delete=models.CASCADE,
                                        related_name='events',
                                        verbose_name=gettext_lazy('instrument type'))

    name = models.CharField(max_length=255, verbose_name=gettext_lazy('name'))

    order = models.IntegerField(default=0, verbose_name=gettext_lazy('order'))

    autogenerate = models.BooleanField(default=True, verbose_name=gettext_lazy('autogenerate'))

    json_data = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('json data'))

    class Meta:

        ordering = ['order']

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


class InstrumentTypeInstrumentAttribute(models.Model):
    STRING = 10
    NUMBER = 20
    CLASSIFIER = 30
    DATE = 40

    VALUE_TYPES = (
        (NUMBER, gettext_lazy('Number')),
        (STRING, gettext_lazy('String')),
        (DATE, gettext_lazy('Date')),
        (CLASSIFIER, gettext_lazy('Classifier')),
    )

    instrument_type = models.ForeignKey(InstrumentType, on_delete=models.CASCADE,
                                        related_name='instrument_attributes',
                                        verbose_name=gettext_lazy('instrument attributes'))

    attribute_type_user_code = models.CharField(max_length=255, verbose_name=gettext_lazy('attribute type user code'))

    value_type = models.PositiveSmallIntegerField(choices=VALUE_TYPES, default=STRING,
                                                  verbose_name=gettext_lazy('value type'))

    value_string = models.CharField(db_index=True, max_length=255, null=True, blank=True,
                                    verbose_name=gettext_lazy('value (String)'))
    value_float = models.FloatField(db_index=True, null=True, blank=True, verbose_name=gettext_lazy('value (Float)'))
    value_date = models.DateField(db_index=True, null=True, blank=True, verbose_name=gettext_lazy('value (Date)'))
    value_classifier = models.CharField(db_index=True, max_length=255, null=True, blank=True,
                                        verbose_name=gettext_lazy('value (Classifier)'))


class InstrumentTypeInstrumentFactorSchedule(models.Model):
    instrument_type = models.ForeignKey(InstrumentType, on_delete=models.CASCADE,
                                        related_name='instrument_factor_schedules',
                                        verbose_name=gettext_lazy('instrument attributes'))

    effective_date = models.CharField(max_length=255, null=True, blank=True,
                                      verbose_name=gettext_lazy('effective date'))
    effective_date_value_type = models.PositiveSmallIntegerField(choices=SYSTEM_VALUE_TYPES,
                                                                 default=SystemValueType.DATE,
                                                                 verbose_name=gettext_lazy('effective date'))

    position_factor_value = models.CharField(max_length=255, null=True, blank=True,
                                             verbose_name=gettext_lazy('position factor value'))
    position_factor_value_value_type = models.PositiveSmallIntegerField(choices=SYSTEM_VALUE_TYPES,
                                                                        default=SystemValueType.DATE,
                                                                        verbose_name=gettext_lazy(
                                                                            'position factor value value type'))

    factor_value1 = models.CharField(max_length=255, null=True, blank=True, verbose_name=gettext_lazy('factor value 1'))
    factor_value1_value_type = models.PositiveSmallIntegerField(choices=SYSTEM_VALUE_TYPES,
                                                                default=SystemValueType.DATE,
                                                                verbose_name=gettext_lazy('factor value1 value type'))

    factor_value2 = models.CharField(max_length=255, null=True, blank=True, verbose_name=gettext_lazy('factor value 2'))
    factor_value2_value_type = models.PositiveSmallIntegerField(choices=SYSTEM_VALUE_TYPES,
                                                                default=SystemValueType.DATE,
                                                                verbose_name=gettext_lazy('factor value2 value type'))

    factor_value3 = models.CharField(max_length=255, null=True, blank=True,
                                     verbose_name=gettext_lazy('factor value 3 '))
    factor_value3_value_type = models.PositiveSmallIntegerField(choices=SYSTEM_VALUE_TYPES,
                                                                default=SystemValueType.DATE,
                                                                verbose_name=gettext_lazy('factor value3 value type'))

    class Meta:
        verbose_name = gettext_lazy('instrument type instrument factor schedule')
        verbose_name_plural = gettext_lazy('instrument type  instrument factor schedules')

    def __str__(self):
        return '%s' % self.effective_date


class Instrument(NamedModelAutoMapping, FakeDeletableModel, DataTimeStampedModel):
    # class Instrument(NamedModelAutoMapping, FakeDeletableModel, DataTimeStampedModel):
    master_user = models.ForeignKey(MasterUser, related_name='instruments', verbose_name=gettext_lazy('master user'),
                                    on_delete=models.CASCADE)

    instrument_type = models.ForeignKey(InstrumentType, on_delete=models.PROTECT,
                                        verbose_name=gettext_lazy('instrument type'))

    is_active = models.BooleanField(default=True, verbose_name=gettext_lazy('is active'))
    has_linked_with_portfolio = models.BooleanField(default=False,
                                                    verbose_name=gettext_lazy('has linked with portfolio'))
    pricing_currency = models.ForeignKey('currencies.Currency', on_delete=models.PROTECT,
                                         verbose_name=gettext_lazy('pricing currency'))
    price_multiplier = models.FloatField(default=1.0, verbose_name=gettext_lazy('price multiplier'))
    accrued_currency = models.ForeignKey('currencies.Currency', related_name='instruments_accrued',
                                         on_delete=models.PROTECT, verbose_name=gettext_lazy('accrued currency'))
    accrued_multiplier = models.FloatField(default=1.0, verbose_name=gettext_lazy('accrued multiplier'))

    payment_size_detail = models.ForeignKey(PaymentSizeDetail, on_delete=models.PROTECT, null=True, blank=True,
                                            verbose_name=gettext_lazy('payment size detail'))

    default_price = models.FloatField(default=0.0, verbose_name=gettext_lazy('default price'))
    default_accrued = models.FloatField(default=0.0, verbose_name=gettext_lazy('default accrued'))

    user_text_1 = models.CharField(max_length=255, null=True, blank=True, verbose_name=gettext_lazy('user text 1'),
                                   help_text=gettext_lazy('User specified field 1'))
    user_text_2 = models.CharField(max_length=255, null=True, blank=True, verbose_name=gettext_lazy('user text 2'),
                                   help_text=gettext_lazy('User specified field 2'))
    user_text_3 = models.CharField(max_length=255, null=True, blank=True, verbose_name=gettext_lazy('user text 3'),
                                   help_text=gettext_lazy('User specified field 3'))

    reference_for_pricing = models.CharField(max_length=100, blank=True, default='',
                                             verbose_name=gettext_lazy('reference for pricing'))
    daily_pricing_model = models.ForeignKey(DailyPricingModel, null=True, blank=True,
                                            verbose_name=gettext_lazy('daily pricing model'),
                                            on_delete=models.SET_NULL)

    pricing_condition = models.ForeignKey(PricingCondition, null=True, blank=True,
                                          verbose_name=gettext_lazy('pricing condition'),
                                          on_delete=models.SET_NULL)

    exposure_calculation_model = models.ForeignKey(ExposureCalculationModel, null=True, blank=True,
                                                   verbose_name=gettext_lazy('exposure calculation model'),
                                                   on_delete=models.SET_NULL)

    long_underlying_instrument = models.ForeignKey('self', null=True, blank=True,
                                                   related_name="long_underlying_instruments",
                                                   verbose_name=gettext_lazy('long underlying instrument'),
                                                   on_delete=models.SET_NULL)

    underlying_long_multiplier = models.FloatField(default=1.0, verbose_name=gettext_lazy('underlying long multiplier'))

    short_underlying_instrument = models.ForeignKey('self', null=True, blank=True,
                                                    related_name="short_underlying_instruments",
                                                    verbose_name=gettext_lazy('short underlying instrument'),
                                                    on_delete=models.SET_NULL)

    underlying_short_multiplier = models.FloatField(default=1.0,
                                                    verbose_name=gettext_lazy('underlying short multiplier'))

    long_underlying_exposure = models.ForeignKey(LongUnderlyingExposure, null=True, blank=True,
                                                 related_name="long_instruments",
                                                 verbose_name=gettext_lazy('long underlying exposure'),
                                                 on_delete=models.SET_NULL)

    short_underlying_exposure = models.ForeignKey(ShortUnderlyingExposure, null=True, blank=True,
                                                  related_name="short_instruments",
                                                  verbose_name=gettext_lazy('short underlying exposure'),
                                                  on_delete=models.SET_NULL)

    # price_download_scheme = models.ForeignKey('integrations.PriceDownloadScheme', on_delete=models.PROTECT, null=True,
    #                                           blank=True, verbose_name=gettext_lazy('price download scheme'))
    maturity_date = models.DateField(default=date.max, null=True, verbose_name=gettext_lazy('maturity date'))
    maturity_price = models.FloatField(default=0.0, verbose_name=gettext_lazy('maturity price'))

    attributes = GenericRelation(GenericAttribute, verbose_name=gettext_lazy('attributes'))
    object_permissions = GenericRelation(GenericObjectPermission, verbose_name=gettext_lazy('object permissions'))

    co_directional_exposure_currency = models.ForeignKey('currencies.Currency',
                                                         related_name='co_directional_exposure_currency',
                                                         on_delete=models.SET_NULL, null=True, blank=True,
                                                         verbose_name=gettext_lazy('co directional exposure currency'))

    counter_directional_exposure_currency = models.ForeignKey('currencies.Currency',
                                                              related_name='counter_directional_exposure_currency',
                                                              on_delete=models.SET_NULL, null=True, blank=True,
                                                              verbose_name=gettext_lazy(
                                                                  'counter directional exposure currency'))

    DIRECT_POSITION = 1
    FACTOR_ADJUSTED_POSITION = 2
    DO_NOT_SHOW = 3

    VALUE_TYPES = (
        (DIRECT_POSITION, gettext_lazy('Direct Position')),
        (FACTOR_ADJUSTED_POSITION, gettext_lazy('Factor Adjusted Position')),
        (DO_NOT_SHOW, gettext_lazy('Do not show')),
    )

    position_reporting = models.PositiveSmallIntegerField(choices=VALUE_TYPES, default=DIRECT_POSITION,
                                                          verbose_name=gettext_lazy('position reporting'))

    country = models.ForeignKey(Country, null=True, blank=True,
                                verbose_name=gettext_lazy('country'),
                                on_delete=models.SET_NULL)

    class Meta(NamedModel.Meta, FakeDeletableModel.Meta):
        verbose_name = gettext_lazy('instrument')
        verbose_name_plural = gettext_lazy('instruments')
        permissions = [
            # ('view_instrument', 'Can view instrument'),
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
                    if instrument_type.regular_event:
                        a.transaction_type = instrument_type.regular_event.user_code
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
                if instrument_type.one_off_event:
                    a.transaction_type = instrument_type.one_off_event.user_code
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
            if transaction_type:
                a.transaction_type = transaction_type.user_code
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

        _l.info("get_accrual_calculation_schedules_all %s" % accruals)

        if not accruals:
            return accruals

        if getattr(accruals[0], 'accrual_end_date', None) is not None:
            # already configured
            return accruals

        _l.info('get_accrual_calculation_schedules_all')

        accruals = sorted(accruals, key=lambda x: datetime.date(datetime.strptime(x.accrual_start_date, '%Y-%m-%d')))

        _l.info('get_accrual_calculation_schedules_all after sort')

        a = None
        for next_a in accruals:
            if a is not None:
                a.accrual_end_date = next_a.accrual_start_date
            a = next_a
        if a:
            # a.accrual_end_date = self.maturity_date

            # print('self.maturity_date %s ' % self.maturity_date)
            try:
                a.accrual_end_date = self.maturity_date + timedelta(days=1)
            except (OverflowError, Exception):

                print("Overflow Error %s " % self.maturity_date)

                a.accrual_end_date = self.maturity_date
            # print('a.accrual_end_date %s ' % a.accrual_end_date)

        return accruals

    def find_accrual(self, d):
        if d >= self.maturity_date:
            return None

        accruals = self.get_accrual_calculation_schedules_all()
        accrual = None

        _l.debug('find_accrual.accruals %s' % accruals)

        for a in accruals:
            if datetime.date(datetime.strptime(a.accrual_start_date, '%Y-%m-%d')) <= d:
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
        _l.debug('get_accrual_size.accrual %s' % accrual)
        if accrual is None:
            return 0.0

        return float(accrual.accrual_size)

    def get_future_accrual_payments(self, d0, v0):

        pass

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

        accrual_start_date = datetime.date(datetime.strptime(accrual.accrual_start_date, '%Y-%m-%d'))
        first_payment_date = datetime.date(datetime.strptime(accrual.first_payment_date, '%Y-%m-%d'))

        _l.info('coupon_accrual_factor price_date %s ' % price_date)

        factor = coupon_accrual_factor(accrual_calculation_schedule=accrual,
                                       dt1=accrual_start_date,
                                       dt2=price_date,
                                       dt3=first_payment_date)

        return float(accrual.accrual_size) * factor

    def get_coupon(self, cpn_date, with_maturity=False, factor=False):

        _l.info('get_coupon self.maturity_date %s' % self.maturity_date)

        if cpn_date == self.maturity_date:
            if with_maturity:
                return self.maturity_price, True
            else:
                return 0.0, False

        elif cpn_date > self.maturity_date:
            return 0.0, False

        accruals = self.get_accrual_calculation_schedules_all()

        _l.info('get_coupon len accruals %s ' % len(accruals))

        for accrual in accruals:

            accrual_start_date = datetime.date(datetime.strptime(accrual.accrual_start_date, '%Y-%m-%d'))
            # accrual_end_date = datetime.date(datetime.strptime(accrual.accrual_end_date, '%Y-%m-%d'))
            accrual_end_date = accrual.accrual_end_date
            first_payment_date = datetime.date(datetime.strptime(accrual.first_payment_date, '%Y-%m-%d'))

            _l.info('get_coupon  accrual_start_date %s ' % accrual_start_date)
            _l.info('get_coupon  accrual_end_date %s ' % accrual_end_date)
            _l.info('get_coupon  first_payment_date %s ' % first_payment_date)

            if accrual_start_date <= cpn_date < accrual_end_date:
                _l.info('get coupon start processing ')
                prev_d = accrual_start_date
                for i in range(0, 3652058):
                    stop = False
                    if i == 0:
                        d = first_payment_date
                    else:
                        try:
                            d = first_payment_date + accrual.periodicity.to_timedelta(
                                n=accrual.periodicity_n, i=i, same_date=accrual_start_date)
                        except (OverflowError, ValueError) as e:  # year is out of range
                            _l.info('get_coupon overflow error %s' % e)
                            return 0.0, False

                    if d >= accrual_end_date:
                        d = accrual_end_date - timedelta(days=1)
                        stop = True

                    if d == cpn_date:
                        val_or_factor = get_coupon(accrual, prev_d, d, maturity_date=self.maturity_date, factor=factor)

                        _l.info('get_coupon  d == cpn_date %s' % val_or_factor)

                        return val_or_factor, True

                    if stop or d >= accrual_end_date:
                        break

                    prev_d = d

        _l.info('get_coupon last return')

        return 0.0, False

    def get_future_coupons(self, begin_date=None, with_maturity=False, factor=False):

        res = []
        accruals = self.get_accrual_calculation_schedules_all()
        for accrual in accruals:
            if begin_date >= accrual.accrual_end_date:
                continue

            format = '%Y-%m-%d'
            accrual_start_date_d = datetime.strptime(accrual.accrual_start_date, format).date()
            first_payment_date_d = datetime.strptime(accrual.first_payment_date, format).date()
            # accrual_end_date_d = datetime.strptime(accrual.accrual_end_date, format).date() # seems date field
            accrual_end_date_d = accrual.accrual_end_date

            prev_d = accrual_start_date_d
            for i in range(0, 3652058):
                stop = False
                if i == 0:
                    d = first_payment_date_d
                else:
                    try:
                        d = first_payment_date_d + accrual.periodicity.to_timedelta(
                            n=accrual.periodicity_n, i=i, same_date=accrual_start_date_d)
                    except (OverflowError, ValueError):  # year is out of range
                        break

                if d < begin_date:
                    prev_d = d
                    continue

                if d >= accrual_end_date_d:
                    d = accrual_end_date_d - timedelta(days=1)
                    stop = True

                val_or_factor = get_coupon(accrual, prev_d, d, maturity_date=self.maturity_date, factor=factor)
                res.append((d, val_or_factor))

                if stop or d >= accrual_end_date_d:
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

    def generate_instrument_system_attributes(self):

        from django.contrib.contenttypes.models import ContentType

        content_type = ContentType.objects.get(app_label="instruments", model='instrument')
        instrument_pricing_policies = InstrumentPricingPolicy.objects.filter(instrument=self)

        for ipp in instrument_pricing_policies:

            pp = ipp.pricing_policy

            user_code_scheme = 'pricing_policy_scheme_' + pp.user_code
            user_code_parameter = 'pricing_policy_parameter_' + pp.user_code
            user_code_notes = 'pricing_policy_notes_' + pp.user_code

            name_scheme = 'Pricing Policy Scheme: ' + pp.user_code
            name_parameter = 'Pricing Policy Parameter: ' + pp.user_code
            name_notes = 'Pricing Policy Notes: ' + pp.user_code

            attr_type_scheme = None
            attr_type_parameter = None
            attr_type_notes = None

            try:
                attr_type_scheme = GenericAttributeType.objects.get(master_user=self.master_user,
                                                                    content_type=content_type,
                                                                    user_code=user_code_scheme)
            except GenericAttributeType.DoesNotExist:
                attr_type_scheme = GenericAttributeType.objects.create(
                    master_user=self.master_user,
                    content_type=content_type,
                    value_type=GenericAttributeType.STRING,
                    user_code=user_code_scheme,
                    name=name_scheme,
                    kind=GenericAttributeType.SYSTEM
                )

            try:
                attr_type_parameter = GenericAttributeType.objects.get(master_user=self.master_user,
                                                                       content_type=content_type,
                                                                       user_code=user_code_parameter)
            except GenericAttributeType.DoesNotExist:
                attr_type_parameter = GenericAttributeType.objects.create(
                    master_user=self.master_user,
                    content_type=content_type,
                    value_type=GenericAttributeType.STRING,
                    user_code=user_code_parameter,
                    name=name_parameter,
                    kind=GenericAttributeType.SYSTEM
                )

            try:
                attr_type_notes = GenericAttributeType.objects.get(master_user=self.master_user,
                                                                   content_type=content_type, user_code=user_code_notes)
            except GenericAttributeType.DoesNotExist:
                attr_type_notes = GenericAttributeType.objects.create(
                    master_user=self.master_user,
                    content_type=content_type,
                    value_type=GenericAttributeType.STRING,
                    user_code=user_code_notes,
                    name=name_notes,
                    kind=GenericAttributeType.SYSTEM
                )

            try:

                attr_scheme = GenericAttribute.objects.get(attribute_type=attr_type_scheme, object_id=self.pk,
                                                           content_type=content_type)

            except GenericAttribute.DoesNotExist:

                attr_scheme = GenericAttribute.objects.create(attribute_type=attr_type_scheme, object_id=self.pk,
                                                              content_type=content_type)

            if ipp.pricing_scheme:
                attr_scheme.value_string = ipp.pricing_scheme.name
            else:
                attr_scheme.value_string = ''

            attr_scheme.save()

            try:

                attr_parameter = GenericAttribute.objects.get(attribute_type=attr_type_parameter, object_id=self.pk,
                                                              content_type=content_type)

            except GenericAttribute.DoesNotExist:

                attr_parameter = GenericAttribute.objects.create(attribute_type=attr_type_parameter, object_id=self.pk,
                                                                 content_type=content_type)

            if ipp.attribute_key:

                if 'attributes.' in ipp.attribute_key:

                    try:
                        code = ipp.attribute_key.split('attributes.')[1]
                        type = GenericAttributeType.objects.get(master_user=self.master_user, content_type=content_type,
                                                                user_code=code)

                        attr = GenericAttribute.objects.get(object_id=self.pk, attribute_type=type,
                                                            content_type=content_type)

                        if type.value_type == 10:
                            attr_parameter.value_string = attr.value_string

                        if type.value_type == 20:
                            attr_parameter.value_string = str(attr.value_float)

                        if type.value_type == 30:
                            attr_parameter.value_string = attr.classifier.name

                        if type.value_type == 40:
                            attr_parameter.value_string = attr.value_date

                    except Exception as e:
                        _l.info("Could not get attribute value %s " % e)


                else:
                    attr_parameter.value_string = str(getattr(self, ipp.attribute_key, ''))
            elif ipp.default_value:
                attr_parameter.value_string = ipp.default_value
            else:
                attr_parameter.value_string = ''

            attr_parameter.save()

            try:

                attr_notes = GenericAttribute.objects.get(attribute_type=attr_type_notes, object_id=self.pk,
                                                          content_type=content_type)

            except GenericAttribute.DoesNotExist:

                attr_notes = GenericAttribute.objects.create(attribute_type=attr_type_notes, object_id=self.pk,
                                                             content_type=content_type)

            if ipp.notes:
                attr_notes.value_string = ipp.notes
            else:
                attr_notes.value_string = ''

            _l.info('attr_notes %s' % attr_notes.value_string)

            attr_notes.save()

        _l.info('generate_instrument_system_attributes done')

    def save(self, *args, **kwargs):

        super(Instrument, self).save(*args, **kwargs)

        try:

            self.generate_instrument_system_attributes()

        except Exception as error:

            _l.debug('Instrument save error %s' % error)


# DEPRECTATED (25.05.2020) delete soon
class ManualPricingFormula(models.Model):
    instrument = models.ForeignKey(Instrument, related_name='manual_pricing_formulas',
                                   verbose_name=gettext_lazy('instrument'), on_delete=models.CASCADE)
    pricing_policy = models.ForeignKey(PricingPolicy, on_delete=models.CASCADE, related_name='manual_pricing_formulas',
                                       verbose_name=gettext_lazy('pricing policy'))
    expr = models.CharField(max_length=255, blank=True, default='', verbose_name=gettext_lazy('expression'))
    notes = models.TextField(blank=True, default='', verbose_name=gettext_lazy('notes'))

    class Meta:
        verbose_name = gettext_lazy('manual pricing formula')
        verbose_name_plural = gettext_lazy('manual pricing formulas')
        unique_together = [
            ['instrument', 'pricing_policy']
        ]
        ordering = ['pricing_policy']

    def __str__(self):
        return self.expr


class AccrualCalculationSchedule(models.Model):
    instrument = models.ForeignKey(Instrument, related_name='accrual_calculation_schedules',
                                   verbose_name=gettext_lazy('instrument'), on_delete=models.CASCADE)
    accrual_start_date = models.CharField(max_length=255, null=True, blank=True,
                                          verbose_name=gettext_lazy('accrual start date'))
    accrual_start_date_value_type = models.PositiveSmallIntegerField(choices=SYSTEM_VALUE_TYPES,
                                                                     default=SystemValueType.DATE,
                                                                     verbose_name=gettext_lazy(
                                                                         'accrual start date value type'))
    accrual_end_date = None  # excluded date
    first_payment_date = models.CharField(max_length=255, null=True, blank=True,
                                          verbose_name=gettext_lazy('first payment date'))
    first_payment_date_value_type = models.PositiveSmallIntegerField(choices=SYSTEM_VALUE_TYPES,
                                                                     default=SystemValueType.DATE,
                                                                     verbose_name=gettext_lazy(
                                                                         'first payment date value type'))
    # TODO: is %
    accrual_size = models.CharField(max_length=255, null=True, blank=True, verbose_name=gettext_lazy('accrual size'))
    accrual_size_value_type = models.PositiveSmallIntegerField(choices=SYSTEM_VALUE_TYPES,
                                                               default=SystemValueType.NUMBER,
                                                               verbose_name=gettext_lazy('accrual size value type'))

    accrual_calculation_model = models.ForeignKey(AccrualCalculationModel, on_delete=models.PROTECT,
                                                  verbose_name=gettext_lazy('accrual calculation model'))
    periodicity = models.ForeignKey(Periodicity, on_delete=models.PROTECT, null=True, blank=True,
                                    verbose_name=gettext_lazy('periodicity'))
    periodicity_n = models.CharField(max_length=255, null=True, blank=True, verbose_name=gettext_lazy('periodicity n'))
    periodicity_n_value_type = models.PositiveSmallIntegerField(choices=SYSTEM_VALUE_TYPES,
                                                                default=SystemValueType.NUMBER,
                                                                verbose_name=gettext_lazy('periodicity n value type'))

    notes = models.TextField(blank=True, default='', verbose_name=gettext_lazy('notes'))

    class Meta:
        verbose_name = gettext_lazy('accrual calculation schedule')
        verbose_name_plural = gettext_lazy('accrual calculation schedules')
        ordering = ['accrual_start_date']

    def __str__(self):
        return '%s' % self.accrual_start_date


class PriceHistory(DataTimeStampedModel):
    instrument = models.ForeignKey(Instrument, related_name='prices', verbose_name=gettext_lazy('instrument'),
                                   on_delete=models.CASCADE)
    pricing_policy = models.ForeignKey(PricingPolicy, on_delete=models.CASCADE, null=True, blank=True,
                                       verbose_name=gettext_lazy('pricing policy'))
    date = models.DateField(db_index=True, default=date_now, verbose_name=gettext_lazy('date'))
    principal_price = models.FloatField(default=0.0, verbose_name=gettext_lazy('principal price'))
    accrued_price = models.FloatField(default=0.0, verbose_name=gettext_lazy('accrued price'))

    long_delta = models.FloatField(default=0.0, verbose_name=gettext_lazy('long delta'))
    short_delta = models.FloatField(default=0.0, verbose_name=gettext_lazy('short delta'))

    ytm = models.FloatField(default=0.0, verbose_name=gettext_lazy('ytm'))
    nav = models.FloatField(default=0.0, verbose_name=gettext_lazy('nav'))
    cash_flow = models.FloatField(default=0.0, verbose_name=gettext_lazy('cash flow'))
    modified_duration = models.FloatField(default=0.0, verbose_name=gettext_lazy('modified duration'))

    procedure_modified_datetime = models.DateTimeField(null=True, blank=True,
                                                       verbose_name=gettext_lazy('procedure_modified_datetime'))

    is_temporary_price = models.BooleanField(default=False, verbose_name=gettext_lazy('is temporary price'))

    class Meta:
        verbose_name = gettext_lazy('price history')
        verbose_name_plural = gettext_lazy('price histories')
        unique_together = (
            ('instrument', 'pricing_policy', 'date',)
        )
        ordering = ['date']

    def __str__(self):
        # return '%s:%s:%s:%s:%s' % (
        #     self.instrument_id, self.pricing_policy_id, self.date, self.principal_price, self.accrued_price)
        return '%s;%s @%s' % (self.principal_price, self.accrued_price, self.date)

    def get_instr_ytm_data_d0_v0(self, dt):

        v0 = -(self.principal_price * self.instrument.price_multiplier * self.instrument.get_factor(
            dt) + self.accrued_price * self.instrument.accrued_multiplier * self.instrument.get_factor(dt) * (
                       self.instr_accrued_ccy_cur_fx / self.instr_pricing_ccy_cur_fx))

        return dt, v0

    def get_instr_ytm_data(self, dt):
        if hasattr(self, '_instr_ytm_data'):
            return self._instr_ytm_data

        instr = self.instrument

        if instr.maturity_date is None or instr.maturity_date == date.max:
            # _l.debug('get_instr_ytm_data: [], maturity_date rule')
            return []
        if instr.maturity_price is None or isnan(instr.maturity_price) or isclose(instr.maturity_price, 0.0):
            # _l.debug('get_instr_ytm_data: [], maturity_price rule')
            return []

        try:
            d0, v0 = self.get_instr_ytm_data_d0_v0(dt)
        except ArithmeticError:
            return None

        data = [(d0, v0)]

        for cpn_date, cpn_val in instr.get_future_coupons(begin_date=d0, with_maturity=False):
            try:
                factor = instr.get_factor(cpn_date)
                k = instr.accrued_multiplier * factor * \
                    (self.instr_accrued_ccy_cur_fx / self.instr_pricing_ccy_cur_fx)
            except ArithmeticError:
                k = 0
            data.append((cpn_date, cpn_val * k))

        prev_factor = None
        for factor in instr.factor_schedules.all():
            if factor.effective_date < d0 or factor.effective_date > instr.maturity_date:
                prev_factor = factor
                continue

            prev_factor_value = prev_factor.factor_value if prev_factor else 1.0
            factor_value = factor.factor_value

            k = (prev_factor_value - factor_value) * instr.price_multiplier
            data.append((factor.effective_date, instr.maturity_price * k))

            prev_factor = factor

        factor = instr.get_factor(instr.maturity_date)
        k = instr.price_multiplier * factor
        data.append((instr.maturity_date, instr.maturity_price * k))

        # sort by date
        data.sort()
        self._instr_ytm_data = data

        return data

    def get_instr_ytm_x0(self, dt):
        try:
            accrual_size = self.instrument.get_accrual_size(dt)

            return (accrual_size * self.instrument.accrued_multiplier) * \
                   (self.instr_accrued_ccy_cur_fx / self.instr_pricing_ccy_cur_fx) / \
                   (self.principal_price * self.instrument.price_multiplier)
        except Exception as e:
            _l.error('get_instr_ytm_x0 %s' % e)
            return 0

    def calculate_ytm(self, dt):

        _l.debug('Calculating ytm for %s for %s' % (self.instrument.name, self.date))

        if self.instrument.maturity_date is None or self.instrument.maturity_date == date.max:
            try:
                accrual_size = self.instrument.get_accrual_size(dt)
                ytm = (accrual_size * self.instrument.accrued_multiplier) * \
                      (self.instr_accrued_ccy_cur_fx / self.instr_pricing_ccy_cur_fx) / \
                      (self.principal_price * self.instrument.price_multiplier)

            except Exception as e:
                _l.info('calculate_ytm e %s ' % e)
                ytm = 0
            # _l.debug('get_instr_ytm.1: %s', ytm)
            return ytm

        x0 = self.get_instr_ytm_x0(dt)
        _l.debug('get_instr_ytm: x0=%s', x0)

        data = self.get_instr_ytm_data(dt)
        _l.debug('get_instr_ytm: data=%s', data)

        if data:
            ytm = f_xirr(data, x0=x0)
        else:
            ytm = 0.0

        return ytm

    def calculate_duration(self, dt):

        if self.instrument.maturity_date is None or self.instrument.maturity_date == date.max:
            try:
                duration = 1 / self.ytm
            except ArithmeticError:
                duration = 0
            # _l.debug('get_instr_duration.1: %s', duration)
            return duration
        data = self.get_instr_ytm_data(dt)
        if data:
            duration = f_duration(data, ytm=self.ytm)
        else:
            duration = 0
        # _l.debug('get_instr_duration: %s', duration)
        return duration

    def save(self, *args, **kwargs):

        # TODO make readable exception if currency history is missing

        cache.clear()

        if not self.procedure_modified_datetime:
            self.procedure_modified_datetime = date_now()

        if not self.created:
            self.created = date_now()

        ecosystem_default = EcosystemDefault.objects.get(master_user=self.instrument.master_user)

        try:

            if self.instrument.accrued_currency_id == self.instrument.pricing_currency_id:

                self.instr_accrued_ccy_cur_fx = 1
                self.instr_pricing_ccy_cur_fx = 1

            else:

                if ecosystem_default.currency_id == self.instrument.accrued_currency_id:
                    self.instr_accrued_ccy_cur_fx = 1
                else:
                    self.instr_accrued_ccy_cur_fx = CurrencyHistory.objects.get(date=self.date,
                                                                                currency=self.instrument.accrued_currency).fx_rate

                if ecosystem_default.currency_id == self.instrument.pricing_currency_id:
                    self.instr_pricing_ccy_cur_fx = 1
                else:
                    self.instr_pricing_ccy_cur_fx = CurrencyHistory.objects.get(date=self.date,
                                                                                currency=self.instrument.pricing_currency).fx_rate

            self.ytm = self.calculate_ytm(self.date)
            self.modified_duration = self.calculate_duration(self.date)

            # _l.debug('self.ytm %s' % self.ytm)
            # _l.debug('self.modified_duration %s' % self.modified_duration)

        except Exception as error:

            _l.debug('Price History save error %s' % error)
            _l.debug(traceback.print_exc())

        super(PriceHistory, self).save(*args, **kwargs)


class InstrumentFactorSchedule(models.Model):
    instrument = models.ForeignKey(Instrument, related_name='factor_schedules',
                                   verbose_name=gettext_lazy('instrument'), on_delete=models.CASCADE)
    effective_date = models.DateField(default=date_now, verbose_name=gettext_lazy('effective date'))
    factor_value = models.FloatField(default=0., verbose_name=gettext_lazy('factor value'))

    class Meta:
        verbose_name = gettext_lazy('instrument factor schedule')
        verbose_name_plural = gettext_lazy('instrument factor schedules')
        ordering = ['effective_date']

    def __str__(self):
        return '%s' % self.effective_date


class EventSchedule(models.Model):
    instrument = models.ForeignKey(Instrument, related_name='event_schedules', verbose_name=gettext_lazy('instrument'),
                                   on_delete=models.CASCADE)

    # T O D O: name & description is expression
    # T O D O: default settings.POMS_EVENT_*
    name = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, verbose_name=gettext_lazy('name'))
    description = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                   verbose_name=gettext_lazy('description'))

    event_class = models.ForeignKey('transactions.EventClass', on_delete=models.PROTECT,
                                    verbose_name=gettext_lazy('event class'))

    # T O D O: add to MasterUser defaults
    notification_class = models.ForeignKey('transactions.NotificationClass', on_delete=models.PROTECT,
                                           verbose_name=gettext_lazy('notification class'))

    # TODO: is first_payment_date for regular
    # TODO: is instrument.maturity for one-off
    effective_date = models.CharField(max_length=255, null=True, blank=True,
                                      verbose_name=gettext_lazy('effective date'))
    effective_date_value_type = models.PositiveSmallIntegerField(choices=SYSTEM_VALUE_TYPES,
                                                                 default=SystemValueType.DATE,
                                                                 verbose_name=gettext_lazy('effective date value type'))

    notify_in_n_days = models.PositiveIntegerField(default=0, verbose_name=gettext_lazy('notify in N days'))

    periodicity = models.ForeignKey(Periodicity, null=True, blank=True, on_delete=models.PROTECT,
                                    verbose_name=gettext_lazy('periodicity'))
    periodicity_n = models.CharField(max_length=255, null=True, blank=True, verbose_name=gettext_lazy('periodicity n'))
    periodicity_n_value_type = models.PositiveSmallIntegerField(choices=SYSTEM_VALUE_TYPES,
                                                                default=SystemValueType.NUMBER,
                                                                verbose_name=gettext_lazy('periodicity n value type'))
    # TODO: =see next accrual_calculation_schedule.accrual_start_date or instrument.maturity_date (if last)
    final_date = models.CharField(max_length=255, null=True, blank=True,
                                  verbose_name=gettext_lazy('final date'))  # excluded date
    final_date_value_type = models.PositiveSmallIntegerField(choices=SYSTEM_VALUE_TYPES, default=SystemValueType.DATE,
                                                             verbose_name=gettext_lazy('final_date value type'))

    is_auto_generated = models.BooleanField(default=False, verbose_name=gettext_lazy('is auto generated'))
    accrual_calculation_schedule = models.ForeignKey(AccrualCalculationSchedule, null=True, blank=True, editable=False,
                                                     related_name='event_schedules',
                                                     verbose_name=gettext_lazy('accrual calculation schedule'),
                                                     help_text=gettext_lazy(
                                                         'Used for store link when is_auto_generated is True'),
                                                     on_delete=models.SET_NULL)
    factor_schedule = models.ForeignKey(InstrumentFactorSchedule, null=True, blank=True, editable=False,
                                        related_name='event_schedules', verbose_name=gettext_lazy('factor schedule'),
                                        help_text=gettext_lazy('Used for store link when is_auto_generated is True'),
                                        on_delete=models.SET_NULL)

    json_data = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('json data'))

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
        verbose_name = gettext_lazy('event schedule')
        verbose_name_plural = gettext_lazy('event schedules')
        ordering = ['effective_date']

    def __str__(self):
        return '#%s/#%s' % (self.id, self.instrument_id)

    @cached_property
    def all_dates(self):
        from poms.transactions.models import EventClass

        notify_in_n_days = timedelta(days=self.notify_in_n_days)

        # sdate = self.effective_date
        # edate = self.final_date

        edate = datetime.date(datetime.strptime(self.effective_date, '%Y-%m-%d'))
        fdate = datetime.date(datetime.strptime(self.final_date, '%Y-%m-%d'))

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
            add_date(edate)

        elif self.event_class_id == EventClass.REGULAR:
            for i in range(0, 3652058):
                stop = False
                try:
                    effective_date = edate + self.periodicity.to_timedelta(
                        n=self.periodicity_n, i=i, same_date=edate)
                except (OverflowError, ValueError):  # year is out of range
                    # effective_date = date.max
                    # stop = True
                    break

                if self.accrual_calculation_schedule_id is not None:
                    if effective_date >= fdate:
                        # magic date
                        effective_date = fdate - timedelta(days=1)
                        stop = True

                # notification_date = effective_date - notify_in_n_days
                # if self.effective_date <= notification_date <= self.final_date or self.effective_date <= effective_date <= self.final_date:
                #     dates.append((effective_date, notification_date))
                add_date(effective_date)

                if stop or effective_date >= fdate:
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

        # _l.debug('self.all_dates %s' % self.all_dates)
        # _l.debug('now %s' % now)

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
                                       verbose_name=gettext_lazy('event schedule'), on_delete=models.CASCADE)
    # transaction_type = models.ForeignKey('transactions.TransactionType', on_delete=models.PROTECT,
    #                                      verbose_name=gettext_lazy('transaction type'))

    transaction_type = models.CharField(max_length=255, null=True, blank=True,
                                        verbose_name=gettext_lazy('transaction type'))

    # T O D O: on auto generate fill 'Book: ' + transaction_type
    text = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                            verbose_name=gettext_lazy('text'))
    # T O D O: add to MasterUser defaults
    is_sent_to_pending = models.BooleanField(default=True, verbose_name=gettext_lazy('is sent to pending'))
    # T O D O: add to MasterUser defaults
    # T O D O: rename to: is_book_automatic (used when now notification)
    is_book_automatic = models.BooleanField(default=True, verbose_name=gettext_lazy('is book automatic'))
    button_position = models.IntegerField(default=0, verbose_name=gettext_lazy('button position'))

    json_data = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('json data'))

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
        verbose_name = gettext_lazy('event schedule action')
        verbose_name_plural = gettext_lazy('event schedule actions')
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
        (NEW, gettext_lazy('New')),
        (INFORMED, gettext_lazy('Informed')),
        (BOOKED_SYSTEM_DEFAULT, gettext_lazy('Booked (system, default)')),
        (BOOKED_USER_ACTIONS, gettext_lazy('Booked (user, actions)')),
        (BOOKED_USER_DEFAULT, gettext_lazy('Booked (user, default)')),

        (BOOKED_PENDING_SYSTEM_DEFAULT, gettext_lazy('Booked, pending (system, default)')),
        (BOOKED_PENDING_USER_ACTIONS, gettext_lazy('Booked, pending (user, actions)')),
        (BOOKED_PENDING_USER_DEFAULT, gettext_lazy('Booked, pending (user, default)')),
        (ERROR, gettext_lazy('Error')),
    )

    master_user = models.ForeignKey(MasterUser, related_name='generated_events',
                                    verbose_name=gettext_lazy('master user'), on_delete=models.CASCADE)

    effective_date = models.DateField(default=date_now, db_index=True, verbose_name=gettext_lazy('effective date'))
    effective_date_notified = models.BooleanField(default=False, db_index=True,
                                                  verbose_name=gettext_lazy('effective date notified'))
    notification_date = models.DateField(default=date_now, db_index=True,
                                         verbose_name=gettext_lazy('notification date'))
    notification_date_notified = models.BooleanField(default=False, db_index=True,
                                                     verbose_name=gettext_lazy('notification date notified'))

    status = models.PositiveSmallIntegerField(default=NEW, choices=STATUS_CHOICES, db_index=True,
                                              verbose_name=gettext_lazy('status'))
    status_date = models.DateTimeField(default=timezone.now, db_index=True, verbose_name=gettext_lazy('status date'))

    event_schedule = models.ForeignKey(EventSchedule, on_delete=models.CASCADE,
                                       related_name='generated_events', verbose_name=gettext_lazy('event schedule'))

    instrument = models.ForeignKey('instruments.Instrument', null=True, blank=True, on_delete=models.PROTECT,
                                   related_name='generated_events', verbose_name=gettext_lazy('instrument'))
    portfolio = models.ForeignKey('portfolios.Portfolio', null=True, blank=True, on_delete=models.PROTECT,
                                  related_name='generated_events', verbose_name=gettext_lazy('portfolio'))
    account = models.ForeignKey('accounts.Account', null=True, blank=True, on_delete=models.PROTECT,
                                related_name='generated_events', verbose_name=gettext_lazy('account'))
    strategy1 = models.ForeignKey('strategies.Strategy1', null=True, blank=True, on_delete=models.PROTECT,
                                  related_name='generated_events', verbose_name=gettext_lazy('strategy1'))
    strategy2 = models.ForeignKey('strategies.Strategy2', null=True, blank=True, on_delete=models.PROTECT,
                                  related_name='generated_events', verbose_name=gettext_lazy('strategy2'))
    strategy3 = models.ForeignKey('strategies.Strategy3', null=True, blank=True, on_delete=models.PROTECT,
                                  related_name='generated_events', verbose_name=gettext_lazy('strategy3'))
    position = models.FloatField(default=0.0, verbose_name=gettext_lazy('position'))

    action = models.ForeignKey(EventScheduleAction, null=True, blank=True, on_delete=models.SET_NULL,
                               related_name='generated_events', verbose_name=gettext_lazy('action'))
    transaction_type = models.ForeignKey('transactions.TransactionType', null=True, blank=True,
                                         on_delete=models.SET_NULL, related_name='generated_events',
                                         verbose_name=gettext_lazy('transaction type'))
    complex_transaction = models.ForeignKey('transactions.ComplexTransaction', null=True, blank=True,
                                            on_delete=models.SET_NULL, related_name='generated_events',
                                            verbose_name=gettext_lazy('complex transaction'))
    member = models.ForeignKey('users.Member', null=True, blank=True, on_delete=models.SET_NULL,
                               verbose_name=gettext_lazy('member'))

    json_data = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('json data'))

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
        verbose_name = gettext_lazy('generated event')
        verbose_name_plural = gettext_lazy('generated events')
        ordering = ['effective_date']

    def __str__(self):
        return 'Event #%s' % self.id

    def processed(self, member, action, complex_transaction, status=BOOKED_SYSTEM_DEFAULT):

        from poms.transactions.models import TransactionType
        self.member = member
        self.action = action

        self.status = status

        self.status_date = timezone.now()

        self.transaction_type = TransactionType.objects.get(user_code=action.transaction_type,
                                                            master_user=member.master_user)
        self.complex_transaction = complex_transaction

    def is_notify_on_effective_date(self, now=None):
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
        if self.status == GeneratedEvent.NEW:
            now = now or date_now()
            notification_class = self.event_schedule.notification_class
            return self.effective_date == now and notification_class.is_apply_default_on_effective_date
        return False

    def is_apply_default_on_notification_date(self, now=None):
        if self.status == GeneratedEvent.NEW:
            now = now or date_now()
            notification_class = self.event_schedule.notification_class
            return self.notification_date == now and notification_class.is_apply_default_on_notification_date
        return False

    def is_apply_default_on_date(self, now=None):
        return self.is_apply_default_on_effective_date(now) or self.is_apply_default_on_notification_date(now)

    def is_need_reaction_on_effective_date(self, now=None):
        if self.status == GeneratedEvent.NEW:
            now = now or date_now()
            notification_class = self.event_schedule.notification_class
            return self.effective_date == now and notification_class.is_need_reaction_on_effective_date
        return False

    def is_need_reaction_on_notification_date(self, now=None):
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

    def save(self, *args, **kwargs):

        super(GeneratedEvent, self).save(*args, **kwargs)

        try:

            if self.status == GeneratedEvent.NEW:
                from poms.system_messages.handlers import send_system_message
                send_system_message(master_user=self.master_user,
                                    title='Event',
                                    description=self.event_schedule.description,
                                    type='info',
                                    section='events',
                                    linked_event=self)
        except Exception as e:
            _l.error("Could not send system message on generating event %s" % e)


class EventScheduleConfig(models.Model):
    master_user = models.OneToOneField('users.MasterUser', related_name='instrument_event_schedule_config',
                                       verbose_name=gettext_lazy('master user'), on_delete=models.CASCADE)

    name = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                            verbose_name=gettext_lazy('name'))
    description = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                   verbose_name=gettext_lazy('description'))
    notification_class = models.ForeignKey('transactions.NotificationClass', null=True, blank=True,
                                           on_delete=models.PROTECT, verbose_name=gettext_lazy('notification class'))
    notify_in_n_days = models.PositiveSmallIntegerField(default=0, verbose_name=gettext_lazy('notify in N days'))
    action_text = models.CharField(max_length=255, blank=True, default='', verbose_name=gettext_lazy('action text'))
    action_is_sent_to_pending = models.BooleanField(default=True,
                                                    verbose_name=gettext_lazy('action is sent to pending'))
    action_is_book_automatic = models.BooleanField(default=True, verbose_name=gettext_lazy('action is book automatic'))

    class Meta:
        verbose_name = gettext_lazy('event schedule config')
        verbose_name_plural = gettext_lazy('event schedule configs')

    def __str__(self):
        return gettext_lazy('event schedule config')

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
