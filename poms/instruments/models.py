import json
import logging
import traceback
from datetime import date, datetime, timedelta
from math import isnan

from dateutil import relativedelta, rrule
from django.contrib.contenttypes.fields import GenericRelation
from django.core import serializers
from django.core.exceptions import ObjectDoesNotExist
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy

from poms.common.constants import SYSTEM_VALUE_TYPES, SystemValueType
from poms.common.formula_accruals import get_coupon
from poms.common.models import (
    EXPRESSION_FIELD_LENGTH,
    AbstractClassModel,
    DataTimeStampedModel,
    FakeDeletableModel,
    NamedModel,
)
from poms.common.utils import date_now, isclose
from poms.common.wrapper_models import NamedModelAutoMapping
from poms.configuration.models import ConfigurationModel
from poms.currencies.models import CurrencyHistory
from poms.expressions_engine import formula
from poms.obj_attrs.models import GenericAttribute, GenericAttributeType
from poms.pricing.models import (
    CurrencyPricingScheme,
    InstrumentPricingPolicy,
    InstrumentPricingScheme,
)
from poms.users.models import EcosystemDefault, MasterUser

_l = logging.getLogger("poms.instruments")
DATE_FORMAT = "%Y-%m-%d"


class InstrumentClass(AbstractClassModel):
    GENERAL = 1
    EVENT_AT_MATURITY = 2
    REGULAR_EVENT_AT_MATURITY = 3
    PERPETUAL_REGULAR_EVENT = 4
    CONTRACT_FOR_DIFFERENCE = 5
    DEFAULT = 6

    CLASSES = (
        (
            GENERAL,
            "GENERAL",
            gettext_lazy("General Class"),
        ),
        (
            EVENT_AT_MATURITY,
            "EVENT_AT_MATURITY",
            gettext_lazy("Event at Maturity"),
        ),
        (
            REGULAR_EVENT_AT_MATURITY,
            "REGULAR_EVENT_AT_MATURITY",
            gettext_lazy("Regular Event with Maturity"),
        ),
        (
            PERPETUAL_REGULAR_EVENT,
            "PERPETUAL_REGULAR_EVENT",
            gettext_lazy("Perpetual Regular Event"),
        ),
        (
            CONTRACT_FOR_DIFFERENCE,
            "CONTRACT_FOR_DIFFERENCE",
            gettext_lazy("Contract for Difference"),
        ),
        (DEFAULT, "-", gettext_lazy("Default")),
    )

    class Meta(AbstractClassModel.Meta):
        verbose_name = gettext_lazy("instrument class")
        verbose_name_plural = gettext_lazy("instrument classes")

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
        (SKIP, "SKIP", gettext_lazy("No Pricing (no Price History)")),
        (
            FORMULA_ALWAYS,
            "FORMULA_ALWAYS",
            gettext_lazy(
                "Don't download, just apply Formula / Pricing Policy (always)"
            ),
        ),
        (
            FORMULA_IF_OPEN,
            "FORMULA_IF_OPEN",
            gettext_lazy(
                "Download & apply Formula / Pricing Policy (if non-zero position)"
            ),
        ),
        (
            PROVIDER_ALWAYS,
            "PROVIDER_ALWAYS",
            gettext_lazy("Download & apply Formula / Pricing Policy (always)"),
        ),
        (
            PROVIDER_IF_OPEN,
            "PROVIDER_IF_OPEN",
            gettext_lazy(
                "Don't download, just apply Formula / Pricing Policy (if non-zero position)"
            ),
        ),
        (DEFAULT, "-", gettext_lazy("Use Default Price (no Price History)")),
    )

    class Meta(AbstractClassModel.Meta):
        verbose_name = gettext_lazy("daily pricing model")
        verbose_name_plural = gettext_lazy("daily pricing models")


class PricingCondition(AbstractClassModel):
    NO_VALUATION = 1
    RUN_VALUATION_IF_NON_ZERO = 2
    RUN_VALUATION_ALWAYS = 3

    CLASSES = (
        (NO_VALUATION, "NO_VALUATION", gettext_lazy("Don't Run Valuation")),
        (
            RUN_VALUATION_IF_NON_ZERO,
            "RUN_VALUATION_IF_OPEN",
            gettext_lazy("Run Valuation: if non-zero position"),
        ),
        (
            RUN_VALUATION_ALWAYS,
            "RUN_VALUATION_ALWAYS",
            gettext_lazy("Run Valuation: always"),
        ),
    )

    class Meta(AbstractClassModel.Meta):
        verbose_name = gettext_lazy("pricing condition")
        verbose_name_plural = gettext_lazy("pricing conditions ")
        base_manager_name = "objects"


class ExposureCalculationModel(AbstractClassModel):
    MARKET_VALUE = 1
    PRICE_EXPOSURE = 2
    DELTA_ADJUSTED_PRICE_EXPOSURE = 3
    UNDERLYING_LONG_SHORT_EXPOSURE_NET = 4
    UNDERLYING_LONG_SHORT_EXPOSURE_SPLIT = 5

    CLASSES = (
        (MARKET_VALUE, "MARKET_VALUE", gettext_lazy("Market value")),
        (PRICE_EXPOSURE, "PRICE_EXPOSURE", gettext_lazy("Price exposure")),
        (
            DELTA_ADJUSTED_PRICE_EXPOSURE,
            "DELTA_ADJUSTED_PRICE_EXPOSURE",
            gettext_lazy("Delta adjusted price exposure"),
        ),
        (
            UNDERLYING_LONG_SHORT_EXPOSURE_NET,
            "UNDERLYING_LONG_SHORT_EXPOSURE_NET",
            gettext_lazy("Underlying long short exposure net"),
        ),
        (
            UNDERLYING_LONG_SHORT_EXPOSURE_SPLIT,
            "UNDERLYING_LONG_SHORT_EXPOSURE_SPLIT",
            gettext_lazy("Underlying long short exposure split"),
        ),
    )

    class Meta(AbstractClassModel.Meta):
        verbose_name = gettext_lazy("Exposure calculation model")
        verbose_name_plural = gettext_lazy("Exposure calculation models ")


class LongUnderlyingExposure(AbstractClassModel):
    ZERO = 1
    LONG_UNDERLYING_INSTRUMENT_PRICE_EXPOSURE = 2
    LONG_UNDERLYING_INSTRUMENT_PRICE_DELTA = 3
    LONG_UNDERLYING_CURRENCY_FX_RATE_EXPOSURE = 4
    LONG_UNDERLYING_CURRENCY_FX_RATE_DELTA_ADJUSTED_EXPOSURE = 5

    CLASSES = (
        (ZERO, "ZERO", gettext_lazy("Zero")),
        (
            LONG_UNDERLYING_INSTRUMENT_PRICE_EXPOSURE,
            "LONG_UNDERLYING_INSTRUMENT_PRICE_EXPOSURE",
            gettext_lazy("Long Underlying Instrument Price Exposure"),
        ),
        (
            LONG_UNDERLYING_INSTRUMENT_PRICE_DELTA,
            "LONG_UNDERLYING_INSTRUMENT_PRICE_DELTA",
            gettext_lazy("Long Underlying Instrument Price Delta"),
        ),
        (
            LONG_UNDERLYING_CURRENCY_FX_RATE_EXPOSURE,
            "LONG_UNDERLYING_CURRENCY_FX_RATE_EXPOSURE",
            gettext_lazy("Long Underlying Currency FX Rate Exposure"),
        ),
        (
            LONG_UNDERLYING_CURRENCY_FX_RATE_DELTA_ADJUSTED_EXPOSURE,
            "LONG_UNDERLYING_CURRENCY_FX_RATE_DELTA_ADJUSTED_EXPOSURE",
            gettext_lazy("Long Underlying Currency FX Rate Delta-adjusted Exposure"),
        ),
    )

    class Meta(AbstractClassModel.Meta):
        verbose_name = gettext_lazy("Long underlying exposure")
        verbose_name_plural = gettext_lazy("Long underlying exposure ")


class ShortUnderlyingExposure(AbstractClassModel):
    ZERO = 1
    SHORT_UNDERLYING_INSTRUMENT_PRICE_EXPOSURE = 2
    SHORT_UNDERLYING_INSTRUMENT_PRICE_DELTA = 3
    SHORT_UNDERLYING_CURRENCY_FX_RATE_EXPOSURE = 4
    SHORT_UNDERLYING_CURRENCY_FX_RATE_DELTA_ADJUSTED_EXPOSURE = 5

    CLASSES = (
        (ZERO, "ZERO", gettext_lazy("Zero")),
        (
            SHORT_UNDERLYING_INSTRUMENT_PRICE_EXPOSURE,
            "SHORT_UNDERLYING_INSTRUMENT_PRICE_EXPOSURE",
            gettext_lazy("Short Underlying Instrument Price Exposure"),
        ),
        (
            SHORT_UNDERLYING_INSTRUMENT_PRICE_DELTA,
            "SHORT_UNDERLYING_INSTRUMENT_PRICE_DELTA",
            gettext_lazy("Short Underlying Instrument Price Delta"),
        ),
        (
            SHORT_UNDERLYING_CURRENCY_FX_RATE_EXPOSURE,
            "SHORT_UNDERLYING_CURRENCY_FX_RATE_EXPOSURE",
            gettext_lazy("Short Underlying Currency FX Rate Exposure"),
        ),
        (
            SHORT_UNDERLYING_CURRENCY_FX_RATE_DELTA_ADJUSTED_EXPOSURE,
            "SHORT_UNDERLYING_CURRENCY_FX_RATE_DELTA_ADJUSTED_EXPOSURE",
            gettext_lazy("Short Underlying Currency FX Rate Delta-adjusted Exposure"),
        ),
    )

    class Meta(AbstractClassModel.Meta):
        verbose_name = gettext_lazy("Short underlying exposure")
        verbose_name_plural = gettext_lazy("Short underlying exposure ")


