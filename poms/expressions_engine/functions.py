import calendar
import datetime
import hashlib
import json
import logging
import random
import re
import traceback
import uuid
from math import isclose

from dateutil import relativedelta
from django.contrib.contenttypes.models import ContentType
from django.forms.models import model_to_dict
from django.utils import numberformat
from pandas.tseries.offsets import BDay, BMonthEnd, BQuarterEnd, BYearEnd

from poms.common.utils import (
    calculate_period_date,
    date_now,
    get_list_of_dates_between_two_dates,
)
from poms.expressions_engine.exceptions import ExpressionEvalError, InvalidExpression

_l = logging.getLogger("poms.formula")


def _check_float(val):
    return val if val is not None else 0.0


def _str(a):
    return str(a)


def _upper(a):
    return str(a).upper()


def _lower(a):
    return str(a).lower()


def _contains(a, b):
    return str(b) in str(a)


def _replace(text, oldvalue, newvalue):
    return text.replace(oldvalue, newvalue)


def _int(a):
    return int(a)


def _float(a):
    return float(a)


def _bool(a):
    return bool(a)


def _round(a, ndigits=None):
    if ndigits is not None:
        ndigits = int(ndigits)
    return round(float(a), ndigits)


def _trunc(a):
    return int(a)


def _abs(a):
    return abs(a)


def _min(a, b):
    return min(a, b)


def _max(a, b):
    return max(a, b)


def _isclose(a, b, rel_tol=1e-09, abs_tol=0.0):
    return isclose(float(a), float(b), rel_tol=float(rel_tol), abs_tol=float(abs_tol))


def _iff(test, a, b):
    return a if test else b


def _len(a):
    return len(a)


def _range(*args):
    return range(*args)


def _now():
    return date_now()


def _date(year, month=1, day=1):
    return datetime.date(year=int(year), month=int(month), day=int(day))


def _date_min():
    return datetime.date.min


def _date_max():
    return datetime.date.max


def _isleap(date_or_year):
    if isinstance(date_or_year, datetime.date):
        return calendar.isleap(date_or_year.year)
    else:
        return calendar.isleap(int(date_or_year))


def _days(days):
    return datetime.timedelta(days=int(days))


def _weeks(weeks):
    return datetime.timedelta(weeks=int(weeks))


def _months(months):
    return relativedelta.relativedelta(months=int(months))


def _timedelta(
    years=0,
    months=0,
    days=0,
    leapdays=0,
    weeks=0,
    year=None,
    month=None,
    day=None,
    weekday=None,
    yearday=None,
    nlyearday=None,
):
    return relativedelta.relativedelta(
        years=int(years),
        months=int(months),
        days=int(days),
        leapdays=int(leapdays),
        weeks=int(weeks),
        year=int(year) if year is not None else None,
        month=int(month) if month is not None else None,
        day=int(day) if day is not None else None,
        weekday=int(weekday) if weekday is not None else None,
        yearday=int(yearday) if yearday is not None else None,
        nlyearday=int(nlyearday) if nlyearday is not None else None,
    )


def _add_days(date, days):
    if not isinstance(date, datetime.date):
        date = _parse_date(str(date))
    # _check_date(date)
    if not isinstance(days, datetime.timedelta):
        days = datetime.timedelta(days=int(days))
    return date + days


def _days_diff(date_1, date_2):
    """
    Calculate the difference in days between two dates.
    :param date_1: First date (datetime or string in YYYY-MM-DD format).
    :param date_2: Second date (datetime or string in YYYY-MM-DD format).
    :return: Integer difference in days.
    """
    # If the dates are strings, convert them to datetime objects
    if isinstance(date_1, str):
        date_1 = datetime.datetime.strptime(date_1, "%Y-%m-%d")
    if isinstance(date_2, str):
        date_2 = datetime.datetime.strptime(date_2, "%Y-%m-%d")

    # Calculate the difference
    diff = date_2 - date_1

    # Return the absolute difference in days
    return diff.days


def _add_weeks(date, weeks):
    if not isinstance(date, datetime.date):
        date = _parse_date(str(date))
    # _check_date(date)
    if not isinstance(weeks, datetime.timedelta):
        weeks = datetime.timedelta(weeks=int(weeks))
    return date + weeks


def _add_workdays(date, workdays, only_workdays=True):
    # _check_date(date)
    if not isinstance(date, datetime.date):
        date = _parse_date(str(date))
    workdays = int(workdays)
    weeks, days_remainder = divmod(workdays, 5)
    date = date + datetime.timedelta(weeks=weeks, days=days_remainder)
    if only_workdays:
        if date.weekday() == 5:
            return date + datetime.timedelta(days=2)
        if date.weekday() == 6:
            return date + datetime.timedelta(days=1)
    return date


def _format_date(date, format_=None):
    if not isinstance(date, datetime.date):
        date = _parse_date(str(date))
    # _check_date(date)
    format_ = str(format_) if format_ else "%Y-%m-%d"
    return date.strftime(format_)


def _get_list_of_dates_between_two_dates(date_from, date_to):
    return get_list_of_dates_between_two_dates(date_from, date_to)


def _send_system_message(
    evaluator,
    title=None,
    description=None,
    type="info",
    section="other",
    action_status="not_required",
    performed_by="Expression Engine",
):
    from poms.system_messages.handlers import send_system_message
    from poms.users.utils import get_master_user_from_context

    try:
        context = evaluator.context

        master_user = get_master_user_from_context(context)

        send_system_message(
            master_user=master_user,
            performed_by=performed_by,
            type=type,
            section=section,
            action_status=action_status,
            title=title,
            description=description,
        )

    except Exception as e:
        _l.error(f"Could not sent system message {e}")


_send_system_message.evaluator = True


def _calculate_performance_report(
    evaluator,
    name,
    date_from,
    date_to,
    report_currency,
    calculation_type,
    segmentation_type,
    registers,
):
    from poms.instruments.models import Instrument
    from poms.reports.common import PerformanceReport
    from poms.reports.performance_report import PerformanceReportBuilder
    from poms.reports.serializers import PerformanceReportSerializer
    from poms.users.utils import get_master_user_from_context, get_member_from_context

    try:
        context = evaluator.context

        master_user = get_master_user_from_context(context)
        member = get_member_from_context(context)

        currency = _safe_get_currency(evaluator, report_currency)

        _l.info("_calculate_performance_report master_user %s", master_user)
        _l.info("_calculate_performance_report member %s", member)
        _l.info("_calculate_performance_report date_from  %s", date_from)
        _l.info("_calculate_performance_report date_to %s", date_to)
        _l.info("_calculate_performance_report currency %s", currency)

        d_from = datetime.datetime.strptime(date_from, "%Y-%m-%d").date()
        d_to = datetime.datetime.strptime(date_to, "%Y-%m-%d").date()

        registers_instances = []

        for register in registers:
            registers_instances.append(Instrument.objects.get(master_user=master_user, user_code=register))

        instance = PerformanceReport(
            report_instance_name=name,
            master_user=master_user,
            member=member,
            report_currency=currency,
            begin_date=d_from,
            end_date=d_to,
            calculation_type=calculation_type,
            segmentation_type=segmentation_type,
            registers=registers_instances,
            save_report=True,
        )

        builder = PerformanceReportBuilder(instance=instance)
        instance = builder.build_report()

        serializer = PerformanceReportSerializer(instance=instance, context=context)

        serializer.to_representation(instance)

    except Exception as e:
        _l.error("_calculate_performance_report.Exception %s", e)
        _l.error("_calculate_performance_report.Trace %s", traceback.format_exc())


_calculate_performance_report.evaluator = True


def _calculate_balance_report(
    evaluator,
    name,
    report_date,
    report_currency,
    pricing_policy=None,
    cost_method="AVCO",
    portfolios=None,
):
    from poms.instruments.models import CostMethod
    from poms.portfolios.models import Portfolio
    from poms.reports.common import Report
    from poms.reports.serializers import BalanceReportSerializer
    from poms.reports.sql_builders.balance import BalanceReportBuilderSql
    from poms.users.models import EcosystemDefault
    from poms.users.utils import get_master_user_from_context, get_member_from_context

    if portfolios is None:
        portfolios = []

    try:
        context = evaluator.context

        master_user = get_master_user_from_context(context)
        member = get_member_from_context(context)

        ecosystem_default = EcosystemDefault.cache.get_cache(master_user_pk=master_user.pk)

        currency = _safe_get_currency(evaluator, report_currency)
        if pricing_policy:
            pricing_policy = _safe_get_pricing_policy(evaluator, pricing_policy)
        else:
            pricing_policy = ecosystem_default.pricing_policy

        cost_method = CostMethod.objects.get(user_code=cost_method)

        _l.info(f"_calculate_balance_report master_user {master_user}")
        _l.info(f"_calculate_balance_report member {member}")
        _l.info(f"_calculate_balance_report report_date  {report_date}")
        _l.info(f"_calculate_balance_report currency {currency}")

        report_date_d = datetime.datetime.strptime(report_date, "%Y-%m-%d").date()

        portfolios_instances = []

        if portfolios:
            for portfolio in portfolios:
                portfolios_instances.append(Portfolio.objects.get(master_user=master_user, user_code=portfolio))

        instance = Report(
            report_instance_name=name,
            master_user=master_user,
            member=member,
            report_currency=currency,
            report_date=report_date_d,
            cost_method=cost_method,
            portfolios=portfolios_instances,
            pricing_policy=pricing_policy,
            custom_fields=[],
            save_report=True,
        )

        builder = BalanceReportBuilderSql(instance=instance)
        instance = builder.build_balance()

        serializer = BalanceReportSerializer(instance=instance, context=context)

        serializer.to_representation(instance)

    except Exception as e:
        _l.error(f"_calculate_balance_report.Exception {e}")
        _l.error(f"_calculate_balance_report.Trace {traceback.format_exc()}")


_calculate_balance_report.evaluator = True


def _calculate_pl_report(
    evaluator,
    name,
    pl_first_date,
    report_date,
    report_currency,
    pricing_policy=None,
    cost_method="AVCO",
    portfolios=None,
):
    from poms.instruments.models import CostMethod
    from poms.portfolios.models import Portfolio
    from poms.reports.common import Report
    from poms.reports.sql_builders.balance import PLReportBuilderSql
    from poms.users.models import EcosystemDefault
    from poms.users.utils import get_master_user_from_context, get_member_from_context

    if portfolios is None:
        portfolios = []

    try:
        context = evaluator.context

        master_user = get_master_user_from_context(context)
        member = get_member_from_context(context)

        ecosystem_default = EcosystemDefault.cache.get_cache(master_user_pk=master_user.pk)

        currency = _safe_get_currency(evaluator, report_currency)
        if pricing_policy:
            pricing_policy = _safe_get_pricing_policy(evaluator, pricing_policy)
        else:
            pricing_policy = ecosystem_default.pricing_policy

        cost_method = CostMethod.objects.get(user_code=cost_method)

        _l.info("_calculate_pl_report master_user %s", master_user)
        _l.info("_calculate_pl_report member %s", member)
        _l.info("_calculate_pl_report report_date  %s", report_date)
        _l.info("_calculate_pl_report pl_first_date  %s", pl_first_date)
        _l.info("_calculate_pl_report currency %s", currency)

        report_date_d = datetime.datetime.strptime(report_date, "%Y-%m-%d").date()
        pl_first_date_d = datetime.datetime.strptime(pl_first_date, "%Y-%m-%d").date()

        portfolios_instances = []

        if portfolios:
            for portfolio in portfolios:
                portfolios_instances.append(Portfolio.objects.get(master_user=master_user, user_code=portfolio))

        instance = Report(
            report_instance_name=name,
            master_user=master_user,
            member=member,
            report_currency=currency,
            report_date=report_date_d,
            pl_first_date=pl_first_date_d,
            cost_method=cost_method,
            pricing_policy=pricing_policy,
            portfolios=portfolios_instances,
            custom_fields=[],
            save_report=True,
        )

        builder = PLReportBuilderSql(instance=instance)
        instance = builder.build_balance()  # FIXME invalid method

        from poms.reports.serializers import PLReportSerializer

        serializer = PLReportSerializer(instance=instance, context=context)

        serializer.to_representation(instance)

    except Exception as e:
        _l.error("_calculate_pl_report.Exception %s", e)
        _l.error("_calculate_pl_report.Trace %s", traceback.format_exc())


_calculate_pl_report.evaluator = True


def _get_current_member(evaluator):
    from poms.users.utils import get_member_from_context

    context = evaluator.context

    member = get_member_from_context(context)

    return member


_get_current_member.evaluator = True


def _transaction_import__find_row(evaluator, **kwargs):
    context = evaluator.context  # noqa: F841

    result = {}

    if "row_number" in kwargs:
        result = {"row_number": kwargs["row_number"]}

    return result


_transaction_import__find_row.evaluator = True


def _md5(text):
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def _to_json(obj):
    return json.dumps(obj, default=str, indent=4)


def _parse_date(date_string, format=None):
    if not date_string:
        return None
    if isinstance(date_string, datetime.date):
        return date_string
    date_string = str(date_string)

    result = None

    if type(format) is list:
        for f in format:
            # print("Trying format %s" % f)
            try:
                result = datetime.datetime.strptime(date_string, f).date()
                break
            except Exception as e:
                print(f"_parse_date date_string {date_string}")
                print(f"_parse_date format {f}")
                print(f"_parse_date error {e}")
    else:
        if not format:
            format = "%Y-%m-%d"
        else:
            format = str(format)

        result = datetime.datetime.strptime(date_string, format).date()

    return result


def _universal_parse_date(date_string, **kwargs):
    # from dateutil.parser import parse
    # dt = parse('Mon Feb 15 2010')
    # print(dt)
    # # datetime.datetime(2010, 2, 15, 0, 0)
    # print(dt.strftime('%d/%m/%Y'))
    # # 15/02/2010

    from dateutil.parser import parse

    dt = parse(date_string, **kwargs)

    return dt.strftime("%Y-%m-%d")


def _get_quarter(date):
    import pandas as pd

    quarter = pd.Timestamp(_parse_date(date)).quarter

    return quarter


def _get_year(date):
    date = _parse_date(date)
    return date.year


def _get_month(date):
    date = _parse_date(date)
    return date.month


def _universal_parse_country(value):
    result = None

    from poms.instruments.models import Country

    try:
        country = Country.objects.filter(name=value)[0]
        result = country
        return result
    except Exception:
        pass

    try:
        country = Country.objects.filter(alpha_3=value)[0]
        result = country
        return result
    except Exception:
        pass

    try:
        country = Country.objects.filter(alpha_2=value)[0]
        result = country
        return result
    except Exception:
        pass

    return result


def _unix_to_date(unix, format_=None):
    if not unix:
        return None
    if isinstance(unix, datetime.date):
        return unix
    unix = int(unix)
    format_ = str(format) if format else "%Y-%m-%d"
    return datetime.datetime.utcfromtimestamp(unix).strftime(format_)


def _last_business_day(date):
    date = _parse_date(date)

    offset = BDay()

    return offset.rollback(date).date()


def _get_date_last_week_end_business(date):
    date = _parse_date(date)

    # 6 - is a last day of the week, 7 - days in a week
    subtract_days = (date.weekday() - 6) % 7
    subtract_delta = datetime.timedelta(days=subtract_days)

    date = date - subtract_delta  # last day of the previous week

    offset = BDay()

    return offset.rollback(date).date()


def _get_date_last_month_end_business(date):
    date = _parse_date(date)

    offset = BMonthEnd()

    return offset.rollback(date).date()


def _get_date_last_quarter_end_business(date):
    date = _parse_date(date)

    offset = BQuarterEnd()

    return offset.rollback(date).date()


def _get_date_last_year_end_business(date):
    date = _parse_date(date)

    offset = BYearEnd()

    return offset.rollback(date).date()


def _calculate_period_date(
    date: str | datetime.date,
    frequency: str,
    shift: int,
    is_only_bday=False,
    start=False,
) -> str:
    """
    To get information refer to docstring for the `calculate_period_date` function

    :param date: A string in YYYY-MM-DD ISO format representing the current date / date / a string that is
    another expression that evaluates to date.

    """
    date = _parse_date(date)

    return calculate_period_date(date, frequency, shift, is_only_bday, start)


def _format_date2(date, format_=None, locale=None):
    if not isinstance(date, datetime.date):
        date = _parse_date2(str(date))
    format_ = str(format_) if format_ else "yyyy-MM-dd"
    from babel import Locale
    from babel.dates import LC_TIME, format_date

    l = Locale.parse(locale or LC_TIME)  # noqa: E741
    return format_date(date, format=format_, locale=l)  # noqa: E741


