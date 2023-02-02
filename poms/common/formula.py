from __future__ import unicode_literals, print_function, division

import ast
import calendar
import datetime
import logging
import random
import re
import time
import traceback
import types
import uuid
from collections import OrderedDict

from dateutil import relativedelta
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.forms.models import model_to_dict
from django.utils import numberformat
from django.utils.functional import Promise, SimpleLazyObject
from pandas.tseries.offsets import BMonthEnd, BYearEnd, BQuarterEnd, BDay

from poms.common.utils import date_now, isclose, get_list_of_dates_between_two_dates

_l = logging.getLogger('poms.formula')

MAX_STR_LEN = 20000
# MAX_EXPONENT = 4000000  # highest exponent
MAX_EXPONENT = 10000  # highest exponent
# MAX_SHIFT = 1000
MAX_SHIFT = 10
MAX_LEN = 1000


class InvalidExpression(Exception):
    pass


class ExpressionSyntaxError(InvalidExpression):
    pass


class ExpressionEvalError(InvalidExpression):
    pass


class FunctionNotDefined(InvalidExpression):
    def __init__(self, name):
        self.message = "Function '%s' not defined" % name
        super(InvalidExpression, self).__init__(self.message)


class NameNotDefined(InvalidExpression):
    def __init__(self, name):
        self.message = "Name '%s' not defined" % name
        super(InvalidExpression, self).__init__(self.message)


class AttributeDoesNotExist(InvalidExpression):
    def __init__(self, attr):
        self.message = "Attribute '%s' does not exist in expression" % attr
        super(AttributeDoesNotExist, self).__init__(self.message)


class _Break(InvalidExpression):
    pass


class _Return(InvalidExpression):
    def __init__(self, value):
        self.value = value
        super(_Return, self).__init__()


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


def _timedelta(years=0, months=0, days=0, leapdays=0, weeks=0,
               year=None, month=None, day=None, weekday=None,
               yearday=None, nlyearday=None):
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
    weeks = int(workdays / 5)
    days_remainder = workdays % 5
    date = date + datetime.timedelta(weeks=weeks, days=days_remainder)
    if only_workdays:
        if date.weekday() == 5:
            return date + datetime.timedelta(days=2)
        if date.weekday() == 6:
            return date + datetime.timedelta(days=1)
    return date


def _format_date(date, format=None):
    if not isinstance(date, datetime.date):
        date = _parse_date(str(date))
    # _check_date(date)
    if not format:
        format = '%Y-%m-%d'
    else:
        format = str(format)
    return date.strftime(format)


def _get_list_of_dates_between_two_dates(date_from, date_to):
    return get_list_of_dates_between_two_dates(date_from, date_to)


def _send_system_message(evaluator, title=None, description=None, type='info', section='other',
                         action_status='not_required',
                         performed_by="Expression Engine"):
    try:
        from poms.system_messages.handlers import send_system_message
        from poms.system_messages.models import SystemMessage

        context = evaluator.context
        from poms.users.utils import get_master_user_from_context

        master_user = get_master_user_from_context(context)

        send_system_message(master_user=master_user,
                            performed_by=performed_by,
                            type=type,
                            section=section,
                            action_status=action_status,
                            title=title,
                            description=description)

    except Exception as e:
        _l.error("Could not sent system message %s" % e)


_send_system_message.evaluator = True


def _calculate_performance_report(evaluator, name, date_from, date_to, report_currency, calculation_type,
                                  segmentation_type, registers):
    try:

        from poms.system_messages.handlers import send_system_message

        context = evaluator.context
        from poms.users.utils import get_master_user_from_context, get_member_from_context

        master_user = get_master_user_from_context(context)
        member = get_member_from_context(context)

        from poms.reports.common import PerformanceReport
        from poms.reports.performance_report import PerformanceReportBuilder
        from poms.reports.serializers import PerformanceReportSerializer
        from poms.instruments.models import Instrument

        currency = _safe_get_currency(evaluator, report_currency)

        _l.info('_calculate_performance_report master_user %s' % master_user)
        _l.info('_calculate_performance_report member %s' % member)
        _l.info('_calculate_performance_report date_from  %s' % date_from)
        _l.info('_calculate_performance_report date_to %s' % date_to)
        _l.info('_calculate_performance_report currency %s' % currency)

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
            save_report=True
        )

        builder = PerformanceReportBuilder(instance=instance)
        instance = builder.build_report()

        serializer = PerformanceReportSerializer(instance=instance, context=context)

        serializer.to_representation(instance)



    except Exception as e:
        _l.error("_calculate_performance_report.Exception %s" % e)
        _l.error("_calculate_performance_report.Trace %s" % traceback.format_exc())


_calculate_performance_report.evaluator = True


def _calculate_balance_report(evaluator, name, report_date, report_currency, pricing_policy=None, cost_method="AVCO",
                              portfolios=[]):
    try:

        from poms.system_messages.handlers import send_system_message

        context = evaluator.context
        from poms.users.utils import get_master_user_from_context, get_member_from_context

        master_user = get_master_user_from_context(context)
        member = get_member_from_context(context)

        from poms.reports.sql_builders.balance import BalanceReportBuilderSql
        from poms.reports.serializers import BalanceReportSerializer
        from poms.reports.common import Report
        from poms.instruments.models import Instrument

        from poms.users.models import EcosystemDefault
        ecosystem_default = EcosystemDefault.objects.get(master_user=master_user)

        currency = _safe_get_currency(evaluator, report_currency)
        if pricing_policy:
            pricing_policy = _safe_get_pricing_policy(evaluator, pricing_policy)
        else:
            pricing_policy = ecosystem_default.pricing_policy

        from poms.instruments.models import CostMethod
        cost_method = CostMethod.objects.get(user_code=cost_method)

        _l.info('_calculate_balance_report master_user %s' % master_user)
        _l.info('_calculate_balance_report member %s' % member)
        _l.info('_calculate_balance_report report_date  %s' % report_date)
        _l.info('_calculate_balance_report currency %s' % currency)

        report_date_d = datetime.datetime.strptime(report_date, "%Y-%m-%d").date()

        from poms.portfolios.models import Portfolio

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
            save_report=True
        )

        builder = BalanceReportBuilderSql(instance=instance)
        instance = builder.build_balance()

        serializer = BalanceReportSerializer(instance=instance, context=context)

        serializer.to_representation(instance)

    except Exception as e:
        _l.error("_calculate_balance_report.Exception %s" % e)
        _l.error("_calculate_balance_report.Trace %s" % traceback.format_exc())


_calculate_balance_report.evaluator = True


def _calculate_pl_report(evaluator, name, pl_first_date, report_date, report_currency, pricing_policy=None,
                         cost_method="AVCO", portfolios=[]):
    try:

        from poms.system_messages.handlers import send_system_message

        context = evaluator.context
        from poms.users.utils import get_master_user_from_context, get_member_from_context

        master_user = get_master_user_from_context(context)
        member = get_member_from_context(context)

        from poms.reports.sql_builders.balance import PLReportBuilderSql
        from poms.legacy_reports.builders.balance_serializers import PLReportSqlSerializer
        from poms.reports.common import Report
        from poms.instruments.models import Instrument

        from poms.users.models import EcosystemDefault
        ecosystem_default = EcosystemDefault.objects.get(master_user=master_user)

        currency = _safe_get_currency(evaluator, report_currency)
        if pricing_policy:
            pricing_policy = _safe_get_pricing_policy(evaluator, pricing_policy)
        else:
            pricing_policy = ecosystem_default.pricing_policy

        from poms.instruments.models import CostMethod
        cost_method = CostMethod.objects.get(user_code=cost_method)

        _l.info('_calculate_pl_report master_user %s' % master_user)
        _l.info('_calculate_pl_report member %s' % member)
        _l.info('_calculate_pl_report report_date  %s' % report_date)
        _l.info('_calculate_pl_report pl_first_date  %s' % pl_first_date)
        _l.info('_calculate_pl_report currency %s' % currency)

        report_date_d = datetime.datetime.strptime(report_date, "%Y-%m-%d").date()
        pl_first_date_d = datetime.datetime.strptime(pl_first_date, "%Y-%m-%d").date()

        from poms.portfolios.models import Portfolio

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
            save_report=True
        )

        builder = PLReportBuilderSql(instance=instance)
        instance = builder.build_balance()

        serializer = PLReportSerializer(instance=instance, context=context)

        serializer.to_representation(instance)

    except Exception as e:
        _l.error("_calculate_pl_report.Exception %s" % e)
        _l.error("_calculate_pl_report.Trace %s" % traceback.format_exc())


_calculate_pl_report.evaluator = True


def _get_current_member(evaluator):
    context = evaluator.context
    from poms.users.utils import get_member_from_context

    member = get_member_from_context(context)

    return member


_get_current_member.evaluator = True


def _transaction_import__find_row(evaluator, **kwargs):
    context = evaluator.context

    result = {}

    if 'row_number' in kwargs:
        result = {'row_number': kwargs['row_number']}

    return result


_transaction_import__find_row.evaluator = True


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
                print("_parse_date date_string %s " % date_string)
                print("_parse_date format %s " % f)
                print("_parse_date error %s " % e)
    else:
        if not format:
            format = '%Y-%m-%d'
        else:
            format = str(format)

        result = datetime.datetime.strptime(date_string, format).date()

    return result


def _universal_parse_date(date_string):
    # from dateutil.parser import parse
    # dt = parse('Mon Feb 15 2010')
    # print(dt)
    # # datetime.datetime(2010, 2, 15, 0, 0)
    # print(dt.strftime('%d/%m/%Y'))
    # # 15/02/2010

    from dateutil.parser import parse

    dt = parse(date_string)

    return dt.strftime('%Y-%m-%d')


def _unix_to_date(unix, format=None):
    if not unix:
        return None
    if isinstance(unix, datetime.date):
        return unix
    unix = int(unix)
    if not format:
        format = '%Y-%m-%d'
    else:
        format = str(format)
    return datetime.datetime.utcfromtimestamp(unix).strftime(format)


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


def _format_date2(date, format=None, locale=None):
    if not isinstance(date, datetime.date):
        date = _parse_date2(str(date))
    if not format:
        format = 'yyyy-MM-dd'
    else:
        format = str(format)

    from babel.dates import format_date, LC_TIME
    from babel import Locale

    l = Locale.parse(locale or LC_TIME)
    return format_date(date, format=format, locale=l)


def _parse_date2(date_string, format=None, locale=None):
    # babel haven't supported parse by dynamic pattern
    if not date_string:
        return None
    if isinstance(date_string, datetime.date):
        return date_string
    date_string = str(date_string)
    if not format:
        format = 'yyyy-MM-dd'
    else:
        format = str(format)

    from babel.dates import parse_pattern, LC_TIME
    from babel import Locale

    l = Locale.parse(locale or LC_TIME)
    p = parse_pattern(format)
    return p.apply(date_string, l)


def _format_number(number, decimal_sep='.', decimal_pos=None, grouping=3, thousand_sep='', use_grouping=False):
    number = float(number)
    decimal_sep = str(decimal_sep)
    if decimal_pos is not None:
        decimal_pos = int(decimal_pos)
    grouping = int(grouping)
    thousand_sep = str(thousand_sep)
    return numberformat.format(number, decimal_sep, decimal_pos=decimal_pos, grouping=grouping,
                               thousand_sep=thousand_sep, force_grouping=use_grouping)


def _parse_number(a):
    if isinstance(a, (float, int)):
        return a
    return float(a)


def _join(data, separator):
    return separator.join(data)


def _reverse(items):
    if isinstance(items, str):
        return items[::-1]

    items.reverse()

    return items


def _split(text, delimeter):
    return text.split(delimeter)


def _parse_bool(a):
    if isinstance(a, (bool)):
        return a
    return bool(a)


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
    from poms.transactions.models import TransactionTypeInput

    from poms.accounts.models import Account
    from poms.counterparties.models import Counterparty, Responsible
    from poms.currencies.models import Currency
    from poms.instruments.models import Instrument, InstrumentType, DailyPricingModel, PaymentSizeDetail, PricingPolicy, \
        Periodicity, AccrualCalculationModel
    from poms.integrations.models import PriceDownloadScheme
    from poms.portfolios.models import Portfolio
    from poms.strategies.models import Strategy1, Strategy2, Strategy3
    from poms.transactions.models import EventClass, NotificationClass

    context = evaluator.context

    try:
        transaction_type = context['transaction_type']
    except ValueError:
        raise ExpressionEvalError('Missing context: Transacion Type')

    inputs = list(transaction_type.inputs.all())

    input_obj = None

    for tt_input in inputs:

        if input == tt_input.name:
            input_obj = tt_input

    print('input_obj %s' % input_obj)

    if input_obj is None:
        raise ExpressionEvalError('Input is not found')

    print('input_obj.value_type %s' % input_obj.value_type)
    print('input_obj.value %s' % input_obj.value)

    if input_obj.value_type == TransactionTypeInput.RELATION:

        def _get_val_by_model_cls(obj, model_class):
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

        print('model_class %s' % model_class)

        result = _get_val_by_model_cls(input_obj, model_class).__dict__

        # print('result relation.name %s' % result.name)
        print('result relation[name] %s' % result['name'])

    else:
        result = input_obj.value

    return result


_get_ttype_default_input.evaluator = True


def _set_complex_transaction_input(evaluator, input, value):
    try:

        from poms.transactions.models import TransactionTypeInput

        context = evaluator.context

        try:
            complex_transaction = context['complex_transaction']
        except ValueError:
            raise ExpressionEvalError('Missing context: Complex Transaction')

        inputs = list(complex_transaction.inputs.all())

        input_obj = None

        for ct_input in inputs:

            if input == ct_input.transaction_type_input.name:
                input_obj = ct_input

        print('input_obj %s' % input_obj)

        if input_obj is None:
            raise ExpressionEvalError('Input is not found')

        print('input_obj.transaction_type_input.value_type  %s' % input_obj.transaction_type_input.value_type)
        print('value %s' % value)

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
        _l.info("_set_complex_transaction_input exception %s " % e)
        return False


_set_complex_transaction_input.evaluator = True


def _set_complex_transaction_form_data(evaluator, key, value):
    try:

        from poms.transactions.models import TransactionTypeInput

        context = evaluator.context

        try:
            values = context['values']
        except ValueError:
            raise ExpressionEvalError('Missing context: Complex Transaction')

        values[key] = value

        return True
    except Exception as e:
        _l.info("_set_complex_transaction_form_data exception %s " % e)
        return False


_set_complex_transaction_form_data.evaluator = True


def _set_complex_transaction_user_field(evaluator, field, value):
    try:

        from poms.transactions.models import TransactionTypeInput

        context = evaluator.context

        try:
            complex_transaction = context['complex_transaction']
        except ValueError:
            raise ExpressionEvalError('Missing context: Complex Transaction')

        setattr(complex_transaction, field, value)

        return True
    except Exception as e:
        _l.info("_set_complex_transaction_user_field exception %s " % e)
        return False


_set_complex_transaction_user_field.evaluator = True