class AccrualCalculationModel(AbstractClassModel):

    DAY_COUNT_NONE = 1  # Probably dont used
    DAY_COUNT_ACT_ACT_ISMA = 2  # Actual/Actual (ICMA): Used mainly for Eurobonds. Considers actual days in period and year fraction is # based on the actual number of days in the respective coupon period.
    DAY_COUNT_ACT_ACT_ISDA = 3  # Actual/Actual (ISDA): Actual days in the period. Uses 365 or 366 for year fraction. Defined by ISDA.
    DAY_COUNT_ACT_360 = 4  # Actual/360: Actual days in the period divided by 360.
    DAY_COUNT_ACT_365 = 5  # Actual/365 (Actual/365F): Actual days in period over a fixed 365-day year.
    # ACT_365_25 = 6 # DEPRECATED
    DAY_COUNT_ACT_365L = 7  # Actual/365L: Similar to Actual/365, but uses 366 for leap years.
    # ACT_1_365 = 8 # DEPRECATED
    # ACT_1_360 = 9 # DEPRECATED
    # C_30_ACT = 10 # DEPRECATED
    DAY_COUNT_30_360_ISDA = 11  # 30/360 (30/360 ISDA): Assumes 30 days in a month and 360 days in a year. Used by ISDA for swaps.
    # C_30_360_NO_EOM = 12 # DEPRECATED
    DAY_COUNT_30E_PLUS_360 = 24  # 30E+/360: Similar to 30E/360, but with adjustments for end-of-month dates.
    # C_30E_P_360_ITL = 13 # DEPRECATED
    DAY_COUNT_NL_365 = 14  # NL/365: Uses actual days but assumes 365 days in year, even for leap years.
    # NL_365_NO_EOM = 15 # DEPRECATED
    DAY_COUNT_30_360_ISMA = 16 # 30/360 (30/360 ISMA): Also known as 30/360 ICMA or 30/360 European. Assumes 30 days in each month and 360 days in a year
    # ISMA_30_360_NO_EOM = 17 DEPRECATED
    DAY_COUNT_30_360_US = 18  # 30/360 US: U.S. version of 30/360. Adjusts end-month dates, considers February with 30 days.
    #US_MINI_30_360_NO_EOM = 19 #DEPRECATED
    DAY_COUNT_BD_252 = 20 # # BD/252: Based on the number of business days in the period over a 252 business day year (common in Brazilian markets).
    DAY_COUNT_30_360_GERMAN = 21 # 30/360 German: German variation of 30/360. Specific rules for handling end-month and February dates.
    # GERMAN_30_360_NO_EOM = 22 #DEPRECATED
    #REVERSED_ACT_365 = 23 #DEPRECATED

    # NEW DAY COUNT CONVENTION
    # 2023-09-07

    DAY_COUNT_ACT_ACT_AFB = 26 # Actual/Actual (AFB): French version of Actual/Actual. It's commonly used for Euro denominated bonds.
    DAY_COUNT_ACT_365_FIXED = 27 # Actual/365: Assumes a fixed 365-day year.

    DAY_COUNT_30E_360 = 28  # 30E/360: European version. Assumes 30 days per month, 360 days per year, but doesn't adjust end-month dates.
    DAY_COUNT_ACT_365A = 29  # Actual/365A: Year fraction is actual days in period over average of 365 and 366 if leap year included.
    DAY_COUNT_ACT_366 = 30  # Actual/366: Assumes a fixed 366-day year.
    DAY_COUNT_ACT_364 = 31  # Actual/364: Assumes a fixed 364-day year.
    DAY_COUNT_SIMPLE = 100  # Simple: Interest is calculated on the principal amount, or on that portion of the principal amount which remains unpaid.

    DAY_COUNT_30_365 = 32  # 30/365: Assumes 30 days in each month and 365 days in a year.


    CLASSES = (
        (DAY_COUNT_NONE, "NONE", gettext_lazy("none")),
        (DAY_COUNT_ACT_ACT_ISMA, "DAY_COUNT_ACT_ACT_ISMA", gettext_lazy("Actual/Actual (ICMA)")),
        (DAY_COUNT_ACT_ACT_ISDA, "DAY_COUNT_ACT_ACT_ISDA", gettext_lazy("Actual/Actual (ISDA)")),
        (DAY_COUNT_ACT_360, "DAY_COUNT_ACT_360", gettext_lazy("Actual/360")),
        (DAY_COUNT_ACT_365, "DAY_COUNT_ACT_365", gettext_lazy("Actual/365")),
        (DAY_COUNT_ACT_365L, "DAY_COUNT_ACT_365L", gettext_lazy("Actual/365L")),
        (DAY_COUNT_30_360_ISDA, "DAY_COUNT_30_360_ISDA", gettext_lazy("30/360 (30/360 ISDA)")),
        (DAY_COUNT_30E_PLUS_360, "DAY_COUNT_30E_PLUS_360", gettext_lazy("30E+/360")),
        (DAY_COUNT_NL_365, "DAY_COUNT_NL_365", gettext_lazy("NL/365")),
        (DAY_COUNT_30_360_ISMA, "DAY_COUNT_30_360_ISMA", gettext_lazy("30/360 (30/360 ISMA)")),
        (DAY_COUNT_30_360_US, "DAY_COUNT_30_360_US", gettext_lazy("30/360 US")),
        (DAY_COUNT_BD_252, "DAY_COUNT_BD_252", gettext_lazy("BD/252")),
        (DAY_COUNT_30_360_GERMAN, "DAY_COUNT_30_360_GERMAN", gettext_lazy("30/360 German")),
        (DAY_COUNT_ACT_ACT_AFB, "DAY_COUNT_ACT_ACT_AFB", gettext_lazy("Actual/Actual (AFB)")),
        (DAY_COUNT_ACT_365_FIXED, "DAY_COUNT_ACT_365_FIXED", gettext_lazy("Actual/365 (Actual/365F)")),
        (DAY_COUNT_30E_360, "DAY_COUNT_30E_360", gettext_lazy("30E/360")),
        (DAY_COUNT_ACT_365A, "DAY_COUNT_ACT_365A", gettext_lazy("Actual/365A")),
        (DAY_COUNT_ACT_366, "DAY_COUNT_ACT_366", gettext_lazy("Actual/366")),
        (DAY_COUNT_ACT_364, "DAY_COUNT_ACT_364", gettext_lazy("Actual/364")),
        (DAY_COUNT_SIMPLE, "DAY_COUNT_SIMPLE", gettext_lazy("Simple")),
        (DAY_COUNT_30_365, "DAY_COUNT_30_365", gettext_lazy("30/365")),
    )

    @staticmethod
    def get_quantlib_day_count(finmars_accrual_calculation_model):
        import QuantLib as ql

        default = ql.SimpleDayCounter()

        map_daycount_convention = {
            AccrualCalculationModel.DAY_COUNT_30_360_ISDA: ql.Thirty360(ql.Thirty360.ISDA),
            AccrualCalculationModel.DAY_COUNT_30_360_ISMA: ql.Thirty360(ql.Thirty360.ISMA),
            AccrualCalculationModel.DAY_COUNT_30_360_US: ql.Thirty360(ql.Thirty360.USA),
            AccrualCalculationModel.DAY_COUNT_30E_360: ql.Thirty360(ql.Thirty360.European),
            AccrualCalculationModel.DAY_COUNT_30_360_GERMAN: ql.Thirty360(ql.Thirty360.German),
            AccrualCalculationModel.DAY_COUNT_30E_PLUS_360: ql.Thirty360(ql.Thirty360.Italian),
            AccrualCalculationModel.DAY_COUNT_ACT_ACT_ISDA: ql.ActualActual(ql.ActualActual.ISDA),
            AccrualCalculationModel.DAY_COUNT_ACT_ACT_ISMA: ql.ActualActual(ql.ActualActual.ISMA),
            AccrualCalculationModel.DAY_COUNT_ACT_365: ql.ActualActual(ql.ActualActual.Actual365),
            AccrualCalculationModel.DAY_COUNT_ACT_365_FIXED: ql.Actual365Fixed(),
            AccrualCalculationModel.DAY_COUNT_ACT_360: ql.Actual360(),
            AccrualCalculationModel.DAY_COUNT_ACT_365A: ql.Actual365Fixed(),
            AccrualCalculationModel.DAY_COUNT_ACT_365L: ql.Actual365Fixed(ql.Actual365Fixed.NoLeap),
            AccrualCalculationModel.DAY_COUNT_NL_365: ql.Actual365Fixed(ql.Actual365Fixed.NoLeap),
            AccrualCalculationModel.DAY_COUNT_ACT_366: ql.Actual366(),
            AccrualCalculationModel.DAY_COUNT_ACT_364: ql.Actual364(),
            AccrualCalculationModel.DAY_COUNT_BD_252: ql.Business252(),
            AccrualCalculationModel.DAY_COUNT_SIMPLE: ql.SimpleDayCounter(),
            AccrualCalculationModel.DAY_COUNT_30_365: ql.Thirty365(),
            AccrualCalculationModel.DAY_COUNT_ACT_ACT_AFB: ql.ActualActual(ql.ActualActual.AFB),
        }

        return map_daycount_convention.get(finmars_accrual_calculation_model, default)

    class Meta(AbstractClassModel.Meta):
        verbose_name = gettext_lazy("accrual calculation model")
        verbose_name_plural = gettext_lazy("accrual calculation models")


class PaymentSizeDetail(AbstractClassModel):
    PERCENT = 1
    PER_ANNUM = 2
    PER_QUARTER = 3
    PER_MONTH = 4
    PER_WEEK = 5
    PER_DAY = 6
    DEFAULT = 7
    CLASSES = (
        (PERCENT, "PERCENT", gettext_lazy("% per annum")),
        (PER_ANNUM, "PER_ANNUM", gettext_lazy("per annum")),
        (PER_QUARTER, "PER_QUARTER", gettext_lazy("per quarter")),
        (PER_MONTH, "PER_MONTH", gettext_lazy("per month")),
        (PER_WEEK, "PER_WEEK", gettext_lazy("per week")),
        (PER_DAY, "PER_DAY", gettext_lazy("per day")),
        (DEFAULT, "-", gettext_lazy("Default")),
    )

    class Meta(AbstractClassModel.Meta):
        verbose_name = gettext_lazy("payment size detail")
        verbose_name_plural = gettext_lazy("payment size details")


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
        (N_DAY, "N_DAY", gettext_lazy("N Days")),
        (N_WEEK_EOBW, "N_WEEK_EOBW", gettext_lazy("N Weeks (eobw)")),
        (N_MONTH_EOM, "N_MONTH_EOM", gettext_lazy("N Months (eom)")),
        (N_MONTH_SAME_DAY, "N_MONTH_SAME_DAY", gettext_lazy("N Months (same date)")),
        (N_YEAR_EOY, "N_YEAR_EOY", gettext_lazy("N Years (eoy)")),
        (N_YEAR_SAME_DAY, "N_YEAR_SAME_DAY", gettext_lazy("N Years (same date)")),
        (WEEKLY, "WEEKLY", gettext_lazy("Weekly")),
        (MONTHLY, "MONTHLY", gettext_lazy("Monthly")),
        (BIMONTHLY, "BIMONTHLY", gettext_lazy("Bimonthly")),
        (QUARTERLY, "QUARTERLY", gettext_lazy("Quarterly")),
        (SEMI_ANNUALLY, "SEMI_ANNUALLY", gettext_lazy("Semi-annually")),
        (ANNUALLY, "ANNUALLY", gettext_lazy("Annually")),
        (DEFAULT, "-", gettext_lazy("-")),
    )

    @staticmethod
    def get_quantlib_periodicity(finmars_periodicity):
        import QuantLib as ql

        default = ql.Period(12, ql.Months)  # default semi-annually

        mapping = {
            # TODO probably add mapping for other finmars periodicities
            Periodicity.N_DAY: ql.Period(1, ql.Days),
            Periodicity.WEEKLY: ql.Period(1, ql.Weeks),
            Periodicity.MONTHLY: ql.Period(1, ql.Months),
            Periodicity.BIMONTHLY: ql.Period(2, ql.Months),
            Periodicity.QUARTERLY: ql.Period(3, ql.Months),
            Periodicity.SEMI_ANNUALLY: ql.Period(6, ql.Months),
            Periodicity.ANNUALLY: ql.Period(12, ql.Months),
        }

        result = mapping.get(finmars_periodicity, default)

        return result

    class Meta(AbstractClassModel.Meta):
        verbose_name = gettext_lazy("periodicity")
        verbose_name_plural = gettext_lazy("periodicities")

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
            return relativedelta.relativedelta(
                years=n * i, month=same_date.month, day=same_date.day
            )
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
        (AVCO, "avco", gettext_lazy("AVCO")),
        (FIFO, "fifo", gettext_lazy("FIFO")),
        # (LIFO, "lifo", gettext_lazy('LIFO')),
    )

    class Meta(AbstractClassModel.Meta):
        verbose_name = gettext_lazy("cost method")
        verbose_name_plural = gettext_lazy("cost methods")


class Country(DataTimeStampedModel):
    name = models.CharField(
        max_length=255,
        verbose_name=gettext_lazy("name"),
    )
    user_code = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name=gettext_lazy("user code"),
    )
    short_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name=gettext_lazy("short name"),
    )
    description = models.TextField(
        blank=True,
        default="",
        verbose_name=gettext_lazy("description"),
    )
    alpha_2 = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("alpha 2"),
    )
    alpha_3 = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("alpha 3"),
    )
    country_code = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("country code"),
    )
    iso_3166_2 = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("iso_3166_2"),
    )
    region = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("region"),
    )
    sub_region = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("sub region"),
    )
    intermediate_region = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("intermediate region"),
    )
    region_code = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("region code"),
    )
    sub_region_code = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("sub region code"),
    )
    intermediate_region_code = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("intermediate region code"),
    )


class PricingPolicy(NamedModel, DataTimeStampedModel, ConfigurationModel):
    master_user = models.ForeignKey(
        MasterUser,
        related_name="pricing_policies",
        verbose_name=gettext_lazy("master user"),
        on_delete=models.CASCADE,
    )
    # expr - DEPRECATED
    expr = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        default="",
        blank=True,
        null=True,
        verbose_name=gettext_lazy("expression"),
    )
    default_instrument_pricing_scheme = models.ForeignKey(
        InstrumentPricingScheme,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("default instrument pricing scheme"),
        on_delete=models.SET_NULL,
    )
    default_currency_pricing_scheme = models.ForeignKey(
        CurrencyPricingScheme,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("default currency pricing scheme"),
        on_delete=models.SET_NULL,
    )

    class Meta(AbstractClassModel.Meta):
        verbose_name = gettext_lazy("pricing policy")
        verbose_name_plural = gettext_lazy("pricing policies")
        unique_together = [["master_user", "user_code"]]
        ordering = ["user_code"]
        base_manager_name = "objects"