def _parse_date2(date_string, format=None, locale=None):
    from babel import Locale
    from babel.dates import LC_TIME, parse_pattern

    # babel haven't supported parse by dynamic pattern
    if not date_string:
        return None
    if isinstance(date_string, datetime.date):
        return date_string

    date_string = str(date_string)
    format = str(format) if format else "yyyy-MM-dd"
    l = Locale.parse(locale or LC_TIME)  # noqa: E741
    p = parse_pattern(format)
    return p.apply(date_string, l)


def _format_number(
    number,
    decimal_sep=".",
    decimal_pos=None,
    grouping=3,
    thousand_sep="",
    use_grouping=False,
):
    number = float(number)
    decimal_sep = str(decimal_sep)
    if decimal_pos is not None:
        decimal_pos = int(decimal_pos)
    grouping = int(grouping)
    thousand_sep = str(thousand_sep)
    return numberformat.format(
        number,
        decimal_sep,
        decimal_pos=decimal_pos,
        grouping=grouping,
        thousand_sep=thousand_sep,
        force_grouping=use_grouping,
    )


def _parse_number(a):
    return a if isinstance(a, float | int) else float(a)


def _join(data, separator):
    return separator.join(data)


def _strip(data):
    return data.strip()


def _reverse(items):
    if isinstance(items, str):
        return items[::-1]

    items.reverse()

    return items


def _split(text, delimeter):
    return text.split(delimeter)


def _parse_bool(a):
    return a if isinstance(a, bool) else bool(a)


def _simple_price(date, date1, value1, date2, value2):
    if isinstance(date, str):
        date = _parse_date(date)
    if isinstance(date1, str):
        date1 = _parse_date(date1)
    if isinstance(date2, str):
        date2 = _parse_date(date2)
    if not isinstance(date, datetime.date):
        date = _parse_date(str(date))
    if not isinstance(date1, datetime.date):
        date1 = _parse_date(str(date1))
    if not isinstance(date2, datetime.date):
        date2 = _parse_date(str(date2))
    # _check_date(date)
    # _check_date(date1)
    # _check_date(date2)
    value1 = float(value1)
    value2 = float(value2)
    # _check_number(value1)
    # _check_number(value2)

    # if isclose(value1, value2):
    #     return value1
    # if date1 == date2:
    #     if isclose(value1, value2):
    #         return value1
    #     raise ValueError()
    # if date < date1:
    #     return 0.0
    # if date == date1:
    #     return value1
    # if date > date2:
    #     return 0.0
    # if date == date2:
    #     return value2
    if date1 <= date <= date2:
        d = 1.0 * (date - date1).days / (date2 - date1).days
        return value1 + d * (value2 - value1)
    return 0.0


def _get_ttype_default_input(evaluator, input):
    from poms.accounts.models import Account
    from poms.counterparties.models import Counterparty, Responsible
    from poms.currencies.models import Currency
    from poms.instruments.models import (
        AccrualCalculationModel,
        DailyPricingModel,
        Instrument,
        InstrumentType,
        PaymentSizeDetail,
        Periodicity,
        PricingPolicy,
    )
    from poms.integrations.models import PriceDownloadScheme
    from poms.portfolios.models import Portfolio
    from poms.strategies.models import Strategy1, Strategy2, Strategy3
    from poms.transactions.models import (
        EventClass,
        NotificationClass,
        TransactionTypeInput,
    )

    context = evaluator.context

    try:
        transaction_type = context["transaction_type"]
    except ValueError as e:
        raise ExpressionEvalError("Missing context: Transacion Type") from e

    inputs = list(transaction_type.inputs.all())

    input_obj = None

    for tt_input in inputs:
        if input == tt_input.name:
            input_obj = tt_input

    print(f"input_obj {input_obj}")

    if input_obj is None:
        raise ExpressionEvalError("Input is not found")

    print(f"input_obj.value_type {input_obj.value_type}")
    print(f"input_obj.value {input_obj.value}")

    if input_obj.value_type == TransactionTypeInput.RELATION:

        def _get_val_by_model_cls(obj, model_class):  # noqa: PLR0911, PLR0912
            if issubclass(model_class, Account):
                return obj.account
            elif issubclass(model_class, Currency):
                return obj.currency
            elif issubclass(model_class, Instrument):
                return obj.instrument
            elif issubclass(model_class, InstrumentType):
                return obj.instrument_type
            elif issubclass(model_class, Counterparty):
                return obj.counterparty
            elif issubclass(model_class, Responsible):
                return obj.responsible
            elif issubclass(model_class, Strategy1):
                return obj.strategy1
            elif issubclass(model_class, Strategy2):
                return obj.strategy2
            elif issubclass(model_class, Strategy3):
                return obj.strategy3
            elif issubclass(model_class, DailyPricingModel):
                return obj.daily_pricing_model
            elif issubclass(model_class, PaymentSizeDetail):
                return obj.payment_size_detail
            elif issubclass(model_class, Portfolio):
                return obj.portfolio
            elif issubclass(model_class, PriceDownloadScheme):
                return obj.price_download_scheme
            elif issubclass(model_class, PricingPolicy):
                return obj.pricing_policy
            elif issubclass(model_class, Periodicity):
                return obj.periodicity
            elif issubclass(model_class, AccrualCalculationModel):
                return obj.accrual_calculation_model
            elif issubclass(model_class, EventClass):
                return obj.event_class
            elif issubclass(model_class, NotificationClass):
                return obj.notification_class
            return None

        model_class = input_obj.content_type.model_class()

        print(f"model_class {model_class}")

        result = _get_val_by_model_cls(input_obj, model_class).__dict__

        # print('result relation.name %s' % result.name)
        print(f"result relation[name] {result['name']}")

    else:
        result = input_obj.value

    return result


_get_ttype_default_input.evaluator = True


def _set_complex_transaction_input(evaluator, input, value):
    try:
        from poms.transactions.models import TransactionTypeInput

        context = evaluator.context

        try:
            complex_transaction = context["complex_transaction"]
        except ValueError as e:
            raise ExpressionEvalError("Missing context: Complex Transaction") from e

        inputs = list(complex_transaction.inputs.all())

        input_obj = None

        for ct_input in inputs:
            if input == ct_input.transaction_type_input.name:
                input_obj = ct_input

        print(f"input_obj {input_obj}")

        if input_obj is None:
            raise ExpressionEvalError("Input is not found")

        print(f"input_obj.transaction_type_input.value_type  {input_obj.transaction_type_input.value_type}")
        print(f"value {value}")

        if value:
            if input_obj.transaction_type_input.value_type == TransactionTypeInput.RELATION:
                input_obj.value_relation = value
            elif input_obj.transaction_type_input.value_type == TransactionTypeInput.STRING:
                input_obj.value_string = value
            elif input_obj.transaction_type_input.value_type == TransactionTypeInput.NUMBER:
                input_obj.value_float = value
            elif input_obj.transaction_type_input.value_type == TransactionTypeInput.DATE:
                input_obj.value_date = value
            elif input_obj.transaction_type_input.value_type == TransactionTypeInput.SELECTOR:
                input_obj.value_string = value

            input_obj.save()

        return True
    except Exception as e:
        _l.info("_set_complex_transaction_input exception %s", e)
        return False


_set_complex_transaction_input.evaluator = True


def _set_complex_transaction_form_data(evaluator, key, value):
    try:
        context = evaluator.context

        try:
            values = context["values"]
        except ValueError as e:
            raise ExpressionEvalError("Missing context: Complex Transaction") from e

        values[key] = value

        return True
    except Exception as e:
        _l.info("_set_complex_transaction_form_data exception %s", e)
        return False


_set_complex_transaction_form_data.evaluator = True


def _set_complex_transaction_user_field(evaluator, field, value):
    try:
        context = evaluator.context

        try:
            complex_transaction = context["complex_transaction"]
        except ValueError as e:
            raise ExpressionEvalError("Missing context: Complex Transaction") from e

        setattr(complex_transaction, field, value)

        return True
    except Exception as e:
        _l.info("_set_complex_transaction_user_field exception %s", e)
        return False


_set_complex_transaction_user_field.evaluator = True


def _get_complex_transaction(evaluator, identifier):
    context = evaluator.context  # noqa: F841
    from poms.transactions.models import ComplexTransaction

    try:
        result = ComplexTransaction.objects.get(transaction_unique_code=identifier)
    except Exception:
        result = ComplexTransaction.objects.get(code=identifier)

    return result


_get_complex_transaction.evaluator = True


def _get_relation_by_user_code(evaluator, content_type, user_code):
    try:
        from poms.accounts.models import Account
        from poms.counterparties.models import Counterparty, Responsible
        from poms.currencies.models import Currency
        from poms.instruments.models import (
            AccrualCalculationModel,
            DailyPricingModel,
            Instrument,
            InstrumentType,
            PaymentSizeDetail,
            Periodicity,
            PricingPolicy,
        )
        from poms.portfolios.models import Portfolio
        from poms.strategies.models import Strategy1, Strategy2, Strategy3
        from poms.transactions.models import (
            EventClass,
            NotificationClass,
        )

        context = evaluator.context
        from poms.users.utils import get_master_user_from_context

        master_user = get_master_user_from_context(context)

        def _get_val_by_model_cls(model_class, user_code):  # noqa: PLR0911, PLR0912
            if issubclass(model_class, Account):
                return Account.objects.get(master_user=master_user, user_code=user_code)
            elif issubclass(model_class, Currency):
                return Currency.objects.get(master_user=master_user, user_code=user_code)
            elif issubclass(model_class, Instrument):
                return Instrument.objects.get(master_user=master_user, user_code=user_code)
            elif issubclass(model_class, InstrumentType):
                return InstrumentType.objects.get(master_user=master_user, user_code=user_code)
            elif issubclass(model_class, Counterparty):
                return Counterparty.objects.get(master_user=master_user, user_code=user_code)
            elif issubclass(model_class, Responsible):
                return Responsible.objects.get(master_user=master_user, user_code=user_code)
            elif issubclass(model_class, Strategy1):
                return Strategy1.objects.get(master_user=master_user, user_code=user_code)
            elif issubclass(model_class, Strategy2):
                return Strategy2.objects.get(master_user=master_user, user_code=user_code)
            elif issubclass(model_class, Strategy3):
                return Strategy3.objects.get(master_user=master_user, user_code=user_code)
            elif issubclass(model_class, DailyPricingModel):
                return DailyPricingModel.objects.get(user_code=user_code)
            elif issubclass(model_class, PaymentSizeDetail):
                return PaymentSizeDetail.objects.get(user_code=user_code)
            elif issubclass(model_class, Portfolio):
                return Portfolio.objects.get(master_user=master_user, user_code=user_code)
            elif issubclass(model_class, PricingPolicy):
                return PricingPolicy.objects.get(master_user=master_user, user_code=user_code)
            elif issubclass(model_class, Periodicity):
                return Periodicity.objects.get(user_code=user_code)
            elif issubclass(model_class, AccrualCalculationModel):
                return AccrualCalculationModel.objects.get(user_code=user_code)
            elif issubclass(model_class, EventClass):
                return EventClass.objects.get(user_code=user_code)
            elif issubclass(model_class, NotificationClass):
                return NotificationClass.objects.get(user_code=user_code)
            return None

        app_label, model = content_type.split(".")
        model_class = ContentType.objects.get_by_natural_key(app_label, model).model_class()

        _l.info("model_class %s", model_class)

        result = model_to_dict(_get_val_by_model_cls(model_class, user_code))

        return result
    except Exception:
        return None


_get_relation_by_user_code.evaluator = True


def _get_instruments(evaluator, **kwargs):
    try:
        from poms.instruments.models import (
            Instrument,
        )

        context = evaluator.context
        from poms.users.utils import get_master_user_from_context

        master_user = get_master_user_from_context(context)

        items = Instrument.objects.filter(master_user=master_user, is_deleted=False, **kwargs)
        result = []

        for item in items:
            result.append(model_to_dict(item))

        return result
    except Exception as e:
        _l.error("_get_instruments.exception %s", e)
        return None


_get_instruments.evaluator = True


def _get_currencies(evaluator, **kwargs):
    try:
        from poms.currencies.models import Currency

        context = evaluator.context
        from poms.users.utils import get_master_user_from_context

        master_user = get_master_user_from_context(context)

        items = Currency.objects.filter(master_user=master_user, is_deleted=False, **kwargs)

        result = []

        for item in items:
            result.append(model_to_dict(item))

        return result
    except Exception as e:
        _l.error("_get_currencies.exception %s", e)
        return None


_get_currencies.evaluator = True


def _get_mapping_key_by_value(evaluator, user_code, value, **kwargs):
    try:
        context = evaluator.context
        from poms.users.utils import get_master_user_from_context

        master_user = get_master_user_from_context(context)

        from poms.integrations.models import MappingTable

        mapping_table = MappingTable.objects.get(master_user=master_user, user_code=user_code)

        result = None

        for item in mapping_table.items.all():
            if item.value == value:
                result = item.key
                break

        return result
    except Exception as e:
        _l.error("_get_mapping_key_by_value.exception %s", e)
        return None


_get_mapping_key_by_value.evaluator = True


def _get_mapping_value_by_key(evaluator, user_code, key, **kwargs):
    try:
        context = evaluator.context
        from poms.users.utils import get_master_user_from_context

        master_user = get_master_user_from_context(context)

        from poms.integrations.models import MappingTable

        mapping_table = MappingTable.objects.get(master_user=master_user, user_code=user_code)

        result = None

        for item in mapping_table.items.all():
            if item.key == key:
                result = item.value
                break

        return result
    except Exception as e:
        _l.error("_get_mapping_value_by_key.exception %s", e)
        return None


_get_mapping_value_by_key.evaluator = True


def _get_mapping_keys(evaluator, user_code, **kwargs):
    try:
        context = evaluator.context
        from poms.users.utils import get_master_user_from_context

        master_user = get_master_user_from_context(context)

        from poms.integrations.models import MappingTable

        mapping_table = MappingTable.objects.get(master_user=master_user, user_code=user_code)

        result = []

        for item in mapping_table.items.all():
            result.append(item.key)

        return result
    except Exception as e:
        _l.error("_get_mapping_keys.exception %s", e)
        return None


_get_mapping_keys.evaluator = True


def _get_mapping_key_values(evaluator, user_code, key, **kwargs):
    try:
        context = evaluator.context
        from poms.users.utils import get_master_user_from_context

        master_user = get_master_user_from_context(context)

        from poms.integrations.models import MappingTable

        mapping_table = MappingTable.objects.get(master_user=master_user, user_code=user_code)

        result = []

        for item in mapping_table.items.all():
            if item.key == key:
                result.append(item.value)

        return result
    except Exception as e:
        _l.error("_get_mapping_key_values.exception %s", e)
        return None


_get_mapping_key_values.evaluator = True


def _convert_to_number(
    evaluator,
    text_number,
    thousand_separator="",
    decimal_separator=".",
    has_braces=False,
):
    result = text_number.replace(thousand_separator, "")

    result = result.replace(decimal_separator, ".")

    if has_braces:
        result = result.replace("(", "")
        result = result.replace(")", "")
        result = "-" + result

    return _parse_number(result)


_convert_to_number.evaluator = True


def _if_null(evaluator, input, default):
    if input:
        return input

    return default


_if_null.evaluator = True


def _substr(evaluator, text, start_index, end_index):
    return text[start_index:end_index]


_substr.evaluator = True


def _reg_search(evaluator, text, expression):
    return re.search(expression, text).group()


_reg_search.evaluator = True


def _reg_replace(evaluator, text, expession, replace_text):
    return re.sub(expession, replace_text, text)


_reg_replace.evaluator = True


def _generate_user_code(evaluator, prefix="", suffix="", counter=0):
    from poms.users.utils import get_master_user_from_context

    context = evaluator.context

    master_user = get_master_user_from_context(context)

    if not master_user.user_code_counters:
        master_user.user_code_counters = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

    if counter < 0:
        raise InvalidExpression("Counter is lower than 0")

    if counter > 10:
        raise InvalidExpression("Counter is greater than 10")

    master_user.user_code_counters[counter] = master_user.user_code_counters[counter] + 1
    master_user.save()

    result = prefix + str(master_user.user_code_counters[counter]).zfill(17) + suffix

    if len(result) > 25:
        raise InvalidExpression("User code is too big")

    return result


_generate_user_code.evaluator = True


