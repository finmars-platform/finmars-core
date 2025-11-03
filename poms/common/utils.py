import calendar
import contextlib
import datetime
import logging
from datetime import timedelta

import pandas as pd

# from django.conf import settings
from django.contrib.admin.utils import NestedObjects
from django.contrib.contenttypes.models import ContentType
from django.db import connection, router
from django.utils.timezone import now
from django.views.generic.dates import timezone_today

from poms_app import settings

_l = logging.getLogger("poms.common")

VALID_FREQUENCY = {
    "D",  # Daily
    "W",  # Weekly
    "M",  # Monthly
    "Q",  # Quarterly
    "HY",  # Half-Yearly (1st or 2nd half of the calendar year)
    "Y",  # Yearly
    "C",  # Custom period - no changes
}
calc_shift_date_map = {
    "D": lambda day: pd.Timestamp(day),
    "W": lambda day: pd.Timestamp(day) - pd.DateOffset(days=day.weekday()),
    "M": lambda day: pd.Timestamp(day).replace(day=1),
    "Q": lambda day: pd.Timestamp(f"{day.year}-{((day.month - 1) // 3) * 3 + 1:02d}-01"),
    "HY": lambda day: pd.Timestamp(f"{day.year}-{1 if day.month <= 6 else 7:02d}-01"),
    "Y": lambda day: pd.Timestamp(f"{day.year}-01-01"),
    "ED": lambda day: pd.Timestamp(day),
    "EW": lambda day: pd.Timestamp(day) - pd.DateOffset(days=day.weekday()) + pd.DateOffset(days=6),
    "EM": lambda day: (pd.Timestamp(day).replace(day=1) + pd.offsets.MonthEnd(0)),
    "EQ": lambda day: pd.Timestamp(f"{day.year}-{((day.month - 1) // 3) * 3 + 3:02d}-01") + pd.offsets.MonthEnd(0),
    "EHY": lambda day: pd.Timestamp(f"{day.year}-{6 if day.month <= 6 else 12:02d}-01") + pd.offsets.MonthEnd(0),
    "EY": lambda day: pd.Timestamp(f"{day.year}-12-31"),
}
frequency_map = {
    "D": lambda shift=1: pd.offsets.Day(shift),
    "W": lambda shift=1: pd.offsets.Week(shift),
    "M": lambda shift=1: pd.offsets.MonthBegin(shift),
    "Q": lambda shift=1: pd.offsets.QuarterBegin(n=shift, startingMonth=1),
    "HY": lambda shift=1: pd.offsets.MonthBegin(shift * 6),
    "Y": lambda shift=1: pd.offsets.YearBegin(shift),
    "ED": lambda shift=1: pd.offsets.Day(shift),
    "EW": lambda shift=1: pd.offsets.Week(shift),
    "EM": lambda shift=1: pd.offsets.MonthEnd(shift),
    "EQ": lambda shift=1: pd.offsets.QuarterEnd(n=shift, startingMonth=3),
    "EHY": lambda shift=1: pd.offsets.MonthEnd(shift * 6),
    "EY": lambda shift=1: pd.offsets.YearEnd(shift),
}


def db_class_check_data(model, verbosity, using):
    from django.db import IntegrityError, ProgrammingError

    try:
        exists = set(model.objects.using(using).values_list("pk", flat=True))
    except ProgrammingError:
        return
    if verbosity >= 2:
        print(f"existed transaction classes -> {exists}")
    for id, code, name in model.CLASSES:
        if id not in exists:
            if verbosity >= 2:
                print(f"create {model._meta.verbose_name} class -> {id}:{name}")
            with contextlib.suppress(IntegrityError, ProgrammingError):
                model.objects.using(using).create(pk=id, user_code=code, short_name=name, name=name, description=name)
        else:
            obj = model.objects.using(using).get(pk=id)
            obj.user_code = code
            obj.name = name
            obj.short_name = name
            obj.description = name
            obj.save()


def date_now():
    return timezone_today()


def date_yesterday():
    return timezone_today() - timedelta(days=1)


def datetime_now():
    return now()