class InstrumentType(
    NamedModelAutoMapping, FakeDeletableModel, DataTimeStampedModel, ConfigurationModel
):
    DIRECT_POSITION = 1
    FACTOR_ADJUSTED_POSITION = 2
    DO_NOT_SHOW = 3

    VALUE_TYPES = (
        (DIRECT_POSITION, gettext_lazy("Direct Position")),
        (FACTOR_ADJUSTED_POSITION, gettext_lazy("Factor Adjusted Position")),
        (DO_NOT_SHOW, gettext_lazy("Do not show")),
    )

    master_user = models.ForeignKey(
        MasterUser,
        related_name="instrument_types",
        verbose_name=gettext_lazy("master user"),
        on_delete=models.CASCADE,
    )
    instrument_class = models.ForeignKey(
        InstrumentClass,
        related_name="instrument_types",
        on_delete=models.PROTECT,
        verbose_name=gettext_lazy("instrument class"),
    )
    one_off_event = models.ForeignKey(
        "transactions.TransactionType",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
        verbose_name=gettext_lazy("one-off event"),
    )
    regular_event = models.ForeignKey(
        "transactions.TransactionType",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
        verbose_name=gettext_lazy("regular event"),
    )
    factor_same = models.ForeignKey(
        "transactions.TransactionType",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
        verbose_name=gettext_lazy("factor same"),
    )
    factor_up = models.ForeignKey(
        "transactions.TransactionType",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
        verbose_name=gettext_lazy("factor up"),
    )
    factor_down = models.ForeignKey(
        "transactions.TransactionType",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
        verbose_name=gettext_lazy("factor down"),
    )
    attributes = GenericRelation(
        GenericAttribute,
        verbose_name=gettext_lazy("attributes"),
    )
    has_second_exposure_currency = models.BooleanField(
        default=False,
        verbose_name=gettext_lazy("has second exposure currency"),
    )
    instrument_form_layouts = models.TextField(
        null=True,
        blank=True,
        verbose_name=gettext_lazy("instrument form layouts"),
    )
    payment_size_detail = models.ForeignKey(
        PaymentSizeDetail,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("payment size detail"),
    )
    accrued_currency = models.ForeignKey(
        "currencies.Currency",
        null=True,
        blank=True,
        related_name="instrument_types_accrued",
        on_delete=models.PROTECT,
        verbose_name=gettext_lazy("accrued currency"),
    )
    accrued_multiplier = models.FloatField(
        default=1.0,
        verbose_name=gettext_lazy("accrued multiplier"),
    )
    default_accrued = models.FloatField(
        default=0.0,
        verbose_name=gettext_lazy("default accrued"),
    )
    instrument_factor_schedule_json_data = models.TextField(
        null=True,
        blank=True,
        verbose_name=gettext_lazy("instrument factor schedule json data"),
    )
    exposure_calculation_model = models.ForeignKey(
        ExposureCalculationModel,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("exposure calculation model"),
        on_delete=models.SET_NULL,
    )
    long_underlying_instrument = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("long underlying instrument"),
    )
    underlying_long_multiplier = models.FloatField(
        default=1.0,
        verbose_name=gettext_lazy("underlying long multiplier"),
    )
    short_underlying_instrument = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("short underlying instrument"),
    )
    underlying_short_multiplier = models.FloatField(
        default=1.0,
        verbose_name=gettext_lazy("underlying short multiplier"),
    )
    long_underlying_exposure = models.ForeignKey(
        LongUnderlyingExposure,
        null=True,
        blank=True,
        related_name="instrument_type_long_instruments",
        verbose_name=gettext_lazy("long underlying exposure"),
        on_delete=models.SET_NULL,
    )
    short_underlying_exposure = models.ForeignKey(
        ShortUnderlyingExposure,
        null=True,
        blank=True,
        related_name="instrument_type_short_instruments",
        verbose_name=gettext_lazy("short underlying exposure"),
        on_delete=models.SET_NULL,
    )
    co_directional_exposure_currency = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("co directional exposure currency"),
    )
    co_directional_exposure_currency_value_type = models.PositiveSmallIntegerField(
        choices=SYSTEM_VALUE_TYPES,
        default=SystemValueType.RELATION,
        verbose_name=gettext_lazy("co directional exposure currency value type"),
    )
    counter_directional_exposure_currency = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("counter directional exposure currency"),
    )
    counter_directional_exposure_currency_value_type = models.PositiveSmallIntegerField(
        choices=SYSTEM_VALUE_TYPES,
        default=SystemValueType.RELATION,
        verbose_name=gettext_lazy("counter directional exposure currency value type"),
    )
    default_price = models.FloatField(
        default=0.0,
        verbose_name=gettext_lazy("default price"),
    )
    maturity_date = models.DateField(
        null=True,
        verbose_name=gettext_lazy("maturity date"),
    )
    maturity_price = models.FloatField(
        default=0.0,
        verbose_name=gettext_lazy("maturity price"),
    )
    pricing_currency = models.ForeignKey(
        "currencies.Currency",
        null=True,
        blank=True,
        related_name="instrument_types_pricing",
        on_delete=models.PROTECT,
        verbose_name=gettext_lazy("pricing currency"),
    )
    price_multiplier = models.FloatField(
        default=1.0,
        verbose_name=gettext_lazy("price multiplier"),
    )
    position_reporting = models.PositiveSmallIntegerField(
        choices=VALUE_TYPES,
        default=DIRECT_POSITION,
        verbose_name=gettext_lazy("position reporting"),
    )
    pricing_condition = models.ForeignKey(
        PricingCondition,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("pricing condition"),
        on_delete=models.SET_NULL,
    )
    reference_for_pricing = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name=gettext_lazy("reference for pricing"),
    )

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
                "allow_null": False,
            },
            {
                "key": "short_name",
                "name": "Short name",
                "value_type": 10,
                "allow_null": True,
            },
            {"key": "user_code", "name": "User code", "value_type": 10},
            {
                "key": "configuration_code",
                "name": "Configuration code",
                "value_type": 10,
            },
            {
                "key": "public_name",
                "name": "Public name",
                "value_type": 10,
                "allow_null": True,
            },
            {"key": "notes", "name": "Notes", "value_type": 10, "allow_null": True},
            {
                "key": "is_active",
                "name": "Is active",
                "value_type": 50,
                "allow_null": True,
            },
            {
                "key": "instrument_class",
                "name": "Instrument class",
                "value_type": "field",
                "value_content_type": "instruments.instrumentclass",
                "value_entity": "instrument-class",
                "code": "user_code",
                "allow_null": False,
            },
            {
                "key": "one_off_event",
                "name": "One off event",
                "value_type": "field",
                "value_entity": "transaction-type",
                "value_content_type": "transactions.transactiontype",
                "code": "user_code",
                "allow_null": False,
            },
            {
                "key": "regular_event",
                "name": "Regular event",
                "value_type": "field",
                "value_entity": "transaction-type",
                "value_content_type": "transactions.transactiontype",
                "code": "user_code",
                "allow_null": False,
            },
            {
                "key": "factor_same",
                "name": "Factor same",
                "value_type": "field",
                "value_entity": "transaction-type",
                "value_content_type": "transactions.transactiontype",
                "code": "user_code",
                "allow_null": False,
            },
            {
                "key": "factor_up",
                "name": "Factor up",
                "value_type": "field",
                "value_entity": "transaction-type",
                "value_content_type": "transactions.transactiontype",
                "code": "user_code",
                "allow_null": False,
            },
            {
                "key": "factor_down",
                "name": "Factor down",
                "value_type": "field",
                "value_entity": "transaction-type",
                "value_content_type": "transactions.transactiontype",
                "code": "user_code",
                "allow_null": False,
            },
            {
                "key": "has_second_exposure_currency",
                "name": "Has second exposure currency",
                "value_type": 50,
            },
            # region Exposure
            {
                "key": "underlying_long_multiplier",
                "name": "Underlying long multiplier",
                "value_type": 20,
            },
            {
                "key": "underlying_short_multiplier",
                "name": "Underlying short multiplier",
                "value_type": 20,
            },
            {
                "key": "co_directional_exposure_currency",
                "name": "Exposure Co-Directional Currency",
                "value_content_type": "currencies.currency",
                "value_entity": "currency",
                "code": "user_code",
                "value_type": "field",
            },
            {
                "key": "counter_directional_exposure_currency",
                "name": "Exposure Counter-Directional Currency",
                "value_content_type": "currencies.currency",
                "value_entity": "currency",
                "code": "user_code",
                "value_type": "field",
            },
            {
                "key": "long_underlying_exposure",
                "name": "Long Underlying Exposure",
                "value_content_type": "instruments.longunderlyingexposure",
                "value_entity": "long-underlying-exposure",
                "value_type": "field",
            },
            {
                "key": "short_underlying_exposure",
                "name": "Short Underlying Exposure",
                "value_content_type": "instruments.shortunderlyingexposure",
                "value_entity": "short-underlying-exposure",
                "value_type": "field",
            },
            {
                "key": "exposure_calculation_model",
                "name": "Exposure Calculation Model",
                "value_content_type": "instruments.exposurecalculationmodel",
                "value_entity": "exposure-calculation-model",
                "value_type": "field",
            },
            {
                "key": "long_underlying_instrument",
                "name": "Long Underlying Instrument",
                "value_content_type": "instruments.instrument",
                "value_entity": "instrument",
                "value_type": "field",
            },
            {
                "key": "short_underlying_instrument",
                "name": "Short Underlying Instrument",
                "value_content_type": "instruments.instrument",
                "value_entity": "instrument",
                "value_type": "field",
            },
            # endregion Exposure
            {
                "key": "accrued_currency",
                "name": "Accrued currency",
                "value_content_type": "currencies.currency",
                "value_entity": "currency",
                "code": "user_code",
                "value_type": "field",
            },
            {
                "key": "accrued_multiplier",
                "name": "Accrued multiplier",
                "value_type": 20,
            },
            {
                "key": "payment_size_detail",
                "name": "Payment size detail",
                "value_content_type": "instruments.paymentsizedetail",
                "value_entity": "payment-size-detail",
                "code": "user_code",
                "value_type": "field",
            },
            {
                "key": "default_accrued",
                "name": "Default accrued",
                "value_type": 20,
            },
            {
                "key": "default_price",
                "name": "Default price",
                "value_type": 20,
            },
            {
                "key": "maturity_date",
                "name": "Maturity date",
                "value_type": 40,
            },
            {
                "key": "maturity_price",
                "name": "Maturity price",
                "value_type": 20,
            },
        ]

    @property
    def instrument_factor_schedule_data(self):
        if not self.instrument_factor_schedule_json_data:
            return None

        try:
            return json.loads(self.instrument_factor_schedule_json_data)
        except (ValueError, TypeError):
            return None

    @instrument_factor_schedule_data.setter
    def instrument_factor_schedule_data(self, val):
        if val:
            self.instrument_factor_schedule_json_data = json.dumps(
                val, cls=DjangoJSONEncoder, sort_keys=True
            )
        else:
            self.instrument_factor_schedule_json_data = None

    class Meta(NamedModel.Meta, FakeDeletableModel.Meta):
        verbose_name = gettext_lazy("instrument type")
        verbose_name_plural = gettext_lazy("instrument types")
        permissions = [
            ("manage_instrumenttype", "Can manage instrument type"),
        ]

    def __str__(self):
        return self.user_code

    @property
    def is_default(self):
        return (
            self.master_user.instrument_type_id == self.id
            if self.master_user_id
            else False
        )


class InstrumentTypeAccrual(models.Model):
    instrument_type = models.ForeignKey(
        InstrumentType,
        on_delete=models.CASCADE,
        related_name="accruals",
        verbose_name=gettext_lazy("instrument type"),
    )
    name = models.CharField(
        max_length=255,
        verbose_name=gettext_lazy("name"),
    )
    order = models.IntegerField(
        default=0,
        verbose_name=gettext_lazy("order"),
    )
    autogenerate = models.BooleanField(
        default=True,
        verbose_name=gettext_lazy("autogenerate"),
    )
    json_data = models.TextField(
        null=True,
        blank=True,
        verbose_name=gettext_lazy("json data"),
    )

    class Meta:
        ordering = ["order"]

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


class InstrumentTypeEvent(models.Model):
    instrument_type = models.ForeignKey(
        InstrumentType,
        on_delete=models.CASCADE,
        related_name="events",
        verbose_name=gettext_lazy("instrument type"),
    )
    name = models.CharField(
        max_length=255,
        verbose_name=gettext_lazy("name"),
    )
    order = models.IntegerField(
        default=0,
        verbose_name=gettext_lazy("order"),
    )
    autogenerate = models.BooleanField(
        default=True,
        verbose_name=gettext_lazy("autogenerate"),
    )
    json_data = models.TextField(
        null=True,
        blank=True,
        verbose_name=gettext_lazy("json data"),
    )

    class Meta:
        ordering = ["order"]

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