def _get_fx_rate(evaluator, date, currency, pricing_policy, default_value=0):
    from poms.currencies.models import CurrencyHistory
    from poms.users.utils import get_master_user_from_context

    context = evaluator.context
    master_user = get_master_user_from_context(context)  # noqa: F841

    date = _parse_date(date)
    currency = _safe_get_currency(evaluator, currency)
    pricing_policy = _safe_get_pricing_policy(evaluator, pricing_policy)

    # TODO need master user check, security hole

    try:
        result = CurrencyHistory.objects.get(date=date, currency=currency, pricing_policy=pricing_policy)
    except (CurrencyHistory.DoesNotExist, KeyError):
        result = None

    if result:
        return result.fx_rate

    return default_value


_get_fx_rate.evaluator = True


def _add_fx_rate(evaluator, date, currency, pricing_policy, fx_rate=0, overwrite=True):
    from poms.currencies.models import CurrencyHistory
    from poms.users.utils import get_master_user_from_context

    context = evaluator.context
    master_user = get_master_user_from_context(context)  # noqa: F841

    date = _parse_date(date)
    pricing_policy = _safe_get_pricing_policy(evaluator, pricing_policy)
    currency = _safe_get_currency(evaluator, currency)

    # TODO need master user check, security hole

    try:
        result = CurrencyHistory.objects.get(date=date, currency=currency, pricing_policy=pricing_policy)

        if overwrite:
            result.fx_rate = fx_rate

            result.save()
        else:
            return False

    except CurrencyHistory.DoesNotExist:
        result = CurrencyHistory.objects.create(
            date=date, currency=currency, pricing_policy=pricing_policy, fx_rate=fx_rate
        )

        result.save()

    return True


_add_fx_rate.evaluator = True


def _add_price_history(
    evaluator,
    date,
    instrument,
    pricing_policy,
    principal_price=0,
    accrued_price=None,
    is_temporary_price=False,
    overwrite=True,
):
    """
    Adds a price history entry for an instrument.

    Args:
    - evaluator: The evaluator object.
    - date: The date of the price history entry.
    - instrument: The instrument object.
    - pricing_policy: The pricing policy object.
    - principal_price: The principal price (default: 0).
    - accrued_price: The accrued price (default: 0).
    - is_temporary_price: Indicates if the price is temporary (default: False).
    - overwrite: Indicates if existing price history should be overwritten (default: True).
    """
    from poms.instruments.models import PriceHistory

    # from poms.users.utils import get_master_user_from_context
    # TODO need master user check, security hole
    # context = evaluator.context
    # master_user = get_master_user_from_context(context)

    if not overwrite:
        return False

    date = _parse_date(date)
    instrument = _safe_get_instrument(evaluator, instrument)
    pricing_policy = _safe_get_pricing_policy(evaluator, pricing_policy)
    if accrued_price is None:
        # https://finmars2018.atlassian.net/browse/FN-2233
        accrued_price = instrument.get_accrued_price(date)

    try:
        result = PriceHistory.objects.get(date=date, instrument=instrument, pricing_policy=pricing_policy)

        if principal_price is not None:
            result.principal_price = principal_price

        if accrued_price is not None:
            result.accrued_price = accrued_price

        result.save()

    except PriceHistory.DoesNotExist:
        result = PriceHistory.objects.create(
            date=date,
            instrument=instrument,
            is_temporary_price=is_temporary_price,
            pricing_policy=pricing_policy,
            principal_price=principal_price,
            accrued_price=accrued_price,
        )

        result.save()

    return True


_add_price_history.evaluator = True


def _get_latest_principal_price(evaluator, date_from, date_to, instrument, pricing_policy, default_value=None):
    try:
        from poms.instruments.models import PriceHistory
        from poms.users.utils import get_master_user_from_context

        context = evaluator.context
        master_user = get_master_user_from_context(context)  # noqa: F841

        date_from = _parse_date(date_from)
        date_to = _parse_date(date_to)
        instrument = _safe_get_instrument(evaluator, instrument)
        pricing_policy = _safe_get_pricing_policy(evaluator, pricing_policy)

        _l.info("_get_latest_principal_price instrument %s", instrument)
        _l.info("_get_latest_principal_price  pricing_policy %s", pricing_policy)

        results = (
            PriceHistory.objects.exclude(principal_price=0)
            .filter(
                date__gte=date_from,
                date__lte=date_to,
                instrument=instrument,
                pricing_policy=pricing_policy,
            )
            .order_by("-date")
        )

        _l.info("_get_latest_principal_price results %s", results)

        if list(results):
            return results[0].principal_price

        return default_value
    except Exception as e:
        _l.info("_get_latest_principal_price exception %s", e)
        return default_value


_get_latest_principal_price.evaluator = True


def _get_latest_principal_price_date(evaluator, instrument, pricing_policy, default_value=None):
    try:
        from poms.instruments.models import PriceHistory
        from poms.users.utils import get_master_user_from_context

        context = evaluator.context
        master_user = get_master_user_from_context(context)  # noqa: F841

        instrument = _safe_get_instrument(evaluator, instrument)
        pricing_policy = _safe_get_pricing_policy(evaluator, pricing_policy)

        # _l.info("_get_latest_principal_price instrument %s " % instrument)
        # _l.info("_get_latest_principal_price  pricing_policy %s " % pricing_policy)

        results = (
            PriceHistory.objects.exclude(principal_price=0)
            .filter(instrument=instrument, pricing_policy=pricing_policy)
            .order_by("-date")
        )

        # _l.info("_get_latest_principal_price_date results %s " % results)

        if list(results):
            return results[0].date

        return default_value
    except Exception:
        # _l.error("_get_latest_principal_price_date exception %s " % str(e))
        # _l.error("_get_latest_principal_price_date exception %s " % traceback.format_exc())
        return default_value


_get_latest_principal_price_date.evaluator = True


def _get_latest_fx_rate(evaluator, date_from, date_to, currency, pricing_policy, default_value=None):
    try:
        from poms.currencies.models import CurrencyHistory
        from poms.users.utils import get_master_user_from_context

        context = evaluator.context
        master_user = get_master_user_from_context(context)  # noqa: F841

        date_from = _parse_date(date_from)
        date_to = _parse_date(date_to)
        currency = _safe_get_currency(evaluator, currency)
        pricing_policy = _safe_get_pricing_policy(evaluator, pricing_policy)

        _l.info("_get_latest_fx_rate instrument %s", currency)
        _l.info("_get_latest_fx_rate  pricing_policy %s", pricing_policy)

        results = CurrencyHistory.objects.filter(
            date__gte=date_from,
            date__lte=date_to,
            currency=currency,
            pricing_policy=pricing_policy,
        ).order_by("-date")

        _l.info("_get_latest_fx_rate results %s", results)

        return results[0].fx_rate if list(results) else default_value

    except Exception as e:
        _l.info("_get_latest_fx_rate exception %s", e)
        return default_value


_get_latest_fx_rate.evaluator = True


def _get_price_history_principal_price(evaluator, date, instrument, pricing_policy, default_value=0):
    from poms.instruments.models import PriceHistory
    from poms.users.utils import get_master_user_from_context

    context = evaluator.context
    master_user = get_master_user_from_context(context)  # noqa: F841

    # TODO need master user check, security hole

    date = _parse_date(date)
    instrument = _safe_get_instrument(evaluator, instrument)
    pricing_policy = _safe_get_pricing_policy(evaluator, pricing_policy)

    try:
        result = PriceHistory.objects.get(date=date, instrument=instrument, pricing_policy=pricing_policy)

        return result.principal_price

    except PriceHistory.DoesNotExist:
        print("Price history is not found")

    return default_value


_get_price_history_principal_price.evaluator = True


def _get_price_history_accrued_price(
    evaluator, date, instrument, pricing_policy, default_value=0, days_to_look_back=0
):
    from poms.instruments.models import PriceHistory, PricingPolicy
    from poms.users.utils import get_master_user_from_context

    try:
        days_to_look_back = int(days_to_look_back)
    except TypeError as e:
        raise ExpressionEvalError("Invalid Days To Look Back Value") from e

    context = evaluator.context
    master_user = get_master_user_from_context(context)

    # TODO need master user check, security hole

    date = _parse_date(date)
    instrument = _safe_get_instrument(evaluator, instrument)

    master_user = get_master_user_from_context(context)

    pricing_policy_pk = None

    if isinstance(pricing_policy, dict):
        pricing_policy_pk = int(pricing_policy["id"])

    elif isinstance(pricing_policy, int | float):
        pricing_policy_pk = int(pricing_policy)

    elif isinstance(pricing_policy, str):
        pricing_policy_pk = PricingPolicy.objects.get(master_user=master_user, user_code=pricing_policy).id

    # print('formula pk %s' % pk)

    if pricing_policy_pk is None:
        raise ExpressionEvalError("Invalid Pricing Policy")

    if days_to_look_back == 0:
        try:
            result = PriceHistory.objects.get(date=date, instrument=instrument, pricing_policy_id=pricing_policy_pk)

            return result.accrued_price

        except PriceHistory.DoesNotExist:
            return default_value

    else:
        if days_to_look_back < 0:
            date_to = date
            date_from = date - datetime.timedelta(days=abs(days_to_look_back))

        else:
            date_from = date
            date_to = date + datetime.timedelta(days=abs(days_to_look_back))

        print(f"_get_price_history_accrued_price date_from {date_from} date_to {date_to}")

        prices = PriceHistory.objects.filter(
            date__gte=date_from,
            date_lte=date_to,
            instrument=instrument,
            pricing_policy_id=pricing_policy_pk,
        ).order_by("-date")

        return prices[0].defaul_value if len(prices) else default_value


_get_price_history_accrued_price.evaluator = True


def _get_price_history(evaluator, date, instrument, pricing_policy, default_value=0, days_to_look_back=0):
    from poms.instruments.models import PriceHistory, PricingPolicy
    from poms.users.utils import get_master_user_from_context

    try:
        days_to_look_back = int(days_to_look_back)
    except TypeError as e:
        raise ExpressionEvalError("Invalid Days To Look Back Value") from e

    context = evaluator.context
    master_user = get_master_user_from_context(context)

    # TODO need master user check, security hole

    date = _parse_date(date)
    instrument = _safe_get_instrument(evaluator, instrument)

    master_user = get_master_user_from_context(context)

    pricing_policy_pk = None

    if isinstance(pricing_policy, dict):
        pricing_policy_pk = int(pricing_policy["id"])

    elif isinstance(pricing_policy, int | float):
        pricing_policy_pk = int(pricing_policy)

    elif isinstance(pricing_policy, str):
        pricing_policy_pk = PricingPolicy.objects.get(master_user=master_user, user_code=pricing_policy).id

    # print('formula pk %s' % pk)

    if pricing_policy_pk is None:
        raise ExpressionEvalError("Invalid Pricing Policy")

    if days_to_look_back == 0:
        try:
            return PriceHistory.objects.get(
                date=date,
                instrument=instrument,
                pricing_policy_id=pricing_policy_pk,
            )

        except PriceHistory.DoesNotExist:
            return None

    else:
        if days_to_look_back < 0:
            date_to = date
            date_from = date - datetime.timedelta(days=abs(days_to_look_back))

        else:
            date_from = date
            date_to = date + datetime.timedelta(days=abs(days_to_look_back))

        print(f"_get_price_history_accrued_price date_from {date_from} date_to {date_to}")

        prices = PriceHistory.objects.filter(
            date__gte=date_from,
            date_lte=date_to,
            instrument=instrument,
            pricing_policy_id=pricing_policy_pk,
        ).order_by("-date")

        return prices[0] if len(prices) else None


_get_price_history.evaluator = True


def _get_factor_from_price(evaluator, date, instrument, pricing_policy, default_value=0, days_to_look_back=0):
    from poms.instruments.models import PriceHistory, PricingPolicy
    from poms.users.utils import get_master_user_from_context

    try:
        days_to_look_back = int(days_to_look_back)
    except TypeError as e:
        raise ExpressionEvalError("Invalid Days To Look Back Value") from e

    context = evaluator.context
    master_user = get_master_user_from_context(context)

    # TODO need master user check, security hole

    date = _parse_date(date)
    instrument = _safe_get_instrument(evaluator, instrument)

    master_user = get_master_user_from_context(context)

    pricing_policy_pk = None

    if isinstance(pricing_policy, dict):
        pricing_policy_pk = int(pricing_policy["id"])

    elif isinstance(pricing_policy, int | float):
        pricing_policy_pk = int(pricing_policy)

    elif isinstance(pricing_policy, str):
        pricing_policy_pk = PricingPolicy.objects.get(master_user=master_user, user_code=pricing_policy).id

    # print('formula pk %s' % pk)

    if pricing_policy_pk is None:
        raise ExpressionEvalError("Invalid Pricing Policy")

    if days_to_look_back == 0:
        try:
            result = PriceHistory.objects.get(date=date, instrument=instrument, pricing_policy_id=pricing_policy_pk)

            return result.factor

        except PriceHistory.DoesNotExist:
            return 1

    else:
        if days_to_look_back < 0:
            date_to = date
            date_from = date - datetime.timedelta(days=abs(days_to_look_back))

        else:
            date_from = date
            date_to = date + datetime.timedelta(days=abs(days_to_look_back))

        print(f"_get_price_history_accrued_price date_from {date_from} date_to {date_to}")

        prices = PriceHistory.objects.filter(
            date__gte=date_from,
            date_lte=date_to,
            instrument=instrument,
            pricing_policy_id=pricing_policy_pk,
        ).order_by("-date")

        return prices[0].factor if len(prices) else 1


_get_factor_from_price.evaluator = True


def _get_next_coupon_date(evaluator, date, instrument):
    from poms.users.utils import get_master_user_from_context

    context = evaluator.context
    master_user = get_master_user_from_context(context)

    # TODO need master user check, security hole

    date = _parse_date(date)
    instrument = _safe_get_instrument(evaluator, instrument)

    master_user = get_master_user_from_context(context)  # noqa: F841

    items = instrument.get_future_coupons(begin_date=date, with_maturity=False)

    if len(items):
        next_date = items[0]

        return next_date[0]

    return None


_get_next_coupon_date.evaluator = True


def _get_factor_schedule(evaluator, date, instrument):
    from poms.instruments.models import InstrumentFactorSchedule
    from poms.users.utils import get_master_user_from_context

    context = evaluator.context
    master_user = get_master_user_from_context(context)  # noqa: F841

    instrument = _safe_get_instrument(evaluator, instrument)

    # TODO need master user check, security hole

    try:
        result = InstrumentFactorSchedule.objects.get(effective_date=date, instrument=instrument)
    except (InstrumentFactorSchedule.DoesNotExist, KeyError):
        result = None

    if result is None:
        results = InstrumentFactorSchedule.objects.filter(effective_date__lte=date, instrument=instrument).order_by(
            "-effective_date"
        )

        if list(results):
            result = results[0]
        else:
            result = None

    if result is not None and result.factor_value:
        return result.factor_value

    return 1


_get_factor_schedule.evaluator = True


def _get_instrument_attribute(evaluator, instrument, attribute_type_user_code):
    from poms.users.utils import get_master_user_from_context

    context = evaluator.context
    master_user = get_master_user_from_context(context)  # noqa: F841

    if not isinstance(instrument, dict):
        instrument = _safe_get_instrument(evaluator, instrument)

    attributes = instrument.get("attributes", [])

    result = None
    for attribute in attributes:
        if attribute.get("attribute_type", {}).get("user_code") == attribute_type_user_code:
            value_type = attribute.get("attribute_type", {}).get("value_type")

            if value_type == 10:
                result = attribute.get("value_text")
            elif value_type == 20:
                result = attribute.get("value_float")
            elif value_type == 30:
                classifier = attribute.get("classifier", None)

                if classifier is not None:
                    result = classifier.get("name")

            elif value_type == 40:
                result = attribute.get("value_date")

    return result


_get_instrument_attribute.evaluator = True


def _get_currency_attribute(evaluator, currency, attribute_type_user_code):
    from poms.users.utils import get_master_user_from_context

    context = evaluator.context
    master_user = get_master_user_from_context(context)  # noqa: F841

    currency = _safe_get_currency(evaluator, currency)

    result = None

    for attribute in currency.attributes.all():
        if attribute.attribute_type.user_code == attribute_type_user_code:
            if attribute.attribute_type.value_type == 10:
                result = attribute.value_text

            elif attribute.attribute_type.value_type == 20:
                result = attribute.value_float

            elif attribute.attribute_type.value_type == 30:
                if attribute.classifier:
                    result = attribute.classifier.name

            elif attribute.attribute_type.value_type == 40:
                result = attribute.value_date

    return result


_get_currency_attribute.evaluator = True