class sfloat(float):
    def __truediv__(self, other):
        # print('__truediv__: self=%s, other=%s' % (self, other))
        try:
            return super().__truediv__(other)
        except (ZeroDivisionError, OverflowError):
            return 0.0

    def __rtruediv__(self, other):
        # print('__rtruediv__: self=%s, other=%s' % (self, other))
        try:
            return super().__rtruediv__(other)
        except (ZeroDivisionError, OverflowError):
            return 0.0

    def __floordiv__(self, other):
        # print('__floordiv__: self=%s, other=%s' % (self, other))
        try:
            return super().__floordiv__(other)
        except (ZeroDivisionError, OverflowError):
            return 0.0

    def __rfloordiv__(self, other):
        # print('__floordiv__: self=%s, other=%s' % (self, other))
        try:
            return super().__rfloordiv__(other)
        except (ZeroDivisionError, OverflowError):
            return 0.0

    def __pow__(self, power, **kwargs):
        # print('__pow__: self=%s, other=%s' % (self, other))
        try:
            return super().__pow__(power, **kwargs)
        except (ZeroDivisionError, OverflowError):
            return 0.0

    def __rpow__(self, power, **kwargs):
        # print('__rpow__: self=%s, other=%s' % (self, other))
        try:
            return super().__rpow__(power, **kwargs)
        except (ZeroDivisionError, OverflowError):
            return 0.0


def add_view_and_manage_permissions():
    from django.contrib.auth.models import Permission
    from django.contrib.contenttypes.models import ContentType

    existed = {(p.content_type_id, p.codename) for p in Permission.objects.all()}
    for content_type in ContentType.objects.all():
        codename = f"view_{content_type.model}"
        if (content_type.id, codename) not in existed:
            Permission.objects.update_or_create(
                content_type=content_type,
                codename=codename,
                defaults={"name": f"Can view {content_type.name}"},
            )

        codename = f"manage_{content_type.model}"
        if (content_type.id, codename) not in existed:
            Permission.objects.update_or_create(
                content_type=content_type,
                codename=codename,
                defaults={"name": f"Can manage {content_type.name}"},
            )


def format_float(val):
    # 0.000050000892 -> 0.0000500009
    # 0.005623 -> 0.005623
    # 0.005623000551 -> 0.0056230006

    try:
        float(val)
    except ValueError:
        return val

    return round(val, 10)


def format_float_to_2(val):
    # 0.000050000892 -> 0.0000500009
    # 0.005623 -> 0.005623
    # 0.005623000551 -> 0.0056230006

    try:
        float(val)
    except ValueError:
        return val

    return float(format(round(val, 2), ".2f").rstrip("0").rstrip("."))


def get_content_type_by_name(name):
    pieces = name.split(".")
    app_label_title = pieces[0]
    model_title = pieces[1]

    return ContentType.objects.get(app_label=app_label_title, model=model_title)


def get_first_transaction(portfolio_instance) -> object:
    """
    Get first transaction of portfolio
    :param portfolio_instance:
    :return: Transaction
    """
    from poms.transactions.models import Transaction

    return Transaction.objects.filter(portfolio=portfolio_instance).order_by("accounting_date")[0]


def str_to_date(d):
    """
    Convert string to date
    :param d:
    :return:
    """
    if not isinstance(d, datetime.date):
        d = datetime.datetime.strptime(d, settings.API_DATE_FORMAT).date()

    return d