def _get_relation_by_user_code(evaluator, content_type, user_code):
    try:
        from poms.transactions.models import TransactionTypeInput

        from poms.accounts.models import Account
        from poms.counterparties.models import Counterparty, Responsible
        from poms.currencies.models import Currency
        from poms.instruments.models import Instrument, InstrumentType, DailyPricingModel, PaymentSizeDetail, \
            PricingPolicy, \
            Periodicity, AccrualCalculationModel
        from poms.integrations.models import PriceDownloadScheme
        from poms.portfolios.models import Portfolio
        from poms.strategies.models import Strategy1, Strategy2, Strategy3
        from poms.transactions.models import EventClass, NotificationClass

        context = evaluator.context
        from poms.users.utils import get_master_user_from_context

        master_user = get_master_user_from_context(context)

        def _get_val_by_model_cls(model_class, user_code):
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

        app_label, model = content_type.split('.')
        model_class = ContentType.objects.get_by_natural_key(app_label, model).model_class()

        _l.info('model_class %s' % model_class)

        result = model_to_dict(_get_val_by_model_cls(model_class, user_code))

        return result
    except Exception as e:
        return None


_get_relation_by_user_code.evaluator = True


def _get_instruments(evaluator, **kwargs):
    try:
        from poms.transactions.models import TransactionTypeInput

        from poms.accounts.models import Account
        from poms.counterparties.models import Counterparty, Responsible
        from poms.currencies.models import Currency
        from poms.instruments.models import Instrument, InstrumentType, DailyPricingModel, PaymentSizeDetail, \
            PricingPolicy, \
            Periodicity, AccrualCalculationModel
        from poms.integrations.models import PriceDownloadScheme
        from poms.portfolios.models import Portfolio
        from poms.strategies.models import Strategy1, Strategy2, Strategy3
        from poms.transactions.models import EventClass, NotificationClass

        context = evaluator.context
        from poms.users.utils import get_master_user_from_context

        master_user = get_master_user_from_context(context)

        items = Instrument.objects.filter(master_user=master_user, is_deleted=False, **kwargs)
        result = []

        for item in items:
            result.append(model_to_dict(item))

        return result
    except Exception as e:
        _l.error("_get_instruments.exception %s" % e)
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
        _l.error("_get_currencies.exception %s" % e)
        return None


_get_currencies.evaluator = True


def _convert_to_number(evaluator, text_number, thousand_separator="", decimal_separator=".", has_braces=False):
    result = text_number.replace(thousand_separator, '')

    result = result.replace(decimal_separator, '.')

    if has_braces:
        result = result.replace('(', '')
        result = result.replace(')', '')
        result = '-' + result

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


def _generate_user_code(evaluator, prefix='', suffix='', counter=0):
    from poms.users.utils import get_master_user_from_context

    context = evaluator.context

    master_user = get_master_user_from_context(context)

    if not master_user.user_code_counters:
        master_user.user_code_counters = [0, 0, 0, 0, 0,
                                          0, 0, 0, 0, 0,
                                          0]

    if counter < 0:
        raise InvalidExpression('Counter is lower than 0')

    if counter > 10:
        raise InvalidExpression('Counter is greater than 10')

    master_user.user_code_counters[counter] = master_user.user_code_counters[counter] + 1
    master_user.save()

    result = prefix + str(master_user.user_code_counters[counter]).zfill(17) + suffix

    if len(result) > 25:
        raise InvalidExpression('User code is too big')

    return result


_generate_user_code.evaluator = True


def _get_fx_rate(evaluator, date, currency, pricing_policy, default_value=0):
    from poms.users.utils import get_master_user_from_context
    from poms.currencies.models import CurrencyHistory

    context = evaluator.context
    master_user = get_master_user_from_context(context)

    date = _parse_date(date)
    currency = _safe_get_currency(evaluator, currency)
    pricing_policy = _safe_get_pricing_policy(evaluator, pricing_policy)

    # TODO need master user check, security hole

    try:
        result = CurrencyHistory.objects.get(date=date, currency=currency,
                                             pricing_policy=pricing_policy)
    except (CurrencyHistory.DoesNotExist, KeyError):
        result = None

    if result:
        return result.fx_rate

    return default_value


_get_fx_rate.evaluator = True


def _add_fx_rate(evaluator, date, currency, pricing_policy, fx_rate=0, overwrite=True):
    from poms.users.utils import get_master_user_from_context
    from poms.currencies.models import CurrencyHistory

    context = evaluator.context
    master_user = get_master_user_from_context(context)

    date = _parse_date(date)
    pricing_policy = _safe_get_pricing_policy(evaluator, pricing_policy)
    currency = _safe_get_currency(evaluator, currency)

    # TODO need master user check, security hole

    try:
        result = CurrencyHistory.objects.get(date=date, currency=currency,
                                             pricing_policy=pricing_policy)

        if overwrite:
            result.fx_rate = fx_rate

            result.save()
        else:
            return False

    except CurrencyHistory.DoesNotExist:

        result = CurrencyHistory.objects.create(date=date, currency=currency,
                                                pricing_policy=pricing_policy, fx_rate=fx_rate)

        result.save()

    return True


_add_fx_rate.evaluator = True


def _add_price_history(evaluator, date, instrument, pricing_policy, principal_price=0, accrued_price=0,
                       is_temporary_price=False, overwrite=True):
    from poms.users.utils import get_master_user_from_context
    from poms.instruments.models import PriceHistory

    context = evaluator.context
    master_user = get_master_user_from_context(context)

    date = _parse_date(date)
    instrument = _safe_get_instrument(evaluator, instrument)
    pricing_policy = _safe_get_pricing_policy(evaluator, pricing_policy)

    # TODO need master user check, security hole

    try:
        result = PriceHistory.objects.get(date=date, instrument=instrument,
                                          pricing_policy=pricing_policy)

        if overwrite:
            if principal_price is not None:
                result.principal_price = principal_price

            if accrued_price is not None:
                result.accrued_price = accrued_price

            result.save()

        else:
            return False

    except PriceHistory.DoesNotExist:

        result = PriceHistory.objects.create(date=date, instrument=instrument,
                                             is_temporary_price=is_temporary_price,
                                             pricing_policy=pricing_policy, principal_price=principal_price,
                                             accrued_price=accrued_price)

        result.save()

    return True


_add_price_history.evaluator = True


def _get_latest_principal_price(evaluator, date_from, date_to, instrument, pricing_policy, default_value=None):
    try:
        from poms.users.utils import get_master_user_from_context
        from poms.instruments.models import PriceHistory

        context = evaluator.context
        master_user = get_master_user_from_context(context)

        date_from = _parse_date(date_from)
        date_to = _parse_date(date_to)
        instrument = _safe_get_instrument(evaluator, instrument)
        pricing_policy = _safe_get_pricing_policy(evaluator, pricing_policy)

        _l.info("_get_latest_principal_price instrument %s " % instrument)
        _l.info("_get_latest_principal_price  pricing_policy %s " % pricing_policy)

        results = PriceHistory.objects.exclude(principal_price=0).filter(date__gte=date_from, date__lte=date_to,
                                                                         instrument=instrument,
                                                                         pricing_policy=pricing_policy).order_by(
            '-date')

        _l.info("_get_latest_principal_price results %s " % results)

        if len(list(results)):
            return results[0].principal_price

        return default_value
    except Exception as e:
        _l.info("_get_latest_principal_price exception %s " % e)
        return default_value


_get_latest_principal_price.evaluator = True


def _get_latest_principal_price_date(evaluator, instrument, pricing_policy, default_value=None):
    try:
        from poms.users.utils import get_master_user_from_context
        from poms.instruments.models import PriceHistory

        context = evaluator.context
        master_user = get_master_user_from_context(context)

        instrument = _safe_get_instrument(evaluator, instrument)
        pricing_policy = _safe_get_pricing_policy(evaluator, pricing_policy)

        _l.info("_get_latest_principal_price instrument %s " % instrument)
        _l.info("_get_latest_principal_price  pricing_policy %s " % pricing_policy)

        results = PriceHistory.objects.exclude(principal_price=0).filter(instrument=instrument,
                                                                         pricing_policy=pricing_policy).order_by(
            '-date')

        _l.info("_get_latest_principal_price_date results %s " % results)

        if len(list(results)):
            return results[0].date

        return default_value
    except Exception as e:
        _l.error("_get_latest_principal_price_date exception %s " % str(e))
        _l.error("_get_latest_principal_price_date exception %s " % traceback.format_exc())
        return default_value


_get_latest_principal_price_date.evaluator = True


def _get_latest_fx_rate(evaluator, date_from, date_to, currency, pricing_policy, default_value=None):
    try:
        from poms.users.utils import get_master_user_from_context
        from poms.currencies.models import CurrencyHistory

        context = evaluator.context
        master_user = get_master_user_from_context(context)

        date_from = _parse_date(date_from)
        date_to = _parse_date(date_to)
        currency = _safe_get_currency(evaluator, currency)
        pricing_policy = _safe_get_pricing_policy(evaluator, pricing_policy)

        _l.info("_get_latest_fx_rate instrument %s " % currency)
        _l.info("_get_latest_fx_rate  pricing_policy %s " % pricing_policy)

        results = CurrencyHistory.objects.filter(date__gte=date_from, date__lte=date_to, currency=currency,
                                                 pricing_policy=pricing_policy).order_by('-date')

        _l.info("_get_latest_fx_rate results %s " % results)

        if len(list(results)):
            return results[0].fx_rate

        return default_value
    except Exception as e:
        _l.info("_get_latest_fx_rate exception %s " % e)
        return default_value


_get_latest_fx_rate.evaluator = True


def _get_price_history_principal_price(evaluator, date, instrument, pricing_policy, default_value=0):
    from poms.users.utils import get_master_user_from_context
    from poms.instruments.models import PriceHistory

    context = evaluator.context
    master_user = get_master_user_from_context(context)

    # TODO need master user check, security hole

    date = _parse_date(date)
    instrument = _safe_get_instrument(evaluator, instrument)
    pricing_policy = _safe_get_pricing_policy(evaluator, pricing_policy)

    try:

        result = PriceHistory.objects.get(date=date, instrument=instrument,
                                          pricing_policy=pricing_policy)

        return result.principal_price

    except PriceHistory.DoesNotExist:
        print("Price history is not found")

    return default_value


_get_price_history_principal_price.evaluator = True


def _get_price_history_accrued_price(evaluator, date, instrument, pricing_policy, default_value=0, days_to_look_back=0):
    from poms.users.utils import get_master_user_from_context
    from poms.instruments.models import PriceHistory, PricingPolicy

    try:
        days_to_look_back = int(days_to_look_back)
    except TypeError:
        raise ExpressionEvalError('Invalid Days To Look Back Value')

    context = evaluator.context
    master_user = get_master_user_from_context(context)

    # TODO need master user check, security hole

    date = _parse_date(date)
    instrument = _safe_get_instrument(evaluator, instrument)

    master_user = get_master_user_from_context(context)

    pricing_policy_pk = None

    if isinstance(pricing_policy, dict):
        pricing_policy_pk = int(pricing_policy['id'])

    elif isinstance(pricing_policy, (int, float)):
        pricing_policy_pk = int(pricing_policy)

    elif isinstance(pricing_policy, str):
        pricing_policy_pk = PricingPolicy.objects.get(master_user=master_user, user_code=pricing_policy).id

    # print('formula pk %s' % pk)

    if pricing_policy_pk is None:
        raise ExpressionEvalError('Invalid Pricing Policy')

    if days_to_look_back == 0:

        try:

            result = PriceHistory.objects.get(date=date, instrument=instrument,
                                              pricing_policy_id=pricing_policy_pk)

            return result.accrued_price

        except PriceHistory.DoesNotExist:

            return default_value

    else:

        date_from = None
        date_to = None

        if days_to_look_back < 0:
            date_to = date
            date_from = date - datetime.timedelta(days=abs(days_to_look_back))

        else:
            date_from = date
            date_to = date + datetime.timedelta(days=abs(days_to_look_back))

        print('_get_price_history_accrued_price date_from %s' % date_from)
        print('_get_price_history_accrued_price date_to %s' % date_to)

        prices = PriceHistory.objects.filter(date__gte=date_from, date_lte=date_to,
                                             instrument=instrument,
                                             pricing_policy_id=pricing_policy_pk).order_by('-date')

        if len(prices):
            return prices[0].defaul_value
        else:
            return default_value


_get_price_history_accrued_price.evaluator = True


def _get_next_coupon_date(evaluator, date, instrument):
    from poms.users.utils import get_master_user_from_context

    context = evaluator.context
    master_user = get_master_user_from_context(context)

    # TODO need master user check, security hole

    date = _parse_date(date)
    instrument = _safe_get_instrument(evaluator, instrument)

    master_user = get_master_user_from_context(context)

    items = instrument.get_future_coupons(begin_date=date, with_maturity=False)

    if len(items):
        next_date = items[0]

        return next_date[0]

    return None


_get_next_coupon_date.evaluator = True


def _get_factor_schedule(evaluator, date, instrument):
    from poms.users.utils import get_master_user_from_context
    from poms.instruments.models import InstrumentFactorSchedule

    context = evaluator.context
    master_user = get_master_user_from_context(context)

    instrument = _safe_get_instrument(evaluator, instrument)

    # TODO need master user check, security hole

    try:
        result = InstrumentFactorSchedule.objects.get(effective_date=date, instrument=instrument)
    except (InstrumentFactorSchedule.DoesNotExist, KeyError):
        result = None

    if result is None:

        results = InstrumentFactorSchedule.objects.filter(effective_date__lte=date, instrument=instrument).order_by(
            '-effective_date')

        if len(list(results)):
            result = results[0]
        else:
            result = None

    if result is not None and result.factor_value:
        return result.factor_value

    return 1


_get_factor_schedule.evaluator = True


def _safe_get_pricing_policy(evaluator, pricing_policy):
    from poms.users.utils import get_master_user_from_context, get_member_from_context
    from poms.instruments.models import PricingPolicy

    if isinstance(pricing_policy, PricingPolicy):
        return pricing_policy

    context = evaluator.context

    if context is None:
        raise InvalidExpression('Context must be specified')

    pk = None
    user_code = None

    if isinstance(pricing_policy, dict):
        pk = int(pricing_policy['id'])

    elif isinstance(pricing_policy, (int, float)):
        pk = int(pricing_policy)

    elif isinstance(pricing_policy, str):
        user_code = pricing_policy

    if id is None and user_code is None:
        raise ExpressionEvalError('Invalid pricing policy')

    master_user = get_master_user_from_context(context)
    member = get_member_from_context(context)

    if master_user is None:
        raise ExpressionEvalError('master user in context does not find')

    pricing_policy_qs = PricingPolicy.objects.filter(master_user=master_user)

    try:
        if pk is not None:
            pricing_policy = pricing_policy_qs.get(pk=pk)

        elif user_code is not None:
            pricing_policy = pricing_policy_qs.get(user_code=user_code)

    except PricingPolicy.DoesNotExist:
        raise ExpressionEvalError()

    return pricing_policy


def _safe_get_currency(evaluator, currency):
    from poms.users.utils import get_master_user_from_context, get_member_from_context
    from poms.currencies.models import Currency

    if isinstance(currency, Currency):
        return currency

    context = evaluator.context

    if context is None:
        raise InvalidExpression('Context must be specified')

    pk = None
    user_code = None

    if isinstance(currency, dict):
        pk = int(currency['id'])

    elif isinstance(currency, (int, float)):
        pk = int(currency)

    elif isinstance(currency, str):
        user_code = currency

    if id is None and user_code is None:
        raise ExpressionEvalError('Invalid currency')

    master_user = get_master_user_from_context(context)
    member = get_member_from_context(context)

    if master_user is None:
        raise ExpressionEvalError('master user in context does not find')

    currency_qs = Currency.objects.filter(master_user=master_user)

    try:
        if pk is not None:
            currency = currency_qs.get(pk=pk)

        elif user_code is not None:
            currency = currency_qs.get(user_code=user_code)

    except Currency.DoesNotExist:
        raise ExpressionEvalError()

    return currency