def _add_factor_schedule(evaluator, instrument, effective_date, factor_value):
    from poms.instruments.models import InstrumentFactorSchedule
    from poms.users.utils import get_master_user_from_context

    context = evaluator.context
    master_user = get_master_user_from_context(context)  # noqa: F841

    instrument = _safe_get_instrument(evaluator, instrument)

    result = InstrumentFactorSchedule.objects.create(
        effective_date=effective_date, factor_value=factor_value, instrument=instrument
    )

    return result


_add_factor_schedule.evaluator = True


# DEPRECATED
def _get_instrument_pricing_scheme(evaluator, instrument, pricing_policy):
    from poms.users.utils import get_master_user_from_context

    context = evaluator.context
    master_user = get_master_user_from_context(context)  # noqa: F841

    instrument = _safe_get_instrument(evaluator, instrument)
    pricing_policy = _safe_get_pricing_policy(evaluator, pricing_policy)

    result = None

    for policy in instrument.pricing_policies.all():
        if policy.pricing_policy.id == pricing_policy.id:
            result = policy

    return result


_get_instrument_pricing_scheme.evaluator = True


# DEPRECATED
def _get_currency_pricing_scheme(evaluator, currency, pricing_policy):
    from poms.users.utils import get_master_user_from_context

    context = evaluator.context
    master_user = get_master_user_from_context(context)  # noqa: F841

    currency = _safe_get_currency(evaluator, currency)
    pricing_policy = _safe_get_pricing_policy(evaluator, pricing_policy)

    result = None

    for policy in currency.pricing_policies.all():
        if policy.pricing_policy.id == pricing_policy.id:
            result = policy

    return result


_get_currency_pricing_scheme.evaluator = True


def _add_accrual_schedule(evaluator, instrument, data):
    from poms.instruments.models import AccrualCalculationSchedule
    from poms.instruments.serializers import AccrualCalculationScheduleSerializer
    from poms.users.utils import get_master_user_from_context

    context = evaluator.context
    master_user = get_master_user_from_context(context)  # noqa: F841

    instrument = _safe_get_instrument(evaluator, instrument)

    result = AccrualCalculationSchedule(instrument=instrument)

    if "accrual_start_date" in data:
        result.accrual_start_date = data["accrual_start_date"]

    if "accrual_end_date" in data:
        result.accrual_end_date = data["accrual_end_date"]

    if "first_payment_date" in data:
        result.first_payment_date = data["first_payment_date"]

    if "accrual_calculation_model" in data:
        result.accrual_calculation_model = _safe_get_accrual_calculation_model(
            evaluator, data["accrual_calculation_model"]
        )

    if "periodicity" in data:
        result.periodicity = _safe_get_periodicity(evaluator, data["periodicity"])

    if "periodicity_n" in data:
        result.periodicity_n = data["periodicity_n"]

    if "accrual_size" in data:
        result.accrual_size = float(data["accrual_size"])

    if "notes" in data:
        result.notes = data["notes"]

    result.save()

    return AccrualCalculationScheduleSerializer(result).data


_add_accrual_schedule.evaluator = True


def _delete_accrual_schedules(evaluator, instrument):
    from poms.users.utils import get_master_user_from_context

    context = evaluator.context
    master_user = get_master_user_from_context(context)  # noqa: F841

    instrument = _safe_get_instrument(evaluator, instrument)

    instrument.accrual_calculation_schedules.all().delete()


_delete_accrual_schedules.evaluator = True


def _add_event_schedule(evaluator, instrument, data):
    from poms.instruments.models import EventSchedule
    from poms.users.utils import get_master_user_from_context

    context = evaluator.context
    master_user = get_master_user_from_context(context)  # noqa: F841

    instrument = _safe_get_instrument(evaluator, instrument)

    result = EventSchedule(instrument=instrument)

    if "name" in data:
        result.name = data["name"]

    if "description" in data:
        result.description = data["description"]

    if "event_class" in data:
        result.event_class = _safe_get_event_class(evaluator, data["event_class"])

    if "notification_class" in data:
        result.notification_class = _safe_get_notification_class(evaluator, data["notification_class"])

    if "effective_date" in data:
        result.effective_date = data["effective_date"]

    if "notify_in_n_days" in data:
        result.notify_in_n_days = data["notify_in_n_days"]

    if "periodicity" in data:
        result.periodicity = _safe_get_periodicity(evaluator, data["periodicity"])

    if "periodicity_n" in data:
        result.periodicity_n = data["periodicity_n"]

    if "final_date" in data:
        result.final_date = data["final_date"]

    if "is_auto_generated" in data:
        result.is_auto_generated = data["is_auto_generated"]

    result.save()

    return result


_add_event_schedule.evaluator = True


def _delete_event_schedules(evaluator, instrument):
    from poms.users.utils import get_master_user_from_context

    context = evaluator.context
    master_user = get_master_user_from_context(context)  # noqa: F841

    instrument = _safe_get_instrument(evaluator, instrument)

    instrument.event_schedules.all().delete()


_delete_event_schedules.evaluator = True


def _safe_get_pricing_policy(evaluator, pricing_policy):
    from poms.instruments.models import PricingPolicy
    from poms.users.utils import get_master_user_from_context, get_member_from_context

    if isinstance(pricing_policy, PricingPolicy):
        return pricing_policy

    context = evaluator.context

    if context is None:
        raise InvalidExpression("Context must be specified")

    pk = None
    user_code = None

    if isinstance(pricing_policy, dict):
        pk = int(pricing_policy["id"])

    elif isinstance(pricing_policy, int | float):
        pk = int(pricing_policy)

    elif isinstance(pricing_policy, str):
        user_code = pricing_policy

    if id is None and user_code is None:
        raise ExpressionEvalError("Invalid pricing policy")

    master_user = get_master_user_from_context(context)
    member = get_member_from_context(context)  # noqa: F841

    if master_user is None:
        raise ExpressionEvalError("master user in context does not find")

    pricing_policy_qs = PricingPolicy.objects.filter(master_user=master_user)

    try:
        if pk is not None:
            pricing_policy = pricing_policy_qs.get(pk=pk)

        elif user_code is not None:
            pricing_policy = pricing_policy_qs.get(user_code=user_code)

    except PricingPolicy.DoesNotExist as e:
        raise ExpressionEvalError() from e

    return pricing_policy


def _safe_get_currency(evaluator, currency):
    from poms.currencies.models import Currency
    from poms.users.utils import get_master_user_from_context, get_member_from_context

    if isinstance(currency, Currency):
        return currency

    context = evaluator.context

    if context is None:
        raise InvalidExpression("Context must be specified")

    pk = None
    user_code = None

    if isinstance(currency, dict):
        pk = int(currency["id"])

    elif isinstance(currency, int | float):
        pk = int(currency)

    elif isinstance(currency, str):
        user_code = currency

    if id is None and user_code is None:
        raise ExpressionEvalError("Invalid currency")

    master_user = get_master_user_from_context(context)
    member = get_member_from_context(context)  # noqa: F841

    if master_user is None:
        raise ExpressionEvalError("master user in context does not find")

    currency_qs = Currency.objects.filter(master_user=master_user)

    try:
        if pk is not None:
            currency = currency_qs.get(pk=pk)

        elif user_code is not None:
            currency = currency_qs.get(user_code=user_code)

    except Currency.DoesNotExist as e:
        raise ExpressionEvalError() from e

    return currency


def _safe_get_account_type(evaluator, account_type):
    from poms.accounts.models import AccountType
    from poms.users.utils import get_master_user_from_context, get_member_from_context

    if isinstance(account_type, AccountType):
        return account_type

    context = evaluator.context

    if context is None:
        raise InvalidExpression("Context must be specified")

    pk = None
    user_code = None

    if isinstance(account_type, dict):
        pk = int(account_type["id"])

    elif isinstance(account_type, int | float):
        pk = int(account_type)

    elif isinstance(account_type, str):
        user_code = account_type

    if id is None and user_code is None:
        raise ExpressionEvalError("Invalid account type")

    master_user = get_master_user_from_context(context)
    member = get_member_from_context(context)  # noqa: F841

    if master_user is None:
        raise ExpressionEvalError("master user in context does not find")

    account_types_qs = AccountType.objects.filter(master_user=master_user)

    try:
        if pk is not None:
            account_type = account_types_qs.get(pk=pk)

        elif user_code is not None:
            account_type = account_types_qs.get(user_code=user_code)

    except AccountType.DoesNotExist as e:
        raise ExpressionEvalError() from e

    return account_type


def _safe_get_periodicity(evaluator, periodicity):
    from poms.instruments.models import Periodicity

    if isinstance(periodicity, Periodicity):
        return periodicity

    context = evaluator.context

    if context is None:
        raise InvalidExpression("Context must be specified")

    pk = None
    user_code = None

    if isinstance(periodicity, dict):
        pk = int(periodicity["id"])

    elif isinstance(periodicity, int | float):
        pk = int(periodicity)

    elif isinstance(periodicity, str):
        user_code = periodicity

    if pk is None and user_code is None:
        raise ExpressionEvalError("Invalid periodicity")

    try:
        if pk is not None:
            periodicity = Periodicity.objects.get(pk=pk)

        elif user_code is not None:
            periodicity = Periodicity.objects.get(user_code=user_code)

    except Periodicity.DoesNotExist as e:
        raise ExpressionEvalError() from e

    return periodicity


def _safe_get_notification_class(evaluator, notification_class):
    from poms.transactions.models import NotificationClass

    if isinstance(notification_class, NotificationClass):
        return notification_class

    context = evaluator.context

    if context is None:
        raise InvalidExpression("Context must be specified")

    pk = None
    user_code = None

    if isinstance(notification_class, dict):
        pk = int(notification_class["id"])

    elif isinstance(notification_class, int | float):
        pk = int(notification_class)

    elif isinstance(notification_class, str):
        user_code = notification_class

    if pk is None and user_code is None:
        raise ExpressionEvalError("Invalid notification_class")

    try:
        if pk is not None:
            notification_class = NotificationClass.objects.get(pk=pk)

        elif user_code is not None:
            notification_class = NotificationClass.objects.get(user_code=user_code)

    except NotificationClass.DoesNotExist as e:
        raise ExpressionEvalError() from e

    return notification_class


def _safe_get_event_class(evaluator, event_class):
    from poms.transactions.models import EventClass

    if isinstance(event_class, EventClass):
        return event_class

    context = evaluator.context

    if context is None:
        raise InvalidExpression("Context must be specified")

    pk = None
    user_code = None

    if isinstance(event_class, dict):
        pk = int(event_class["id"])

    elif isinstance(event_class, int | float):
        pk = int(event_class)

    elif isinstance(event_class, str):
        user_code = event_class

    if pk is None and user_code is None:
        raise ExpressionEvalError("Invalid event_class")

    try:
        if pk is not None:
            event_class = EventClass.objects.get(pk=pk)

        elif user_code is not None:
            event_class = EventClass.objects.get(user_code=user_code)

    except EventClass.DoesNotExist as e:
        raise ExpressionEvalError() from e

    return event_class


def _safe_get_accrual_calculation_model(evaluator, accrual_calculation_model):
    from poms.instruments.models import AccrualCalculationModel

    if isinstance(accrual_calculation_model, AccrualCalculationModel):
        return accrual_calculation_model

    context = evaluator.context

    if context is None:
        raise InvalidExpression("Context must be specified")

    pk = None
    user_code = None

    if isinstance(accrual_calculation_model, dict):
        pk = int(accrual_calculation_model["id"])

    elif isinstance(accrual_calculation_model, int | float):
        pk = int(accrual_calculation_model)

    elif isinstance(accrual_calculation_model, str):
        user_code = accrual_calculation_model

    if pk is None and user_code is None:
        raise ExpressionEvalError("Invalid accrual_calculation_model")

    try:
        if pk is not None:
            accrual_calculation_model = AccrualCalculationModel.objects.get(pk=pk)

        elif user_code is not None:
            accrual_calculation_model = AccrualCalculationModel.objects.get(user_code=user_code)

    except AccrualCalculationModel.DoesNotExist as e:
        raise ExpressionEvalError() from e

    return accrual_calculation_model


def _safe_get_instrument(evaluator, instrument, identifier_key=None):
    from poms.instruments.models import Instrument
    from poms.users.utils import get_master_user_from_context

    if isinstance(instrument, Instrument):
        return instrument

    context = evaluator.context

    if context is None:
        raise InvalidExpression("Context must be specified")

    pk = None
    user_code = None

    if identifier_key:
        query = {f"identifier__{identifier_key}": instrument}
        instrument = Instrument.objects.filter(**query).first()
        if instrument:
            return instrument

    if isinstance(instrument, dict):
        pk = int(instrument["id"])

    elif isinstance(instrument, int | float):
        pk = int(instrument)

    elif isinstance(instrument, str):
        user_code = instrument

    if id is None and user_code is None:
        raise ExpressionEvalError("Invalid instrument")

    if pk is not None:
        instrument = context.get(("_instrument_get_accrued_price", pk, None), None)

    elif user_code is not None:
        instrument = context.get(("_instrument_get_accrued_price", None, user_code), None)

    if instrument is None:
        master_user = get_master_user_from_context(context)
        if master_user is None:
            raise ExpressionEvalError("master user in context does not find")

        instrument_qs = Instrument.objects.filter(master_user=master_user)

        try:
            if pk is not None:
                instrument = instrument_qs.get(pk=pk)

            elif user_code is not None:
                instrument = instrument_qs.get(user_code=user_code)

        except Instrument.DoesNotExist as e:
            raise ExpressionEvalError() from e

        context[("_instrument_get_accrued_price", instrument.pk, None)] = instrument
        context[("_instrument_get_accrued_price", None, instrument.user_code)] = instrument

    return instrument


def _add_instrument_identifier(evaluator, instrument, identifier_key, value):
    """
    Adds or updates a key-value pair in the instrument's identifier JSON field.

    Args:
    instrument (Instrument): The Instrument instance to modify.
    key (str): The key to add or update in the identifier.
    value (str): The value to set for the key.
    """

    instrument = _safe_get_instrument(evaluator, instrument)

    context = evaluator.context  # noqa: F841

    if instrument.identifier is None:
        instrument.identifier = {}

    instrument.identifier[identifier_key] = value
    instrument.save()


_add_instrument_identifier.evaluator = True


def _remove_instrument_identifier(evaluator, instrument, identifier_key):
    """
    Removes a key from the instrument's identifier JSON field if it exists.

    Args:
    instrument (Instrument): The Instrument instance to modify.
    key (str): The key to remove from the identifier.
    """

    instrument = _safe_get_instrument(evaluator, instrument)

    context = evaluator.context  # noqa: F841

    if instrument.identifier and identifier_key in instrument.identifier:
        del instrument.identifier[identifier_key]
        instrument.save()


_remove_instrument_identifier.evaluator = True


def _safe_get_account(evaluator, account):
    from poms.accounts.models import Account
    from poms.users.utils import get_master_user_from_context

    if isinstance(account, Account):
        return account

    context = evaluator.context

    if context is None:
        raise InvalidExpression("Context must be specified")

    pk = None
    user_code = None

    if isinstance(account, dict):
        pk = int(account["id"])

    elif isinstance(account, int | float):
        pk = int(account)

    elif isinstance(account, str):
        user_code = account

    if id is None and user_code is None:
        raise ExpressionEvalError("Invalid account")

    master_user = get_master_user_from_context(context)
    if master_user is None:
        raise ExpressionEvalError("master user in context does not find")

    account_qs = Account.objects.filter(master_user=master_user)

    try:
        if pk is not None:
            account = account_qs.get(pk=pk)

        elif user_code is not None:
            account = account_qs.get(user_code=user_code)

    except Account.DoesNotExist as e:
        raise ExpressionEvalError() from e

    return account


def _get_currency(evaluator, currency):
    try:
        currency = _safe_get_currency(evaluator, currency)

        context = evaluator.context

        from poms.currencies.serializers import CurrencySerializer

        return CurrencySerializer(instance=currency, context=context).data
    except Exception:
        return None


_get_currency.evaluator = True