def get_serializer(content_type_key):
    """
    Returns serializer for given content type key.
    :param content_type_key:
    :return: serializer class
    """

    from poms.accounts.serializers import AccountSerializer, AccountTypeSerializer
    from poms.configuration.serializers import NewMemberSetupConfigurationSerializer
    from poms.counterparties.serializers import (
        CounterpartySerializer,
        ResponsibleSerializer,
    )
    from poms.csv_import.serializers import CsvImportSchemeSerializer
    from poms.currencies.serializers import (
        CurrencyHistorySerializer,
        CurrencySerializer,
    )
    from poms.iam.serializers import (
        AccessPolicySerializer,
        GroupSerializer,
        ResourceGroupSerializer,
        RoleSerializer,
    )
    from poms.instruments.serializers import (
        AccrualCalculationScheduleStandaloneSerializer,
        CurrencyPricingPolicySerializer,
        InstrumentFactorScheduleStandaloneSerializer,
        InstrumentPricingPolicySerializer,
        InstrumentSerializer,
        InstrumentTypePricingPolicySerializer,
        InstrumentTypeSerializer,
        PriceHistorySerializer,
        PricingPolicySerializer,
    )
    from poms.integrations.serializers import (
        ComplexTransactionImportSchemeSerializer,
        InstrumentDownloadSchemeSerializer,
        MappingTableSerializer,
    )
    from poms.obj_attrs.serializers import GenericAttributeTypeSerializer
    from poms.portfolios.serializers import (
        PortfolioRegisterRecordSerializer,
        PortfolioRegisterSerializer,
        PortfolioSerializer,
        PortfolioTypeSerializer,
    )
    from poms.procedures.serializers import (
        ExpressionProcedureSerializer,
        PricingProcedureSerializer,
        RequestDataFileProcedureSerializer,
    )
    from poms.reference_tables.serializers import ReferenceTableSerializer
    from poms.reports.serializers import (
        BalanceReportCustomFieldSerializer,
        PLReportCustomFieldSerializer,
        TransactionReportCustomFieldSerializer,
    )
    from poms.schedules.serializers import ScheduleSerializer
    from poms.strategies.serializers import Strategy1Serializer, Strategy2Serializer
    from poms.system.serializers import WhitelabelSerializer
    from poms.transactions.serializers import (
        TransactionTypeGroupSerializer,
        TransactionTypeSerializer,
    )
    from poms.ui.serializers import (
        ComplexTransactionUserFieldSerializer,
        ContextMenuLayoutSerializer,
        DashboardLayoutSerializer,
        EditLayoutSerializer,
        InstrumentUserFieldSerializer,
        ListLayoutSerializer,
        MemberLayoutSerializer,
        MobileLayoutSerializer,
        TransactionUserFieldSerializer,
    )

    serializer_map = {
        "transactions.transactiontype": TransactionTypeSerializer,
        "transactions.transactiontypegroup": TransactionTypeGroupSerializer,
        "instruments.instrument": InstrumentSerializer,
        "instruments.instrumentfactorschedule": InstrumentFactorScheduleStandaloneSerializer,
        "instruments.accrualcalculationschedule": AccrualCalculationScheduleStandaloneSerializer,
        "instruments.instrumenttype": InstrumentTypeSerializer,
        "instruments.pricingpolicy": PricingPolicySerializer,
        "instruments.instrumenttypepricingpolicy": InstrumentTypePricingPolicySerializer,
        "instruments.instrumentpricingpolicy": InstrumentPricingPolicySerializer,
        "instruments.currencypricingpolicy": CurrencyPricingPolicySerializer,
        "currencies.currency": CurrencySerializer,
        "accounts.account": AccountSerializer,
        "accounts.accounttype": AccountTypeSerializer,
        "portfolios.portfolio": PortfolioSerializer,
        "portfolios.portfoliotype": PortfolioTypeSerializer,
        "portfolios.portfolioregister": PortfolioRegisterSerializer,
        "portfolios.portfolioregisterrecord": PortfolioRegisterRecordSerializer,
        "instruments.pricehistory": PriceHistorySerializer,
        "currencies.currencyhistory": CurrencyHistorySerializer,
        "counterparties.counterparty": CounterpartySerializer,
        "counterparties.responsible": ResponsibleSerializer,
        "strategies.strategy1": Strategy1Serializer,
        "strategies.strategy2": Strategy2Serializer,
        "strategies.strategy3": Strategy2Serializer,
        "csv_import.csvimportscheme": CsvImportSchemeSerializer,
        "integrations.complextransactionimportscheme": ComplexTransactionImportSchemeSerializer,
        "integrations.instrumentdownloadscheme": InstrumentDownloadSchemeSerializer,
        "integrations.mappingtable": MappingTableSerializer,
        "procedures.pricingprocedure": PricingProcedureSerializer,
        "procedures.expressionprocedure": ExpressionProcedureSerializer,
        "procedures.requestdatafileprocedure": RequestDataFileProcedureSerializer,
        "schedules.schedule": ScheduleSerializer,
        "obj_attrs.genericattributetype": GenericAttributeTypeSerializer,
        "ui.dashboardlayout": DashboardLayoutSerializer,
        "ui.memberlayout": MemberLayoutSerializer,
        "ui.mobilelayout": MobileLayoutSerializer,
        "ui.listlayout": ListLayoutSerializer,
        "ui.editlayout": EditLayoutSerializer,
        "ui.contextmenulayout": ContextMenuLayoutSerializer,
        "ui.complextransactionuserfield": ComplexTransactionUserFieldSerializer,
        "ui.transactionuserfield": TransactionUserFieldSerializer,
        "ui.instrumentuserfield": InstrumentUserFieldSerializer,
        "iam.group": GroupSerializer,
        "iam.role": RoleSerializer,
        "iam.accesspolicy": AccessPolicySerializer,
        "iam.resourcegroup": ResourceGroupSerializer,
        "reference_tables.referencetable": ReferenceTableSerializer,
        "configuration.newmembersetupconfiguration": NewMemberSetupConfigurationSerializer,
        "reports.balancereportcustomfield": BalanceReportCustomFieldSerializer,
        "reports.plreportcustomfield": PLReportCustomFieldSerializer,
        "reports.transactionreportcustomfield": TransactionReportCustomFieldSerializer,
        "system.whitelabelmodel": WhitelabelSerializer,
    }

    return serializer_map[content_type_key]