def _safe_get_instrument(evaluator, instrument):
    from poms.users.utils import get_master_user_from_context, get_member_from_context
    from poms.instruments.models import Instrument
    from poms.obj_perms.utils import obj_perms_filter_objects, get_view_perms

    if isinstance(instrument, Instrument):
        return instrument

    context = evaluator.context

    if context is None:
        raise InvalidExpression('Context must be specified')

    pk = None
    user_code = None

    if isinstance(instrument, dict):
        pk = int(instrument['id'])

    elif isinstance(instrument, (int, float)):
        pk = int(instrument)

    elif isinstance(instrument, str):
        user_code = instrument

    if id is None and user_code is None:
        raise ExpressionEvalError('Invalid instrument')

    if pk is not None:
        instrument = context.get(('_instrument_get_accrued_price', pk, None), None)

    elif user_code is not None:
        instrument = context.get(('_instrument_get_accrued_price', None, user_code), None)

    if instrument is None:
        master_user = get_master_user_from_context(context)
        member = get_member_from_context(context)

        if master_user is None:
            raise ExpressionEvalError('master user in context does not find')

        instrument_qs = Instrument.objects.filter(master_user=master_user)
        instrument_qs = obj_perms_filter_objects(member, get_view_perms(Instrument), instrument_qs)

        try:
            if pk is not None:
                instrument = instrument_qs.get(pk=pk)

            elif user_code is not None:
                instrument = instrument_qs.get(user_code=user_code)

        except Instrument.DoesNotExist:
            raise ExpressionEvalError()

        context[('_instrument_get_accrued_price', instrument.pk, None)] = instrument
        context[('_instrument_get_accrued_price', None, instrument.user_code)] = instrument

    return instrument


def _get_currency(evaluator, currency):
    try:

        currency = _safe_get_currency(evaluator, currency)

        context = evaluator.context

        from poms.currencies.serializers import CurrencySerializer
        return CurrencySerializer(instance=currency, context=context).data
    except Exception as e:
        return None


_get_currency.evaluator = True


def _get_instrument(evaluator, instrument):
    try:
        instrument = _safe_get_instrument(evaluator, instrument)

        context = evaluator.context

        from poms.instruments.serializers import InstrumentSerializer
        return InstrumentSerializer(instance=instrument, context=context).data

    except Exception as e:
        return None


_get_instrument.evaluator = True


def _set_instrument_field(evaluator, instrument, parameter_name, parameter_value):
    context = evaluator.context

    instrument = _safe_get_instrument(evaluator, instrument)

    try:
        if isinstance(parameter_value, dict):
            parameter_name = parameter_name + '_id'
            parameter_value = parameter_value['id']

        setattr(instrument, parameter_name, parameter_value)
        instrument.save()
    except AttributeError:

        raise InvalidExpression('Invalid Property')


_set_instrument_field.evaluator = True


def _set_currency_field(evaluator, currency, parameter_name, parameter_value):
    context = evaluator.context

    currency = _safe_get_currency(evaluator, currency)

    try:
        setattr(currency, parameter_name, parameter_value)
        currency.save()
    except AttributeError:
        raise InvalidExpression('Invalid Property')


_set_currency_field.evaluator = True


def _get_instrument_field(evaluator, instrument, parameter_name):
    context = evaluator.context

    instrument = _safe_get_instrument(evaluator, instrument)

    result = None

    try:
        result = getattr(instrument, parameter_name, None)
    except AttributeError:
        raise InvalidExpression('Invalid Property')

    return result


_get_instrument_field.evaluator = True


def _get_currency_field(evaluator, currency, parameter_name):
    context = evaluator.context

    currency = _safe_get_currency(evaluator, currency)

    result = None

    try:
        result = getattr(currency, parameter_name, None)
    except AttributeError:
        raise InvalidExpression('Invalid Property')

    return result


_get_currency_field.evaluator = True


def _get_instrument_user_attribute_value(evaluator, instrument, attribute_user_code):
    from poms.users.utils import get_master_user_from_context
    from poms.instruments.models import Instrument
    from poms.obj_attrs.models import GenericAttributeType, GenericAttribute
    from django.contrib.contenttypes.models import ContentType

    # print('formula instrument %s' % instrument)
    # print('formula attribute_user_code %s' % attribute_user_code)

    if isinstance(instrument, Instrument):
        return instrument

    context = evaluator.context

    if context is None:
        raise InvalidExpression('Context must be specified')

    if attribute_user_code is None:
        raise InvalidExpression('User code is not set')

    pk = None

    master_user = get_master_user_from_context(context)

    if isinstance(instrument, dict):
        pk = int(instrument['id'])

    elif isinstance(instrument, (int, float)):
        pk = int(instrument)

    elif isinstance(instrument, str):
        pk = Instrument.objects.get(master_user=master_user, user_code=instrument).id

    # print('formula pk %s' % pk)

    if pk is None:
        raise ExpressionEvalError('Invalid instrument')

    attribute_type = None
    attribute = None

    try:
        attribute_type = GenericAttributeType.objects.get(master_user=master_user, user_code=attribute_user_code,
                                                          content_type=ContentType.objects.get_for_model(Instrument))
    except GenericAttributeType.DoesNotExist:
        raise ExpressionEvalError('Attribute type is not found')

    # print('formula attribute_type %s ' % attribute_type)

    try:
        attribute = GenericAttribute.objects.get(attribute_type=attribute_type, object_id=pk,
                                                 content_type=ContentType.objects.get_for_model(Instrument))
    except GenericAttribute.DoesNotExist:
        raise ExpressionEvalError('Attribute is not found')

    # print('formula attribute %s' % attribute)

    if attribute_type.value_type == GenericAttributeType.STRING:
        return attribute.value_string

    if attribute_type.value_type == GenericAttributeType.NUMBER:
        return attribute.value_float

    if attribute_type.value_type == GenericAttributeType.CLASSIFIER:
        if attribute.classifier:
            return attribute.classifier.name
        else:
            raise ExpressionEvalError('Classifier is not exist')

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
    try:
        result = 0

        context = evaluator.context

        from poms.users.utils import get_master_user_from_context
        from poms.transactions.models import Transaction
        master_user = get_master_user_from_context(context)

        instrument = _safe_get_instrument(evaluator, instrument)
        date = _parse_date(date)

        transactions = Transaction.objects.filter(master_user=master_user, accounting_date__lte=date,
                                                  instrument=instrument)

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
        _l.error('_get_position_size_on_date exception occurred %s' % e)
        _l.error(traceback.format_exc())
        return 0


_get_position_size_on_date.evaluator = True


def _get_instrument_report_data(evaluator, instrument, report_date, report_currency=None, pricing_policy=None,
                                cost_method="AVCO", accounts=None, portfolios=None):
    try:
        result = 0

        context = evaluator.context

        from poms.users.utils import get_master_user_from_context, get_member_from_context
        from poms.transactions.models import Transaction
        master_user = get_master_user_from_context(context)
        member = get_member_from_context(context)

        instrument = _safe_get_instrument(evaluator, instrument)

        from poms.reports.sql_builders.balance import BalanceReportBuilderSql
        from poms.reports.serializers import BalanceReportSerializer
        from poms.reports.common import Report
        from poms.instruments.models import Instrument

        from poms.users.models import EcosystemDefault
        ecosystem_default = EcosystemDefault.objects.get(master_user=master_user)

        currency = _safe_get_currency(evaluator, report_currency)
        if pricing_policy:
            pricing_policy = _safe_get_pricing_policy(evaluator, pricing_policy)
        else:
            pricing_policy = ecosystem_default.pricing_policy

        from poms.instruments.models import CostMethod
        cost_method = CostMethod.objects.get(user_code=cost_method)

        _l.info('_calculate_balance_report master_user %s' % master_user)
        _l.info('_calculate_balance_report member %s' % member)
        _l.info('_calculate_balance_report report_date  %s' % report_date)
        _l.info('_calculate_balance_report currency %s' % currency)

        report_date_d = datetime.datetime.strptime(report_date, "%Y-%m-%d").date()

        from poms.portfolios.models import Portfolio
        from poms.accounts.models import Account

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
            save_report=True
        )

        builder = BalanceReportBuilderSql(instance=instance)
        instance = builder.build_balance()

        serializer = BalanceReportSerializer(instance=instance, context=context)

        data = serializer.to_representation(instance)

        for item in data['items']:

            if item['instrument'] == instrument.id:
                result = item

        return result

    except Exception as e:
        _l.error('_get_instrument_report_data exception occurred %s' % e)
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
    val = instrument.get_accrual_factor(date)
    return _check_float(val)


_get_instrument_accrual_factor.evaluator = True


def _get_instrument_coupon(evaluator, instrument, date):
    try:

        _l.info("_get_instrument_coupon instrument %s" % instrument)
        _l.info("_get_instrument_coupon date %s" % date)

        if instrument is None or date is None:
            return 0.0
        instrument = _safe_get_instrument(evaluator, instrument)
        date = _parse_date(date)
        cpn_val, is_cpn = instrument.get_coupon(date, with_maturity=False)

        _l.info("_get_instrument_coupon cpn_val %s" % cpn_val)

        return _check_float(cpn_val)

    except Exception as e:
        _l.info('_get_instrument_coupon exception occurred %s' % e)
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

        item = EcosystemDefault.objects.get(master_user=master_user)

        return item.portfolio_id

    except Exception as e:
        print("get_default_portfolio error %s" % e)

    return None


_get_default_portfolio.evaluator = True


def _get_default_instrument(evaluator):
    from poms.users.utils import get_master_user_from_context

    context = evaluator.context

    master_user = get_master_user_from_context(context)

    from poms.users.models import EcosystemDefault

    try:

        item = EcosystemDefault.objects.get(master_user=master_user)

        return item.instrument_id

    except Exception as e:
        print("get_default_instrument error %s" % e)

    return None


_get_default_instrument.evaluator = True


def _get_default_account(evaluator):
    from poms.users.utils import get_master_user_from_context

    context = evaluator.context

    master_user = get_master_user_from_context(context)

    from poms.users.models import EcosystemDefault

    try:

        item = EcosystemDefault.objects.get(master_user=master_user)

        return item.account_id

    except Exception as e:
        print("get_default_account error %s" % e)

    return None


_get_default_account.evaluator = True


def _get_default_currency(evaluator):
    from poms.users.utils import get_master_user_from_context

    context = evaluator.context

    master_user = get_master_user_from_context(context)

    from poms.users.models import EcosystemDefault

    try:

        item = EcosystemDefault.objects.get(master_user=master_user)

        return item.currency_id

    except Exception as e:
        print("get_default_currency error %s" % e)

    return None


_get_default_currency.evaluator = True


def _get_default_transaction_type(evaluator):
    from poms.users.utils import get_master_user_from_context

    context = evaluator.context

    master_user = get_master_user_from_context(context)

    from poms.users.models import EcosystemDefault

    try:

        item = EcosystemDefault.objects.get(master_user=master_user)

        return item.transaction_type_id

    except Exception as e:
        print("get_default_transaction_type error %s" % e)

    return None


_get_default_transaction_type.evaluator = True


def _get_default_instrument_type(evaluator):
    from poms.users.utils import get_master_user_from_context

    context = evaluator.context

    master_user = get_master_user_from_context(context)

    from poms.users.models import EcosystemDefault

    try:

        item = EcosystemDefault.objects.get(master_user=master_user)

        return item.instrument_type_id

    except Exception as e:
        print("get_default_instrument_type error %s" % e)

    return None


_get_default_instrument_type.evaluator = True


def _get_default_account_type(evaluator):
    from poms.users.utils import get_master_user_from_context

    context = evaluator.context

    master_user = get_master_user_from_context(context)

    from poms.users.models import EcosystemDefault

    try:

        item = EcosystemDefault.objects.get(master_user=master_user)

        return item.account_type_id

    except Exception as e:
        print("get_default_account_type error %s" % e)

    return None


_get_default_account_type.evaluator = True


def _get_default_pricing_policy(evaluator):
    from poms.users.utils import get_master_user_from_context

    context = evaluator.context

    master_user = get_master_user_from_context(context)

    from poms.users.models import EcosystemDefault

    try:

        item = EcosystemDefault.objects.get(master_user=master_user)

        return item.pricing_policy_id

    except Exception as e:
        print("get_default_pricing_policy error %s" % e)

    return None


_get_default_pricing_policy.evaluator = True


def _get_default_responsible(evaluator):
    from poms.users.utils import get_master_user_from_context

    context = evaluator.context

    master_user = get_master_user_from_context(context)

    from poms.users.models import EcosystemDefault

    try:

        item = EcosystemDefault.objects.get(master_user=master_user)

        return item.responsible_id

    except Exception as e:
        print("get_default_responsible error %s" % e)

    return None


_get_default_responsible.evaluator = True


def _get_default_counterparty(evaluator):
    from poms.users.utils import get_master_user_from_context

    context = evaluator.context

    master_user = get_master_user_from_context(context)

    from poms.users.models import EcosystemDefault

    try:

        item = EcosystemDefault.objects.get(master_user=master_user)

        return item.counterparty_id

    except Exception as e:
        print("get_default_counterparty error %s" % e)

    return None


_get_default_counterparty.evaluator = True


def _get_default_strategy1(evaluator):
    from poms.users.utils import get_master_user_from_context

    context = evaluator.context

    master_user = get_master_user_from_context(context)

    from poms.users.models import EcosystemDefault

    try:

        item = EcosystemDefault.objects.get(master_user=master_user)

        return item.strategy1_id

    except Exception as e:
        print("get_default_strategy1 error %s" % e)

    return None


_get_default_strategy1.evaluator = True


def _get_default_strategy2(evaluator):
    from poms.users.utils import get_master_user_from_context

    context = evaluator.context

    master_user = get_master_user_from_context(context)

    from poms.users.models import EcosystemDefault

    try:

        item = EcosystemDefault.objects.get(master_user=master_user)

        return item.strategy2_id

    except Exception as e:
        print("get_default_strategy2 error %s" % e)

    return None


_get_default_strategy2.evaluator = True


def _get_default_strategy3(evaluator):
    from poms.users.utils import get_master_user_from_context

    context = evaluator.context

    master_user = get_master_user_from_context(context)

    from poms.users.models import EcosystemDefault

    try:

        item = EcosystemDefault.objects.get(master_user=master_user)

        return item.strategy3_id

    except Exception as e:
        print("get_default_strategy3 error %s" % e)

    return None


_get_default_strategy3.evaluator = True


def _create_task(evaluator, name, type='user_task', options=None, function_name=None, notes=None, **kwargs):
    _l.info('_create_task task_name: %s' % name)

    try:

        from poms.celery_tasks.models import CeleryTask

        context = evaluator.context
        from poms.users.utils import get_master_user_from_context
        from poms.users.utils import get_member_from_context

        master_user = get_master_user_from_context(context)
        member = get_member_from_context(context)

        celery_task = CeleryTask.objects.create(master_user=master_user,
                                                member=member,
                                                verbose_name=name,
                                                function_name=function_name,
                                                type=type)

        celery_task.options_object = options
        celery_task.save()

        return celery_task.id

    except Exception as e:
        _l.debug("_create_task.exception %s" % e)