def _check_currency(evaluator, currency) -> dict | None:
    """
    Check if the given currency is valid and return its serialized data.

    Parameters:
    - evaluator: The evaluator object used for expression evaluation.
    - currency: The currency code to check.

    Returns:
    - Optional[dict]: The serialized data of the currency if it is valid, or None if it is not valid.
    """

    from poms.currencies.serializers import CurrencySerializer

    if isinstance(currency, str) and (len(currency) == 3 and currency.isupper() and currency.isalpha()):
        try:
            currency_obj = _safe_get_currency(evaluator, currency)

            context = evaluator.context
            return CurrencySerializer(instance=currency_obj, context=context).data
        except ExpressionEvalError:
            return {
                "id": None,
                "master_user": None,
                "user_code": currency,
                "name": currency,
                "short_name": currency,
                "notes": None,
                "reference_for_pricing": "",
                "pricing_condition": None,
                "default_fx_rate": None,
                "is_deleted": None,
                "is_enabled": None,
                "pricing_policies": None,
                "country": None,
            }
    return None


_check_currency.evaluator = True


def _get_account_type(evaluator, account_type):
    try:
        account_type = _safe_get_account_type(evaluator, account_type)

        context = evaluator.context

        from poms.accounts.serializers import AccountTypeSerializer

        return AccountTypeSerializer(instance=account_type, context=context).data
    except Exception:
        return None


_get_account_type.evaluator = True


def _set_account_user_attribute(evaluator, account, user_code, value):
    account = _safe_get_account(evaluator, account)

    try:
        for attribute in account.attributes.all():
            if attribute.attribute_type.user_code == user_code:
                if attribute.attribute_type.value_type == 10:
                    attribute.value_string = value

                elif attribute.attribute_type.value_type == 20:
                    attribute.value_float = value

                elif attribute.attribute_type.value_type == 30:
                    try:
                        from poms.obj_attrs.models import GenericClassifier

                        classifier = GenericClassifier.objects.get(attribute_type=attribute.attribute_type, name=value)

                        attribute.classifier = classifier

                    except Exception as e:
                        _l.error(f"Error setting classifier: {e}")
                        attribute.classifier = None

                elif attribute.attribute_type.value_type == 40:
                    attribute.value_date = value

                attribute.save()

        account.save()
    except Exception as e:
        _l.info("_set_account_user_attribute.e", e)
        _l.info("_set_account_user_attribute.traceback", traceback.print_exc())
        raise InvalidExpression("Invalid Property") from e


_set_account_user_attribute.evaluator = True


def _get_account_user_attribute(evaluator, account, user_code):
    try:
        account = _safe_get_account(evaluator, account)

        result = None
        for attribute in account.attributes.all():
            if attribute.attribute_type.user_code == user_code:
                if attribute.attribute_type.value_type == 10:
                    result = attribute.value_string

                elif attribute.attribute_type.value_type == 20:
                    result = attribute.value_float

                elif attribute.attribute_type.value_type == 30:
                    try:
                        result = attribute.classifier.name

                    except Exception:
                        result = None

                elif attribute.attribute_type.value_type == 40:
                    result = attribute.value_date

        return result

    except Exception as e:
        _l.error("e %s", e)
        return None


_get_account_user_attribute.evaluator = True


def _get_instrument(evaluator, instrument, identifier_key=None):
    try:
        instrument = _safe_get_instrument(evaluator, instrument, identifier_key)

        context = evaluator.context  # noqa: F841

        return instrument

    except Exception:
        return None


_get_instrument.evaluator = True


def _set_instrument_field(evaluator, instrument, parameter_name, parameter_value):
    context = evaluator.context  # noqa: F841

    instrument = _safe_get_instrument(evaluator, instrument)

    try:
        if isinstance(parameter_value, dict):
            parameter_name = parameter_name + "_id"
            parameter_value = parameter_value["id"]

        setattr(instrument, parameter_name, parameter_value)
        instrument.save()
    except AttributeError as e:
        raise InvalidExpression("Invalid Property") from e


_set_instrument_field.evaluator = True


def _set_instrument_user_attribute(evaluator, instrument, user_code, value):
    context = evaluator.context  # noqa: F841

    instrument = _safe_get_instrument(evaluator, instrument)

    try:
        for attribute in instrument.attributes.all():
            if attribute.attribute_type.user_code == user_code:
                if attribute.attribute_type.value_type == 10:
                    attribute.value_string = value

                elif attribute.attribute_type.value_type == 20:
                    attribute.value_float = value

                elif attribute.attribute_type.value_type == 30:
                    try:
                        from poms.obj_attrs.models import GenericClassifier

                        classifier = GenericClassifier.objects.get(attribute_type=attribute.attribute_type, name=value)

                        attribute.classifier = classifier

                    except Exception as e:
                        _l.error("Error setting classifier: %s", e)
                        attribute.classifier = None

                elif attribute.attribute_type.value_type == 40:
                    attribute.value_date = value

                attribute.save()

        instrument.save()
    except AttributeError as e:
        raise InvalidExpression("Invalid Property") from e


_set_instrument_user_attribute.evaluator = True


def _get_instrument_user_attribute(evaluator, instrument, user_code):
    from poms.obj_attrs.models import GenericClassifier

    try:
        instrument = _safe_get_instrument(evaluator, instrument)

        result = None
        for attribute in instrument.attributes.all():
            if attribute.attribute_type.user_code == user_code:
                if attribute.attribute_type.value_type == 10:
                    result = attribute.value_string

                elif attribute.attribute_type.value_type == 20:
                    result = attribute.value_float

                elif attribute.attribute_type.value_type == 30:
                    try:
                        classifier = GenericClassifier.objects.get(
                            attribute_type=attribute.attribute_type,
                            # name=value,  # FIXME undefined value!
                        )
                        result = classifier.name

                    except Exception:
                        result = None

                elif attribute.attribute_type.value_type == 40:
                    result = attribute.value_date

        return result

    except Exception:
        return None


_get_instrument_user_attribute.evaluator = True


def _set_currency_field(evaluator, currency, parameter_name, parameter_value):
    context = evaluator.context  # noqa: F841

    currency = _safe_get_currency(evaluator, currency)

    try:
        setattr(currency, parameter_name, parameter_value)
        currency.save()
    except AttributeError as e:
        raise InvalidExpression("Invalid Property") from e


_set_currency_field.evaluator = True


def _get_instrument_field(evaluator, instrument, parameter_name):
    context = evaluator.context  # noqa: F841

    instrument = _safe_get_instrument(evaluator, instrument)

    result = None

    try:
        result = getattr(instrument, parameter_name, None)
    except AttributeError as e:
        raise InvalidExpression("Invalid Property") from e

    return result


_get_instrument_field.evaluator = True


def _get_currency_field(evaluator, currency, parameter_name):
    context = evaluator.context  # noqa: F841

    currency = _safe_get_currency(evaluator, currency)

    result = None

    try:
        result = getattr(currency, parameter_name, None)
    except AttributeError as e:
        raise InvalidExpression("Invalid Property") from e

    return result


_get_currency_field.evaluator = True


def _get_instrument_user_attribute_value(evaluator, instrument, attribute_user_code):
    from django.contrib.contenttypes.models import ContentType

    from poms.instruments.models import Instrument
    from poms.obj_attrs.models import GenericAttribute, GenericAttributeType
    from poms.users.utils import get_master_user_from_context

    # print('formula instrument %s' % instrument)
    # print('formula attribute_user_code %s' % attribute_user_code)

    if isinstance(instrument, Instrument):
        return instrument

    context = evaluator.context

    if context is None:
        raise InvalidExpression("Context must be specified")

    if attribute_user_code is None:
        raise InvalidExpression("User code is not set")

    pk = None

    master_user = get_master_user_from_context(context)

    if isinstance(instrument, dict):
        pk = int(instrument["id"])

    elif isinstance(instrument, int | float):
        pk = int(instrument)

    elif isinstance(instrument, str):
        pk = Instrument.objects.get(master_user=master_user, user_code=instrument).id

    # print('formula pk %s' % pk)

    if pk is None:
        raise ExpressionEvalError("Invalid instrument")

    attribute_type = None
    attribute = None

    try:
        attribute_type = GenericAttributeType.objects.get(
            master_user=master_user,
            user_code=attribute_user_code,
            content_type=ContentType.objects.get(app_label="instruments", model="instrument"),
        )
    except GenericAttributeType.DoesNotExist as e:
        raise ExpressionEvalError("Attribute type is not found") from e

    # print('formula attribute_type %s ' % attribute_type)

    try:
        attribute = GenericAttribute.objects.get(
            attribute_type=attribute_type,
            object_id=pk,
            content_type=ContentType.objects.get(app_label="instruments", model="instrument"),
        )
    except GenericAttribute.DoesNotExist as e:
        raise ExpressionEvalError("Attribute is not found") from e

    # print('formula attribute %s' % attribute)

    if attribute_type.value_type == GenericAttributeType.STRING:
        return attribute.value_string

    if attribute_type.value_type == GenericAttributeType.NUMBER:
        return attribute.value_float

    if attribute_type.value_type == GenericAttributeType.CLASSIFIER:
        if attribute.classifier:
            return attribute.classifier.name
        else:
            raise ExpressionEvalError("Classifier is not exist")

    if attribute_type.value_type == GenericAttributeType.DATE:
        return attribute.value_date


_get_instrument_user_attribute_value.evaluator = True


def _calculate_accrued_price(evaluator, instrument, date):
    if instrument is None or date is None:
        return 0.0
    instrument = _safe_get_instrument(evaluator, instrument)
    date = _parse_date(date)
    val = instrument.get_accrued_price(date)
    return _check_float(val)


_calculate_accrued_price.evaluator = True


def _get_position_size_on_date(evaluator, instrument, date, accounts=None, portfolios=None):
    from poms.transactions.models import Transaction
    from poms.users.utils import get_master_user_from_context

    try:
        result = 0

        context = evaluator.context

        master_user = get_master_user_from_context(context)

        instrument = _safe_get_instrument(evaluator, instrument)
        date = _parse_date(date)

        from poms.transactions.models import TransactionClass

        # Transfer is deprecated, but for now still in use
        # szhitenev 2024-02-12
        transactions = Transaction.objects.filter(
            master_user=master_user,
            accounting_date__lte=date,
            instrument=instrument,
            transaction_class_id__in=[
                TransactionClass.BUY,
                TransactionClass.SELL,
                TransactionClass.TRANSFER,
            ],
        )

        if accounts:
            transactions = transactions.filter(account_position__in=accounts)

        # _l.info('portfolios %s' % type(portfolios))

        if portfolios:
            transactions = transactions.filter(portfolio__in=portfolios)

        # _l.info('transactions %s ' % transactions)

        for trn in transactions:
            result = result + trn.position_size_with_sign

        return result

    except Exception as e:
        _l.error("_get_position_size_on_date exception occurred %s", e)
        _l.error(traceback.format_exc())
        return 0


_get_position_size_on_date.evaluator = True


def _get_principal_on_date(
    evaluator,
    instrument,
    date,
    report_currency=None,
    pricing_policy=None,
    accounts=None,
    portfolios=None,
):
    from poms.currencies.models import CurrencyHistory
    from poms.transactions.models import Transaction, TransactionClass
    from poms.users.utils import get_master_user_from_context

    try:
        result = 0

        context = evaluator.context

        master_user = get_master_user_from_context(context)

        instrument = _safe_get_instrument(evaluator, instrument)
        date = _parse_date(date)

        master_user = get_master_user_from_context(context)

        from poms.users.models import EcosystemDefault

        ecosystem_default = EcosystemDefault.cache.get_cache(master_user_pk=master_user.pk)

        if report_currency:
            report_currency = _safe_get_currency(evaluator, report_currency)
        else:
            report_currency = _safe_get_currency(evaluator, instrument.pricing_currency)

        if pricing_policy:
            pricing_policy = _safe_get_pricing_policy(evaluator, pricing_policy)
        else:
            pricing_policy = ecosystem_default.pricing_policy

        default_currency_id = ecosystem_default.currency_id

        # Transfer is deprecated, but for now still in use
        # szhitenev 2024-02-12

        transactions = Transaction.objects.filter(
            master_user=master_user,
            accounting_date__lte=date,
            instrument=instrument,
            transaction_class_id__in=[
                TransactionClass.BUY,
                TransactionClass.SELL,
                TransactionClass.TRANSFER,
            ],
        )

        if accounts:
            transactions = transactions.filter(account_position__in=accounts)

        # _l.info('portfolios %s' % type(portfolios))

        if portfolios:
            transactions = transactions.filter(portfolio__in=portfolios)

        # _l.info('transactions %s ' % transactions)

        for trn in transactions:
            result_principal = 0

            try:
                if trn.transaction_currency_id == report_currency.id:
                    result_principal = trn.principal_with_sign * trn.reference_fx_rate
                else:
                    if trn.transaction_currency_id == default_currency_id:
                        trn_currency_fx_rate = 1
                    else:
                        trn_currency_fx_rate = CurrencyHistory.objects.get(
                            currency_id=trn.transaction_currency_id,
                            pricing_policy=pricing_policy,
                            date=date,
                        ).fx_rate

                    if report_currency.id == default_currency_id:
                        report_currency_fx_rate = 1
                    else:
                        report_currency_fx_rate = CurrencyHistory.objects.get(
                            currency_id=report_currency.id,
                            pricing_policy=pricing_policy,
                            date=date,
                        ).fx_rate

                    result_principal = (
                        trn.principal_with_sign
                        * trn.reference_fx_rate
                        * trn_currency_fx_rate
                        / report_currency_fx_rate
                    )

                result = result + result_principal

            except Exception as e:
                _l.error("Could not fetch fx rate %s", e)
                raise Exception("Could not calculate principal, missing FX Rates") from e

        return result

    except Exception as e:
        _l.error("_get_principal_on_date exception occurred %s", e)
        _l.error(traceback.format_exc())
        return 0


_get_principal_on_date.evaluator = True


def _get_principal_on_date(
    evaluator,
    instrument,
    date,
    report_currency=None,
    pricing_policy=None,
    accounts=None,
    portfolios=None,
):
    from poms.currencies.models import CurrencyHistory
    from poms.transactions.models import Transaction, TransactionClass
    from poms.users.utils import get_master_user_from_context

    try:
        result = 0

        context = evaluator.context

        master_user = get_master_user_from_context(context)

        instrument = _safe_get_instrument(evaluator, instrument)
        date = _parse_date(date)

        master_user = get_master_user_from_context(context)

        from poms.users.models import EcosystemDefault

        ecosystem_default = EcosystemDefault.cache.get_cache(master_user_pk=master_user.pk)

        if report_currency:
            report_currency = _safe_get_currency(evaluator, report_currency)
        else:
            report_currency = _safe_get_currency(evaluator, instrument.pricing_currency)

        if pricing_policy:
            pricing_policy = _safe_get_pricing_policy(evaluator, pricing_policy)
        else:
            pricing_policy = ecosystem_default.pricing_policy

        default_currency_id = ecosystem_default.currency_id

        # Transfer is deprecated, but for now still in use
        # szhitenev 2024-02-12

        transactions = Transaction.objects.filter(
            master_user=master_user,
            accounting_date__lte=date,
            instrument=instrument,
            transaction_class_id__in=[
                TransactionClass.BUY,
                TransactionClass.SELL,
                TransactionClass.TRANSFER,
            ],
        )

        if accounts:
            transactions = transactions.filter(account_position__in=accounts)

        # _l.info('portfolios %s' % type(portfolios))

        if portfolios:
            transactions = transactions.filter(portfolio__in=portfolios)

        # _l.info('transactions %s ' % transactions)

        for trn in transactions:
            result_principal = 0

            try:
                if trn.transaction_currency_id == report_currency.id:
                    result_principal = trn.principal_with_sign * trn.reference_fx_rate
                else:
                    if trn.transaction_currency_id == default_currency_id:
                        trn_currency_fx_rate = 1
                    else:
                        trn_currency_fx_rate = CurrencyHistory.objects.get(
                            currency_id=trn.transaction_currency_id,
                            pricing_policy=pricing_policy,
                            date=date,
                        ).fx_rate

                    if report_currency.id == default_currency_id:
                        report_currency_fx_rate = 1
                    else:
                        report_currency_fx_rate = CurrencyHistory.objects.get(
                            currency_id=report_currency.id,
                            pricing_policy=pricing_policy,
                            date=date,
                        ).fx_rate

                    result_principal = (
                        trn.principal_with_sign
                        * trn.reference_fx_rate
                        * trn_currency_fx_rate
                        / report_currency_fx_rate
                    )

                result = result + result_principal

            except Exception as e:
                _l.error("Could not fetch fx rate %s", e)
                raise Exception("Could not calculate principal, missing FX Rates") from e

        return result

    except Exception as e:
        _l.error("_get_principal_on_date exception occurred %s", e)
        _l.error(traceback.format_exc())
        return 0


_get_principal_on_date.evaluator = True