def get_list_of_entity_attributes(content_type_key):
    """
    Returns a list of attributes for a given entity type.
    :param content_type_key:
    :return: list of attributes
    """
    from poms.obj_attrs.models import GenericAttributeType

    content_type = get_content_type_by_name(content_type_key)
    attribute_types = GenericAttributeType.objects.filter(content_type=content_type)

    return [
        {
            "name": attribute_type.name,
            "key": "attributes." + attribute_type.user_code,
            "value_type": attribute_type.value_type,
            "tooltip": attribute_type.tooltip,
            "can_recalculate": attribute_type.can_recalculate,
        }
        for attribute_type in attribute_types
    ]


def compare_versions(version1, version2):
    v1_parts = version1.split(".")
    v2_parts = version2.split(".")

    for v1_part, v2_part in zip(v1_parts, v2_parts, strict=False):
        v1_number = int(v1_part)
        v2_number = int(v2_part)

        if v1_number < v2_number:
            return -1
        elif v1_number > v2_number:
            return 1

    if len(v1_parts) < len(v2_parts):
        return -1
    elif len(v1_parts) > len(v2_parts):
        return 1

    return 0


# region Dates
def is_business_day(date_obj: pd.Timestamp | datetime.date | datetime.datetime) -> bool:
    """Check if a date is a business day (Monday=0 to Friday=4)."""
    return date_obj.weekday() < 5


def get_last_business_day(day: datetime.date | str, to_string=False) -> str | datetime.date:
    """
    Returns the previous business day of the given date.
    :param day:
    :param to_string:
    :return:
    """

    if not isinstance(day, datetime.date):
        day = datetime.datetime.strptime(day, settings.API_DATE_FORMAT).date()

    weekday = datetime.date.weekday(day)
    if weekday > 4:  # if it's Saturday or Sunday
        day = day - datetime.timedelta(days=weekday - 4)

    return day.strftime(settings.API_DATE_FORMAT) if to_string else day


def last_day_of_month(any_day: datetime.date) -> datetime.date:
    # Day 28 exists in every month. 4 days later, it's always next month
    next_month = any_day.replace(day=28) + datetime.timedelta(days=4)
    # subtracting the number of the current day brings us back one month
    return next_month - datetime.timedelta(days=next_month.day)


def get_list_of_dates_between_two_dates(date_from, date_to, to_string=False):
    if not (date_from and date_to):
        raise ValueError("Both parameters 'date_from' & 'date_to' must be set")

    date_from = (
        date_from
        if isinstance(date_from, datetime.date)
        else datetime.datetime.strptime(date_from, settings.API_DATE_FORMAT).date()
    )

    date_to = (
        date_to
        if isinstance(date_to, datetime.date)
        else datetime.datetime.strptime(date_to, settings.API_DATE_FORMAT).date()
    )

    if date_from > date_to:
        raise ValueError(f"Parameter 'date_from' {date_from} must be less or equal 'date_to' {date_to}")

    dates = [date_from + timedelta(days=i) for i in range((date_to - date_from).days + 1)]

    return [str(date) for date in dates] if to_string else dates