_create_task.evaluator = True


def _update_task(evaluator, id, name, type=None, status='P', options=None, notes=None, error_message=None, result=None,
                 **kwargs):
    _l.info('_create_task task_name: %s' % name)

    try:

        from poms.celery_tasks.models import CeleryTask

        context = evaluator.context
        from poms.users.utils import get_master_user_from_context
        from poms.users.utils import get_member_from_context

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
        _l.debug("_create_task.exception %s" % e)


_update_task.evaluator = True


def _run_task(evaluator, task_name, options={}):
    _l.info('_run_task task_name: %s' % task_name)

    try:

        from poms_app import celery_app

        celery_app.send_task(task_name, kwargs=options)

    except Exception as e:
        _l.debug("_run_task.exception %s" % e)


_run_task.evaluator = True


def _run_pricing_procedure(evaluator, user_code, **kwargs):
    try:
        from poms.users.utils import get_master_user_from_context
        from poms.users.utils import get_member_from_context
        from poms.procedures.models import PricingProcedure
        from poms.pricing.handlers import PricingProcedureProcess

        context = evaluator.context

        master_user = get_master_user_from_context(context)
        member = get_member_from_context(context)

        procedure = PricingProcedure.objects.get(master_user=master_user, user_code=user_code)

        instance = PricingProcedureProcess(procedure=procedure, master_user=master_user, member=member, **kwargs)
        instance.process()


    except Exception as e:
        _l.debug("_run_pricing_procedure.exception %s" % e)
        raise Exception(e)


_run_pricing_procedure.evaluator = True


def _run_data_procedure(evaluator, user_code, user_context=None, linked_task_kwargs=None, **kwargs):
    _l.info('_run_data_procedure')

    try:
        from poms.users.utils import get_master_user_from_context
        from poms.users.utils import get_member_from_context
        from poms.procedures.models import RequestDataFileProcedure
        from poms.procedures.handlers import DataProcedureProcess
        from poms.procedures.tasks import run_data_procedure_from_formula

        context = evaluator.context

        master_user = get_master_user_from_context(context)
        member = get_member_from_context(context)

        _l.info('_run_data_procedure.context %s' % context)

        procedure_kwargs = {
            'master_user_id': master_user.id,
            'member_id': member.id,
            'user_code': user_code,
            'user_context': user_context,

        }
        procedure_kwargs.update(kwargs)

        link = []

        if linked_task_kwargs:
            link = [run_data_procedure_from_formula.apply_async(kwargs=linked_task_kwargs)]

        run_data_procedure_from_formula.apply_async(kwargs=procedure_kwargs, link=link)

        #
        # merged_context = {}
        # merged_context.update(context)
        #
        # if 'names' not in merged_context:
        #     merged_context['names'] = {}
        #
        # if user_context:
        #     merged_context['names'].update(user_context)
        #
        # _l.info('merged_context %s' % merged_context)
        #
        # procedure = RequestDataFileProcedure.objects.get(master_user=master_user, user_code=user_code)
        #
        # kwargs.pop('user_context', None)
        #
        # instance = DataProcedureProcess(procedure=procedure, master_user=master_user, member=member,
        #                                            context=merged_context, **kwargs)
        # instance.process()


    except Exception as e:
        _l.error("_run_data_procedure.exception %s" % e)
        _l.error("_run_data_procedure.exception traceback %s" % traceback.format_exc())
        raise Exception(e)


_run_data_procedure.evaluator = True


def _run_data_procedure_sync(evaluator, user_code, user_context=None, **kwargs):
    _l.info('_run_data_procedure_sync')

    try:
        from poms.users.utils import get_master_user_from_context
        from poms.users.utils import get_member_from_context
        from poms.procedures.models import RequestDataFileProcedure
        from poms.procedures.handlers import DataProcedureProcess
        from poms.procedures.tasks import run_data_procedure_from_formula

        context = evaluator.context

        master_user = get_master_user_from_context(context)
        member = get_member_from_context(context)

        merged_context = {}
        merged_context.update(context)

        if 'names' not in merged_context:
            merged_context['names'] = {}

        if user_context:
            merged_context['names'].update(user_context)

        _l.info('merged_context %s' % merged_context)

        procedure = RequestDataFileProcedure.objects.get(master_user=master_user, user_code=user_code)

        kwargs.pop('user_context', None)

        instance = DataProcedureProcess(procedure=procedure, master_user=master_user, member=member,
                                        context=merged_context, **kwargs)
        instance.process()


    except Exception as e:
        _l.error("_run_data_procedure_sync.exception %s" % e)
        _l.error("_run_data_procedure_sync.exception traceback %s" % traceback.format_exc())
        raise Exception(e)


_run_data_procedure_sync.evaluator = True


def _rebook_transaction(evaluator, code, values=None, user_context=None, **kwargs):
    _l.info('_rebook_transaction')

    try:
        from poms.users.utils import get_master_user_from_context
        from poms.users.utils import get_member_from_context
        from poms.procedures.models import RequestDataFileProcedure
        from poms.procedures.handlers import DataProcedureProcess
        from poms.transactions.handlers import TransactionTypeProcess
        from poms.transactions.models import ComplexTransaction
        from poms.transactions.serializers import TransactionTypeProcessSerializer

        context = evaluator.context

        master_user = get_master_user_from_context(context)
        member = get_member_from_context(context)

        _l.info('_rebook_transaction.context %s' % context)

        merged_context = {}
        merged_context.update(context)

        if 'names' not in merged_context:
            merged_context['names'] = {}

        if user_context:
            merged_context['names'].update(user_context)

        _l.info('_rebook_transaction.merged_context %s' % merged_context)

        try:

            complex_transaction = ComplexTransaction.objects.get(code=code)

            _l.debug('_rebook_transaction.get complex transaction %s' % complex_transaction)

            instance = TransactionTypeProcess(transaction_type=complex_transaction.transaction_type,
                                              process_mode='rebook',
                                              complex_transaction=complex_transaction,
                                              context=merged_context, member=member)

            serializer = TransactionTypeProcessSerializer(instance=instance, context=merged_context)

            data = serializer.data

            # _l.debug('_rebook_transaction.get data to fill rebook processor %s' % data)

            instance = TransactionTypeProcess(transaction_type=complex_transaction.transaction_type,
                                              process_mode='rebook',
                                              complex_transaction=complex_transaction,
                                              complex_transaction_status=ComplexTransaction.PRODUCTION,
                                              context=merged_context,
                                              member=member)

            if not values:
                values = {}

            data['values'] = dict(data['values'])

            data['values'].update(values)

            _l.debug('_rebook_transaction.get data to fill with values %s' % values)
            _l.debug('_rebook_transaction.get data to fill with result values %s' % data['values'])

            # _l.info('_rebook_transaction.data %s' % data)

            serializer = TransactionTypeProcessSerializer(instance=instance, data=data, context=merged_context)
            serializer.is_valid(raise_exception=True)
            serializer.save()

        except Exception as e:

            _l.error("_rebook_transaction. could not rebook exception %s" % e)
            _l.error("_rebook_transaction. could not rebook traceback %s" % traceback.format_exc())


    except Exception as e:
        _l.error("_rebook_transaction. general exception %s" % e)
        _l.error("_rebook_transaction. general exception traceback %s" % traceback.format_exc())


_rebook_transaction.evaluator = True


def _download_instrument_from_finmars_database(evaluator, reference, instrument_name=None,
                                               instrument_type_user_code=None):
    _l.info('_download_instrument_from_finmars_database formula')

    try:

        from poms.users.utils import get_master_user_from_context
        from poms.users.utils import get_member_from_context
        from poms.integrations.tasks import download_instrument_finmars_database_async
        from poms.celery_tasks.models import CeleryTask

        context = evaluator.context

        master_user = get_master_user_from_context(context)
        member = get_member_from_context(context)

        task = CeleryTask.objects.create(
            master_user=master_user,
            member=member,
            verbose_name="Download Instrument From Finmars Database",
            type='download_instrument_from_finmars_database'
        )

        options = {
            'reference': reference,
        }

        if instrument_name:
            options['instrument_name'] = instrument_name

        if instrument_type_user_code:
            options['instrument_type_user_code'] = instrument_type_user_code

        task.options_object = options
        task.save()

        _l.info('_download_instrument_from_finmars_database. task created init a process')

        download_instrument_finmars_database_async.apply_async(kwargs={'task_id': task.id})

    except Exception as e:
        _l.error("_download_instrument_from_finmars_database. general exception %s" % e)
        _l.error("_download_instrument_from_finmars_database. general exception traceback %s" % traceback.format_exc())


_download_instrument_from_finmars_database.evaluator = True


def _create_workflow(evaluator, name=None):
    from django.db import transaction

    with transaction.atomic():
        from poms.workflows.models import Workflow

        from poms.users.utils import get_master_user_from_context
        from poms.users.utils import get_member_from_context

        context = evaluator.context

        master_user = get_master_user_from_context(context)
        member = get_member_from_context(context)

        if not name:
            name = 'Workflow ' + str((Workflow.objects.all().count() + 1))

        workflow = Workflow.objects.create(name=name, master_user=master_user, member=member, current_step=1)

        return workflow.id


_create_workflow.evaluator = True


def _register_workflow_step(evaluator, workflow_id, code, name=None):
    from django.db import transaction

    with transaction.atomic():
        from poms.workflows.models import Workflow, WorkflowStep

        workflow = Workflow.objects.get(id=workflow_id)

        order = WorkflowStep.objects.filter(workflow_id=workflow_id).count() + 1

        if not name:
            name = workflow.name + ' step ' + str((order))

        code_txt = ast.unparse(code.node)

        workflow_step = WorkflowStep.objects.create(workflow_id=workflow_id, code=code_txt, name=name, order=order)

        return workflow_step.id


_register_workflow_step.evaluator = True


def _run_workflow(evaluator, workflow_id):
    from poms.workflows.tasks import run_workflow_step

    # workflow = Workflow.objects.get(id=workflow_id)
    from django.db import transaction

    transaction.on_commit(lambda: run_workflow_step.apply_async(kwargs={"workflow_id": workflow_id}))


_run_workflow.evaluator = True


def _get_filenames_from_storage(evaluator, pattern=None, path_to_folder=None):
    # pattern \.txt$

    from poms.users.utils import get_master_user_from_context
    from poms.users.utils import get_member_from_context
    from poms.common.storage import get_storage
    storage = get_storage()

    context = evaluator.context

    master_user = get_master_user_from_context(context)
    member = get_member_from_context(context)

    # TODO check that file could be placed either in public or member home folder

    if not path_to_folder:
        path_to_folder = settings.BASE_API_URL
    else:

        if path_to_folder[0] == '/':
            path_to_folder = settings.BASE_API_URL + path_to_folder
        else:
            path_to_folder = settings.BASE_API_URL + '/' + path_to_folder

    print('path_to_folder %s' % path_to_folder)

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

    from poms.users.utils import get_master_user_from_context
    from poms.users.utils import get_member_from_context
    from poms.common.storage import get_storage
    storage = get_storage()

    context = evaluator.context

    master_user = get_master_user_from_context(context)
    member = get_member_from_context(context)

    # TODO check that file could be placed either in public or member home folder

    if not path:
        path = settings.BASE_API_URL
    else:

        if path[0] == '/':
            path = settings.BASE_API_URL + path
        else:
            path = settings.BASE_API_URL + '/' + path

    try:
        storage.delete(path)
        return True
    except Exception as e:
        _l.error("_delete_file_from_storage %s" % e)
        return False


_delete_file_from_storage.evaluator = True


def _put_file_to_storage(evaluator, path, content):
    # pattern \.txt$

    from poms.users.utils import get_master_user_from_context
    from poms.users.utils import get_member_from_context
    from poms.common.storage import get_storage
    storage = get_storage()

    context = evaluator.context

    master_user = get_master_user_from_context(context)
    member = get_member_from_context(context)

    # TODO check that file could be placed either in public or member home folder

    if not path:
        path = settings.BASE_API_URL
    else:

        if path[0] == '/':
            path = settings.BASE_API_URL + path
        else:
            path = settings.BASE_API_URL + '/' + path

    if settings.BASE_API_URL + '/import/' not in path:

        try:
            from django.core.files.base import ContentFile
            storage.save(path, ContentFile(content.encode('utf-8')))
            return True
        except Exception as e:
            _l.error("_put_file_to_storage %s" % e)
            return False

    else:
        _l.error("_put_file_to_storage could not put files in import folder")
        return False


_put_file_to_storage.evaluator = True


def _run_data_import(evaluator, filepath, scheme):
    try:

        _l.info('_run_data_import %s' % filepath)

        if filepath[0] == '/':
            filepath = settings.BASE_API_URL + filepath
        else:
            filepath = settings.BASE_API_URL + '/' + filepath

        from poms.users.utils import get_master_user_from_context
        from poms.users.utils import get_member_from_context
        from poms.csv_import.models import CsvImportScheme
        from poms.celery_tasks.models import CeleryTask
        from poms.csv_import.tasks import data_csv_file_import

        context = evaluator.context

        master_user = get_master_user_from_context(context)
        member = get_member_from_context(context)

        celery_task = CeleryTask.objects.create(master_user=master_user, member=member, type='simple_import',
                                                verbose_name="Simple Import")
        celery_task.status = CeleryTask.STATUS_DONE

        scheme = CsvImportScheme.objects.get(master_user=master_user,
                                             user_code=scheme)

        options_object = {}

        options_object['file_path'] = filepath
        options_object['filename'] = ''
        options_object['scheme_id'] = scheme.id
        options_object['execution_context'] = None

        celery_task.options_object = options_object
        celery_task.save()

        data_csv_file_import.apply(kwargs={'task_id': celery_task.id})

        return None

    except Exception as e:
        _l.error("_run_data_import. general exception %s" % e)
        _l.error("_run_data_import. general exception traceback %s" % traceback.format_exc())


_run_data_import.evaluator = True


def _run_transaction_import(evaluator, filepath, scheme):
    try:

        _l.info('_run_transaction_import %s' % filepath)

        if filepath[0] == '/':
            filepath = settings.BASE_API_URL + filepath
        else:
            filepath = settings.BASE_API_URL + '/' + filepath

        # pattern \.txt$

        from poms.workflows.models import Workflow, WorkflowStep

        from poms.users.utils import get_master_user_from_context
        from poms.users.utils import get_member_from_context
        from poms.common.storage import get_storage
        storage = get_storage()

        context = evaluator.context

        master_user = get_master_user_from_context(context)
        member = get_member_from_context(context)

        from poms.users.utils import get_master_user_from_context
        from poms.users.utils import get_member_from_context
        from poms.integrations.models import ComplexTransactionImportScheme
        from poms.celery_tasks.models import CeleryTask
        from poms.transaction_import.tasks import transaction_import

        context = evaluator.context

        master_user = get_master_user_from_context(context)
        member = get_member_from_context(context)

        celery_task = CeleryTask.objects.create(master_user=master_user, member=member,
                                                type='transaction_import',
                                                verbose_name="Transaction Import by %s" % member.username)
        celery_task.status = CeleryTask.STATUS_DONE

        scheme = ComplexTransactionImportScheme.objects.get(master_user=master_user,
                                                            user_code=scheme)

        options_object = {}

        options_object['file_path'] = filepath
        options_object['filename'] = ''
        options_object['scheme_id'] = scheme.id
        options_object['execution_context'] = None

        celery_task.options_object = options_object
        celery_task.save()

        transaction_import.apply(kwargs={'task_id': celery_task.id})

        return None

    except Exception as e:
        _l.error("_run_transaction_import. general exception %s" % e)
        _l.error("_run_transaction_import. general exception traceback %s" % traceback.format_exc())