class InstrumentTypeInstrumentAttribute(models.Model):
    STRING = 10
    NUMBER = 20
    CLASSIFIER = 30
    DATE = 40

    VALUE_TYPES = (
        (NUMBER, gettext_lazy("Number")),
        (STRING, gettext_lazy("String")),
        (DATE, gettext_lazy("Date")),
        (CLASSIFIER, gettext_lazy("Classifier")),
    )

    instrument_type = models.ForeignKey(
        InstrumentType,
        on_delete=models.CASCADE,
        related_name="instrument_attributes",
        verbose_name=gettext_lazy("instrument attributes"),
    )
    attribute_type_user_code = models.CharField(
        max_length=255,
        verbose_name=gettext_lazy("attribute type user code"),
    )
    value_type = models.PositiveSmallIntegerField(
        choices=VALUE_TYPES,
        default=STRING,
        verbose_name=gettext_lazy("value type"),
    )
    value_string = models.CharField(
        db_index=True,
        max_length=255,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("value (String)"),
    )
    value_float = models.FloatField(
        db_index=True,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("value (Float)"),
    )
    value_date = models.DateField(
        db_index=True,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("value (Date)"),
    )
    value_classifier = models.CharField(
        db_index=True,
        max_length=255,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("value (Classifier)"),
    )


class InstrumentTypeInstrumentFactorSchedule(models.Model):
    instrument_type = models.ForeignKey(
        InstrumentType,
        on_delete=models.CASCADE,
        related_name="instrument_factor_schedules",
        verbose_name=gettext_lazy("instrument attributes"),
    )
    effective_date = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("effective date"),
    )
    effective_date_value_type = models.PositiveSmallIntegerField(
        choices=SYSTEM_VALUE_TYPES,
        default=SystemValueType.DATE,
        verbose_name=gettext_lazy("effective date"),
    )
    position_factor_value = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("position factor value"),
    )
    position_factor_value_value_type = models.PositiveSmallIntegerField(
        choices=SYSTEM_VALUE_TYPES,
        default=SystemValueType.DATE,
        verbose_name=gettext_lazy("position factor value value type"),
    )
    factor_value1 = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("factor value 1"),
    )
    factor_value1_value_type = models.PositiveSmallIntegerField(
        choices=SYSTEM_VALUE_TYPES,
        default=SystemValueType.DATE,
        verbose_name=gettext_lazy("factor value1 value type"),
    )
    factor_value2 = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("factor value 2"),
    )
    factor_value2_value_type = models.PositiveSmallIntegerField(
        choices=SYSTEM_VALUE_TYPES,
        default=SystemValueType.DATE,
        verbose_name=gettext_lazy("factor value2 value type"),
    )
    factor_value3 = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("factor value 3 "),
    )
    factor_value3_value_type = models.PositiveSmallIntegerField(
        choices=SYSTEM_VALUE_TYPES,
        default=SystemValueType.DATE,
        verbose_name=gettext_lazy("factor value3 value type"),
    )

    class Meta:
        verbose_name = gettext_lazy("instrument type instrument factor schedule")
        verbose_name_plural = gettext_lazy(
            "instrument type  instrument factor schedules"
        )

    def __str__(self):
        return str(self.effective_date)