def get_list_of_business_days_between_two_dates(date_from, date_to, to_string=False):
    if not isinstance(date_from, datetime.date):
        date_from = datetime.datetime.strptime(date_from, settings.API_DATE_FORMAT).date()

    if not isinstance(date_to, datetime.date):
        date_to = datetime.datetime.strptime(date_to, settings.API_DATE_FORMAT).date()

    diff = date_to - date_from

    result = []
    for i in range(diff.days + 1):
        day = date_from + timedelta(days=i)

        if is_business_day(day):
            if to_string:
                result.append(str(day))
            else:
                result.append(day)

    return result


def get_list_of_months_between_two_dates(date_from, date_to, to_string=False):
    if not isinstance(date_from, datetime.date):
        date_from = datetime.datetime.strptime(date_from, settings.API_DATE_FORMAT).date()

    if not isinstance(date_to, datetime.date):
        date_to = datetime.datetime.strptime(date_to, settings.API_DATE_FORMAT).date()

    diff = date_to - date_from

    result = []
    if date_from.day != 1:
        if to_string:
            result.append(str(date_from))
        else:
            result.append(date_from)

    for i in range(diff.days + 1):
        day = date_from + timedelta(days=i)

        if day.day == 1:
            if to_string:
                result.append(str(day))
            else:
                result.append(day)

    return result


def get_last_business_day_in_month(year: int, month: int, to_string=False):
    """
    Get last business day of month
    :param year:
    :param month:
    :param to_string:
    :return: date or string
    """
    day = max(calendar.monthcalendar(year, month)[-1:][0][:5])

    d = datetime.datetime(year, month, day).date()

    return d.strftime(settings.API_DATE_FORMAT) if to_string else d


def get_last_bdays_of_months_between_two_dates(date_from, date_to, to_string=False):
    """
    Get last business day of each month between two dates
    :param date_from:
    :param date_to:
    :param to_string:
    :return: list of dates or strings
    """
    months = get_list_of_months_between_two_dates(date_from, date_to)
    end_of_months = []

    if not isinstance(date_to, datetime.date):
        d_date_to = datetime.datetime.strptime(date_to, settings.API_DATE_FORMAT).date()
    else:
        d_date_to = date_to

    for month in months:
        # _l.info(month)
        # _l.info(d_date_to)

        last_business_day = get_last_business_day_in_month(month.year, month.month)

        if month.year == d_date_to.year and month.month == d_date_to.month:
            if to_string:
                end_of_months.append(d_date_to.strftime(settings.API_DATE_FORMAT))
            else:
                end_of_months.append(d_date_to)

        elif to_string:
            end_of_months.append(last_business_day.strftime(settings.API_DATE_FORMAT))

        else:
            end_of_months.append(last_business_day)

    return end_of_months


def get_closest_bday_of_yesterday(to_string=False):
    """
    Get the closest business day of yesterday
    :param to_string:
    :return: date or string
    """
    yesterday = datetime.date.today() - timedelta(days=1)
    return get_last_business_day(yesterday, to_string=to_string)


def get_last_business_day_of_previous_year(date):
    """
    Given a date in 'YYYY-MM-DD' format, returns the last business day of the previous year.
    """
    # Parse the date string
    if not isinstance(date, datetime.date):
        date = datetime.datetime.strptime(date, settings.API_DATE_FORMAT).date()

    # Find the last day of the previous year
    last_day_of_previous_year = datetime.date(date.year - 1, 12, 31)

    # If the last day is a Saturday (5) or Sunday (6), subtract the necessary days
    while last_day_of_previous_year.weekday() >= 5:  # 5 for Saturday, 6 for Sunday
        last_day_of_previous_year -= timedelta(days=1)

    return last_day_of_previous_year