_run_transaction_import.evaluator = True


def _simple_group(val, ranges, default=None):
    for begin, end, text in ranges:
        if begin is None:
            begin = float('-inf')
        else:
            begin = float(begin)

        if end is None:
            end = float('inf')
        else:
            end = float(end)

        if begin < val <= end:
            return text

    return default


def _date_group(evaluator, val, ranges, default=None):
    val = _parse_date(val)

    # _l.debug('_date_group: val=%s', val)

    def _make_name(begin, end, fmt):
        # if end != datetime.date.max:
        #     end -= datetime.timedelta(days=1)
        if isinstance(fmt, (list, tuple)):
            ifmt = iter(fmt)
            s1 = str(next(ifmt, '') or '')
            begin_fmt = str(next(ifmt, '') or '')
            s3 = str(next(ifmt, '') or '')
            s4 = str(next(ifmt, '') or '')
            end_fmt = str(next(ifmt, '') or '')
            s6 = str(next(ifmt, '') or '')
            sbegin = _format_date(begin, begin_fmt) if begin_fmt else ''
            send = _format_date(end, end_fmt) if end_fmt else ''
            ret = ''.join([s1, sbegin, s3, s4, send, s6])
        else:
            ret = str(fmt)
        if evaluator.context.get('date_group_with_dates', False):
            return ret, begin, end
        return ret

    for begin, end, step, fmt in ranges:
        evaluator.check_time()

        if not begin:
            # begin = datetime.date.min
            begin = datetime.date(1900, 1, 1)
        else:
            begin = _parse_date(begin)

        if not end:
            # end = datetime.date.max
            end = datetime.date(2100, 12, 31)
        else:
            end = _parse_date(end)

        if begin <= val <= end:
            if step:
                if not isinstance(step, (datetime.timedelta, relativedelta.relativedelta,)):
                    step = _timedelta(days=step)
                # _l.debug('start=%s, end=%s, step=%s', start, end, step)

                ld = begin
                while ld < end:
                    evaluator.check_time()
                    lbegin = ld
                    lend = ld + step - datetime.timedelta(days=1)
                    if lend > end:
                        lend = end
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
    return ''


def _random():
    return random.random()


def _uuid():
    return str(uuid.uuid4())


def _print_message(evaluator, text):
    context = evaluator.context

    if 'log' not in context:
        context['log'] = ''

    context['log'] = context['log'] + text + '\n'

    # _l.info("CONTEXT %s" % context)


_print_message.evaluator = True


def _print(message, *args, **kwargs):
    _l.debug(message, *args, **kwargs)


def _op_power(a, b):
    """ a limited exponent/to-the-power-of function, for safety reasons """
    if abs(a) > MAX_EXPONENT or abs(b) > MAX_EXPONENT:
        raise InvalidExpression("Invalid exponent, max exponent is %s" % MAX_EXPONENT)
    return a ** b


def _op_mult(a, b):
    # """ limit the number of times a string can be repeated... """
    # if isinstance(a, int) and a * len(b) > MAX_STRING_LENGTH:
    #         raise InvalidExpression("Sorry, a string that long is not allowed")
    #     elif isinstance(b, int) and b * len(a) > MAX_STRING_LENGTH:
    #         raise InvalidExpression("Sorry, a string that long is not allowed")
    if isinstance(a, str):
        raise TypeError("Can't convert '%s' object to str implicitly" % type(a).__name__)
    if isinstance(b, str):
        raise TypeError("Can't convert '%s' object to str implicitly" % type(b).__name__)
    return a * b


def _op_add(a, b):
    """ string length limit again """
    if isinstance(a, str) and isinstance(b, str) and len(a) + len(b) > MAX_STR_LEN:
        raise InvalidExpression("Sorry, adding those two strings would make a too long string.")
    return a + b


def _op_lshift(a, b):
    if b > MAX_SHIFT:
        raise InvalidExpression("Invalid left shift, max left shift is %s" % MAX_SHIFT)
    return a << b


OPERATORS = {
    ast.Is: lambda a, b: a is b,
    ast.IsNot: lambda a, b: a is not b,
    ast.In: lambda a, b: a in b,
    ast.NotIn: lambda a, b: a not in b,
    ast.Add: _op_add,
    ast.BitAnd: lambda a, b: a & b,
    ast.BitOr: lambda a, b: a | b,
    ast.BitXor: lambda a, b: a ^ b,
    ast.Div: lambda a, b: a / b,
    ast.FloorDiv: lambda a, b: a // b,
    ast.LShift: _op_lshift,
    ast.RShift: lambda a, b: a >> b,
    ast.Mult: _op_mult,
    ast.Pow: _op_power,
    ast.Sub: lambda a, b: a - b,
    ast.Mod: lambda a, b: a % b,
    ast.And: lambda a, b: a and b,
    ast.Or: lambda a, b: a or b,
    ast.Eq: lambda a, b: a == b,
    ast.Gt: lambda a, b: a > b,
    ast.GtE: lambda a, b: a >= b,
    ast.Lt: lambda a, b: a < b,
    ast.LtE: lambda a, b: a <= b,
    ast.NotEq: lambda a, b: a != b,
    ast.Invert: lambda a: ~a,
    ast.Not: lambda a: not a,
    ast.UAdd: lambda a: +a,
    ast.USub: lambda a: -a
}


class SimpleEval2Def(object):
    def __init__(self, name, func):
        self.name = name
        self.func = func

    def __str__(self):
        return '<def %s>' % self.name

    def __repr__(self):
        return '<def %s>' % self.name

    def __call__(self, evaluator, *args, **kwargs):
        if getattr(self.func, 'evaluator', False):
            return self.func(evaluator, *args, **kwargs)
        else:
            return self.func(*args, **kwargs)


class _UserDef(object):
    def __init__(self, parent, node):
        self.parent = parent
        self.node = node

    def __str__(self):
        return '<def %s>' % self.node.name

    def __repr__(self):
        return '<def %s>' % self.node.name

    def __call__(self, evaluator, *args, **kwargs):
        kwargs = kwargs.copy()
        for i, val in enumerate(args):
            name = self.node.args.args[i].arg
            kwargs[name] = val

        offset = len(self.node.args.args) - len(self.node.args.defaults)
        for i, arg in enumerate(self.node.args.args):
            if arg.arg not in kwargs:
                val = self.parent._eval(self.node.args.defaults[i - offset])
                kwargs[arg.arg] = val

        save_table = self.parent._table
        try:
            self.parent._table = save_table.copy()
            self.parent._table.update(kwargs)
            try:
                ret = self.parent._eval(self.node.body)
            except _Return as e:
                ret = e.value
        finally:
            self.parent._table = save_table

        return ret


FUNCTIONS = [
    SimpleEval2Def('str', _str),
    SimpleEval2Def('substr', _substr),
    SimpleEval2Def('upper', _upper),
    SimpleEval2Def('lower', _lower),
    SimpleEval2Def('contains', _contains),
    SimpleEval2Def('replace', _replace),

    SimpleEval2Def('reg_search', _reg_search),
    SimpleEval2Def('reg_replace', _reg_replace),

    SimpleEval2Def('int', _int),
    SimpleEval2Def('float', _float),
    SimpleEval2Def('bool', _bool),
    SimpleEval2Def('round', _round),
    SimpleEval2Def('trunc', _trunc),
    SimpleEval2Def('abs', _abs),
    SimpleEval2Def('isclose', _isclose),
    SimpleEval2Def('random', _random),
    SimpleEval2Def('min', _min),
    SimpleEval2Def('max', _max),
    SimpleEval2Def('uuid', _uuid),
    SimpleEval2Def('print_message', _print_message),

    SimpleEval2Def('iff', _iff),
    SimpleEval2Def('len', _len),
    SimpleEval2Def('range', _range),

    SimpleEval2Def('now', _now),

    SimpleEval2Def('date', _date),
    SimpleEval2Def('date_min', _date_min),
    SimpleEval2Def('date_max', _date_max),
    SimpleEval2Def('isleap', _isleap),
    SimpleEval2Def('days', _days),
    SimpleEval2Def('weeks', _weeks),
    SimpleEval2Def('months', _months),
    SimpleEval2Def('timedelta', _timedelta),
    SimpleEval2Def('add_days', _add_days),
    SimpleEval2Def('add_weeks', _add_weeks),
    SimpleEval2Def('add_workdays', _add_workdays),

    SimpleEval2Def('format_date', _format_date),
    SimpleEval2Def('get_list_of_dates_between_two_dates', _get_list_of_dates_between_two_dates),
    SimpleEval2Def('parse_date', _parse_date),
    SimpleEval2Def('universal_parse_date', _universal_parse_date),
    SimpleEval2Def('unix_to_date', _unix_to_date),

    SimpleEval2Def('last_business_day', _last_business_day),
    SimpleEval2Def('get_date_last_week_end_business', _get_date_last_week_end_business),
    SimpleEval2Def('get_date_last_month_end_business', _get_date_last_month_end_business),
    SimpleEval2Def('get_date_last_quarter_end_business', _get_date_last_quarter_end_business),
    SimpleEval2Def('get_date_last_year_end_business', _get_date_last_year_end_business),
    # SimpleEval2Def('format_date2', _format_date2),
    # SimpleEval2Def('parse_date2', _parse_date2),

    SimpleEval2Def('format_number', _format_number),
    SimpleEval2Def('parse_number', _parse_number),
    SimpleEval2Def('join', _join),
    SimpleEval2Def('reverse', _reverse),
    SimpleEval2Def('split', _split),

    SimpleEval2Def('simple_price', _simple_price),

    SimpleEval2Def('get_instrument', _get_instrument),
    SimpleEval2Def('get_currency', _get_currency),

    SimpleEval2Def('get_currency_field', _get_currency_field),
    SimpleEval2Def('set_currency_field', _set_currency_field),

    SimpleEval2Def('get_instrument_field', _get_instrument_field),
    SimpleEval2Def('set_instrument_field', _set_instrument_field),

    SimpleEval2Def('get_instrument_accrual_size', _get_instrument_accrual_size),
    SimpleEval2Def('get_instrument_accrual_factor', _get_instrument_accrual_factor),
    SimpleEval2Def('calculate_accrued_price', _calculate_accrued_price),
    SimpleEval2Def('get_position_size_on_date', _get_position_size_on_date),
    SimpleEval2Def('get_instrument_report_data', _get_instrument_report_data),
    SimpleEval2Def('get_instrument_factor', _get_instrument_factor),
    SimpleEval2Def('get_instrument_coupon_factor', _get_instrument_coupon_factor),
    SimpleEval2Def('get_instrument_coupon', _get_instrument_coupon),

    SimpleEval2Def('get_fx_rate', _get_fx_rate),
    SimpleEval2Def('get_principal_price', _get_price_history_principal_price),
    SimpleEval2Def('get_accrued_price', _get_price_history_accrued_price),
    SimpleEval2Def('get_next_coupon_date', _get_next_coupon_date),
    SimpleEval2Def('get_factor', _get_factor_schedule),
    SimpleEval2Def('add_fx_rate', _add_fx_rate),
    SimpleEval2Def('add_price_history', _add_price_history),
    SimpleEval2Def('generate_user_code', _generate_user_code),
    SimpleEval2Def('get_latest_principal_price', _get_latest_principal_price),
    SimpleEval2Def('get_latest_principal_price_date', _get_latest_principal_price_date),
    SimpleEval2Def('get_latest_fx_rate', _get_latest_fx_rate),

    SimpleEval2Def('get_instrument_user_attribute_value', _get_instrument_user_attribute_value),

    SimpleEval2Def('get_ttype_default_input', _get_ttype_default_input),
    SimpleEval2Def('set_complex_transaction_input', _set_complex_transaction_input),
    SimpleEval2Def('set_complex_transaction_user_field', _set_complex_transaction_user_field),
    SimpleEval2Def('set_complex_transaction_form_data', _set_complex_transaction_form_data),
    SimpleEval2Def('get_relation_by_user_code', _get_relation_by_user_code),
    SimpleEval2Def('get_instruments', _get_instruments),
    SimpleEval2Def('get_currencies', _get_currencies),
    SimpleEval2Def('get_rt_value', _get_rt_value),
    SimpleEval2Def('convert_to_number', _convert_to_number),
    SimpleEval2Def('if_null', _if_null),
    SimpleEval2Def('send_system_message', _send_system_message),
    SimpleEval2Def('calculate_performance_report', _calculate_performance_report),
    SimpleEval2Def('calculate_balance_report', _calculate_balance_report),
    SimpleEval2Def('calculate_pl_report', _calculate_pl_report),
    SimpleEval2Def('get_current_member', _get_current_member),

    # SimpleEval2Def('get_instr_accrual_size', _get_instrument_accrual_size),
    # SimpleEval2Def('get_instr_accrual_factor', _get_instrument_accrual_factor),
    # SimpleEval2Def('get_instr_accrued_price', _get_instrument_accrued_price),
    # SimpleEval2Def('get_instr_factor', _get_instrument_factor),
    # SimpleEval2Def('get_instr_coupon_factor', _get_instrument_coupon_factor),
    # SimpleEval2Def('get_instr_coupon', _get_instrument_coupon),

    SimpleEval2Def('find_name', _find_name),

    SimpleEval2Def('simple_group', _simple_group),
    SimpleEval2Def('date_group', _date_group),

    SimpleEval2Def('has_var', _has_var),
    SimpleEval2Def('get_var', _get_var),

    SimpleEval2Def('get_default_portfolio', _get_default_portfolio),
    SimpleEval2Def('get_default_instrument', _get_default_instrument),
    SimpleEval2Def('get_default_account', _get_default_account),
    SimpleEval2Def('get_default_currency', _get_default_currency),
    SimpleEval2Def('get_default_transaction_type', _get_default_transaction_type),
    SimpleEval2Def('get_default_instrument_type', _get_default_instrument_type),
    SimpleEval2Def('get_default_account_type', _get_default_account_type),
    SimpleEval2Def('get_default_pricing_policy', _get_default_pricing_policy),
    SimpleEval2Def('get_default_responsible', _get_default_responsible),
    SimpleEval2Def('get_default_counterparty', _get_default_counterparty),
    SimpleEval2Def('get_default_strategy1', _get_default_strategy1),
    SimpleEval2Def('get_default_strategy2', _get_default_strategy2),
    SimpleEval2Def('get_default_strategy3', _get_default_strategy3),

    SimpleEval2Def('run_task', _run_task),
    SimpleEval2Def('create_task', _create_task),
    SimpleEval2Def('run_pricing_procedure', _run_pricing_procedure),
    SimpleEval2Def('run_data_procedure', _run_data_procedure),
    SimpleEval2Def('run_data_procedure_sync', _run_data_procedure_sync),
    SimpleEval2Def('rebook_transaction', _rebook_transaction),
    SimpleEval2Def('download_instrument_from_finmars_database', _download_instrument_from_finmars_database),

    SimpleEval2Def('create_workflow', _create_workflow),
    SimpleEval2Def('register_workflow_step', _register_workflow_step),
    SimpleEval2Def('run_workflow', _run_workflow),
    SimpleEval2Def('get_filenames_from_storage', _get_filenames_from_storage),
    SimpleEval2Def('delete_file_from_storage', _delete_file_from_storage),
    SimpleEval2Def('put_file_to_storage', _put_file_to_storage),

    SimpleEval2Def('run_data_import', _run_data_import),
    SimpleEval2Def('run_transaction_import', _run_transaction_import),

]