# noinspection PyUnresolvedReferences
class Instrument(NamedModelAutoMapping, FakeDeletableModel, DataTimeStampedModel):
    DIRECT_POSITION = 1
    FACTOR_ADJUSTED_POSITION = 2
    DO_NOT_SHOW = 3
    VALUE_TYPES = (
        (DIRECT_POSITION, gettext_lazy("Direct Position")),
        (FACTOR_ADJUSTED_POSITION, gettext_lazy("Factor Adjusted Position")),
        (DO_NOT_SHOW, gettext_lazy("Do not show")),
    )

    master_user = models.ForeignKey(
        MasterUser,
        related_name="instruments",
        verbose_name=gettext_lazy("master user"),
        on_delete=models.CASCADE,
    )
    instrument_type = models.ForeignKey(
        InstrumentType,
        on_delete=models.PROTECT,
        verbose_name=gettext_lazy("instrument type"),
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=gettext_lazy("is active"),
    )
    has_linked_with_portfolio = models.BooleanField(
        default=False,
        verbose_name=gettext_lazy("has linked with portfolio"),
    )
    pricing_currency = models.ForeignKey(
        "currencies.Currency",
        on_delete=models.PROTECT,
        verbose_name=gettext_lazy("pricing currency"),
    )
    price_multiplier = models.FloatField(
        default=1.0,
        verbose_name=gettext_lazy("price multiplier"),
    )
    accrued_currency = models.ForeignKey(
        "currencies.Currency",
        related_name="instruments_accrued",
        on_delete=models.PROTECT,
        verbose_name=gettext_lazy("accrued currency"),
    )
    accrued_multiplier = models.FloatField(
        default=1.0,
        verbose_name=gettext_lazy("accrued multiplier"),
    )
    payment_size_detail = models.ForeignKey(
        PaymentSizeDetail,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("payment size detail"),
    )
    default_price = models.FloatField(
        default=0.0,
        verbose_name=gettext_lazy("default price"),
    )
    default_accrued = models.FloatField(
        default=0.0,
        verbose_name=gettext_lazy("default accrued"),
    )
    user_text_1 = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("user text 1"),
        help_text=gettext_lazy("User specified field 1"),
    )
    user_text_2 = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("user text 2"),
        help_text=gettext_lazy("User specified field 2"),
    )
    user_text_3 = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("user text 3"),
        help_text=gettext_lazy("User specified field 3"),
    )
    reference_for_pricing = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name=gettext_lazy("reference for pricing"),
    )
    daily_pricing_model = models.ForeignKey(
        DailyPricingModel,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("daily pricing model"),
        on_delete=models.SET_NULL,
    )
    pricing_condition = models.ForeignKey(
        PricingCondition,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("pricing condition"),
        on_delete=models.SET_NULL,
    )
    exposure_calculation_model = models.ForeignKey(
        ExposureCalculationModel,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("exposure calculation model"),
        on_delete=models.SET_NULL,
    )
    long_underlying_instrument = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        related_name="long_underlying_instruments",
        verbose_name=gettext_lazy("long underlying instrument"),
        on_delete=models.SET_NULL,
    )
    underlying_long_multiplier = models.FloatField(
        default=1.0,
        verbose_name=gettext_lazy("underlying long multiplier"),
    )
    short_underlying_instrument = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        related_name="short_underlying_instruments",
        verbose_name=gettext_lazy("short underlying instrument"),
        on_delete=models.SET_NULL,
    )
    underlying_short_multiplier = models.FloatField(
        default=1.0,
        verbose_name=gettext_lazy("underlying short multiplier"),
    )
    long_underlying_exposure = models.ForeignKey(
        LongUnderlyingExposure,
        null=True,
        blank=True,
        related_name="long_instruments",
        verbose_name=gettext_lazy("long underlying exposure"),
        on_delete=models.SET_NULL,
    )
    short_underlying_exposure = models.ForeignKey(
        ShortUnderlyingExposure,
        null=True,
        blank=True,
        related_name="short_instruments",
        verbose_name=gettext_lazy("short underlying exposure"),
        on_delete=models.SET_NULL,
    )
    maturity_date = models.DateField(
        null=True,
        verbose_name=gettext_lazy("maturity date"),
    )
    maturity_price = models.FloatField(
        default=0.0,
        verbose_name=gettext_lazy("maturity price"),
    )
    attributes = GenericRelation(
        GenericAttribute,
        verbose_name=gettext_lazy("attributes"),
    )
    co_directional_exposure_currency = models.ForeignKey(
        "currencies.Currency",
        related_name="co_directional_exposure_currency",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("co directional exposure currency"),
    )
    counter_directional_exposure_currency = models.ForeignKey(
        "currencies.Currency",
        related_name="counter_directional_exposure_currency",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("counter directional exposure currency"),
    )
    position_reporting = models.PositiveSmallIntegerField(
        choices=VALUE_TYPES,
        default=DIRECT_POSITION,
        verbose_name=gettext_lazy("position reporting"),
    )
    country = models.ForeignKey(
        Country,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("Country"),
        on_delete=models.SET_NULL,
    )

    class Meta(NamedModel.Meta, FakeDeletableModel.Meta):
        verbose_name = gettext_lazy("instrument")
        verbose_name_plural = gettext_lazy("instruments")
        permissions = [
            ("manage_instrument", "Can manage instrument"),
        ]
        ordering = ["user_code"]

    @staticmethod
    def get_system_attrs():
        return [
            {"key": "name", "name": "Name", "value_type": 10},
            {"key": "short_name", "name": "Short name", "value_type": 10},
            {"key": "user_code", "name": "User code", "value_type": 10},
            {"key": "public_name", "name": "Public name", "value_type": 10},
            {"key": "notes", "name": "Notes", "value_type": 10},
            {
                "key": "instrument_type",
                "name": "Instrument type",
                "value_type": "field",
                "value_content_type": "instruments.instrumenttype",
                "value_entity": "instrument-type",
                "code": "user_code",
            },
            {"key": "is_active", "name": "Is active", "value_type": 50},
            {
                "key": "has_linked_with_portfolio",
                "name": "Has linked with portfolio",
                "value_type": 50,
            },
            {
                "key": "reference_for_pricing",
                "name": "Reference for pricing",
                "value_type": 10,
            },
            {
                "key": "pricing_currency",
                "name": "Pricing currency",
                "value_content_type": "currencies.currency",
                "value_entity": "currency",
                "code": "user_code",
                "value_type": "field",
            },
            {"key": "price_multiplier", "name": "Price multiplier", "value_type": 20},
            {
                "key": "position_reporting",
                "name": "Position reporting",
                "value_content_type": "instruments.positionreporting",
                "value_entity": "position-reporting",
                "value_type": "field",
            },
            {
                "key": "accrued_currency",
                "name": "Accrued currency",
                "value_content_type": "currencies.currency",
                "value_entity": "currency",
                "code": "user_code",
                "value_type": "field",
            },
            {"key": "maturity_date", "name": "Maturity date", "value_type": 40},
            {"key": "maturity_price", "name": "Maturity price", "value_type": 20},
            {
                "key": "accrued_multiplier",
                "name": "Accrued multiplier",
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
            {
                "key": "payment_size_detail",
                "name": "Accrual Size Clarification",
                "value_content_type": "instruments.paymentsizedetail",
                "value_entity": "payment-size-detail",
                "code": "user_code",
                "value_type": "field",
            },
            {
                "key": "default_price",
                "name": "Default price",
                "value_type": 20,
            },
            {
                "key": "default_accrued",
                "name": "Default accrued",
                "value_type": 20,
            },
            {
                "key": "user_text_1",
                "name": "User text 1",
                "value_type": 10,
            },
            {
                "key": "user_text_2",
                "name": "User text 2",
                "value_type": 10,
            },
            {
                "key": "user_text_3",
                "name": "User text 3",
                "value_type": 10,
            },
            {
                "key": "underlying_long_multiplier",
                "name": "Underlying long multiplier",
                "value_type": 20,
            },
            {
                "key": "underlying_short_multiplier",
                "name": "Underlying short multiplier",
                "value_type": 20,
            },
            {
                "key": "co_directional_exposure_currency",
                "name": "Exposure Co-Directional Currency",
                "value_content_type": "currencies.currency",
                "value_entity": "currency",
                "code": "user_code",
                "value_type": "field",
            },
            {
                "key": "counter_directional_exposure_currency",
                "name": "Exposure Counter-Directional Currency",
                "value_content_type": "currencies.currency",
                "value_entity": "currency",
                "code": "user_code",
                "value_type": "field",
            },
            {
                "key": "long_underlying_exposure",
                "name": "Long Underlying Exposure",
                "value_content_type": "instruments.longunderlyingexposure",
                "value_entity": "long-underlying-exposure",
                "value_type": "field",
            },
            {
                "key": "short_underlying_exposure",
                "name": "Short Underlying Exposure",
                "value_content_type": "instruments.shortunderlyingexposure",
                "value_entity": "short-underlying-exposure",
                "value_type": "field",
            },
            {
                "key": "exposure_calculation_model",
                "name": "Exposure Calculation Model",
                "value_content_type": "instruments.exposurecalculationmodel",
                "value_entity": "exposure-calculation-model",
                "value_type": "field",
            },
            {
                "key": "long_underlying_instrument",
                "name": "Long Underlying Instrument",
                "value_content_type": "instruments.instrument",
                "value_entity": "instrument",
                "value_type": "field",
            },
            {
                "key": "short_underlying_instrument",
                "name": "Short Underlying Instrument",
                "value_content_type": "instruments.instrument",
                "value_entity": "instrument",
                "value_type": "field",
            },
            {
                "key": "country",
                "name": "Country",
                "value_content_type": "instruments.country",
                "value_entity": "country",
                "code": "user_code",
                "value_type": "field",
            },
        ]

    @property
    def is_default(self):
        return (
            self.master_user.instrument_id == self.id if self.master_user_id else False
        )

    date_pattern = "%Y-%m-%d"  # YYYY-MM-DD, used in calculate_ytm method

    def get_first_accrual(self):
        result = None

        accruals = self.accrual_calculation_schedules.all()
        if len(accruals):
            result = accruals[0]

        return result

    def get_quantlib_bond(self):
        import QuantLib as ql

        bond = None

        face_value = (
            100.0  # TODO OG commented: probably we need to add parameter notional
        )
        calendar = ql.TARGET()

        if self.maturity_date:

            _l.info('get_quantlib_bond.self.type maturity_date %s' % type(self.maturity_date))
            _l.info('get_quantlib_bond.self.maturity_date %s' % self.maturity_date)
            _l.info('get_quantlib_bond.self.date_pattern %s' % self.date_pattern)

            maturity = ql.Date(str(self.maturity_date), self.date_pattern)

            if self.has_factor_schedules():
                factor_schedules = self.get_factors()

                factor_dates = [ql.Date(str(item.effective_date), self.date_pattern) for item in factor_schedules]
                factor_values = [item.factor_value for item in factor_schedules]

                # TODO OG commented: we need issue date

                first_accrual = self.get_first_accrual()

                business_convention = ql.Following

                periodicity = Periodicity.get_quantlib_periodicity(
                    first_accrual.periodicity
                )

                start_date = ql.Date(str(first_accrual.accrual_start_date), self.date_pattern)
                float_accrual_size = float(first_accrual.accrual_size) / 100
                # yield_guess = 0.1
                day_count = AccrualCalculationModel.get_quantlib_day_count(
                    first_accrual.accrual_calculation_model
                )
                # build accrual schedule
                # schedule = ql.MakeSchedule(start_date, maturity_date, period )

                schedule = ql.Schedule(
                    start_date,
                    maturity,
                    periodicity,
                    calendar,
                    business_convention,
                    business_convention,
                    ql.DateGeneration.Backward,
                    False,
                )

                # cast to dates list
                schedule_dates = list(schedule)

                notionals = []

                # TODO probably need to move somewhere else
                def active_factor(date, factors, factor_dates):
                    tmp_list = {idate for idate in factor_dates if idate <= date}
                    factor = 1
                    if len(tmp_list) > 0:
                        active_date = max(tmp_list)
                        index = factor_dates.index(active_date)
                        factor = factors[index]
                    return factor

                # we need notinals (factors) list to be of same length as accrual schedule
                for date in schedule_dates:
                    val = (
                            active_factor(
                                date=date, factors=factor_values, factor_dates=factor_dates
                            )
                            * face_value
                    )

                    notionals.append(val)

                bond = ql.AmortizingFixedRateBond(
                    0, notionals, schedule, [float_accrual_size], day_count
                )

            else:
                first_accrual = self.get_first_accrual()

                settlementDays = 0

                if first_accrual:
                    start = ql.Date(
                        str(first_accrual.accrual_start_date), self.date_pattern
                    )  # Start accrual date
                    periodicity = Periodicity.get_quantlib_periodicity(
                        first_accrual.periodicity
                    )

                    schedule = ql.MakeSchedule(
                        start, maturity, periodicity
                    )  # period - semiannual

                    float_accrual_size = float(first_accrual.accrual_size) / 100
                    day_count = AccrualCalculationModel.get_quantlib_day_count(
                        first_accrual.accrual_calculation_model
                    )

                    coupons = [float_accrual_size]

                    face_value = 100 # probably self.default_price

                    bond = ql.FixedRateBond(settlementDays, face_value, schedule, coupons, day_count)

                else:
                    bond = ql.ZeroCouponBond(
                        settlementDays=settlementDays,
                        calendar=calendar,
                        faceAmount=face_value,
                        maturityDate=maturity,
                    )
                    _l.info("ZeroCouponBond %s" % bond)

        return bond

    # Important function for calculating YTM
    # 2023-08-21
    def calculate_quantlib_ytm(self, date, price):
        import QuantLib as ql

        ytm = 0

        bond = self.get_quantlib_bond()

        # _l.info('calculate_quantlib_ytm %s ' % bond)
        # _l.info('calculate_quantlib_ytm type price %s ' % type(price))
        # _l.info('calculate_quantlib_ytm price %s ' % price)

        if bond:
            ql.Settings.instance().evaluationDate = ql.Date(str(date), self.date_pattern)

            try:
                frequency = bond.frequency()
            except Exception as e:
                _l.error("Could not take frequency from bond %s" % e)
                frequency = 1
            # _l.info('calculate_quantlib_ytm type price %s ' % type(price))
            # _l.info('calculate_quantlib_ytm type ql.Actual360 %s ' % bond.dayCounter())
            # _l.info('calculate_quantlib_ytm type ql.Compounded %s ' % type(ql.Compounded))
            _l.info('calculate_quantlib_ytm type frequency %s ' % type(frequency))
            _l.info('calculate_quantlib_ytm frequency %s ' % frequency)

            ytm = bond.bondYield(price, bond.dayCounter(), ql.Compounded, frequency)

        return ytm

    def calculate_quantlib_modified_duration(self, date, ytm):
        import QuantLib as ql

        modified_duration = 0

        bond = self.get_quantlib_bond()

        if bond:
            ql.Settings.instance().evaluationDate = ql.Date(str(date), self.date_pattern)

            try:
                frequency = bond.frequency()
            except Exception as e:
                _l.error("Could not take frequency from bond %s" % e)
                frequency = 1
            # first_cashflow = bond.cashflows()[0]
            # day_count_convention = first_cashflow.dayCounter()
            day_count_convention = bond.dayCounter()

            # Macaulay Duration
            # TODO probably do not need right now
            # macaulay_duration = ql.BondFunctions.duration(amort_bond, ytm, day_count, ql.Compounded, frequency, ql.Duration.Macaulay)

            # Modified Duration
            modified_duration = ql.BondFunctions.duration(
                bond,
                ytm,
                day_count_convention,
                ql.Compounded,
                frequency,
                ql.Duration.Modified,
            )

        return modified_duration

    def rebuild_event_schedules(self):
        from poms.transactions.models import EventClass, NotificationClass

        master_user = self.master_user
        instrument_type = self.instrument_type
        instrument_class = instrument_type.instrument_class

        try:
            event_schedule_config = master_user.instrument_event_schedule_config
        except ObjectDoesNotExist:
            event_schedule_config = EventScheduleConfig.create_default(
                master_user=master_user
            )

        notification_class_id = event_schedule_config.notification_class_id
        if notification_class_id is None:
            notification_class_id = NotificationClass.DONT_REACT

        events = list(
            self.event_schedules.prefetch_related("actions").filter(
                is_auto_generated=True
            )
        )
        events_by_accrual = {
            e.accrual_calculation_schedule_id: e
            for e in events
            if e.accrual_calculation_schedule_id is not None
        }
        events_by_factor = {
            e.factor_schedule_id: e for e in events if e.factor_schedule_id is not None
        }

        processed = []
        accruals = self.get_accrual_calculation_schedules_all()
        for i, accrual in enumerate(accruals):
            try:
                accrual_next = accruals[i + 1]
            except IndexError:
                accrual_next = None

            if instrument_class.has_regular_event:
                if not instrument_type.regular_event:
                    raise ValueError(
                        f'Field regular event in instrument type "{instrument_type}" '
                        f"must be set"
                    )

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
                e.final_date = (
                    accrual_next.accrual_start_date
                    if accrual_next
                    else self.maturity_date
                )
                a = EventScheduleAction()
                a.text = event_schedule_config.action_text
                a.transaction_type = instrument_type.regular_event.user_code
                a.is_sent_to_pending = event_schedule_config.action_is_sent_to_pending
                a.is_book_automatic = event_schedule_config.action_is_book_automatic
                a.button_position = 1

                eold = events_by_accrual.get(accrual.id)
                self._event_save(processed, e, a, eold)
        if instrument_class.has_one_off_event:
            if not instrument_type.one_off_event:
                raise ValueError(
                    f'Field one-off event in instrument type "{instrument_type}" '
                    f"must be set"
                )

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
            a.transaction_type = instrument_type.one_off_event.user_code
            a.is_sent_to_pending = event_schedule_config.action_is_sent_to_pending
            a.is_book_automatic = event_schedule_config.action_is_book_automatic
            a.button_position = 1

            eold = None
            for e0 in events:
                if (
                        e0.is_auto_generated
                        and e0.event_class_id == EventClass.ONE_OFF
                        and e0.accrual_calculation_schedule_id is None
                        and e0.factor_schedule_id is None
                ):
                    eold = e0
                    break
            self._event_save(processed, e, a, eold)

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
            elif f.factor_value > fprev.factor_value:
                transaction_type = instrument_type.factor_up
            else:
                transaction_type = instrument_type.factor_down
            if transaction_type is None:
                continue

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

            eold = events_by_factor.get(f.id)
            self._event_save(processed, e, a, eold)

        self.event_schedules.filter(is_auto_generated=True).exclude(
            pk__in=processed
        ).delete()

    def _event_to_dict(self, event, event_actions=None):
        # build dict from attrs for compare its
        if event is None:
            return None
        event_values = serializers.serialize("python", [event])[0]
        if event_actions is None and hasattr(event, "actions"):
            event_actions = event_actions or event.actions.all()
        event_values["fields"]["actions"] = serializers.serialize(
            "python", event_actions
        )
        event_values.pop("pk")
        for action_values in event_values["fields"]["actions"]:
            action_values.pop("pk")
            action_values["fields"].pop("event_schedule")
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
        elif old_event:
            processed.append(old_event.id)

    def get_accrual_calculation_schedules_all(self):
        accruals = list(self.accrual_calculation_schedules.all())

        # _l.info("get_accrual_calculation_schedules_all %s" % accruals)

        if not accruals:
            return accruals

        if getattr(accruals[0], "accrual_end_date", None) is not None:
            return accruals

        # _l.info('get_accrual_calculation_schedules_all')

        accruals = sorted(
            accruals,
            key=lambda x: datetime.date(
                datetime.strptime(x.accrual_start_date, DATE_FORMAT)
            ),
        )

        # _l.info('get_accrual_calculation_schedules_all after sort')

        a = None
        for next_a in accruals:
            if a is not None:
                a.accrual_end_date = next_a.accrual_start_date
            a = next_a
        if a:
            try:
                a.accrual_end_date = self.maturity_date + timedelta(days=1)
            except Exception:
                print(f"Overflow Error {self.maturity_date} ")

                a.accrual_end_date = self.maturity_date

        return accruals

    def find_accrual(self, d):
        if d >= self.maturity_date:
            return None

        accruals = self.get_accrual_calculation_schedules_all()
        accrual = None

        # _l.debug('find_accrual.accruals %s' % accruals)

        for a in accruals:
            if datetime.date(datetime.strptime(a.accrual_start_date, DATE_FORMAT)) <= d:
                accrual = a

        return accrual

    def calculate_prices_accrued_price(self, begin_date=None, end_date=None):
        accruals = self.get_accrual_calculation_schedules_all()

        if not accruals:
            return

        existed_prices = PriceHistory.objects.filter(
            instrument=self, date__range=(begin_date, end_date)
        )

        if begin_date is None and end_date is None:
            # used from admin
            for price in existed_prices:
                if price.date >= self.maturity_date:
                    continue
                accrued_price = self.get_accrued_price(price.date)
                if accrued_price is None:
                    accrued_price = 0.0
                price.accrued_price = accrued_price
                price.save(update_fields=["accrued_price"])

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
                        price.save(update_fields=["accrued_price"])

    def get_accrual_size(self, price_date):
        if not self.maturity_date or (price_date >= self.maturity_date):
            return 0.0

        accrual = self.find_accrual(price_date)
        # _l.debug('get_accrual_size.accrual %s' % accrual)
        return 0.0 if accrual is None else float(accrual.accrual_size)

    def get_future_accrual_payments(self, d0, v0):
        pass

    def get_accrual_factor(self, price_date):
        from poms.common.formula_accruals import coupon_accrual_factor

        if not self.maturity_date or (price_date >= self.maturity_date):
            return 0.0

        accrual = self.find_accrual(price_date)
        if accrual is None:
            return 0.0

        return coupon_accrual_factor(
            accrual_calculation_schedule=accrual,
            dt1=accrual.accrual_start_date,
            dt2=price_date,
            dt3=accrual.first_payment_date,
        )

    def get_accrued_price(self, price_date):
        from poms.common.formula_accruals import coupon_accrual_factor

        if price_date >= self.maturity_date:
            return 0.0

        accrual = self.find_accrual(price_date)
        if accrual is None:
            return 0.0

        accrual_start_date = datetime.date(
            datetime.strptime(accrual.accrual_start_date, DATE_FORMAT)
        )
        first_payment_date = datetime.date(
            datetime.strptime(accrual.first_payment_date, DATE_FORMAT)
        )

        _l.info(f"coupon_accrual_factor price_date {price_date} ")

        factor = coupon_accrual_factor(
            accrual_calculation_schedule=accrual,
            dt1=accrual_start_date,
            dt2=price_date,
            dt3=first_payment_date,
        )

        return float(accrual.accrual_size) * factor

    def get_coupon(self, cpn_date, with_maturity=False, factor=False):
        _l.info(f"get_coupon self.maturity_date {self.maturity_date}")

        if cpn_date == self.maturity_date and with_maturity:
            return self.maturity_price, True

        elif cpn_date == self.maturity_date or cpn_date > self.maturity_date:
            return 0.0, False

        accruals = self.get_accrual_calculation_schedules_all()

        _l.info(f"get_coupon len accruals {len(accruals)} ")

        for accrual in accruals:
            accrual_start_date = datetime.date(
                datetime.strptime(accrual.accrual_start_date, DATE_FORMAT)
            )
            accrual_end_date = accrual.accrual_end_date
            first_payment_date = datetime.date(
                datetime.strptime(accrual.first_payment_date, DATE_FORMAT)
            )

            _l.info(
                f"get_coupon  accrual_start_date {accrual_start_date} accrual_end_date"
                f" {accrual_end_date} first_payment_date {first_payment_date}"
            )

            if accrual_start_date <= cpn_date < accrual_end_date:
                _l.info("get coupon start processing ")
                prev_d = accrual_start_date
                for i in range(3652058):
                    stop = False
                    if i == 0:
                        d = first_payment_date
                    else:
                        try:
                            d = first_payment_date + accrual.periodicity.to_timedelta(
                                n=accrual.periodicity_n,
                                i=i,
                                same_date=accrual_start_date,
                            )
                        except (OverflowError, ValueError) as e:  # year is out of range
                            _l.info(f"get_coupon overflow error {e}")
                            return 0.0, False

                    if d >= accrual_end_date:
                        d = accrual_end_date - timedelta(days=1)
                        stop = True

                    if d == cpn_date:
                        val_or_factor = get_coupon(
                            accrual,
                            prev_d,
                            d,
                            maturity_date=self.maturity_date,
                            factor=factor,
                        )

                        _l.info(f"get_coupon  d == cpn_date {val_or_factor}")

                        return val_or_factor, True

                    if stop or d >= accrual_end_date:
                        break

                    prev_d = d

        _l.info("get_coupon last return")

        return 0.0, False

    def get_future_coupons(self, begin_date=None, with_maturity=False, factor=False):
        res = []
        accruals = self.get_accrual_calculation_schedules_all()
        for accrual in accruals:
            if begin_date >= accrual.accrual_end_date:
                continue

            accrual_start_date_d = datetime.strptime(
                accrual.accrual_start_date, DATE_FORMAT
            ).date()
            first_payment_date_d = datetime.strptime(
                accrual.first_payment_date, DATE_FORMAT
            ).date()
            accrual_end_date_d = accrual.accrual_end_date

            prev_d = accrual_start_date_d
            for i in range(3652058):
                stop = False
                if i == 0:
                    d = first_payment_date_d
                else:
                    try:
                        d = first_payment_date_d + accrual.periodicity.to_timedelta(
                            n=accrual.periodicity_n, i=i, same_date=accrual_start_date_d
                        )
                    except (OverflowError, ValueError):  # year is out of range
                        break

                if d < begin_date:
                    prev_d = d
                    continue

                if d >= accrual_end_date_d:
                    d = accrual_end_date_d - timedelta(days=1)
                    stop = True

                val_or_factor = get_coupon(
                    accrual, prev_d, d, maturity_date=self.maturity_date, factor=factor
                )
                res.append((d, val_or_factor))

                if stop or d >= accrual_end_date_d:
                    break

                prev_d = d

        if with_maturity:
            val_or_factor = 1.0 if factor else self.maturity_price
            res.append((self.maturity_date, val_or_factor))

        return res

    # Need in new ytm calculation
    # 2023-08-21
    def has_factor_schedules(self):
        factors = list(self.factor_schedules.all())

        return bool(len(factors))

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

        return res.factor_value if res else 1.0

    def generate_instrument_system_attributes(self):
        from django.contrib.contenttypes.models import ContentType
        from poms.configuration.utils import get_default_configuration_code

        content_type = ContentType.objects.get(
            app_label="instruments", model="instrument"
        )
        instrument_pricing_policies = InstrumentPricingPolicy.objects.filter(
            instrument=self
        )

        configuration_code = get_default_configuration_code()

        for ipp in instrument_pricing_policies:
            pp = ipp.pricing_policy

            user_code_scheme = f"{configuration_code}:pricing_policy_scheme_{pp.user_code}"
            user_code_parameter = f"{configuration_code}:pricing_policy_parameter_{pp.user_code}"
            user_code_notes = f"{configuration_code}:pricing_policy_notes_{pp.user_code}"

            name_scheme = f"Pricing Policy Scheme: {pp.user_code}"
            name_parameter = f"Pricing Policy Parameter: {pp.user_code}"
            name_notes = f"Pricing Policy Notes: {pp.user_code}"

            try:
                attr_type_scheme = GenericAttributeType.objects.get(
                    master_user=self.master_user,
                    owner=self.owner,
                    content_type=content_type,
                    user_code=user_code_scheme,
                )
            except GenericAttributeType.DoesNotExist:
                attr_type_scheme = GenericAttributeType.objects.create(
                    master_user=self.master_user,
                    owner=self.owner,
                    content_type=content_type,
                    value_type=GenericAttributeType.STRING,
                    user_code=user_code_scheme,
                    name=name_scheme,
                    kind=GenericAttributeType.SYSTEM,
                    configuration_code=configuration_code,
                )

            try:
                attr_type_parameter = GenericAttributeType.objects.get(
                    master_user=self.master_user,
                    owner=self.owner,
                    content_type=content_type,
                    user_code=user_code_parameter,
                )
            except GenericAttributeType.DoesNotExist:
                attr_type_parameter = GenericAttributeType.objects.create(
                    master_user=self.master_user,
                    owner=self.owner,
                    content_type=content_type,
                    value_type=GenericAttributeType.STRING,
                    user_code=user_code_parameter,
                    name=name_parameter,
                    kind=GenericAttributeType.SYSTEM,
                    configuration_code=configuration_code,
                )

            try:
                attr_type_notes = GenericAttributeType.objects.get(
                    master_user=self.master_user,
                    owner=self.owner,
                    content_type=content_type,
                    user_code=user_code_notes,
                )
            except GenericAttributeType.DoesNotExist:
                attr_type_notes = GenericAttributeType.objects.create(
                    master_user=self.master_user,
                    owner=self.owner,
                    content_type=content_type,
                    value_type=GenericAttributeType.STRING,
                    user_code=user_code_notes,
                    name=name_notes,
                    kind=GenericAttributeType.SYSTEM,
                    configuration_code=configuration_code,
                )

            try:
                attr_scheme = GenericAttribute.objects.get(
                    attribute_type=attr_type_scheme,
                    object_id=self.pk,
                    content_type=content_type,
                )

            except GenericAttribute.DoesNotExist:
                attr_scheme = GenericAttribute.objects.create(
                    attribute_type=attr_type_scheme,
                    object_id=self.pk,
                    content_type=content_type,
                )

            if ipp.pricing_scheme:
                attr_scheme.value_string = ipp.pricing_scheme.name
            else:
                attr_scheme.value_string = ""

            attr_scheme.save()

            try:
                attr_parameter = GenericAttribute.objects.get(
                    attribute_type=attr_type_parameter,
                    object_id=self.pk,
                    content_type=content_type,
                )

            except GenericAttribute.DoesNotExist:
                attr_parameter = GenericAttribute.objects.create(
                    attribute_type=attr_type_parameter,
                    object_id=self.pk,
                    content_type=content_type,
                )

            if ipp.attribute_key:
                if "attributes." in ipp.attribute_key:
                    try:
                        code = ipp.attribute_key.split("attributes.")[1]
                        type = GenericAttributeType.objects.get(
                            master_user=self.master_user,
                            owner=self.owner,
                            content_type=content_type,
                            user_code=code,
                        )

                        attr = GenericAttribute.objects.get(
                            object_id=self.pk,
                            attribute_type=type,
                            content_type=content_type,
                        )

                        if type.value_type == 10:
                            attr_parameter.value_string = attr.value_string

                        elif type.value_type == 20:
                            attr_parameter.value_string = str(attr.value_float)

                        elif type.value_type == 30:
                            attr_parameter.value_string = attr.classifier.name

                        elif type.value_type == 40:
                            attr_parameter.value_string = attr.value_date

                    except Exception as e:
                        _l.info(f"Could not get attribute value={e} ")

                else:
                    attr_parameter.value_string = str(
                        getattr(self, ipp.attribute_key, "")
                    )
            elif ipp.default_value:
                attr_parameter.value_string = ipp.default_value
            else:
                attr_parameter.value_string = ""

            attr_parameter.save()

            try:
                attr_notes = GenericAttribute.objects.get(
                    attribute_type=attr_type_notes,
                    object_id=self.pk,
                    content_type=content_type,
                )

            except GenericAttribute.DoesNotExist:
                attr_notes = GenericAttribute.objects.create(
                    attribute_type=attr_type_notes,
                    object_id=self.pk,
                    content_type=content_type,
                )

            attr_notes.value_string = ipp.notes or ""
            _l.info(f"attr_notes={attr_notes.value_string}")

            attr_notes.save()

        _l.info("generate_instrument_system_attributes done")

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        try:
            self.generate_instrument_system_attributes()

        except Exception as error:
            _l.error(f"Instrument save error {error}\n {traceback.format_exc()}")


# DEPRECTATED (25.05.2020) delete soon
class ManualPricingFormula(models.Model):
    instrument = models.ForeignKey(
        Instrument,
        related_name="manual_pricing_formulas",
        verbose_name=gettext_lazy("instrument"),
        on_delete=models.CASCADE,
    )
    pricing_policy = models.ForeignKey(
        PricingPolicy,
        on_delete=models.CASCADE,
        related_name="manual_pricing_formulas",
        verbose_name=gettext_lazy("pricing policy"),
    )
    expr = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name=gettext_lazy("expression"),
    )
    notes = models.TextField(
        blank=True,
        default="",
        verbose_name=gettext_lazy("notes"),
    )

    class Meta:
        verbose_name = gettext_lazy("manual pricing formula")
        verbose_name_plural = gettext_lazy("manual pricing formulas")
        unique_together = [["instrument", "pricing_policy"]]
        ordering = ["pricing_policy"]

    def __str__(self):
        return self.expr