def get_last_business_day_of_previous_month(date):
    """
    Given a date in 'YYYY-MM-DD' format, returns the last business day of the previous month.
    """
    # Parse the date string
    if not isinstance(date, datetime.date):
        date = datetime.datetime.strptime(date, settings.API_DATE_FORMAT).date()

    # Find the last day of the previous month
    first_day_of_month = datetime.date(date.year, date.month, 1)
    last_day_of_previous_month = first_day_of_month - timedelta(days=1)

    # If the last day is a Saturday (5) or Sunday (6), subtract the necessary days
    while last_day_of_previous_month.weekday() >= 5:  # 5 for Saturday, 6 for Sunday
        last_day_of_previous_month -= timedelta(days=1)

    return last_day_of_previous_month


def get_last_business_day_in_previous_quarter(date):
    """
    Given a date in 'YYYY-MM-DD' format, returns the start date
    of the Quarter-To-Date (QTD) period.
    """

    if not isinstance(date, datetime.date):
        date = datetime.datetime.strptime(date, settings.API_DATE_FORMAT).date()

    # Determine the start of the current quarter
    if date.month in [1, 2, 3]:
        start_date = datetime.date(date.year, 1, 1)
    elif date.month in [4, 5, 6]:
        start_date = datetime.date(date.year, 4, 1)
    elif date.month in [7, 8, 9]:
        start_date = datetime.date(date.year, 7, 1)
    else:
        start_date = datetime.date(date.year, 10, 1)
    last_day_of_previous_quarter = start_date - timedelta(days=1)

    # If the last day is a Saturday (5) or Sunday (6), subtract the necessary days
    while last_day_of_previous_quarter.weekday() >= 5:  # 5 for Saturday, 6 for Sunday
        last_day_of_previous_quarter -= timedelta(days=1)

    return last_day_of_previous_quarter


def shift_to_bday(date, shift):
    shift = 1 if shift > 0 else -1
    while not is_business_day(date):
        date += datetime.timedelta(days=shift)

    return date


def get_validated_date(day: datetime.date | str) -> datetime.date:
    if not isinstance(day, datetime.date):
        return datetime.datetime.strptime(day, settings.API_DATE_FORMAT).date()

    return day


def split_date_range(
    start_date: str | datetime.date,
    end_date: str | datetime.date,
    frequency: str,
    is_only_bday: bool,
) -> list[tuple]:
    """
    Splits a date range into subperiods with a given frequency.

    :param start_date: Start date in YYYY-MM-DD format (string) or datetime.date object
    :param end_date: End date in YYYY-MM-DD format (string) or datetime.date object
    :param frequency: "D" - (daily) / "W" - (weekly) / "M" - (monthly) / "Q" - (quarterly) /
                      "HY" - (half-yearly) / "Y" - (yearly) / "C" - (custom).
    :param is_only_bday: Whether to adjust the dates to business days.
    :return: A list of string tuples, each containing the start and end of a period.
    """
    # Validate frequency
    if frequency not in VALID_FREQUENCY:
        raise ValueError(f"Invalid frequency '{frequency}'. Valid options: {VALID_FREQUENCY}")

    # Handle "C" frequency to return always list with one tuple
    if frequency == "C":
        start_str: str = start_date if isinstance(start_date, str) else start_date.strftime(settings.API_DATE_FORMAT)
        end_str: str = end_date if isinstance(end_date, str) else end_date.strftime(settings.API_DATE_FORMAT)
        return [(start_str, end_str)]

    start_date = get_validated_date(start_date)
    end_date = get_validated_date(end_date)

    # Preserve original requested range for overlap filtering
    original_start_date = start_date
    original_end_date = end_date
    ts_range_start = pd.Timestamp(original_start_date)
    ts_range_end = pd.Timestamp(original_end_date)

    # Validate date range
    if start_date > end_date:
        raise ValueError(f"start_date ({start_date}) must be <= end_date ({end_date})")

    freq_start = frequency
    freq_end = f"E{frequency}"

    start_date = calc_shift_date_map[freq_start](start_date)
    ranges = pd.date_range(start=start_date, end=end_date, freq=frequency_map[frequency]())

    date_pairs: list[tuple] = []
    for sd in ranges:
        ed = calc_shift_date_map[freq_end](sd)

        if is_only_bday:
            if frequency == "D" and not is_business_day(sd):
                continue
            sd = shift_to_bday(sd, 1)  # noqa: PLW2901
            ed = shift_to_bday(ed, -1)

        # Skip periods that do not overlap the originally requested range
        if ed < ts_range_start or sd > ts_range_end:
            continue

        sd_str = str(sd.strftime(settings.API_DATE_FORMAT))
        ed_str = str(ed.strftime(settings.API_DATE_FORMAT))
        date_pair: tuple = (sd_str, ed_str)
        date_pairs.append(date_pair)

    return date_pairs