TRANSACTION_IMPORT_FUNCTIONS = [
    SimpleEval2Def('find_row', _transaction_import__find_row),
]

empty = object()

SAFE_TYPES = (bool, int, float, str, list, tuple, dict, OrderedDict,
              datetime.date, datetime.timedelta, datetime.datetime, relativedelta.relativedelta,
              SimpleEval2Def, _UserDef)


class SimpleEval2(object):
    def __init__(self, names=None, max_time=None, add_print=False, allow_assign=False, now=None, context=None):
        self.max_time = max_time or 60 * 30  # 30 min
        # self.max_time = 10000000000
        self.start_time = 0
        self.tik_time = 0
        self.allow_assign = allow_assign
        self.context = context if context is not None else {}
        # self.imperial_mode = context.get('imperial_mode', False)

        self.expr = None
        self.expr_ast = None
        self.result = None

        _globals = {f.name: f for f in FUNCTIONS}
        if callable(now):
            _globals['now'] = SimpleEval2Def('now', now)
        elif isinstance(now, datetime.date):
            _globals['now'] = SimpleEval2Def('now', lambda: now)

        _globals['transaction_import'] = {f.name: f for f in TRANSACTION_IMPORT_FUNCTIONS}

        _globals['globals'] = SimpleEval2Def('globals', lambda: _globals)
        _globals['locals'] = SimpleEval2Def('locals', lambda: self._table)
        _globals['true'] = True
        _globals['false'] = False

        if names:
            for k, v in names.items():
                _globals[k] = v
        if add_print:
            _globals['print'] = _print

        self._table = _globals

    @staticmethod
    def try_parse(expr):
        if not expr:
            raise InvalidExpression('Empty expression')
        try:
            return ast.parse(expr)
        except SyntaxError as e:
            raise ExpressionSyntaxError(e)
        except Exception as e:
            raise InvalidExpression(e)

    def check_time(self):
        if settings.DEBUG:
            return
        self.tik_time = time.time()
        if self.tik_time - self.start_time > self.max_time:
            raise InvalidExpression("Execution exceeded time limit, max runtime is %s" % self.max_time)

    @staticmethod
    def is_valid(expr):
        try:
            SimpleEval2.try_parse(expr)
            return True
        except:
            return False

    def has_var(self, name):
        return name in self._table

    def get_var(self, name, default):
        try:
            return self._find_name(name)
        except NameNotDefined:
            return default

    def _find_name(self, name):
        try:
            val = self._table[name]
            val = self._check_value(val)
            return val
        except (IndexError, KeyError, TypeError):
            raise NameNotDefined(name)

    def _check_value(self, val):
        # from django.db import models
        if val is None:
            return None
        elif isinstance(val, SAFE_TYPES):
            return val
        # elif isinstance(val, models.Model):
        else:
            # return get_model_data_ext(val, many=False, context=self.context)
            key = (
                type(val),
                getattr(val, 'pk', getattr(val, 'id', None))
            )
            if key in self._table:
                val = self._table[key]
            else:
                val = get_model_data_ext(val, context=self.context)
                self._table[key] = val
            return val
            # return val

    def eval(self, expr, names=None):
        if not expr:
            raise InvalidExpression('Empty expression')

        self.expr = expr
        self.expr_ast = SimpleEval2.try_parse(expr)

        save_table = self._table
        self._table = save_table.copy()
        if names:
            for k, v in names.items():
                self._table[k] = v
        try:
            self.start_time = time.time()
            self.result = self._eval(self.expr_ast.body)
            return self.result
        except InvalidExpression:
            # _l.debug('InvalidExpression', exc_info=True)
            raise
        except Exception as e:
            # _l.debug('Exception', exc_info=True)
            raise ExpressionEvalError(e)
        finally:
            self._table = save_table

    def multiline_eval(self, expr, names=None):

        if not expr:
            raise InvalidExpression('Empty expression')

        self.expr = expr
        self.expr_ast = SimpleEval2.try_parse(expr)

        save_table = self._table
        self._table = save_table.copy()

        print('self.expr_ast.body %s' % self.expr_ast.body)

        if names:
            for k, v in names.items():
                self._table[k] = v
        try:
            self.start_time = time.time()
            self.result = self._eval(self.expr_ast.body)
            return self.result
        except InvalidExpression:
            # _l.debug('InvalidExpression', exc_info=True)
            raise
        except Exception as e:
            # _l.debug('Exception', exc_info=True)
            raise ExpressionEvalError(e)
        finally:
            self._table = save_table

        "Evaluate several lines of input, returning the result of the last line"

        # self.expr_ast = SimpleEval2.try_parse(expr)
        # eval_exprs = []
        # exec_exprs = []
        # for module in self.expr_ast.body:
        #     if isinstance(module, ast.Expr):
        #         eval_exprs.append(module.value)
        #     else:
        #         exec_exprs.append(module)
        #
        # print('exec_exprs %s' % exec_exprs)
        # print('eval_exprs %s' % eval_exprs)
        #
        # exec_expr = ast.Module(exec_exprs, type_ignores=[])
        #
        # exec(compile(exec_expr, 'file', 'exec'), context)
        #
        # results = []
        #
        # for eval_expr in eval_exprs:
        #
        #     print(compile(ast.Expression((eval_expr)), 'file', 'eval'))
        #
        #     results.append(self._eval(compile(ast.Expression((eval_expr)), 'file', 'eval')))
        #
        #
        # return '\n'.join([str(r) for r in results])

    def _eval(self, node):
        # _l.debug('%s - %s - %s', node, type(node), node.__class__)
        # self.tik_time = time.time()
        # if self.tik_time - self.start_time > self.max_time:
        #     raise InvalidExpression("Execution exceeded time limit, max runtime is %s" % self.max_time)
        self.check_time()

        try:
            if isinstance(node, (list, tuple)):
                return self._on_many(node)
            else:
                op = '_on_ast_%s' % type(node).__name__
                if hasattr(self, op):
                    return getattr(self, op)(node)
        except _Return as e:
            return e.value

        raise InvalidExpression("Sorry, %s is not available in this evaluator" % type(node).__name__)

    def _on_many(self, node):
        ret = None
        for n in node:
            ret = self._eval(n)
        return ret

    def _on_ast_Assign(self, node):
        if not self.allow_assign:
            raise InvalidExpression("Sorry, %s is not available in this evaluator" % type(node).__name__)

        ret = self._eval(node.value)
        for t in node.targets:
            if isinstance(t, ast.Name):
                self._table[t.id] = ret
            elif isinstance(t, ast.Subscript):
                obj = self._eval(t.value)
                obj[self._eval(t.slice)] = ret
            elif isinstance(t, ast.Attribute):
                # TODO: check security
                obj = self._eval(t.value)
                if isinstance(obj, (dict, OrderedDict)):
                    obj[t.attr] = ret
                else:
                    raise ExpressionSyntaxError('Invalid assign')
                    # raise ExpressionSyntaxError('Invalid assign')
            else:
                raise ExpressionSyntaxError('Invalid assign')
        return ret

    def _on_ast_If(self, node):
        return self._eval(node.body) if self._eval(node.test) else self._eval(node.orelse)

    def _on_ast_For(self, node):
        ret = None
        for val in self._eval(node.iter):
            self._table[node.target.id] = val
            try:
                ret = self._eval(node.body)
            except _Break:
                break
        return ret

    def _on_ast_While(self, node):
        ret = None
        while self._eval(node.test):
            try:
                ret = self._eval(node.body)
            except _Break:
                break
        return ret

    def _on_ast_Break(self, node):
        raise _Break()

    def _on_ast_FunctionDef(self, node):
        # self.local_functions[node.name] = node
        self._table[node.name] = _UserDef(self, node)
        return None

    def _on_ast_Pass(self, node):
        return None

    def _on_ast_Try(self, node):
        ret = None
        try:
            ret = self._eval(node.body)
        except:
            if node.handlers:
                for n in node.handlers:
                    # ast.ExceptHandler
                    if n.body:
                        ret = self._eval(n.body)
        else:
            if node.orelse:
                ret = self._eval(node.orelse)
        finally:
            if node.finalbody:
                ret = self._eval(node.finalbody)

        return ret

    def _on_ast_Num(self, node):
        return node.n

    def _on_ast_Str(self, node):
        if len(node.s) > MAX_STR_LEN:
            raise ExpressionEvalError(
                "String Literal in statement is too long! (%s, when %s is max)" % (len(node.s), MAX_STR_LEN))
        return node.s

    def _on_ast_NameConstant(self, node):
        return node.value

    def _on_ast_Constant(self, node):
        return node.value

    def _on_ast_Dict(self, node):
        d = {}
        for k, v in zip(node.keys, node.values):
            k = self._eval(k)
            v = self._eval(v)
            d[k] = v
            if len(d) > MAX_LEN:
                raise ExpressionEvalError('Max dict length.')
        return d

    def _on_ast_List(self, node):
        d = []
        for v in node.elts:
            v = self._eval(v)
            d.append(v)
            if len(d) > MAX_LEN:
                raise ExpressionEvalError('Max list/tuple/set length.')
        return d

    def _on_ast_Tuple(self, node):
        return tuple(self._on_ast_List(node))

    def _on_ast_Set(self, node):
        return set(self._on_ast_List(node))

    def _on_ast_UnaryOp(self, node):
        return OPERATORS[type(node.op)](self._eval(node.operand))

    def _on_ast_BinOp(self, node):
        return OPERATORS[type(node.op)](self._eval(node.left), self._eval(node.right))

    def _on_ast_BoolOp(self, node):
        if isinstance(node.op, ast.And):
            # return all((self._eval(v) for v in node.values))
            res = False
            for v in node.values:
                res = self._eval(v)
                if not res:
                    return False
            return res
        elif isinstance(node.op, ast.Or):
            # return any((self._eval(v) for v in node.values))
            res = True
            for v in node.values:
                res = self._eval(v)
                if res:
                    return res
            return res

    def _on_ast_Compare(self, node):
        return OPERATORS[type(node.ops[0])](self._eval(node.left), self._eval(node.comparators[0]))

    def _on_ast_IfExp(self, node):
        return self._eval(node.body) if self._eval(node.test) else self._eval(node.orelse)

    def _on_ast_Call(self, node):
        f = self._eval(node.func)
        if not callable(f):
            raise FunctionNotDefined(node.func.id)

        f_args = [self._eval(a) for a in node.args]
        f_kwargs = {k.arg: self._eval(k.value) for k in node.keywords}

        try:
            if node.func.attr in ['append', 'pop', 'remove']:
                return f(*f_args)
        except Exception as e:
            pass
            # TODO check why error is occuring
            # _l.error("append do not work %s" % e)

        return f(self, *f_args, **f_kwargs)

    def _on_ast_Return(self, node):
        val = self._eval(node.value)
        raise _Return(val)

    def _on_ast_Name(self, node):
        ret = self._find_name(node.id)
        return ret

    def _on_ast_Subscript(self, node):
        val = self._eval(node.value)
        index_or_key = self._eval(node.slice)
        try:
            val = val[index_or_key]
            val = self._check_value(val)
            return val
        except (IndexError, KeyError, TypeError):
            return None

    def _on_ast_Attribute(self, node, val=empty):

        if val is empty:
            val = self._eval(node.value)
        if val is None:
            return None

        if isinstance(val, types.FunctionType):
            val = self._eval(node.value)

        if isinstance(val, (dict, OrderedDict)):
            try:
                return val[node.attr]
            except (IndexError, KeyError, TypeError):
                raise AttributeDoesNotExist(node.attr)

        elif isinstance(val, list):
            _l.debug("list here? %s" % val)
            _l.debug("list here? node.value %s" % node.value)
            _l.debug("list here? node.attr %s" % node.attr)
            if node.attr in ['append', 'pop', 'remove']:
                return getattr(val, node.attr)
        else:

            if isinstance(val, datetime.date):
                if node.attr in ['year', 'month', 'day']:
                    return getattr(val, node.attr)

            elif isinstance(val, datetime.timedelta):
                if node.attr in ['days']:
                    return getattr(val, node.attr)

            elif isinstance(val, relativedelta.relativedelta):
                if node.attr in ['years', 'months', 'days', 'leapdays', 'year', 'month', 'day', 'weekday']:
                    return getattr(val, node.attr)

        raise AttributeDoesNotExist(node.attr)

    def _on_ast_Index(self, node):
        return self._eval(node.value)

    def _on_ast_Expr(self, node):
        return self._eval(node.value)

    def _on_ast_Slice(self, node):
        lower = upper = step = None
        if node.lower is not None:
            lower = self._eval(node.lower)
        if node.upper is not None:
            upper = self._eval(node.upper)
        if node.step is not None:
            step = self._eval(node.step)
        return slice(lower, upper, step)


def validate(expr):
    from rest_framework.exceptions import ValidationError
    try:
        SimpleEval2.try_parse(expr)
        # try_parse(expr)
    except InvalidExpression as e:
        raise ValidationError('Invalid expression: %s' % e)


def safe_eval(s, names=None, max_time=None, add_print=False, allow_assign=True, now=None, context=None):
    e = SimpleEval2(names=names, max_time=max_time, add_print=add_print, allow_assign=allow_assign, now=now,
                    context=context)
    return e.eval(s)


def safe_eval_with_logs(s, names=None, max_time=None, add_print=False, allow_assign=True, now=None, context=None):
    e = SimpleEval2(names=names, max_time=max_time, add_print=add_print, allow_assign=allow_assign, now=now,
                    context=context)
    if "log" not in context:
        context["log"] = ""

    return e.eval(s), context["log"]


def validate_date(val):
    return _parse_date(val)


def validate_num(val):
    return _parse_number(val)


def validate_bool(val):
    print('validate_bool val %s' % val)

    return _parse_bool(val)


def register_fun(name, callback):
    if not callable(callback):
        raise InvalidExpression('Bad function callback')
    if name is None:
        raise InvalidExpression('Invalid function name')
    if name is FUNCTIONS:
        raise InvalidExpression('Function with this name already registered')

    if isinstance(callback, SimpleEval2Def):
        FUNCTIONS[name] = callback
    else:
        FUNCTIONS[name] = SimpleEval2Def(name, callback)