def _get_transactions_amounts_on_date(  # noqa: PLR0912, PLR0915
    evaluator,
    instrument,
    date,
    report_currency=None,
    pricing_policy=None,
    accounts_position=None,
    accounts_cash=None,
    portfolios=None,
):
    from poms.currencies.models import CurrencyHistory
    from poms.transactions.models import Transaction, TransactionClass
    from poms.users.utils import get_master_user_from_context

    result = {
        "position_size_with_sign": 0,
        "principal_with_sign": 0,
        "carry_with_sign": 0,
        "overheads_with_sign": 0,
        "cash_consideration": 0,
    }

    try:
        context = evaluator.context

        master_user = get_master_user_from_context(context)

        instrument = _safe_get_instrument(evaluator, instrument)
        date = _parse_date(date)

        master_user = get_master_user_from_context(context)

        from poms.users.models import EcosystemDefault

        ecosystem_default = EcosystemDefault.cache.get_cache(master_user_pk=master_user.pk)

        if report_currency:
            report_currency = _safe_get_currency(evaluator, report_currency)
        else:
            report_currency = _safe_get_currency(evaluator, instrument.pricing_currency)

        if pricing_policy:
            pricing_policy = _safe_get_pricing_policy(evaluator, pricing_policy)
        else:
            pricing_policy = ecosystem_default.pricing_policy

        default_currency_id = ecosystem_default.currency_id

        # Transfer is deprecated, but for now still in use
        # szhitenev 2024-02-12

        transactions = Transaction.objects.filter(
            master_user=master_user,
            accounting_date__lte=date,
            instrument=instrument,
            transaction_class_id__in=[
                TransactionClass.BUY,
                TransactionClass.SELL,
                TransactionClass.TRANSFER,
            ],
        )

        if accounts_position and len(accounts_position):
            transactions = transactions.filter(account_position__user_code__in=accounts_position)

        if accounts_cash and len(accounts_cash):
            transactions = transactions.filter(account_cash__user_code__in=accounts_cash)

        # _l.info('portfolios %s' % type(portfolios))

        if portfolios:
            transactions = transactions.filter(portfolio__user_code__in=portfolios)

        # _l.info('transactions %s ' % transactions)

        for trn in transactions:
            result_position_size = 0
            result_principal = 0
            result_carry = 0
            result_overheads = 0
            cash_consideration = 0  # noqa: F841

            try:
                if trn.transaction_currency_id == report_currency.id:
                    result_position_size = trn.position_size_with_sign
                    result_principal = trn.principal_with_sign * trn.reference_fx_rate
                    result_carry = trn.carry_with_sign * trn.reference_fx_rate
                    result_overheads = trn.overheads_with_sign * trn.reference_fx_rate
                    result_cash_consideration = trn.cash_consideration * trn.reference_fx_rate
                else:
                    if trn.transaction_currency_id == default_currency_id:
                        trn_currency_fx_rate = 1
                    else:
                        trn_currency_fx_rate = CurrencyHistory.objects.get(
                            currency_id=trn.transaction_currency_id,
                            pricing_policy=pricing_policy,
                            date=date,
                        ).fx_rate

                    if report_currency.id == default_currency_id:
                        report_currency_fx_rate = 1
                    else:
                        report_currency_fx_rate = CurrencyHistory.objects.get(
                            currency_id=report_currency.id,
                            pricing_policy=pricing_policy,
                            date=date,
                        ).fx_rate

                    result_position_size = trn.position_size_with_sign
                    result_principal = (
                        trn.principal_with_sign
                        * trn.reference_fx_rate
                        * trn_currency_fx_rate
                        / report_currency_fx_rate
                    )
                    result_carry = (
                        trn.carry_with_sign * trn.reference_fx_rate * trn_currency_fx_rate / report_currency_fx_rate
                    )
                    result_overheads = (
                        trn.overheads_with_sign
                        * trn.reference_fx_rate
                        * trn_currency_fx_rate
                        / report_currency_fx_rate
                    )
                    result_cash_consideration = (
                        trn.cash_consideration * trn.reference_fx_rate * trn_currency_fx_rate / report_currency_fx_rate
                    )

                result["position_size_with_sign"] = result["position_size_with_sign"] + result_position_size
                result["principal_with_sign"] = result["principal_with_sign"] + result_principal
                result["carry_with_sign"] = result["carry_with_sign"] + result_carry
                result["overheads_with_sign"] = result["overheads_with_sign"] + result_overheads
                result["cash_consideration"] = result["cash_consideration"] + result_cash_consideration

            except Exception as e:
                _l.error("Could not fetch fx rate %s", e)
                raise Exception(f"Could not calculate amounts {e}") from e

        return result

    except Exception as e:
        _l.error("_get_principal_on_date exception occurred %s", e)
        _l.error(traceback.format_exc())
        return result


_get_transactions_amounts_on_date.evaluator = True


def _get_net_cost_price_on_date(evaluator, instrument, date, accounts=None, portfolios=None):
    from poms.transactions.models import Transaction, TransactionClass
    from poms.users.utils import get_master_user_from_context

    try:
        result = 0

        context = evaluator.context

        master_user = get_master_user_from_context(context)

        instrument = _safe_get_instrument(evaluator, instrument)
        date = _parse_date(date)

        # Transfer is deprecated, but for now still in use
        # szhitenev 2024-02-12

        transactions = Transaction.objects.filter(
            master_user=master_user,
            accounting_date__lte=date,
            instrument=instrument,
            transaction_class_id__in=[
                TransactionClass.BUY,
                TransactionClass.SELL,
                TransactionClass.TRANSFER,
            ],
        )

        if accounts:
            transactions = transactions.filter(account_position__in=accounts)

        # _l.info('portfolios %s' % type(portfolios))

        if portfolios:
            transactions = transactions.filter(portfolio__in=portfolios)

        # _l.info('transactions %s ' % transactions)

        total_principal = 0
        total_position = 0

        for trn in transactions:
            total_principal = total_principal + trn.principal_with_sign
            total_position = total_position + trn.position_size_with_sign

        if total_position != 0:
            result = total_principal / total_position

            result = result * -1  # get price with the right sign

        return result

    except Exception as e:
        _l.error("_get_net_cost_price_on_date exception occurred %s", e)
        _l.error(traceback.format_exc())
        return 0


_get_net_cost_price_on_date.evaluator = True


def _get_instrument_report_data(
    evaluator,
    instrument,
    report_date,
    report_currency=None,
    pricing_policy=None,
    cost_method="AVCO",
    accounts=None,
    portfolios=None,
):
    from poms.reports.common import Report
    from poms.reports.serializers import BalanceReportSerializer
    from poms.reports.sql_builders.balance import BalanceReportBuilderSql
    from poms.users.models import EcosystemDefault
    from poms.users.utils import get_master_user_from_context, get_member_from_context

    try:
        result = 0

        context = evaluator.context

        master_user = get_master_user_from_context(context)
        member = get_member_from_context(context)

        instrument = _safe_get_instrument(evaluator, instrument)

        ecosystem_default = EcosystemDefault.cache.get_cache(master_user_pk=master_user.pk)

        currency = _safe_get_currency(evaluator, report_currency)
        if pricing_policy:
            pricing_policy = _safe_get_pricing_policy(evaluator, pricing_policy)
        else:
            pricing_policy = ecosystem_default.pricing_policy

        from poms.instruments.models import CostMethod

        cost_method = CostMethod.objects.get(user_code=cost_method)

        _l.info("_calculate_balance_report master_user %s", master_user)
        _l.info("_calculate_balance_report member %s", member)
        _l.info("_calculate_balance_report report_date  %s", report_date)
        _l.info("_calculate_balance_report currency %s", currency)

        report_date_d = datetime.datetime.strptime(report_date, "%Y-%m-%d").date()

        from poms.accounts.models import Account
        from poms.portfolios.models import Portfolio

        portfolios_instances = []
        accounts_instances = []

        if portfolios:
            for portfolio in portfolios:
                portfolios_instances.append(Portfolio.objects.get(master_user=master_user, user_code=portfolio))

        if accounts:
            for account in accounts:
                accounts_instances.append(Account.objects.get(master_user=master_user, user_code=account))

        instance = Report(
            master_user=master_user,
            member=member,
            report_currency=currency,
            report_date=report_date_d,
            cost_method=cost_method,
            portfolios=portfolios_instances,
            accounts=accounts_instances,
            pricing_policy=pricing_policy,
            custom_fields=[],
            save_report=True,
        )

        builder = BalanceReportBuilderSql(instance=instance)
        instance = builder.build_balance()

        serializer = BalanceReportSerializer(instance=instance, context=context)

        data = serializer.to_representation(instance)

        for item in data["items"]:
            if item["instrument"] == instrument.id:
                result = item

        return result

    except Exception as e:
        _l.error("_get_instrument_report_data exception occurred %s", e)
        _l.error(traceback.format_exc())
        return 0


_get_instrument_report_data.evaluator = True


def _get_instrument_accrual_size(evaluator, instrument, date):
    if instrument is None or date is None:
        return 0.0
    instrument = _safe_get_instrument(evaluator, instrument)
    date = _parse_date(date)
    val = instrument.get_accrual_size(date)
    return _check_float(val)


_get_instrument_accrual_size.evaluator = True


def _get_instrument_accrual_factor(evaluator, instrument, date):
    if instrument is None or date is None:
        return 0.0
    instrument = _safe_get_instrument(evaluator, instrument)
    date = _parse_date(date)
    val = instrument.get_accrual_schedule_factor(date)
    return _check_float(val)


_get_instrument_accrual_factor.evaluator = True


def _get_instrument_coupon(evaluator, instrument, date):
    try:
        _l.info("_get_instrument_coupon instrument %s", instrument)
        _l.info("_get_instrument_coupon date %s", date)

        if instrument is None or date is None:
            return 0.0
        instrument = _safe_get_instrument(evaluator, instrument)
        date = _parse_date(date)
        cpn_val, is_cpn = instrument.get_coupon(date, with_maturity=False)

        _l.info("_get_instrument_coupon cpn_val %s", cpn_val)

        return _check_float(cpn_val)

    except Exception as e:
        _l.info("_get_instrument_coupon exception occurred %s", e)
        _l.info(traceback.format_exc())
        return 0.0


_get_instrument_coupon.evaluator = True


def _get_instrument_coupon_factor(evaluator, instrument, date):
    if instrument is None or date is None:
        return 0.0
    instrument = _safe_get_instrument(evaluator, instrument)
    date = _parse_date(date)
    cpn_val, is_cpn = instrument.get_coupon(date, with_maturity=False, factor=True)
    return _check_float(cpn_val)


_get_instrument_coupon_factor.evaluator = True


def _get_instrument_factor(evaluator, instrument, date):
    if instrument is None or date is None:
        return 0.0
    instrument = _safe_get_instrument(evaluator, instrument)
    date = _parse_date(date)
    return instrument.get_factor(date)


_get_instrument_factor.evaluator = True


def _get_rt_value(evaluator, key, table_name, default=None):
    from poms.users.utils import get_master_user_from_context

    context = evaluator.context

    master_user = get_master_user_from_context(context)

    from poms.reference_tables.models import ReferenceTable, ReferenceTableRow

    try:
        table = ReferenceTable.objects.get(master_user=master_user, name=table_name)

        try:
            row = ReferenceTableRow.objects.get(reference_table=table, key=key)

            return row.value

        except ReferenceTableRow.DoesNotExist:
            return default

    except ReferenceTable.DoesNotExist:
        print("_get_rt_value error")

    return default


_get_rt_value.evaluator = True


def _get_default_portfolio(evaluator):
    from poms.users.utils import get_master_user_from_context

    context = evaluator.context

    master_user = get_master_user_from_context(context)

    from poms.users.models import EcosystemDefault

    try:
        item = EcosystemDefault.cache.get_cache(master_user_pk=master_user.pk)

        return item.portfolio

    except Exception as e:
        print(f"get_default_portfolio error {e}")

    return None


_get_default_portfolio.evaluator = True


def _get_default_instrument(evaluator):
    from poms.users.utils import get_master_user_from_context

    context = evaluator.context

    master_user = get_master_user_from_context(context)

    from poms.users.models import EcosystemDefault

    try:
        item = EcosystemDefault.cache.get_cache(master_user_pk=master_user.pk)

        return item.instrument

    except Exception as e:
        print(f"get_default_instrument error {e}")

    return None


_get_default_instrument.evaluator = True


def _get_default_account(evaluator):
    from poms.users.utils import get_master_user_from_context

    context = evaluator.context

    master_user = get_master_user_from_context(context)

    from poms.users.models import EcosystemDefault

    try:
        item = EcosystemDefault.cache.get_cache(master_user_pk=master_user.pk)

        return item.account

    except Exception as e:
        print(f"get_default_account error {e}")

    return None


_get_default_account.evaluator = True


def _get_default_currency(evaluator):
    from poms.users.utils import get_master_user_from_context

    context = evaluator.context

    master_user = get_master_user_from_context(context)

    from poms.users.models import EcosystemDefault

    try:
        item = EcosystemDefault.cache.get_cache(master_user_pk=master_user.pk)

        return item.currency

    except Exception as e:
        print(f"get_default_currency error {e}")

    return None


_get_default_currency.evaluator = True


def _get_default_transaction_type(evaluator):
    from poms.users.utils import get_master_user_from_context

    context = evaluator.context

    master_user = get_master_user_from_context(context)

    from poms.users.models import EcosystemDefault

    try:
        item = EcosystemDefault.cache.get_cache(master_user_pk=master_user.pk)

        return item.transaction_type

    except Exception as e:
        print(f"get_default_transaction_type error {e}")

    return None


_get_default_transaction_type.evaluator = True


def _get_default_instrument_type(evaluator):
    from poms.users.utils import get_master_user_from_context

    context = evaluator.context

    master_user = get_master_user_from_context(context)

    from poms.users.models import EcosystemDefault

    try:
        item = EcosystemDefault.cache.get_cache(master_user_pk=master_user.pk)

        return item.instrument_type

    except Exception as e:
        print(f"get_default_instrument_type error {e}")

    return None


_get_default_instrument_type.evaluator = True


def _get_default_account_type(evaluator):
    from poms.users.utils import get_master_user_from_context

    context = evaluator.context

    master_user = get_master_user_from_context(context)

    from poms.users.models import EcosystemDefault

    try:
        item = EcosystemDefault.cache.get_cache(master_user_pk=master_user.pk)

        return item.account_type

    except Exception as e:
        print(f"get_default_account_type error {e}")

    return None


_get_default_account_type.evaluator = True


def _get_default_pricing_policy(evaluator):
    from poms.users.utils import get_master_user_from_context

    context = evaluator.context

    master_user = get_master_user_from_context(context)

    from poms.users.models import EcosystemDefault

    try:
        item = EcosystemDefault.cache.get_cache(master_user_pk=master_user.pk)

        return item.pricing_policy

    except Exception as e:
        print(f"get_default_pricing_policy error {e}")

    return None


_get_default_pricing_policy.evaluator = True


def _get_default_responsible(evaluator):
    from poms.users.utils import get_master_user_from_context

    context = evaluator.context

    master_user = get_master_user_from_context(context)

    from poms.users.models import EcosystemDefault

    try:
        item = EcosystemDefault.cache.get_cache(master_user_pk=master_user.pk)

        return item.responsible

    except Exception as e:
        print("get_default_responsible error %s", e)

    return None


_get_default_responsible.evaluator = True


def _get_default_counterparty(evaluator):
    from poms.users.utils import get_master_user_from_context

    context = evaluator.context

    master_user = get_master_user_from_context(context)

    from poms.users.models import EcosystemDefault

    try:
        item = EcosystemDefault.cache.get_cache(master_user_pk=master_user.pk)

        return item.counterparty

    except Exception as e:
        print("get_default_counterparty error %s", e)

    return None


_get_default_counterparty.evaluator = True


def _get_default_strategy1(evaluator):
    from poms.users.utils import get_master_user_from_context

    context = evaluator.context

    master_user = get_master_user_from_context(context)

    from poms.users.models import EcosystemDefault

    try:
        item = EcosystemDefault.cache.get_cache(master_user_pk=master_user.pk)

        return item.strategy1

    except Exception as e:
        print("get_default_strategy1 error %s", e)

    return None


_get_default_strategy1.evaluator = True


def _get_default_strategy2(evaluator):
    from poms.users.utils import get_master_user_from_context

    context = evaluator.context

    master_user = get_master_user_from_context(context)

    from poms.users.models import EcosystemDefault

    try:
        item = EcosystemDefault.cache.get_cache(master_user_pk=master_user.pk)

        return item.strategy2

    except Exception as e:
        print("get_default_strategy2 error %s", e)

    return None