def shift_to_week_boundary(
    input_date: datetime.date,
    sdate: datetime.date,
    edate: datetime.date,
    start: bool,
    freq: str,
) -> datetime.date:
    """
    Changes the day to the beginning/end of the week,
    taking into account the boundaries of the range
    """
    if (start and input_date > sdate) or (not start and input_date < edate):
        input_date = calc_shift_date_map[freq](input_date)

    return input_date


def pick_dates_from_range(  # noqa: PLR0912
    start_date: str | datetime.date,
    end_date: str | datetime.date,
    frequency: str,
    is_only_bday: bool,
    start: bool,
) -> list[str]:
    """
    Generates a list of dates from a range with a given frequency.

    :param start_date: Start date in YYYY-MM-DD format.
    :param end_date: End date in YYYY-MM-DD format.
    :param frequency: "D" - (daily) / "W" - (weekly) / "M" - (monthly) / "Q" - (quarterly) /
                      "HY" - (half-yearly) / "Y" - (yearly) / "C" - (custom).
    :param is_only_bday: Whether to adjust the dates to business days.
    :param start: The beginning of frequency, if False, then end of frequency.
    :return: A list, containing the start or end of each frequency.
    """
    # Validate frequency
    if frequency not in VALID_FREQUENCY:
        raise ValueError(f"Invalid frequency '{frequency}'. Valid options: {VALID_FREQUENCY}")

    # Handle "C" frequency - return dates as strings
    if frequency == "C":
        start_str = start_date if isinstance(start_date, str) else start_date.strftime(settings.API_DATE_FORMAT)
        end_str = end_date if isinstance(end_date, str) else end_date.strftime(settings.API_DATE_FORMAT)
        return [start_str, end_str]

    start_date = get_validated_date(start_date)
    end_date = get_validated_date(end_date)

    # Validate date range
    if start_date > end_date:
        raise ValueError(f"start_date ({start_date}) must be less than or equal to end_date ({end_date})")

    # Preserve the original start_date for incomplete period handling
    original_start_date = start_date

    frequency = frequency if start else f"E{frequency}"

    # Align the start_date to the period boundary for proper date range generation
    # Skip alignment for weekly frequency as it has special handling via shift_to_week_boundary
    if "W" not in frequency:
        aligned_start_date = calc_shift_date_map[frequency](start_date)
    else:
        aligned_start_date = start_date

    dates = pd.date_range(start=aligned_start_date, end=end_date, freq=frequency_map[frequency]())
    dates = [d.date() for d in dates]

    # Filter out dates that are before the original start date
    dates = [d for d in dates if d >= original_start_date]

    # pd.date_range - adds dates that fall completely within
    # the frequency range. Adding dates from incomplete periods at the start/end
    # the frequency. Adding in the list uneven areas of date
    if dates:
        if start and original_start_date != dates[0]:
            dates.insert(0, original_start_date)
        if not start and end_date != dates[-1]:
            dates.append(end_date)

    pick_dates: list[str] = []
    for day in dates:
        if "W" in frequency:
            day = shift_to_week_boundary(day, original_start_date, end_date, start, frequency)  # noqa: PLW2901

        if is_only_bday:
            # For daily frequency, skip non-business days entirely
            if "D" in frequency and not is_business_day(day):
                continue

            # For other frequencies, shift to the nearest business day
            if "D" not in frequency and not is_business_day(day):
                if start:
                    day = shift_to_bday(day, 1)  # noqa: PLW2901
                else:
                    day = shift_to_bday(day, -1)  # noqa: PLW2901

        date_str = day.strftime(settings.API_DATE_FORMAT)
        if date_str not in pick_dates:
            pick_dates.append(date_str)

    return pick_dates