def value_prepare(orig):
    def _dict(data):
        ret = OrderedDict()

        from poms.obj_attrs.models import GenericAttributeType

        for k, v in data.items():
            if k in ['user_object_permissions', 'group_object_permissions', 'object_permissions',
                     'granted_permissions']:
                continue

            elif k == 'attributes':

                if 'attributes' not in ret:
                    ret[k] = {}

                # oattrs = _value(v)
                # nattrs = OrderedDict()
                # for attr in oattrs:
                #     attr_t = attr['attribute_type']
                #     attr_n = attr_t['user_code']
                #     val_t = attr_t['value_type']
                #     if val_t == GenericAttributeType.CLASSIFIER:
                #         attr['value'] = attr['classifier']
                #     elif val_t == GenericAttributeType.NUMBER:
                #         attr['value'] = attr['value_float']
                #     elif val_t == GenericAttributeType.DATE:
                #         attr['value'] = attr['value_date']
                #     elif val_t == GenericAttributeType.STRING:
                #         attr['value'] = attr['value_string']
                #     else:
                #         attr['value'] = None
                #     nattrs[attr_n] = attr
                # ret[k] = nattrs

                oattrs = _value(v)
                nattrs = OrderedDict()
                for attr in oattrs:
                    attr_t = attr['attribute_type']
                    attr_n = attr_t['user_code']
                    val_t = attr_t['value_type']

                    if val_t == GenericAttributeType.CLASSIFIER:

                        if attr['classifier']:
                            ret[k][attr_n] = attr['classifier']['name']
                        else:
                            ret[k][attr_n] = None
                    elif val_t == GenericAttributeType.NUMBER:
                        ret[k][attr_n] = attr['value_float']
                    elif val_t == GenericAttributeType.DATE:
                        ret[k][attr_n] = str(attr['value_date'])
                    elif val_t == GenericAttributeType.STRING:
                        ret[k][attr_n] = attr['value_string']
                    else:
                        ret[k][attr_n] = None

                # print('ret[k] %s' % ret[k])


            elif k.endswith('_object'):
                k = k[:-7]
                ret[k] = _value(v)

            else:
                if k not in ret:
                    ret[k] = _value(v)
        return ret

    def _list(data):
        ret = []
        for v in data:
            ret.append(_value(v))
        return ret

    def _value(data):
        if data is None:
            return None
        elif isinstance(data, (datetime.date, datetime.datetime)):
            return str(data)
        elif isinstance(data, Promise):
            return str(data)
        elif isinstance(data, (dict, OrderedDict)):
            return _dict(data)
        elif isinstance(data, (list, tuple, set)):
            return _list(data)
        return data

    return _value(orig)


def get_model_data(instance, object_class, serializer_class, many=False, context=None, hide_fields=None):
    def _dumps():
        serializer = serializer_class(instance=instance, many=many, context=context)
        if hide_fields:
            for f in hide_fields:
                serializer.fields.pop(f)
        data = serializer.data
        data = value_prepare(data)
        if isinstance(data, (list, tuple)):
            for o in data:
                o['object_class'] = object_class
        else:
            data['object_class'] = object_class
        # import json
        # print(json.dumps(data, indent=2))
        return data

    return SimpleLazyObject(_dumps)


def _get_supported_models_serializer_class():
    from poms.users.models import Member
    from poms.users.serializers import MemberSerializer

    from poms.accounts.models import Account
    from poms.accounts.serializers import AccountSerializer
    from poms.counterparties.models import Counterparty, Responsible
    from poms.counterparties.serializers import CounterpartySerializer, ResponsibleSerializer
    from poms.instruments.models import Instrument, DailyPricingModel, PaymentSizeDetail, GeneratedEvent, InstrumentType
    from poms.instruments.serializers import InstrumentSerializer, DailyPricingModelSerializer, \
        InstrumentTypeSerializer, \
        PaymentSizeDetailSerializer, GeneratedEventSerializer
    from poms.currencies.models import Currency
    from poms.currencies.serializers import CurrencySerializer
    from poms.portfolios.models import Portfolio
    from poms.portfolios.serializers import PortfolioSerializer
    from poms.strategies.models import Strategy1, Strategy2, Strategy3
    from poms.strategies.serializers import Strategy1Serializer, Strategy2Serializer, Strategy3Serializer
    from poms.integrations.models import PriceDownloadScheme
    from poms.integrations.serializers import PriceDownloadSchemeSerializer
    from poms.transactions.models import Transaction, ComplexTransaction
    from poms.transactions.serializers import TransactionTextRenderSerializer, ComplexTransactionEvalSerializer

    return {
        Account: AccountSerializer,
        Counterparty: CounterpartySerializer,
        Responsible: ResponsibleSerializer,
        Instrument: InstrumentSerializer,
        InstrumentType: InstrumentTypeSerializer,
        Currency: CurrencySerializer,
        Portfolio: PortfolioSerializer,
        Strategy1: Strategy1Serializer,
        Strategy2: Strategy2Serializer,
        Strategy3: Strategy3Serializer,
        DailyPricingModel: DailyPricingModelSerializer,
        PaymentSizeDetail: PaymentSizeDetailSerializer,
        PriceDownloadScheme: PriceDownloadSchemeSerializer,
        Transaction: TransactionTextRenderSerializer,
        ComplexTransaction: ComplexTransactionEvalSerializer,
        GeneratedEvent: GeneratedEventSerializer,
        Member: MemberSerializer
    }


_supported_models_serializer_class = SimpleLazyObject(_get_supported_models_serializer_class)


def get_model_data_ext(instance, context=None, hide_fields=None):
    from django.db.models import QuerySet, Manager
    from django.db.models.manager import BaseManager

    if instance is None:
        return None

    many = False
    if isinstance(instance, (list, tuple)):
        if not instance:
            return []
        many = True
        model = instance[0].__class__
    elif isinstance(instance, QuerySet):
        if not instance:
            return []
        many = True
        model = instance.model
    elif isinstance(instance, (Manager, BaseManager)):
        if not instance:
            return []
        many = True
        model = instance.model
        instance = instance.all()
    else:
        if not instance:
            return None
        model = instance.__class__
    object_class = str(model.__name__)

    try:
        serializer_class = _supported_models_serializer_class[model]
    except KeyError:
        raise InvalidExpression("'%s' can't serialize" % model)
    return get_model_data(instance=instance, object_class=object_class, serializer_class=serializer_class, many=many,
                          context=context, hide_fields=hide_fields)


HELP = """
TYPES:

string: '' or ""
number: 1 or 1.0
boolean: True/False

hidden types
date: date object
timedelta: time delta object for operations with dates

OPERATORS:

    +, -, /, *, ==, !=, >, >=, <, <=


VARIABLES:

access to context value in formulas
    x * 10
    context['x'] * 10
    instrument.price_multiplier
    instrument['price_multiplier']
    context['instrument']['price_multiplier']


FUNCTIONS:

function description
    function_name(arg1, arg2=<default value for arg>)

example of function call->
    iff(d==now(), 1, 2)
    iff(d==now(), v1=1, v2=2)

supported functions:

str(a)
    any value to string
float(a)
    convert string to number
round(number)
    math round float
trunc(number)
    math truncate float
iff(expr, a, b)
    return a if x is True else v2
isclose(a, b)
    compare to float number to equality
now()
    current date
date(year, month=1, day=1)
    create date object
days(days)
    create timedelta object for operations with dates
    now() - days(10)
    now() + days(10)
add_days(date, days)
    same as date + days(x)
add_weeks(date, days)
    same as d + days(x * 7)
add_workdays(date, workdays)
    add "x" work days to d
format_date(date, format='%Y-%m-%d')
    format date, by default format is '%Y-%m-%d'
parse_date(date_string, format='%Y-%m-%d')
    parse date from string, by default format is '%Y-%m-%d'
format_number(number, decimal_sep='.', decimal_pos=None, grouping=3, thousand_sep='', use_grouping=False)
    decimal_sep: Decimal separator symbol (for example ".")
    decimal_pos: Number of decimal positions
    grouping: Number of digits in every group limited by thousand separator
    thousand_sep: Thousand separator symbol (for example ",")
    use_grouping: use thousand separator
parse_number(a)
    same as float(a)
simple_price(date, date1, value1, date2, value2)
    calculate price on date using 2 point
    date, date1, date2 - date or string in format '%Y-%m-%d'


DATE format string (also used in parse):
    %w 	Weekday as a decimal number, where 0 is Sunday and 6 is Saturday - 0, 1, ..., 6
    %d 	Day of the month as a zero-padded decimal number - 01, 02, ..., 31
    %m 	Month as a zero-padded decimal number - 01, 02, ..., 12
    %y 	Year without century as a zero-padded decimal number - 00, 01, ..., 99
    %Y 	Year with century as a decimal number - 1970, 1988, 2001, 2013
    %j 	Day of the year as a zero-padded decimal number - 001, 002, ..., 366
    %U 	Week number of the year (Sunday as the first day of the week) as a zero padded decimal number.
        All days in a new year preceding the first Sunday are considered to be in week 0. - 00, 01, ..., 53
    %W 	Week number of the year (Monday as the first day of the week) as a decimal number.
        All days in a new year preceding the first Monday are considered to be in week 0. - 00, 01, ..., 53
    %% 	A literal '%' character - %
"""

# %a 	Weekday as locale’s abbreviated name - Sun, Mon, ..., Sat (en_US)
# %A 	Weekday as locale’s full name - Sunday, Monday, ..., Saturday (en_US);
# %b 	Month as locale’s abbreviated name - Jan, Feb, ..., Dec (en_US)
# %B 	Month as locale’s full name  - January, February, ..., December (en_US);