class AccrualCalculationSchedule(models.Model):
    instrument = models.ForeignKey(
        Instrument,
        related_name="accrual_calculation_schedules",
        verbose_name=gettext_lazy("instrument"),
        on_delete=models.CASCADE,
    )
    accrual_start_date = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_index=True,
        verbose_name=gettext_lazy("accrual start date"),
    )
    accrual_start_date_value_type = models.PositiveSmallIntegerField(
        choices=SYSTEM_VALUE_TYPES,
        default=SystemValueType.DATE,
        verbose_name=gettext_lazy("accrual start date value type"),
    )
    accrual_end_date = None  # excluded date
    first_payment_date = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("first payment date"),
    )
    first_payment_date_value_type = models.PositiveSmallIntegerField(
        choices=SYSTEM_VALUE_TYPES,
        default=SystemValueType.DATE,
        verbose_name=gettext_lazy("first payment date value type"),
    )
    accrual_size = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("accrual size"),
    )
    accrual_size_value_type = models.PositiveSmallIntegerField(
        choices=SYSTEM_VALUE_TYPES,
        default=SystemValueType.NUMBER,
        verbose_name=gettext_lazy("accrual size value type"),
    )
    accrual_calculation_model = models.ForeignKey(
        AccrualCalculationModel,
        on_delete=models.PROTECT,
        verbose_name=gettext_lazy("accrual calculation model"),
    )
    periodicity = models.ForeignKey(
        Periodicity,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("periodicity"),
    )
    periodicity_n = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("periodicity n"),
    )
    periodicity_n_value_type = models.PositiveSmallIntegerField(
        choices=SYSTEM_VALUE_TYPES,
        default=SystemValueType.NUMBER,
        verbose_name=gettext_lazy("periodicity n value type"),
    )
    notes = models.TextField(
        blank=True,
        default="",
        verbose_name=gettext_lazy("notes"),
    )

    eom = models.BooleanField(
        default=False,
        verbose_name=gettext_lazy("EOM"),
        help_text="If the start date of a bond is at the end of a month (e.g., January 30 or 31), the date is adjusted to the end of February for a semi-annual or full annual coupon. "
    )

    def save(self, *args, **kwargs):
        from dateutil.parser import parse

        if self.accrual_start_date:
            try:
                self.accrual_start_date = parse(self.accrual_start_date).strftime(
                    DATE_FORMAT
                )
            except Exception:
                self.accrual_start_date = None

        if self.first_payment_date:
            try:
                self.first_payment_date = parse(self.first_payment_date).strftime(
                    DATE_FORMAT
                )
            except Exception:
                self.first_payment_date = None

        super().save(*args, **kwargs)

    class Meta:
        verbose_name = gettext_lazy("accrual calculation schedule")
        verbose_name_plural = gettext_lazy("accrual calculation schedules")
        ordering = ["accrual_start_date"]
        index_together = [["instrument", "accrual_start_date"]]

    def __str__(self):
        return str(self.accrual_start_date)