_get_default_strategy2.evaluator = True


def _get_default_strategy3(evaluator):
    from poms.users.utils import get_master_user_from_context

    context = evaluator.context

    master_user = get_master_user_from_context(context)

    from poms.users.models import EcosystemDefault

    try:
        item = EcosystemDefault.cache.get_cache(master_user_pk=master_user.pk)

        return item.strategy3

    except Exception as e:
        print("get_default_strategy3 error %s", e)

    return None


_get_default_strategy3.evaluator = True


def _create_task(
    evaluator,
    name,
    type="user_task",
    options=None,
    function_name=None,
    notes=None,
    **kwargs,
):
    _l.info(f"_create_task task_name: {name}")

    try:
        from poms.celery_tasks.models import CeleryTask

        context = evaluator.context
        from poms.users.utils import (
            get_master_user_from_context,
            get_member_from_context,
        )

        master_user = get_master_user_from_context(context)
        member = get_member_from_context(context)

        celery_task = CeleryTask.objects.create(
            master_user=master_user,
            member=member,
            verbose_name=name,
            function_name=function_name,
            type=type,
        )

        celery_task.options_object = options
        celery_task.save()

        return celery_task.id

    except Exception as e:
        _l.debug(f"_create_task.exception {e}")


_create_task.evaluator = True


def _update_task(
    evaluator,
    id,
    name,
    type=None,
    status="P",
    options=None,
    notes=None,
    error_message=None,
    result=None,
    **kwargs,
):
    _l.info("_create_task task_name: %s", name)

    try:
        from poms.celery_tasks.models import CeleryTask

        context = evaluator.context  # noqa: F841

        celery_task = CeleryTask.objects.get(id=id)

        celery_task.type = type
        if notes:
            celery_task.notes = notes
        if error_message:
            celery_task.error_message = error_message
        if status:
            celery_task.status = status
        if options:
            celery_task.options_object = options
        if result:
            celery_task.result_object = result
        celery_task.save()

        return celery_task.id

    except Exception as e:
        _l.debug("_create_task.exception %s", e)


_update_task.evaluator = True


def _run_task(evaluator, task_name, options=None):
    from poms_app import celery_app

    if options is None:
        options = {}

    _l.info("_run_task task_name: %s", task_name)

    try:
        context = evaluator.context
        from poms.users.utils import (
            get_master_user_from_context,
            get_member_from_context,
        )

        master_user = get_master_user_from_context(context)
        member = get_member_from_context(context)

        from poms.celery_tasks.models import CeleryTask

        task = CeleryTask.objects.create(
            master_user=master_user,
            member=member,
            type=task_name,
            options_object=options,
        )

        celery_app.send_task(
            task_name,
            kwargs={
                "task_id": task.id,
                "context": {
                    "realm_code": task.realm_code,
                    "space_code": task.space_code,
                },
            },
        )

    except Exception as e:
        _l.error(f"_run_task err {e} trace {traceback.format_exc()}")


_run_task.evaluator = True


def _run_pricing_procedure(evaluator, user_code, **kwargs):
    try:
        from poms.pricing.handlers import PricingProcedureProcess  # FIXME no such class
        from poms.procedures.models import PricingProcedure
        from poms.users.utils import (
            get_master_user_from_context,
            get_member_from_context,
        )

        context = evaluator.context

        master_user = get_master_user_from_context(context)
        member = get_member_from_context(context)

        procedure = PricingProcedure.objects.get(master_user=master_user, user_code=user_code)

        instance = PricingProcedureProcess(procedure=procedure, master_user=master_user, member=member, **kwargs)
        instance.process()

    except Exception as e:
        _l.debug(f"_run_pricing_procedure.exception {e}")
        raise e


_run_pricing_procedure.evaluator = True


def _run_data_procedure(evaluator, user_code, user_context=None, linked_task_kwargs=None, **kwargs):
    _l.info("_run_data_procedure")

    try:
        from poms.procedures.tasks import run_data_procedure_from_formula
        from poms.users.utils import (
            get_master_user_from_context,
            get_member_from_context,
        )

        context = evaluator.context

        master_user = get_master_user_from_context(context)
        member = get_member_from_context(context)

        _l.info("_run_data_procedure.context %s", context)

        procedure_kwargs = {
            "master_user_id": master_user.id,
            "member_id": member.id,
            "user_code": user_code,
            "user_context": user_context,
            "context": {
                "space_code": master_user.space_code,
                "realm_code": master_user.realm_code,
            },
        }
        procedure_kwargs.update(kwargs)

        link = []

        if linked_task_kwargs:
            # TODO maybe should append mode here
            linked_task_kwargs["context"] = {
                "space_code": master_user.space_code,
                "realm_code": master_user.realm_code,
            }

            link = [run_data_procedure_from_formula.apply_async(kwargs=linked_task_kwargs)]

        run_data_procedure_from_formula.apply_async(kwargs=procedure_kwargs, link=link)

    except Exception as e:
        _l.error("_run_data_procedure.exception %s", e)
        _l.error("_run_data_procedure.exception traceback %s", traceback.format_exc())
        raise Exception(e) from e


_run_data_procedure.evaluator = True


def _run_data_procedure_sync(evaluator, user_code, user_context=None, **kwargs):
    _l.info("_run_data_procedure_sync")

    try:
        from poms.procedures.handlers import DataProcedureProcess
        from poms.procedures.models import RequestDataFileProcedure
        from poms.users.utils import (
            get_master_user_from_context,
            get_member_from_context,
        )

        context = evaluator.context

        master_user = get_master_user_from_context(context)
        member = get_member_from_context(context)

        merged_context = {}
        merged_context.update(context)

        if "names" not in merged_context:
            merged_context["names"] = {}

        if user_context:
            merged_context["names"].update(user_context)

        _l.info("merged_context %s", merged_context)

        procedure = RequestDataFileProcedure.objects.get(master_user=master_user, user_code=user_code)

        kwargs.pop("user_context", None)

        instance = DataProcedureProcess(
            procedure=procedure,
            master_user=master_user,
            member=member,
            context=merged_context,
            **kwargs,
        )
        instance.process()

    except Exception as e:
        _l.error("_run_data_procedure_sync.exception %s", e)
        _l.error("_run_data_procedure_sync.exception traceback %s", traceback.format_exc())
        raise Exception(e) from e


_run_data_procedure_sync.evaluator = True


def _rebook_transaction(evaluator, code, values=None, user_context=None, **kwargs):
    _l.info("_rebook_transaction")

    try:
        from poms.transactions.handlers import TransactionTypeProcess
        from poms.transactions.models import ComplexTransaction
        from poms.transactions.serializers import TransactionTypeProcessSerializer
        from poms.users.utils import (
            get_master_user_from_context,
            get_member_from_context,
        )

        context = evaluator.context

        master_user = get_master_user_from_context(context)  # noqa: F841
        member = get_member_from_context(context)

        _l.info("_rebook_transaction.context %s", context)

        merged_context = {}
        merged_context.update(context)

        if "names" not in merged_context:
            merged_context["names"] = {}

        if user_context:
            merged_context["names"].update(user_context)

        _l.info("_rebook_transaction.merged_context %s", merged_context)

        try:
            complex_transaction = ComplexTransaction.objects.get(code=code)

            _l.debug("_rebook_transaction.get complex transaction %s", complex_transaction)

            instance = TransactionTypeProcess(
                transaction_type=complex_transaction.transaction_type,
                process_mode="rebook",
                complex_transaction=complex_transaction,
                context=merged_context,
                member=member,
            )

            serializer = TransactionTypeProcessSerializer(instance=instance, context=merged_context)

            data = serializer.data

            # _l.debug('_rebook_transaction.get data to fill rebook processor %s' % data)

            instance = TransactionTypeProcess(
                transaction_type=complex_transaction.transaction_type,
                process_mode="rebook",
                complex_transaction=complex_transaction,
                complex_transaction_status=ComplexTransaction.PRODUCTION,
                context=merged_context,
                member=member,
            )

            if not values:
                values = {}

            data["values"] = dict(data["values"])

            data["values"].update(values)

            _l.debug("_rebook_transaction.get data to fill with values %s", values)
            _l.debug("_rebook_transaction.get data to fill with result values %s", data["values"])

            # _l.info('_rebook_transaction.data %s' % data)

            serializer = TransactionTypeProcessSerializer(instance=instance, data=data, context=merged_context)
            serializer.is_valid(raise_exception=True)
            serializer.save()

        except Exception as e:
            _l.error("_rebook_transaction. could not rebook exception %s", e)
            _l.error("_rebook_transaction. could not rebook traceback %s", traceback.format_exc())

    except Exception as e:
        _l.error(f"_rebook_transaction. general exception {e}")
        _l.error("_rebook_transaction. general exception traceback %s", traceback.format_exc())


_rebook_transaction.evaluator = True


def _download_instrument_from_finmars_database(
    evaluator, reference, instrument_name=None, instrument_type_user_code=None
):
    _l.info("_download_instrument_from_finmars_database formula")

    try:
        from poms.celery_tasks.models import CeleryTask
        from poms.integrations.tasks import download_instrument_finmars_database_async
        from poms.users.utils import (
            get_master_user_from_context,
            get_member_from_context,
        )

        context = evaluator.context

        master_user = get_master_user_from_context(context)
        member = get_member_from_context(context)

        task = CeleryTask.objects.create(
            master_user=master_user,
            member=member,
            verbose_name="Download Instrument From Finmars Database",
            type="download_instrument_from_finmars_database",
        )

        options = {
            "reference": reference,
        }

        if instrument_name:
            options["instrument_name"] = instrument_name

        if instrument_type_user_code:
            options["instrument_type_user_code"] = instrument_type_user_code

        task.options_object = options
        task.save()

        _l.info("_download_instrument_from_finmars_database. task created init a process")

        download_instrument_finmars_database_async.apply_async(
            kwargs={
                "task_id": task.id,
                "context": {
                    "space_code": task.master_user.space_code,
                    "realm_code": task.master_user.realm_code,
                },
            }
        )

    except Exception as e:
        _l.error("_download_instrument_from_finmars_database. general exception %s", e)
        _l.error("_download_instrument_from_finmars_database. general exception traceback %s", traceback.format_exc())


_download_instrument_from_finmars_database.evaluator = True


def _get_filenames_from_storage(evaluator, pattern=None, path_to_folder=None):
    # pattern \.txt$

    from poms.common.storage import get_storage
    from poms.users.utils import get_master_user_from_context, get_member_from_context

    storage = get_storage()

    context = evaluator.context

    master_user = get_master_user_from_context(context)
    member = get_member_from_context(context)  # noqa: F841

    # TODO check that file could be placed either in public or member home folder

    if not path_to_folder:
        path_to_folder = master_user.space_code
    elif path_to_folder[0] == "/":
        path_to_folder = master_user.space_code + path_to_folder
    else:
        path_to_folder = master_user.space_code + "/" + path_to_folder

    print("path_to_folder %s", path_to_folder)

    items = storage.listdir(path_to_folder)

    results = []

    for file in items[1]:
        if pattern:
            if re.search(pattern, file):
                results.append(file)
        else:
            results.append(file)

    return results


_get_filenames_from_storage.evaluator = True


def _delete_file_from_storage(evaluator, path):
    # pattern \.txt$

    from poms.common.storage import get_storage
    from poms.users.utils import get_master_user_from_context, get_member_from_context

    storage = get_storage()

    context = evaluator.context

    master_user = get_master_user_from_context(context)
    member = get_member_from_context(context)  # noqa: F841

    # TODO check that file could be placed either in public or member home folder

    if not path:
        path = master_user.space_code
    elif path[0] == "/":
        path = master_user.space_code + path
    else:
        path = master_user.space_code + "/" + path

    try:
        storage.delete(path)
        return True
    except Exception as e:
        _l.error("_delete_file_from_storage %s", e)
        return False


_delete_file_from_storage.evaluator = True


def _put_file_to_storage(evaluator, path, content):
    # pattern \.txt$

    from poms.common.storage import get_storage
    from poms.users.utils import get_master_user_from_context, get_member_from_context

    storage = get_storage()

    context = evaluator.context

    master_user = get_master_user_from_context(context)
    member = get_member_from_context(context)  # noqa: F841

    # TODO check that file could be placed either in public or member home folder

    if not path:
        path = master_user.space_code
    elif path[0] == "/":
        path = master_user.space_code + path
    else:
        path = master_user.space_code + "/" + path

    if master_user.space_code + "/import/" not in path:
        try:
            from django.core.files.base import ContentFile

            storage.save(path, ContentFile(content.encode("utf-8")))
            return True
        except Exception as e:
            _l.error("_put_file_to_storage %s", e)
            return False

    else:
        _l.error("_put_file_to_storage could not put files in import folder")
        return False


_put_file_to_storage.evaluator = True


def _run_data_import(evaluator, filepath, scheme):
    try:
        _l.info("_run_data_import %s", filepath)

        from poms.users.utils import (
            get_master_user_from_context,
            get_member_from_context,
        )

        context = evaluator.context

        master_user = get_master_user_from_context(context)
        member = get_member_from_context(context)

        if filepath[0] == "/":
            filepath = master_user.space_code + filepath
        else:
            filepath = master_user.space_code + "/" + filepath

        from poms.celery_tasks.models import CeleryTask
        from poms.csv_import.models import CsvImportScheme
        from poms.csv_import.tasks import simple_import

        celery_task = CeleryTask.objects.create(
            master_user=master_user,
            member=member,
            type="simple_import",
            verbose_name="Simple Import",
        )
        celery_task.status = CeleryTask.STATUS_DONE

        scheme = CsvImportScheme.objects.get(master_user=master_user, user_code=scheme)

        options_object = {
            "file_path": filepath,
            "filename": "",
            "scheme_id": scheme.id,
            "execution_context": None,
        }

        celery_task.options_object = options_object
        celery_task.save()

        simple_import.apply(
            kwargs={
                "task_id": celery_task.id,
                "context": {
                    "realm_code": celery_task.master_user.realm_code,
                    "space_code": celery_task.master_user.space_code,
                },
            },
            queue="backend-background-queue",
        )

        return {"task_id": celery_task.id}

    except Exception as e:
        _l.error("_run_data_import. general exception %s", e)
        _l.error("_run_data_import. general exception traceback %s", traceback.format_exc())


_run_data_import.evaluator = True


def _run_transaction_import(evaluator, filepath, scheme):
    from poms.celery_tasks.models import CeleryTask
    from poms.integrations.models import ComplexTransactionImportScheme
    from poms.transaction_import.tasks import transaction_import
    from poms.users.utils import get_master_user_from_context, get_member_from_context

    try:
        _l.info(f"_run_transaction_import {filepath}")

        context = evaluator.context
        master_user = get_master_user_from_context(context)
        member = get_member_from_context(context)

        if filepath[0] == "/":
            filepath = master_user.space_code + filepath
        else:
            filepath = f"{master_user.space_code}/{filepath}"

        celery_task = CeleryTask.objects.create(
            master_user=master_user,
            member=member,
            type="transaction_import",
            verbose_name="Transaction Import",
        )
        celery_task.status = CeleryTask.STATUS_DONE

        scheme = ComplexTransactionImportScheme.objects.get(master_user=master_user, user_code=scheme)

        options_object = {
            "file_path": filepath,
            "filename": "",
            "scheme_id": scheme.id,
            "execution_context": None,
        }

        celery_task.options_object = options_object
        celery_task.save()

        transaction_import.apply(
            kwargs={
                "task_id": celery_task.id,
                "context": {
                    "realm_code": celery_task.master_user.realm_code,
                    "space_code": celery_task.master_user.space_code,
                },
            },
            queue="backend-background-queue",
        )

        return None

    except Exception as e:
        _l.error(f"_run_transaction_import. general exception {e}")
        _l.error("_run_transaction_import. general exception traceback %s", traceback.format_exc())


_run_transaction_import.evaluator = True


def _simple_group(val, ranges, default=None):
    for begin, end, text in ranges:
        begin = float("-inf") if begin is None else float(begin)  # noqa: PLW2901
        end = float("inf") if end is None else float(end)  # noqa: PLW2901

        if begin < val <= end:
            return text

    return default