if __name__ == "__main__":
    import os

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "poms_app.settings")
    import django

    django.setup()

    names = {
        "v0": 1.00001,
        "v1": "str",
        "v2": {
            "id": 1,
            "name": "V2",
            "code": 12354
        },
        "v3": [
            {
                "id": 2,
                "name": "V31"
            },
            {
                "id": 3,
                "name": "V32"
            },
        ],
        "v4": OrderedDict(
            [
                ("id", 3),
                ("name", "Lol"),
            ]
        ),
    }


    # _l.debug(safe_eval('(1).__class__.__bases__', names=names))
    # _l.debug(safe_eval('{"a":1, "b":2}'))
    # _l.debug(safe_eval('[1,]'))
    # _l.debug(safe_eval('(1,)'))
    # _l.debug(safe_eval('{1,}'))
    # _l.debug(safe_eval('[1, 1.0, "str", None, True, False]'))

    # _l.debug(safe_eval('parse_date("2000-01-01") + days(100)'))
    # _l.debug(safe_eval(
    #     'simple_price(parse_date("2000-01-05"), parse_date("2000-01-01"), 0, parse_date("2000-04-10"), 100)'))
    # _l.debug(safe_eval('simple_price("2000-01-05", "2000-01-01", 0, "2000-04-10", 100)'))
    # _l.debug(safe_eval('simple_price("2000-01-02", "2000-01-01", 0, "2000-04-10", 100)'))
    # _l.debug(safe_eval('v0 * 10', names=names))
    # _l.debug(safe_eval('globals()["v0"] * 10', names=names))
    # _l.debug(safe_eval('v2.id', names=names))
    # _l.debug(safe_eval('v4.id', names=names))

    # _l.debug(safe_eval('func1()'))
    # _l.debug(safe_eval('name1'))
    # _l.debug(safe_eval('name1.id', names={"name1": {'id':1}}))
    # _l.debug(safe_eval('name1.id2', names={"name1": {'id':1}}))
    # _l.debug(safe_eval('1+'))
    # _l.debug(safe_eval('1 if 1 > 2 else 2'))
    # _l.debug(safe_eval('"a" in "ab"'))
    # _l.debug(safe_eval('y = now().year'))
    # _l.debug(safe_eval('eval("2+eval(\\\"2+2\\\")")'))
    # _l.debug(ast.literal_eval('2+2'))
    # _l.debug(safe_eval("globals()['now']()"))

    def test_eval(expr, names=None):
        # _l.debug('-' * 79)
        try:
            se = SimpleEval2(names=names, add_print=True)
            ret = se.eval(expr)
            # res = safe_eval(expr, names=names)
        except InvalidExpression as e:
            import time
            ret = "<ERROR1: %s>" % e
            time.sleep(1)
            # raise e
        except Exception as e:
            ret = "<ERROR2: %s>" % e
        _l.debug("\t%-60s -> %s" % (expr, ret))


    #     test_eval('''
    # pass
    #
    # a = 1000
    # # not supported
    # # if 1 <= a <= 2000:
    # #     pass
    # if 1 <= a and a <= 2000:
    #     pass
    #
    # for i in [1,2]:
    #     pass
    #
    # i = 0
    # while i < 2:
    #     pass
    #     i = i + 1
    #
    # a = 0
    # try:
    #     a = a + 1
    # except:
    #     a = a + 10
    # else:
    #     a = a + 100
    # finally:
    #     a = a + 1000
    #
    # b = 1
    # if b == 0:
    #     pass
    # elif b == 1:
    #     pass
    # else:
    #     pass
    #
    # def f1(v):
    #     pass
    #     for i in [1,2]:
    #         if v > 1:
    #             pass
    #             return True
    #         else:
    #             return False
    # f1(1)
    #
    # b = 0
    # for a in range(1,10):
    #     b = b + a
    # b
    #
    # b2 = 0
    # for a in range(10):
    #     b2 = b2 + a
    # b2
    #
    # range(10)
    # date(2016)
    # ''')

    def demo():
        # from poms.common.formula_serializers import EvalInstrumentSerializer, EvalTransactionSerializer

        from rest_framework.test import APIRequestFactory
        factory = APIRequestFactory()
        instrument_request = factory.get('/api/v1/instruments/instrument/1/', format='json')
        transactions_request = factory.get('/api/v1/transactions/transaction/', format='json')
        names = {
            "v0": 1.00001,
            "v1": "str",
            "v2": {"id": 1, "name": "V2", "trn_code": 12354, "num": 1.234},
            "v3": [{"id": 2, "name": "V31"}, {"id": 3, "name": "V32"}, ],
            "v4": OrderedDict([["id", 3], ["name", "Lol"]]),
            # "instr": OrderedDict(
            #     InstrumentSerializer(instance=Instrument.objects.first(),
            #                          context={'request': instrument_request}).data
            # ),
            # "trns": [
            #     OrderedDict(
            #         TransactionSerializer(instance=Transaction.objects.all(), many=True,
            #                               context={'request': transactions_request}).data
            #     )
            # ],

        }
        _l.debug("test variables:\n", names)
        # for n in sorted(six.iterkeys(names)):
        #     _l.debug(n, "\n")
        #     pprint.pprint(names[n])
        #     # print("\t%s -> %s" % (n, json.dumps(names[n], sort_keys=True, indent=2)))

        _l.debug("simple:")
        test_eval("2 * 2 + 2", names)
        test_eval("2 * (2 + 2)", names)
        test_eval("16 ** 16", names)
        test_eval("5 / 2", names)
        test_eval("5 % 2", names)

        _l.debug('')
        _l.debug("with variables:")
        test_eval("v0 + 1", names)
        test_eval("v1 + ' & ' + str(v0)", names)
        test_eval("v2.name", names)
        test_eval("v2.num * 3", names)
        test_eval("v3[1].name", names)
        test_eval("v3[1].name", names)
        test_eval("globals()", names)
        test_eval("globals()['v0']", names)
        # test_eval("instr.name", names)
        # test_eval("instr.instrument_type.id", names)
        # test_eval("instr.instrument_type.user_code", names)
        # test_eval("instr.price_multiplier", names)
        # test_eval("instr['price_multiplier']", names)
        # test_eval("globals()['instr']", names)
        # test_eval("globals()['instr'].price_multiplier", names)
        # test_eval("globals()['instr']['price_multiplier']", names)

        _l.debug('')
        _l.debug("functions: ")
        test_eval("round(1.73456)", names)
        test_eval("round(1.73456, 3)", names)
        test_eval("round(1.73456, 4)", names)
        test_eval("trunc(1.73456)", names)
        test_eval("int(1.5)", names)
        test_eval("now()", names)
        test_eval("add_days(now(), 10)", names)
        test_eval("add_workdays(now(), 10)", names)
        test_eval("iff(1.001 > 1.002, 'really?', 'ok')", names)
        test_eval("'really?' if 1.001 > 1.002 else 'ok'", names)
        test_eval("'N' + format_date(now(), '%Y%m%d') + '/' + str(v2.trn_code)", names)

        test_eval("format_date(now())", names)
        test_eval("format_date(now(), '%Y/%m/%d')", names)
        test_eval("format_date(now(), format='%Y/%m/%d')", names)
        test_eval("format_number(1234.234)", names)
        test_eval("format_number(1234.234, '.', 2)", names)

        # r = safe_eval3('"%r" % now()', names=names, functions=functions)
        # r = safe_eval('format_date(now(), "EEE, MMM d, yy")')
        # _l.debug(repr(r))
        # _l.debug(add_workdays(datetime.date(2016, 6, 15), 3, only_workdays=False))
        # _l.debug(add_workdays(datetime.date(2016, 6, 15), 4, only_workdays=False))
        # _l.debug(add_workdays(datetime.date(2016, 6, 15), 3))
        # _l.debug(add_workdays(datetime.date(2016, 6, 15), 4))


    demo()
    pass


    def demo_stmt():
        test_eval('a = 2 + 3')

        test_eval('''
a = {}
a['2'] = {}
a['2']['1'] = {}
a['2']['1'][1]=123
a
''')

        test_eval('''
a = 2
b = None
if b is None:
    b = 2
if b is not None:
    b = 3
if not b:
    b = 1
a * b
        ''')

        test_eval('''
r = 0
for a in [1,2,3]:
    r = r + a
r
        ''')

        test_eval('''
r = 0
while r < 100:
    r = r + 2
r
        ''')

        test_eval('''
a = date(2000, 1, 1)
b = date(2001, 1, 1)
r = a
k = 0
while r < b:
    r = r + weeks(k * 2)
    k = k + 1
k, r
        ''')

        test_eval('''
a = date(2000, 1, 1)
b = date(2001, 1, 1)
r = a
k = 0
while r < b:
    r = r + timedelta(weeks=k * 2)
    k = k + 1
k, r
        ''')

        test_eval('''
def f1(a, b = 200, c = 300):
    r = a * b
    return r + c
f1(10, b = 20)
        ''')

        test_eval('''
def accrl_C_30E_P_360(dt1, dt2):
    d1 = dt1.day
    d2 = dt2.day
    m1 = dt1.month
    m2 = dt1.month
    if d1 == 31:
        d1 = 30
    if d2 == 31:
        m2 += 1
        d2 = 1
    return ((dt2.year - dt1.year) * 360 + (m2 - m1) * 30 + (d2 - d1)) / 360
accrl_C_30E_P_360(parse_date('2001-01-01'), parse_date('2001-01-25'))
        ''')

        test_eval('''
def accrl_NL_365_NO_EOM(dt1, dt2):
    is_leap1 = isleap(dt1.year)
    is_leap2 = isleap(dt2.year)
    k = 0
    if is_leap1 and dt1 < date(dt1.year, 2, 29) and dt2 >= date(dt1.year, 2, 29):
        k = 1
    if is_leap2 and dt2 >= date(dt2.year, 2, 29) and dt1 < date(dt2.year, 2, 29):
        k = 1
    return (dt2 - dt1 - days(k)).days / 365
accrl_NL_365_NO_EOM(parse_date('2000-01-01'), parse_date('2000-01-25'))
        ''')

        test_eval('''
a = 1

def f1():
    print('f1: 1 - a=%s', a)

def f2():
    print('f2: 1 - a=%s', a)
    a = 2
    print('f2: 2 - a=%s', a)

def f3():
    print('f3: 1 - a=%s', a)
    a = 3
    print('f3: 2 - a=%s', a)

f1()
f2()
f3()
print('gg: 1 - a=%s', a)
        ''')


    # demo_stmt()
    pass


    def perf_tests():
        import timeit

        def f_native():
            def accrual_NL_365_NO_EOM(dt1, dt2):
                k = 0
                if _isleap(dt1.year) and dt1 < _date(dt1.year, 2, 29) <= dt2:
                    k = 1
                if _isleap(dt2.year) and dt2 >= _date(dt2.year, 2, 29) > dt1:
                    k = 1
                return ((dt2 - dt1).days - k) / 365

            # for i in range(50):
            #     accrual_NL_365_NO_EOM(_date(2000, 1, 1), _date(2000, 1, 25))
            # for i in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]:
            #     # accrual_NL_365_NO_EOM(_parse_date('2000-01-01'), _parse_date('2000-01-25'))
            #     accrual_NL_365_NO_EOM(_date(2000, 1, 1), _date(2000, i, 25))
            # accrual_NL_365_NO_EOM(_parse_date('2000-01-01'), _parse_date('2000-01-25'))
            accrual_NL_365_NO_EOM(_date(2000, 1, 1), _date(2000, 1, 25))

        expr = '''
def accrual_NL_365_NO_EOM(dt1, dt2):
    k = 0
    if isleap(dt1.year) and dt1 < date(dt1.year, 2, 29) <= dt2:
        k = 1
    if isleap(dt2.year) and dt2 >= date(dt2.year, 2, 29) > dt1:
        k = 1
    return ((dt2 - dt1).days - k) / 365
# for i in range(50):
#     accrual_NL_365_NO_EOM(date(2000, 1, 1), date(2000, 1, 25))
# for i in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]:
#     # accrual_NL_365_NO_EOM(parse_date('2000-01-01'), parse_date('2000-01-25'))
#     accrual_NL_365_NO_EOM(date(2000, 1, 1), date(2000, i, 25))
# accrual_NL_365_NO_EOM(parse_date('2000-01-01'), parse_date('2000-01-25'))
accrual_NL_365_NO_EOM(date(2000, 1, 1), date(2000, 1, 25))
        '''

        _l.debug('PERF')
        number = 1000
        _l.debug('-' * 79)
        _l.debug(expr)
        _l.debug('-' * 79)
        _l.debug('native          : %f', timeit.timeit(f_native, number=number))
        _l.debug('parse           : %f', timeit.timeit(lambda: ast.parse(expr), number=number))
        _l.debug('exec            : %f', timeit.timeit(lambda: exec(expr, {
            'parse_date': _parse_date,
            'isleap': calendar.isleap,
            'date': _date,
            'days': _days,
        }), number=number))
        _l.debug('safe_eval       : %f', timeit.timeit(lambda: safe_eval(expr, allow_assign=True), number=number))

        _l.debug('-' * 79)
        expr = '-(4-1)*5+(2+4.67)+5.89/(.2+7)'
        _l.debug('eval            : %f', timeit.timeit(lambda: exec(expr), number=number))
        _l.debug('safe_eval       : %f', timeit.timeit(lambda: safe_eval(expr), number=number))


    # perf_tests()
    pass


    def model_access_test():
        from poms.users.models import Member
        from poms.transactions.models import Transaction
        from poms.accounts.models import Account
        from poms.instruments.models import Instrument

        from poms.users.models import Member
        member = Member.objects.get(user__username='a')
        master_user = member.master_user
        context = {
            'master_user': master_user,
            'member': member,
        }

        names = {
            # 'transactions': ts_qs,
            'transactions': list(Transaction.objects.filter(master_user=master_user)),
            'transaction': Transaction.objects.filter(master_user=master_user).first(),
            'accounts': list(Account.objects.filter(master_user=master_user)),
            'account': Account.objects.filter(master_user=master_user).first(),
            'instruments': list(Instrument.objects.filter(master_user=master_user)),
            'instrument': Instrument.objects.filter(master_user=master_user).first(),
            'instrument1': Instrument.objects.filter(master_user=master_user).first(),
        }

        _l.debug('---------')
        # _l.debug(safe_eval('instrument', names=names, context=context))
        # _l.debug(safe_eval('instrument1.attributes', names=names, context=context))
        # _l.debug(safe_eval('instrument1.price_multiplier', names=names, context=context))
        # _l.debug(safe_eval('instrument1.price_multiplier * instrument1.price_multiplier', names=names, context=context))
        # _l.debug(safe_eval('instrument1["price_multiplier"]', names=names, context=context))
        # _l.debug(safe_eval('return instruments', names=names, context=context))
        # _l.debug(safe_eval('instruments[0].price_multiplier', names=names, context=context))
        # _l.debug(safe_eval('transactions[0].instrument.user_code', names=names, context=context))

        _l.debug(safe_eval('account', names=names, context=context))
        _l.debug(safe_eval('account.attributes', names=names, context=context))
        _l.debug(safe_eval('account.attributes.str1.value', names=names, context=context))
        _l.debug(safe_eval('account.attributes["SomeClassifier"].value', names=names, context=context))
        _l.debug(safe_eval('account.attributes["SomeClassifier"].value.parent.parent.parent.name', names=names,
                           context=context))

        pass


    # model_access_test()
    pass


    def now_test():
        now = datetime.date(2000, 1, 1)
        _l.debug(safe_eval('now()'))
        _l.debug(safe_eval('now()', now=lambda: now))


    # now_test()
    pass


    def accrued_test():
        from poms.users.models import Member
        member = Member.objects.get(user__username='a')
        master_user = member.master_user
        context = {
            'master_user': master_user,
            'member': member,
        }

        # _l.debug('1: %s', safe_eval('get_instrument_accrued_price("petrolios", "2017-11-01")', context=context))
        # _l.debug('2: %s', safe_eval('get_instrument_accrued_price("petrolios", "2017-11-01")', context=context))
        _l.debug('3: %s', safe_eval('get_instrument_coupon("petrolios", "2017-11-01")', context=context))
        # _l.debug('4: %s', safe_eval('get_instrument_factor("petrolios", "2017-11-01")', context=context))
        # _l.debug('5: %s', safe_eval('get_instrument_factor("petrolios", "2017-11-01")', context=context))


    # accrued_test()
    pass


    def group_test():
        _l.debug('1: %s', safe_eval('simple_group(0, [[1,10,"o1"],[10,20,"o2"]], "o3")'))
        _l.debug('2: %s', safe_eval('simple_group(5, [[1,10,"o1"],[10,20,"o2"]], "o3")'))
        _l.debug('3: %s', safe_eval('simple_group(15, [[1,10,"o1"],[10,20,"o2"]], "o3")'))
        _l.debug('4: %s', safe_eval('simple_group(25, [[1,10,"o1"],[10,20,"o2"]], "o3")'))
        _l.debug('5: %s', safe_eval('simple_group(4, [["-inf",10,"o1"],[10,20,"o2"]], default="Olala")'))
        # _l.debug('5: %s', safe_eval('simple_group(4, [["begin","end","name"],...], default="Olala")'))

        _l.debug('10: %s', safe_eval('simple_group(0, [[None,10,"o1"],[10,20,"o2"]], "o3")'))
        _l.debug('11: %s', safe_eval('simple_group(5, [[None,10,"o1"],[10,20,"o2"]], "o3")'))
        _l.debug('12: %s', safe_eval('simple_group(15, [[None,10,"o1"],[10,20,"o2"]], "o3")'))
        _l.debug('13: %s', safe_eval('simple_group(25, [[None,10,"o1"],[10,None,"o2"]], "o3")'))

        _l.debug('100: %s', safe_eval('date_group("2000-11-21", ['
                                      '["2000-01-01","2001-01-01",10,"o1"],'
                                      '["2001-01-01","2002-01-01", timedelta(months=1, day=31),"o2"]'
                                      '], "o3")'))
        _l.debug('101: %s', safe_eval('date_group("2002-11-21", ['
                                      '["2000-01-01","2001-01-01",10,"o1"],'
                                      '["2001-01-01","2002-01-01",timedelta(months=1, day=31),"o2"]'
                                      '], "o3")'))
        _l.debug('102: %s', safe_eval('date_group("2000-11-21", ['
                                      '["2000-01-01","2001-01-01", None,"o1"],'
                                      '["2001-01-01","2002-01-01",timedelta(months=1, day=31),"o2"]'
                                      '], "o3")'))

        _l.debug('110: %s', safe_eval('date_group("2000-11-21", ['
                                      '["2000-01-01","2001-01-01", 10, ["<","%Y-%m-%d-%B",">","<","%Y-%m-%d",">"]],'
                                      '["2000-01-01","2002-01-01",timedelta(months=1, day=31),"o2"]'
                                      '], "o3")'))

        _l.debug('120: %s', safe_eval('date_group("2002-11-21", ['
                                      '["","2001-01-01",None, "o1"],'
                                      '["2001-01-01","2002-01-01",10, "o2"],'
                                      '["2002-01-01","",None,"o3"]'
                                      '], "o4")'))
        _l.debug('121: %s', safe_eval('date_group("2000-11-21", ['
                                      '["","2001-01-01",None, "o1"],'
                                      '["2001-01-01","2002-01-01",10, "o2"],'
                                      '["2002-01-01","",None,"o3"]'
                                      '], "o4")'))

        # timedelta(years=0, months=0, days=0, leapdays=0, weeks=0,
        #        year=None, month=None, day=None, weekday=None,
        #        yearday=None, nlyearday=None)
        # {id: 1, caption: "Daily", step: "timedelta(days=1)"},
        # {id: 2, caption: "Weekly (+7d)", step: "timedelta(weeks=1)"},
        # {id: 3, caption: "Weekly (EoW)"},
        # {id: 4, caption: "Bi-weekly (+14d)", step: "timedelta(weeks=2)"},
        # {id: 5, caption: "Bi-weekly (EoW)"},
        # {id: 6, caption: "Monthly", step: "timedelta(months=1)"},
        # {id: 7, caption: "Monthly (EoM)""},
        # {id: 8, caption: "Monthly (Last business day)"},
        # {id: 9, caption: "Quarterly (Calendar)"},
        # {id: 10, caption: "Quarterly (+3m)", step: "timedelta(months=3)"},
        # {id: 11, caption: "Yearly (+12m)", step: "timedelta(years=1)",
        # {id: 12, caption: "Yearly (EoY)"}
        _l.debug('200: %s', safe_eval('date_group("2001-04-09", ['
                                      '["","2001-02-01",None, "o1"],'
                                      '["2001-02-01","2020-02-01", timedelta(weeks=1, weekday=1), ["<","%Y-%m-%d-%a-%b","/","","%Y-%m-%d-%a-%b",">"]],'
                                      '["2020-02-01","",None,"o3"]'
                                      '], "o4")'))

        # simple_group("expr", [["begin","end","name"],...], default="Olala")
        # date_group("expr", [["begin","end", "step" or None,"str" or ["str1","begin_date_fmt", "str3", "str4","end_date_fmt", "str6"]],...], default="Olala")
        # account.attributes
        # account.attributes.str1.value
        # account.attributes["SomeClassifier"].value
        # account.attributes["SomeClassifier"].value.parent.parent.parent.name

        # _l.debug('102: %s', safe_eval('date_range("2000-11-21", [[None,"2001-01-01",30,"o1"],["2001-01-01","2002-01-01",timedelta(months=1, day=31),"o2"]], "o3")'))

        # _l.debug('1: %s', safe_eval('format_date2("2001-12-12", "yyyy/MM/dd")'))


    # group_test()
    pass