class PriceHistory(DataTimeStampedModel):
    instrument = models.ForeignKey(
        Instrument,
        related_name="prices",
        verbose_name=gettext_lazy("instrument"),
        on_delete=models.CASCADE,
    )
    pricing_policy = models.ForeignKey(
        PricingPolicy,
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
    principal_price = models.FloatField(
        default=0.0,
        verbose_name=gettext_lazy("principal price"),
    )
    accrued_price = models.FloatField(
        default=0.0,
        verbose_name=gettext_lazy("accrued price"),
    )
    long_delta = models.FloatField(
        default=0.0,
        verbose_name=gettext_lazy("long delta"),
    )
    short_delta = models.FloatField(
        default=0.0,
        verbose_name=gettext_lazy("short delta"),
    )
    ytm = models.FloatField(
        default=0.0,
        verbose_name=gettext_lazy("ytm"),
    )
    nav = models.FloatField(
        default=0.0,
        verbose_name=gettext_lazy("nav"),
    )
    factor = models.FloatField(
        default=1.0,
        verbose_name=gettext_lazy("factor"),
    )
    cash_flow = models.FloatField(
        default=0.0,
        verbose_name=gettext_lazy("cash flow"),
    )
    modified_duration = models.FloatField(
        default=0.0,
        verbose_name=gettext_lazy("modified duration"),
    )
    procedure_modified_datetime = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=gettext_lazy("procedure_modified_datetime"),
    )
    is_temporary_price = models.BooleanField(
        default=False,
        verbose_name=gettext_lazy("is temporary price"),
    )

    class Meta:
        verbose_name = gettext_lazy("price history")
        verbose_name_plural = gettext_lazy("price histories")
        unique_together = (
            "instrument",
            "pricing_policy",
            "date",
        )
        index_together = [["instrument", "pricing_policy", "date"]]
        ordering = ["date"]

    def __str__(self):
        return (
            f"{self.instrument.user_code} - {self.principal_price};"
            f"{self.accrued_price} @{self.date}"
        )

    def get_instr_ytm_data_d0_v0(self, dt):
        v0 = -(
                self.principal_price
                * self.instrument.price_multiplier
                * self.instrument.get_factor(dt)
                + self.accrued_price
                * self.instrument.accrued_multiplier
                * self.instrument.get_factor(dt)
                * (self.instr_accrued_ccy_cur_fx / self.instr_pricing_ccy_cur_fx)
        )

        return dt, v0

    def get_instr_ytm_data(self, dt):
        if hasattr(self, "_instr_ytm_data"):
            return self._instr_ytm_data

        instr = self.instrument

        if instr.maturity_date is None or instr.maturity_date == date.max:
            return []
        if (
                instr.maturity_price is None
                or isnan(instr.maturity_price)
                or isclose(instr.maturity_price, 0.0)
        ):
            return []

        try:
            d0, v0 = self.get_instr_ytm_data_d0_v0(dt)
        except ArithmeticError:
            return None

        data = [(d0, v0)]

        for cpn_date, cpn_val in instr.get_future_coupons(
                begin_date=d0, with_maturity=False
        ):
            try:
                factor = instr.get_factor(cpn_date)
                k = (
                        instr.accrued_multiplier
                        * factor
                        * (self.instr_accrued_ccy_cur_fx / self.instr_pricing_ccy_cur_fx)
                )
            except ArithmeticError:
                k = 0
            data.append((cpn_date, cpn_val * k))

        prev_factor = None
        for factor in instr.factor_schedules.all():
            if (
                    factor.effective_date < d0
                    or factor.effective_date > instr.maturity_date
            ):
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

            return (
                    (accrual_size * self.instrument.accrued_multiplier)
                    * (self.instr_accrued_ccy_cur_fx / self.instr_pricing_ccy_cur_fx)
                    / (self.principal_price * self.instrument.price_multiplier)
            )
        except Exception as e:
            _l.error(f"get_instr_ytm_x0 {repr(e)}")
            return 0

    def calculate_ytm(self, date):
        _l.debug(f"Calculating ytm for {self.instrument.name} for {date}")

        ytm = self.instrument.calculate_quantlib_ytm(
            date=date, price=self.principal_price
        )

        # if (
        #     self.instrument.maturity_date is None
        #     or self.instrument.maturity_date == date.max
        #     or str(self.instrument.maturity_date) == "2999-01-01"
        #     or str(self.instrument.maturity_date) == "2099-01-01"
        # ):
        #     try:
        #         accrual_size = self.instrument.get_accrual_size(dt)
        #         ytm = (
        #             (accrual_size * self.instrument.accrued_multiplier)
        #             * (self.instr_accrued_ccy_cur_fx / self.instr_pricing_ccy_cur_fx)
        #             / (self.principal_price * self.instrument.price_multiplier)
        #         )
        #
        #     except Exception as e:
        #         _l.error(f"calculate_ytm error {repr(e)}")
        #         ytm = 0
        #     return ytm
        #
        # x0 = self.get_instr_ytm_x0(dt)
        # _l.debug("get_instr_ytm: x0=%s", x0)
        #
        # data = self.get_instr_ytm_data(dt)
        # _l.debug("get_instr_ytm: data=%s", data)
        #
        # ytm = f_xirr(data, x0=x0) if data else 0.0
        return ytm

    def calculate_duration(self, date, ytm):
        duration = self.instrument.calculate_quantlib_modified_duration(
            date=date, ytm=ytm
        )

        # if (
        #         self.instrument.maturity_date is None
        #         or self.instrument.maturity_date == date.max
        # ):
        #     try:
        #         duration = 1 / self.ytm
        #     except ArithmeticError:
        #         duration = 0
        #
        #     return duration
        # data = self.get_instr_ytm_data(dt)
        # return f_duration(data, ytm=self.ytm) if data else 0

        return duration

    def save(self, *args, **kwargs):
        # TODO make readable exception if currency history is missing

        # cache.clear() # what do have in cache?

        if not self.procedure_modified_datetime:
            self.procedure_modified_datetime = date_now()

        if not self.created:
            self.created = date_now()

        ecosystem_default = EcosystemDefault.objects.get(
            master_user=self.instrument.master_user
        )

        try:
            if (
                    self.instrument.accrued_currency_id
                    == self.instrument.pricing_currency_id
            ):
                self.instr_accrued_ccy_cur_fx = 1
                self.instr_pricing_ccy_cur_fx = 1

            else:
                if ecosystem_default.currency_id == self.instrument.accrued_currency_id:
                    self.instr_accrued_ccy_cur_fx = 1
                else:
                    self.instr_accrued_ccy_cur_fx = CurrencyHistory.objects.get(
                        date=self.date, currency=self.instrument.accrued_currency
                    ).fx_rate

                if ecosystem_default.currency_id == self.instrument.pricing_currency_id:
                    self.instr_pricing_ccy_cur_fx = 1
                else:
                    self.instr_pricing_ccy_cur_fx = CurrencyHistory.objects.get(
                        date=self.date, currency=self.instrument.pricing_currency
                    ).fx_rate

            self.ytm = self.calculate_ytm(self.date)
            self.modified_duration = self.calculate_duration(self.date, self.ytm)

        except Exception as e:
            _l.info(f"PriceHistory save ytm error {repr(e)} {traceback.format_exc()}")

        if not self.factor:
            try:
                self.factor = self.instrument.get_factor(self.date)
            except Exception as e:
                _l.debug(
                    f"PriceHistory factor save ytm error {repr(e)}"
                    f" {traceback.format_exc()}"
                )

        if not self.accrued_price:
            try:
                self.accrued_price = self.instrument.get_accrued_price(self.date)
            except Exception as e:
                _l.error('PriceHistory.error get_accrued_price e %s' % e)
                _l.error('PriceHistory.error get_accrued_price traceback %s' % traceback.format_exc())
                _l.error('PriceHistory cound not get_accrued_price')
                self.accrued_price = 0

        super().save(*args, **kwargs)


class InstrumentFactorSchedule(models.Model):
    instrument = models.ForeignKey(
        Instrument,
        related_name="factor_schedules",
        verbose_name=gettext_lazy("instrument"),
        on_delete=models.CASCADE,
    )
    effective_date = models.DateField(
        default=date_now,
        verbose_name=gettext_lazy("effective date"),
    )
    factor_value = models.FloatField(
        default=0.0,
        verbose_name=gettext_lazy("factor value"),
    )

    class Meta:
        verbose_name = gettext_lazy("instrument factor schedule")
        verbose_name_plural = gettext_lazy("instrument factor schedules")
        ordering = ["effective_date"]

    def __str__(self):
        return str(self.effective_date)