def calculate_period_date(
    input_date: str | datetime.date,
    frequency: str,
    shift: int,
    is_only_bday=False,
    start=False,
) -> str:
    """
    Calculates the start or end date of a certain time period,
    with the possibility of shifting forward or backward by several periods.

    :param input_date: A string in YYYY-MM-DD ISO format representing the current date.
    :param frequency: "D" - (daily) / "W" - (weekly) / "M" - (monthly) / "Q" - (quarterly) /
                      "HY" - (half-yearly) / "Y" - (yearly) / "C" - (custom).
    :param shift: Indicating how many periods to shift (-N for backward, +N for forward).
    :param is_only_bday: Whether to adjust the dates to business days.
    :param start: The beginning of frequency, if False, then end of frequency.
    :return: The calculated date in YYYY-MM-DD format.
    """
    input_date: datetime.date = get_validated_date(input_date)

    # Validate frequency
    if frequency not in VALID_FREQUENCY:
        raise ValueError(f"Invalid frequency '{frequency}'. Valid options: {VALID_FREQUENCY}")

    if frequency == "C":
        return input_date.strftime(settings.API_DATE_FORMAT)

    frequency = frequency if start else f"E{frequency}"

    # Special handling for shift=0: should return start/end of the current period
    if shift == 0:
        input_date = calc_shift_date_map[frequency](input_date)
    else:
        # For non-zero shifts, apply transformation only for weekly frequencies (preserve original logic)
        if "W" in frequency:
            input_date = calc_shift_date_map[frequency](input_date)

        input_date = input_date + frequency_map[frequency](shift)

    if is_only_bday and not is_business_day(input_date):
        if start:
            input_date = shift_to_bday(input_date, 1)
        else:
            input_date = shift_to_bday(input_date, -1)

    return input_date.strftime(settings.API_DATE_FORMAT)


# endregion Dates


def attr_is_relation(content_type_key: str, attribute_key: str) -> bool:
    """
    Determines if the given attribute key is a relation attribute based
    on the content type key.

    :param content_type_key: The key representing the content type.
    :param attribute_key: The key of the attribute to check.
    :return: True if the attribute is a relation attribute, False otherwise.
    """
    if content_type_key == "transactions.transactiontype" and attribute_key == "group":
        # because configuration
        return False

    return attribute_key in {
        "type",
        "currency",
        "instrument",
        "instrument_type",
        "country",
        "group",
        "pricing_policy",
        "portfolio",
        "transaction_type",
        "transaction_currency",
        "settlement_currency",
        "account_cash",
        "account_interim",
        "account_position",
        "accrued_currency",
        "pricing_currency",
        "one_off_event",
        "regular_event",
        "factor_same",
        "factor_up",
        "factor_down",
        "strategy1_position",
        "strategy1_cash",
        "strategy2_position",
        "strategy2_cash",
        "strategy3_position",
        "strategy3_cash",
        "counterparty",
        "responsible",
        "allocation_balance",
        "allocation_pl",
        "linked_instrument",
        "subgroup",
        "instrument_class",
        "transaction_class",
        "daily_pricing_model",
        "payment_size_detail",
        # Portfolio register
        "cash_currency",
        "portfolio_register",
        "valuation_currency",
    }


def set_schema(space_code):
    with connection.cursor() as cursor:
        cursor.execute(f"SET search_path TO {space_code};")


def get_current_schema():
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_schema();")
        return cursor.fetchone()[0]


class FinmarsNestedObjects(NestedObjects):
    def __init__(self, instance):
        using = router.db_for_write(instance._meta.model)
        super().__init__(using=using, origin=[instance])

    def _nested(self, obj, seen):
        if obj in seen:
            return None
        seen.add(obj)
        children = []
        for child in self.edges.get(obj, ()):
            if nested := self._nested(child, seen):
                children.append(nested)
        ret = {
            "name": obj.__class__.__name__,
            "content_type": f"{obj._meta.app_label}.{obj._meta.model_name}",
            "id": obj.id,
        }
        if hasattr(obj, "user_code"):
            ret["user_code"] = obj.user_code
        if children:
            ret["related"] = children
        return ret

    def nested(self, *args, **kwargs):
        seen = set()
        roots = []
        for root in self.edges.get(None, ()):
            if item := self._nested(root, seen):
                item["protected"] = root in self.protected
                roots.append(item)
        return roots