def _date_group(evaluator, val, ranges, default=None):
    val = _parse_date(val)

    # _l.debug('_date_group: val=%s', val)

    def _make_name(begin, end, fmt):
        # if end != datetime.date.max:
        #     end -= datetime.timedelta(days=1)
        if isinstance(fmt, list | tuple):
            ifmt = iter(fmt)
            s1 = str(next(ifmt, "") or "")
            begin_fmt = str(next(ifmt, "") or "")
            s3 = str(next(ifmt, "") or "")
            s4 = str(next(ifmt, "") or "")
            end_fmt = str(next(ifmt, "") or "")
            s6 = str(next(ifmt, "") or "")
            sbegin = _format_date(begin, begin_fmt) if begin_fmt else ""
            send = _format_date(end, end_fmt) if end_fmt else ""
            ret = "".join([s1, sbegin, s3, s4, send, s6])
        else:
            ret = str(fmt)
        if evaluator.context.get("date_group_with_dates", False):
            return ret, begin, end
        return ret

    for begin, end, step, fmt in ranges:
        evaluator.check_time()

        begin = _parse_date(begin) if begin else datetime.date(1900, 1, 1)  # noqa: PLW2901

        end = _parse_date(end) if end else datetime.date(2100, 12, 31)  # noqa: PLW2901

        if begin <= val <= end:
            if step:
                if not isinstance(
                    step,
                    datetime.timedelta | relativedelta.relativedelta,
                ):
                    step = _timedelta(days=step)  # noqa: PLW2901
                # _l.debug('start=%s, end=%s, step=%s', start, end, step)

                ld = begin
                while ld < end:
                    evaluator.check_time()
                    lbegin = ld
                    lend = ld + step - datetime.timedelta(days=1)
                    lend = min(lend, end)
                    # _l.debug('  lstart=%s, lend=%s', lbegin, lend)
                    if lbegin <= val <= lend:
                        return _make_name(lbegin, lend, fmt)
                    ld = ld + step
            else:
                return _make_name(begin, end, fmt)

    return default


_date_group.evaluator = True


def _has_var(evaluator, name):
    return evaluator.has_var(name)


_has_var.evaluator = True


def _get_var(evaluator, name, dafault=None):
    return evaluator.get_var(name, dafault)


_get_var.evaluator = True


def _find_name(*args):
    for s in args:
        if s is not None:
            return str(s)
    return ""


def _random():
    return random.random()


def _uuid():
    return str(uuid.uuid4())


def _print_message(evaluator, text):
    context = evaluator.context

    if "log" not in context:
        context["log"] = ""

    context["log"] = context["log"] + text + "\n"

    # _l.info("CONTEXT %s" % context)


_print_message.evaluator = True


def _if_valid_isin(evaluator, isin: str) -> bool:
    isin = isin.upper().replace("-", "")

    if len(isin) != 12:
        return False
    if not isin.isalnum():
        return False

    if not isin[-1].isdigit():
        return False

    if not isin[:2].isalpha():
        return False

    converted_digits = [str(ord(char) - 55) if char.isalpha() else char for char in isin[:-1]]
    converted_digits_str = "".join(converted_digits)
    converted_digits_str_multiplied = [
        int(char) * 2 if i % 2 == 0 else char for i, char in enumerate(converted_digits_str[::-1])
    ][::-1]
    summed_digits = sum(int(digit) for char in converted_digits_str_multiplied for digit in str(char))
    checksum = (10 - (summed_digits % 10)) % 10

    return isin[-1] == str(checksum)


_if_valid_isin.evaluator = True


def _print(message, *args, **kwargs):
    _l.debug(message, *args, **kwargs)


def _clean_str_val(
    evaluator,
    value: [str, int, float],
    if_empty_str_is_none: bool = False,
    if_number: bool = False,
    decimal_sep: str = ".",
    default_value: [str, int, float] = None,
) -> [str, int, float]:
    """
    Cleans and processes string value based on specified criteria.

    :param value: The input value to be cleaned.
    :type value: [str, int, float]
    :param if_empty_str_is_none: If True, returns default_value for empty strings, defaults to False.
    :type if_empty_str_is_none: bool, optional
    :param if_number: If True, processes the value as a number, removing symbols, defaults to False.
    :type if_number: bool, optional
    :param decimal_sep: The decimal separator used in the number, defaults to ".".
    :type decimal_sep: str, optional
    :param default_value: The value to be returned if the input is None or doesn't meet the criteria, defaults to None.
    :type default_value: [str, int, float], optional
    :return: Cleaned and processed string value based on specified criteria.
    :rtype: [str, int, float]
    """
    if value is None:
        return default_value
    value_str = str(value)
    # remove leading and trailing zeroes
    clean_value = value_str.strip()
    # Remove consecutive spaces
    clean_value = " ".join(clean_value.split())
    if if_empty_str_is_none:
        if clean_value == "":
            return default_value
    # If it's a number value
    if if_number:
        if clean_value == "":
            return default_value
        # remove all symbols except numbers, minus sign, comma and point
        sign = 1
        if clean_value[0] == "-":
            sign = -1
        clean_value = [char for char in clean_value if char.isdigit() or char == decimal_sep]
        clean_value = "".join(clean_value)
        clean_value = clean_value.replace(decimal_sep, ".")
        try:
            clean_value = sign * float(clean_value)
        except ValueError:
            return default_value
    return clean_value


_clean_str_val.evaluator = True


def _get_issuer_country_of_ccy(evaluator, currency):
    try:
        currency = _safe_get_currency(evaluator, currency)
        if not currency.country:
            return None

        from poms.instruments.serializers import CountrySerializer

        return CountrySerializer(instance=currency.country, context=evaluator.context).data

    except Exception:
        return None


_get_issuer_country_of_ccy.evaluator = True


class SimpleEval2Def:
    def __init__(self, name, func):
        self.name = name
        self.func = func

    def __str__(self):
        return f"<def {self.name}>"

    def __repr__(self):
        return f"<def {self.name}>"

    def __call__(self, evaluator, *args, **kwargs):
        if getattr(self.func, "evaluator", False):
            return self.func(evaluator, *args, **kwargs)
        else:
            return self.func(*args, **kwargs)


FINMARS_FUNCTIONS = [
    SimpleEval2Def("str", _str),
    SimpleEval2Def("substr", _substr),
    SimpleEval2Def("upper", _upper),
    SimpleEval2Def("lower", _lower),
    SimpleEval2Def("contains", _contains),
    SimpleEval2Def("replace", _replace),
    SimpleEval2Def("reg_search", _reg_search),
    SimpleEval2Def("reg_replace", _reg_replace),
    SimpleEval2Def("int", _int),
    SimpleEval2Def("float", _float),
    SimpleEval2Def("bool", _bool),
    SimpleEval2Def("round", _round),
    SimpleEval2Def("trunc", _trunc),
    SimpleEval2Def("abs", _abs),
    SimpleEval2Def("isclose", _isclose),
    SimpleEval2Def("random", _random),
    SimpleEval2Def("min", _min),
    SimpleEval2Def("max", _max),
    SimpleEval2Def("uuid", _uuid),
    SimpleEval2Def("print_message", _print_message),
    SimpleEval2Def("iff", _iff),
    SimpleEval2Def("len", _len),
    SimpleEval2Def("range", _range),
    SimpleEval2Def("now", _now),
    SimpleEval2Def("date", _date),
    SimpleEval2Def("date_min", _date_min),
    SimpleEval2Def("date_max", _date_max),
    SimpleEval2Def("isleap", _isleap),
    SimpleEval2Def("days", _days),
    SimpleEval2Def("weeks", _weeks),
    SimpleEval2Def("months", _months),
    SimpleEval2Def("timedelta", _timedelta),
    SimpleEval2Def("days_diff", _days_diff),
    SimpleEval2Def("add_days", _add_days),
    SimpleEval2Def("add_weeks", _add_weeks),
    SimpleEval2Def("add_workdays", _add_workdays),
    SimpleEval2Def("format_date", _format_date),
    SimpleEval2Def("get_list_of_dates_between_two_dates", _get_list_of_dates_between_two_dates),
    SimpleEval2Def("get_quarter", _get_quarter),
    SimpleEval2Def("get_year", _get_year),
    SimpleEval2Def("get_month", _get_month),
    SimpleEval2Def("parse_date", _parse_date),
    SimpleEval2Def("universal_parse_date", _universal_parse_date),
    SimpleEval2Def("universal_parse_country", _universal_parse_country),
    SimpleEval2Def("unix_to_date", _unix_to_date),
    SimpleEval2Def("md5", _md5),
    SimpleEval2Def("to_json", _to_json),
    SimpleEval2Def("last_business_day", _last_business_day),
    SimpleEval2Def("get_date_last_week_end_business", _get_date_last_week_end_business),
    SimpleEval2Def("get_date_last_month_end_business", _get_date_last_month_end_business),
    SimpleEval2Def("get_date_last_quarter_end_business", _get_date_last_quarter_end_business),
    SimpleEval2Def("get_date_last_year_end_business", _get_date_last_year_end_business),
    SimpleEval2Def("calculate_period_date", _calculate_period_date),
    SimpleEval2Def("format_number", _format_number),
    SimpleEval2Def("parse_number", _parse_number),
    SimpleEval2Def("join", _join),
    SimpleEval2Def("strip", _strip),
    SimpleEval2Def("reverse", _reverse),
    SimpleEval2Def("split", _split),
    SimpleEval2Def("simple_price", _simple_price),
    SimpleEval2Def("get_instrument", _get_instrument),
    SimpleEval2Def("add_instrument_identifier", _add_instrument_identifier),
    SimpleEval2Def("remove_instrument_identifier", _remove_instrument_identifier),
    SimpleEval2Def("get_currency", _get_currency),
    SimpleEval2Def("check_currency", _check_currency),
    SimpleEval2Def("get_account_type", _get_account_type),
    SimpleEval2Def("set_account_user_attribute", _set_account_user_attribute),
    SimpleEval2Def("get_account_user_attribute", _get_account_user_attribute),
    SimpleEval2Def("get_currency_field", _get_currency_field),
    SimpleEval2Def("set_currency_field", _set_currency_field),
    SimpleEval2Def("get_instrument_field", _get_instrument_field),
    SimpleEval2Def("set_instrument_field", _set_instrument_field),
    SimpleEval2Def("set_instrument_user_attribute", _set_instrument_user_attribute),
    SimpleEval2Def("get_instrument_user_attribute", _get_instrument_user_attribute),
    SimpleEval2Def("get_instrument_accrual_size", _get_instrument_accrual_size),
    SimpleEval2Def("get_instrument_accrual_factor", _get_instrument_accrual_factor),
    SimpleEval2Def("calculate_accrued_price", _calculate_accrued_price),
    SimpleEval2Def("get_position_size_on_date", _get_position_size_on_date),
    SimpleEval2Def("get_principal_on_date", _get_principal_on_date),
    SimpleEval2Def("get_transactions_amounts_on_date", _get_transactions_amounts_on_date),
    SimpleEval2Def("get_net_cost_price_on_date", _get_net_cost_price_on_date),
    SimpleEval2Def("get_instrument_report_data", _get_instrument_report_data),
    SimpleEval2Def("get_instrument_factor", _get_instrument_factor),
    SimpleEval2Def("get_instrument_coupon_factor", _get_instrument_coupon_factor),
    SimpleEval2Def("get_instrument_coupon", _get_instrument_coupon),
    SimpleEval2Def("get_fx_rate", _get_fx_rate),
    SimpleEval2Def("get_principal_price", _get_price_history_principal_price),
    SimpleEval2Def("get_accrued_price", _get_price_history_accrued_price),
    SimpleEval2Def("get_price", _get_price_history),
    SimpleEval2Def("get_next_coupon_date", _get_next_coupon_date),
    SimpleEval2Def("get_factor_schedule", _get_factor_schedule),
    SimpleEval2Def("get_factor", _get_factor_schedule),
    SimpleEval2Def("get_factor_from_price", _get_factor_from_price),
    SimpleEval2Def("add_factor_schedule", _add_factor_schedule),
    SimpleEval2Def("add_accrual_schedule", _add_accrual_schedule),
    SimpleEval2Def("delete_accrual_schedules", _delete_accrual_schedules),
    SimpleEval2Def("get_instrument_pricing_scheme", _get_instrument_pricing_scheme),
    SimpleEval2Def("get_currency_pricing_scheme", _get_currency_pricing_scheme),
    SimpleEval2Def("get_instrument_attribute", _get_instrument_attribute),
    SimpleEval2Def("get_currency_attribute", _get_currency_attribute),
    SimpleEval2Def("add_fx_rate", _add_fx_rate),
    SimpleEval2Def("add_price_history", _add_price_history),
    SimpleEval2Def("generate_user_code", _generate_user_code),
    SimpleEval2Def("get_latest_principal_price", _get_latest_principal_price),
    SimpleEval2Def("get_latest_principal_price_date", _get_latest_principal_price_date),
    SimpleEval2Def("get_latest_fx_rate", _get_latest_fx_rate),
    SimpleEval2Def("get_instrument_user_attribute_value", _get_instrument_user_attribute_value),
    SimpleEval2Def("get_ttype_default_input", _get_ttype_default_input),
    SimpleEval2Def("set_complex_transaction_input", _set_complex_transaction_input),
    SimpleEval2Def("set_complex_transaction_user_field", _set_complex_transaction_user_field),
    SimpleEval2Def("set_complex_transaction_form_data", _set_complex_transaction_form_data),
    SimpleEval2Def("get_complex_transaction", _get_complex_transaction),
    SimpleEval2Def("get_relation_by_user_code", _get_relation_by_user_code),
    SimpleEval2Def("get_instruments", _get_instruments),
    SimpleEval2Def("get_currencies", _get_currencies),
    SimpleEval2Def("get_mapping_key_by_value", _get_mapping_key_by_value),
    SimpleEval2Def("get_mapping_value_by_key", _get_mapping_value_by_key),
    SimpleEval2Def("get_mapping_keys", _get_mapping_keys),
    SimpleEval2Def("get_mapping_key_values", _get_mapping_key_values),
    SimpleEval2Def("get_rt_value", _get_rt_value),
    SimpleEval2Def("convert_to_number", _convert_to_number),
    SimpleEval2Def("if_null", _if_null),
    SimpleEval2Def("send_system_message", _send_system_message),
    SimpleEval2Def("calculate_performance_report", _calculate_performance_report),
    SimpleEval2Def("calculate_balance_report", _calculate_balance_report),
    SimpleEval2Def("calculate_pl_report", _calculate_pl_report),
    SimpleEval2Def("get_current_member", _get_current_member),
    SimpleEval2Def("find_name", _find_name),
    SimpleEval2Def("simple_group", _simple_group),
    SimpleEval2Def("date_group", _date_group),
    SimpleEval2Def("has_var", _has_var),
    SimpleEval2Def("get_var", _get_var),
    SimpleEval2Def("get_default_portfolio", _get_default_portfolio),
    SimpleEval2Def("get_default_instrument", _get_default_instrument),
    SimpleEval2Def("get_default_account", _get_default_account),
    SimpleEval2Def("get_default_currency", _get_default_currency),
    SimpleEval2Def("get_default_transaction_type", _get_default_transaction_type),
    SimpleEval2Def("get_default_instrument_type", _get_default_instrument_type),
    SimpleEval2Def("get_default_account_type", _get_default_account_type),
    SimpleEval2Def("get_default_pricing_policy", _get_default_pricing_policy),
    SimpleEval2Def("get_default_responsible", _get_default_responsible),
    SimpleEval2Def("get_default_counterparty", _get_default_counterparty),
    SimpleEval2Def("get_default_strategy1", _get_default_strategy1),
    SimpleEval2Def("get_default_strategy2", _get_default_strategy2),
    SimpleEval2Def("get_default_strategy3", _get_default_strategy3),
    SimpleEval2Def("run_task", _run_task),
    SimpleEval2Def("create_task", _create_task),
    SimpleEval2Def("run_pricing_procedure", _run_pricing_procedure),
    SimpleEval2Def("run_data_procedure", _run_data_procedure),
    SimpleEval2Def("run_data_procedure_sync", _run_data_procedure_sync),
    SimpleEval2Def("rebook_transaction", _rebook_transaction),
    SimpleEval2Def(
        "download_instrument_from_finmars_database",
        _download_instrument_from_finmars_database,
    ),
    SimpleEval2Def("get_filenames_from_storage", _get_filenames_from_storage),
    SimpleEval2Def("delete_file_from_storage", _delete_file_from_storage),
    SimpleEval2Def("put_file_to_storage", _put_file_to_storage),
    SimpleEval2Def("run_data_import", _run_data_import),
    SimpleEval2Def("run_transaction_import", _run_transaction_import),
    SimpleEval2Def("clean_str_val", _clean_str_val),
    SimpleEval2Def("if_valid_isin", _if_valid_isin),
    SimpleEval2Def("get_issuer_country_of_ccy", _get_issuer_country_of_ccy),
]