class EventSchedule(models.Model):
    instrument = models.ForeignKey(
        Instrument,
        related_name="event_schedules",
        verbose_name=gettext_lazy("instrument"),
        on_delete=models.CASCADE,
    )
    name = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        verbose_name=gettext_lazy("name"),
    )
    description = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("description"),
    )
    event_class = models.ForeignKey(
        "transactions.EventClass",
        on_delete=models.PROTECT,
        verbose_name=gettext_lazy("event class"),
    )
    notification_class = models.ForeignKey(
        "transactions.NotificationClass",
        on_delete=models.PROTECT,
        verbose_name=gettext_lazy("notification class"),
    )
    effective_date = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("effective date"),
    )
    effective_date_value_type = models.PositiveSmallIntegerField(
        choices=SYSTEM_VALUE_TYPES,
        default=SystemValueType.DATE,
        verbose_name=gettext_lazy("effective date value type"),
    )
    notify_in_n_days = models.PositiveIntegerField(
        default=0,
        verbose_name=gettext_lazy("notify in N days"),
    )
    periodicity = models.ForeignKey(
        Periodicity,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        verbose_name=gettext_lazy("periodicity"),
    )
    periodicity_n = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("periodicity n"),
    )
    periodicity_n_value_type = models.PositiveSmallIntegerField(
        choices=SYSTEM_VALUE_TYPES,
        default=SystemValueType.NUMBER,
        verbose_name=gettext_lazy("periodicity n value type"),
    )
    final_date = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("final date"),
    )  # excluded date
    final_date_value_type = models.PositiveSmallIntegerField(
        choices=SYSTEM_VALUE_TYPES,
        default=SystemValueType.DATE,
        verbose_name=gettext_lazy("final_date value type"),
    )
    is_auto_generated = models.BooleanField(
        default=False,
        verbose_name=gettext_lazy("is auto generated"),
    )
    accrual_calculation_schedule = models.ForeignKey(
        AccrualCalculationSchedule,
        null=True,
        blank=True,
        editable=False,
        related_name="event_schedules",
        verbose_name=gettext_lazy("accrual calculation schedule"),
        help_text=gettext_lazy("Used for store link when is_auto_generated is True"),
        on_delete=models.SET_NULL,
    )
    factor_schedule = models.ForeignKey(
        InstrumentFactorSchedule,
        null=True,
        blank=True,
        editable=False,
        related_name="event_schedules",
        verbose_name=gettext_lazy("factor schedule"),
        help_text=gettext_lazy("Used for store link when is_auto_generated is True"),
        on_delete=models.SET_NULL,
    )
    json_data = models.TextField(
        null=True,
        blank=True,
        verbose_name=gettext_lazy("json data"),
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

    class Meta:
        verbose_name = gettext_lazy("event schedule")
        verbose_name_plural = gettext_lazy("event schedules")
        ordering = ["effective_date"]

    def __str__(self):
        return f"#{self.id}/#{self.instrument_id}"

    @cached_property
    def all_dates(self):
        from poms.transactions.models import EventClass

        notify_in_n_days = timedelta(days=self.notify_in_n_days)
        edate = datetime.date(datetime.strptime(self.effective_date, DATE_FORMAT))
        fdate = datetime.date(datetime.strptime(self.final_date, DATE_FORMAT))

        dates = []

        def add_date(edate):
            ndate = edate - notify_in_n_days
            dates.append((edate, ndate))

        if self.event_class_id == EventClass.ONE_OFF:
            add_date(edate)

        elif self.event_class_id == EventClass.REGULAR:
            for i in range(3652058):
                stop = False
                try:
                    effective_date = edate + self.periodicity.to_timedelta(
                        n=self.periodicity_n,
                        i=i,
                        same_date=edate,
                    )
                except (OverflowError, ValueError):  # year is out of range
                    break

                if (
                        self.accrual_calculation_schedule_id is not None
                        and effective_date >= fdate
                ):
                    effective_date = fdate - timedelta(days=1)
                    stop = True

                add_date(effective_date)

                if stop or effective_date >= fdate:
                    break

        return dates

    def check_date(self, now):
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
    event_schedule = models.ForeignKey(
        EventSchedule,
        related_name="actions",
        verbose_name=gettext_lazy("event schedule"),
        on_delete=models.CASCADE,
    )
    transaction_type = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("transaction type"),
    )
    text = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("text"),
    )
    is_sent_to_pending = models.BooleanField(
        default=True,
        verbose_name=gettext_lazy("is sent to pending"),
    )
    is_book_automatic = models.BooleanField(
        default=True,
        verbose_name=gettext_lazy("is book automatic"),
    )
    button_position = models.IntegerField(
        default=0,
        verbose_name=gettext_lazy("button position"),
    )
    json_data = models.TextField(
        null=True,
        blank=True,
        verbose_name=gettext_lazy("json data"),
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

    class Meta:
        verbose_name = gettext_lazy("event schedule action")
        verbose_name_plural = gettext_lazy("event schedule actions")
        ordering = ["is_book_automatic", "button_position"]

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
        (NEW, gettext_lazy("New")),
        (INFORMED, gettext_lazy("Informed")),
        (BOOKED_SYSTEM_DEFAULT, gettext_lazy("Booked (system, default)")),
        (BOOKED_USER_ACTIONS, gettext_lazy("Booked (user, actions)")),
        (BOOKED_USER_DEFAULT, gettext_lazy("Booked (user, default)")),
        (
            BOOKED_PENDING_SYSTEM_DEFAULT,
            gettext_lazy("Booked, pending (system, default)"),
        ),
        (BOOKED_PENDING_USER_ACTIONS, gettext_lazy("Booked, pending (user, actions)")),
        (BOOKED_PENDING_USER_DEFAULT, gettext_lazy("Booked, pending (user, default)")),
        (ERROR, gettext_lazy("Error")),
    )

    master_user = models.ForeignKey(
        MasterUser,
        related_name="generated_events",
        verbose_name=gettext_lazy("master user"),
        on_delete=models.CASCADE,
    )
    effective_date = models.DateField(
        default=date_now,
        db_index=True,
        verbose_name=gettext_lazy("effective date"),
    )
    effective_date_notified = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name=gettext_lazy("effective date notified"),
    )
    notification_date = models.DateField(
        default=date_now,
        db_index=True,
        verbose_name=gettext_lazy("notification date"),
    )
    notification_date_notified = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name=gettext_lazy("notification date notified"),
    )
    status = models.PositiveSmallIntegerField(
        default=NEW,
        choices=STATUS_CHOICES,
        db_index=True,
        verbose_name=gettext_lazy("status"),
    )
    status_date = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        verbose_name=gettext_lazy("status date"),
    )
    event_schedule = models.ForeignKey(
        EventSchedule,
        on_delete=models.CASCADE,
        related_name="generated_events",
        verbose_name=gettext_lazy("event schedule"),
    )
    instrument = models.ForeignKey(
        "instruments.Instrument",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="generated_events",
        verbose_name=gettext_lazy("instrument"),
    )
    portfolio = models.ForeignKey(
        "portfolios.Portfolio",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="generated_events",
        verbose_name=gettext_lazy("portfolio"),
    )
    account = models.ForeignKey(
        "accounts.Account",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="generated_events",
        verbose_name=gettext_lazy("account"),
    )
    strategy1 = models.ForeignKey(
        "strategies.Strategy1",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="generated_events",
        verbose_name=gettext_lazy("strategy1"),
    )
    strategy2 = models.ForeignKey(
        "strategies.Strategy2",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="generated_events",
        verbose_name=gettext_lazy("strategy2"),
    )
    strategy3 = models.ForeignKey(
        "strategies.Strategy3",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="generated_events",
        verbose_name=gettext_lazy("strategy3"),
    )
    position = models.FloatField(
        default=0.0,
        verbose_name=gettext_lazy("position"),
    )
    action = models.ForeignKey(
        EventScheduleAction,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="generated_events",
        verbose_name=gettext_lazy("action"),
    )
    transaction_type = models.ForeignKey(
        "transactions.TransactionType",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="generated_events",
        verbose_name=gettext_lazy("transaction type"),
    )
    complex_transaction = models.ForeignKey(
        "transactions.ComplexTransaction",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="generated_events",
        verbose_name=gettext_lazy("complex transaction"),
    )
    member = models.ForeignKey(
        "users.Member",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name=gettext_lazy("member"),
    )
    json_data = models.TextField(
        null=True,
        blank=True,
        verbose_name=gettext_lazy("json data"),
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

    class Meta:
        verbose_name = gettext_lazy("generated event")
        verbose_name_plural = gettext_lazy("generated events")
        ordering = ["effective_date"]

    def __str__(self):
        return f"Event #{self.id}"

    def processed(
            self, member, action, complex_transaction, status=BOOKED_SYSTEM_DEFAULT
    ):
        from poms.transactions.models import TransactionType

        self.member = member
        self.action = action
        self.status = status
        self.status_date = timezone.now()
        self.transaction_type = TransactionType.objects.get(
            user_code=action.transaction_type, master_user=member.master_user
        )
        self.complex_transaction = complex_transaction

    def is_notify_on_effective_date(self, now=None):
        if self.effective_date_notified:
            return False

        now = now or date_now()
        notification_class = self.event_schedule.notification_class

        print(f"self event {self} ")
        print(f"self.event_schedule {self.event_schedule} ")
        print(f"self.now {now} ")
        print(f"self.effective_date {self.effective_date} ")
        print(
            f"self.notification_class.is_notify_on_effective_date {notification_class.is_notify_on_effective_date} "
        )

        return (
                self.effective_date == now
                and notification_class.is_notify_on_effective_date
        )

    def is_notify_on_notification_date(self, now=None):
        if self.effective_date_notified:
            return False

        now = now or date_now()

        notification_class = self.event_schedule.notification_class

        print(f"self event {self} ")
        print(f"self.event_schedule {self.event_schedule} ")
        print(f"self.now {now} ")
        print(f"self.notification_date {self.notification_date} ")
        print(
            f"self.notification_class.is_notify_on_notification_date {notification_class.is_notify_on_notification_date} "
        )

        return (
                self.notification_date == now
                and notification_class.is_notify_on_notification_date
        )

    def is_notify_on_date(self, now=None):
        return bool(
            self.is_notify_on_effective_date(now)
            or self.is_notify_on_notification_date(now)
        )

    def is_apply_default_on_effective_date(self, now=None):
        if self.status == GeneratedEvent.NEW:
            now = now or date_now()
            notification_class = self.event_schedule.notification_class
            return (
                    self.effective_date == now
                    and notification_class.is_apply_default_on_effective_date
            )

        return False

    def is_apply_default_on_notification_date(self, now=None):
        if self.status == GeneratedEvent.NEW:
            now = now or date_now()
            notification_class = self.event_schedule.notification_class
            return (
                    self.notification_date == now
                    and notification_class.is_apply_default_on_notification_date
            )

        return False

    def is_apply_default_on_date(self, now=None):
        return bool(
            self.is_apply_default_on_effective_date(now)
            or self.is_apply_default_on_notification_date(now)
        )

    def is_need_reaction_on_effective_date(self, now=None):
        if self.status == GeneratedEvent.NEW:
            now = now or date_now()
            notification_class = self.event_schedule.notification_class
            return (
                    self.effective_date == now
                    and notification_class.is_need_reaction_on_effective_date
            )

        return False

    def is_need_reaction_on_notification_date(self, now=None):
        if self.status == GeneratedEvent.NEW:
            now = now or date_now()
            notification_class = self.event_schedule.notification_class
            return (
                    self.notification_date == now
                    and notification_class.is_need_reaction_on_notification_date
            )

        return False

    def is_need_reaction_on_date(self, now=None):
        return bool(
            self.is_need_reaction_on_effective_date(now)
            or self.is_need_reaction_on_notification_date(now)
        )

    def get_default_action(self, actions=None):
        if actions is None:
            actions = self.event_schedule.actions.all()
        for action in actions:
            if action.is_book_automatic:
                return action

        return None

    def generate_text(self, exr, names=None, context=None):
        names = names or {}
        names.update(
            {
                "effective_date": self.effective_date,
                "notification_date": self.notification_date,
                "instrument": self.instrument,
                "portfolio": self.portfolio,
                "account": self.account,
                "strategy1": self.strategy1,
                "strategy2": self.strategy2,
                "strategy3": self.strategy3,
                "position": self.position,
            }
        )
        try:
            return formula.safe_eval(exr, names=names, context=context)
        except formula.InvalidExpression:
            return "<InvalidExpression>"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        try:
            if self.status == GeneratedEvent.NEW:
                from poms.system_messages.handlers import send_system_message

                send_system_message(
                    master_user=self.master_user,
                    title="Event",
                    description=self.event_schedule.description,
                    type="info",
                    section="events",
                    linked_event=self,
                )
        except Exception as e:
            _l.error(f"Could not send system message on generating event {repr(e)}")


class EventScheduleConfig(models.Model):
    master_user = models.OneToOneField(
        "users.MasterUser",
        related_name="instrument_event_schedule_config",
        verbose_name=gettext_lazy("master user"),
        on_delete=models.CASCADE,
    )
    name = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("name"),
    )
    description = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        blank=True,
        default="",
        verbose_name=gettext_lazy("description"),
    )
    notification_class = models.ForeignKey(
        "transactions.NotificationClass",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        verbose_name=gettext_lazy("notification class"),
    )
    notify_in_n_days = models.PositiveSmallIntegerField(
        default=0,
        verbose_name=gettext_lazy("notify in N days"),
    )
    action_text = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name=gettext_lazy("action text"),
    )
    action_is_sent_to_pending = models.BooleanField(
        default=True,
        verbose_name=gettext_lazy("action is sent to pending"),
    )
    action_is_book_automatic = models.BooleanField(
        default=True,
        verbose_name=gettext_lazy("action is book automatic"),
    )

    class Meta:
        verbose_name = gettext_lazy("event schedule config")
        verbose_name_plural = gettext_lazy("event schedule configs")

    def __str__(self):
        return gettext_lazy("event schedule config")

    @staticmethod
    def create_default(master_user):
        from poms.transactions.models import NotificationClass

        return EventScheduleConfig.objects.create(
            master_user=master_user,
            name='""',
            description='""',
            notification_class_id=NotificationClass.DONT_REACT,
            notify_in_n_days=0,
            action_text='""',
            action_is_sent_to_pending=False,
            action_is_book_automatic=True,
        )
