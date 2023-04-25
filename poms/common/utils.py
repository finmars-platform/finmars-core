import calendar
import copy
import datetime
import logging
import math
from datetime import timedelta
from http import HTTPStatus

import pandas as pd
from django.contrib.contenttypes.models import ContentType
from django.utils.timezone import now
from django.views.generic.dates import timezone_today
from rest_framework.views import exception_handler

from poms_app import settings

_l = logging.getLogger('poms.common')


def force_qs_evaluation(qs):
    list(qs)

    pass

    # for item in qs:
    #     pass


def db_class_check_data(model, verbosity, using):
    from django.db import IntegrityError, ProgrammingError

    try:
        exists = set(model.objects.using(using).values_list('pk', flat=True))
    except ProgrammingError:
        return
    if verbosity >= 2:
        print('existed transaction classes -> %s' % exists)
    for id, code, name in model.CLASSES:
        if id not in exists:
            if verbosity >= 2:
                print('create %s class -> %s:%s' % (model._meta.verbose_name, id, name))
            try:
                model.objects.using(using).create(pk=id, user_code=code,
                                                  short_name=name,
                                                  name=name, description=name)
            except (IntegrityError, ProgrammingError):
                pass
        else:
            obj = model.objects.using(using).get(pk=id)
            obj.user_code = code
            if not obj.name:
                obj.name = name

            if not obj.short_name:
                obj.short_name = name
            if not obj.description:
                obj.description = name
            obj.save()


def date_now():
    return timezone_today()


def datetime_now():
    return now()


try:
    isclose = math.isclose
except AttributeError:
    try:
        import numpy

        isclose = numpy.isclose
    except ImportError:
        numpy = None


        def isclose(a, b, rel_tol=1e-09, abs_tol=0.0):
            # TODO: maybe incorrect!
            return abs(a - b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)


def iszero(v):
    return isclose(v, 0.0)


# def safe_div(a, b, default=0.0):
#     try:
#         return a / b
#     except (ZeroDivisionError, TypeError):
#         return default


class sfloat(float):
    def __truediv__(self, other):
        # print('__truediv__: self=%s, other=%s' % (self, other))
        try:
            return super(sfloat, self).__truediv__(other)
        except (ZeroDivisionError, OverflowError):
            return 0.0

    def __rtruediv__(self, other):
        # print('__rtruediv__: self=%s, other=%s' % (self, other))
        try:
            return super(sfloat, self).__rtruediv__(other)
        except (ZeroDivisionError, OverflowError):
            return 0.0

    def __floordiv__(self, other):
        # print('__floordiv__: self=%s, other=%s' % (self, other))
        try:
            return super(sfloat, self).__floordiv__(other)
        except (ZeroDivisionError, OverflowError):
            return 0.0

    def __rfloordiv__(self, other):
        # print('__floordiv__: self=%s, other=%s' % (self, other))
        try:
            return super(sfloat, self).__rfloordiv__(other)
        except (ZeroDivisionError, OverflowError):
            return 0.0

    def __pow__(self, power):
        # print('__pow__: self=%s, other=%s' % (self, other))
        try:
            return super(sfloat, self).__pow__(power)
        except (ZeroDivisionError, OverflowError):
            return 0.0

    def __rpow__(self, power):
        # print('__rpow__: self=%s, other=%s' % (self, other))
        try:
            return super(sfloat, self).__rpow__(power)
        except (ZeroDivisionError, OverflowError):
            return 0.0


def add_view_and_manage_permissions():
    from django.contrib.contenttypes.models import ContentType
    from django.contrib.auth.models import Permission

    existed = {(p.content_type_id, p.codename) for p in Permission.objects.all()}
    for content_type in ContentType.objects.all():
        codename = "view_%s" % content_type.model
        if (content_type.id, codename) not in existed:
            Permission.objects.update_or_create(
                content_type=content_type, codename=codename,
                defaults={
                    'name': 'Can view %s' % content_type.name
                }
            )

        codename = "manage_%s" % content_type.model
        if (content_type.id, codename) not in existed:
            Permission.objects.update_or_create(
                content_type=content_type, codename=codename,
                defaults={
                    'name': 'Can manage %s' % content_type.name
                }
            )


def delete_keys_from_dict(dict_del, the_keys):
    """
    Delete the keys present in the lst_keys from the dictionary.
    Loops recursively over nested dictionaries.
    """
    # make sure the_keys is a set to get O(1) lookups
    if type(the_keys) is not set:
        the_keys = set(the_keys)
    for k, v in dict_del.items():

        if k in the_keys:
            del dict_del[k]

        if isinstance(v, dict):
            delete_keys_from_dict(v, the_keys)
    return dict_del


def recursive_callback(dict, callback, prop="children"):
    callback(dict)

    # print(dict)

    if prop in dict:
        for item in dict[prop]:
            recursive_callback(item, callback)


class MemorySavingQuerysetIterator(object):

    def __init__(self, queryset, max_obj_num=1000):
        self._base_queryset = queryset
        self._generator = self._setup()
        self.max_obj_num = max_obj_num

    def _setup(self):
        for i in range(0, self._base_queryset.count(), self.max_obj_num):
            # By making a copy of of the queryset and using that to actually access
            # the objects we ensure that there are only `max_obj_num` objects in
            # memory at any given time
            smaller_queryset = copy.deepcopy(self._base_queryset)[i:i + self.max_obj_num]
            # logger.debug('Grabbing next %s objects from DB' % self.max_obj_num)
            for obj in smaller_queryset.iterator():
                yield obj

    def __iter__(self):
        return self

    def next(self):
        return self._generator.next()


def format_float(val):
    # 0.000050000892 -> 0.0000500009
    # 0.005623 -> 0.005623
    # 0.005623000551 -> 0.0056230006

    try:
        float(val)
    except ValueError:
        return val

    # return float(format(round(val, 10), '.10f').rstrip("0").rstrip('.'))
    return round(val, 10)


def format_float_to_2(val):
    # 0.000050000892 -> 0.0000500009
    # 0.005623 -> 0.005623
    # 0.005623000551 -> 0.0056230006

    try:
        float(val)
    except ValueError:
        return val

    return float(format(round(val, 2), '.2f').rstrip("0").rstrip('.'))


def get_content_type_by_name(name):
    pieces = name.split('.')
    app_label_title = pieces[0]
    model_title = pieces[1]

    content_type = ContentType.objects.get(app_label=app_label_title, model=model_title)

    return content_type


def is_business_day(date):
    return bool(len(pd.bdate_range(date, date)))


def get_last_business_day(date, to_string=False):
    '''
    Returns the previous business day of the given date.
    :param date:
    :param to_string:
    :return:
    '''

    format = '%Y-%m-%d'

    if not isinstance(date, datetime.date):
        date = datetime.datetime.strptime(date, format).date()

    weekday = datetime.date.weekday(date)
    if weekday > 4:  # if it's Saturday or Sunday
        date = date - datetime.timedelta(days=weekday - 4)

    if to_string:
        return date.strftime("%Y-%m-%d")

    return date


def last_day_of_month(any_day):
    # The day 28 exists in every month. 4 days later, it's always next month
    next_month = any_day.replace(day=28) + datetime.timedelta(days=4)
    # subtracting the number of the current day brings us back one month
    return next_month - datetime.timedelta(days=next_month.day)


def get_list_of_dates_between_two_dates(date_from, date_to, to_string=False):
    result = []
    format = '%Y-%m-%d'

    if not isinstance(date_from, datetime.date):
        date_from = datetime.datetime.strptime(date_from, format).date()

    if not isinstance(date_to, datetime.date):
        date_to = datetime.datetime.strptime(date_to, format).date()

    diff = date_to - date_from

    for i in range(diff.days + 1):
        day = date_from + timedelta(days=i)
        if to_string:
            result.append(str(day))
        else:
            result.append(day)

    return result


def get_list_of_business_days_between_two_dates(date_from, date_to, to_string=False):
    result = []
    format = '%Y-%m-%d'

    if not isinstance(date_from, datetime.date):
        date_from = datetime.datetime.strptime(date_from, format).date()

    if not isinstance(date_to, datetime.date):
        date_to = datetime.datetime.strptime(date_to, format).date()

    diff = date_to - date_from

    for i in range(diff.days + 1):
        day = date_from + timedelta(days=i)

        if is_business_day(day):

            if to_string:
                result.append(str(day))
            else:
                result.append(day)

    return result


def get_list_of_months_between_two_dates(date_from, date_to, to_string=False):
    result = []
    format = '%Y-%m-%d'

    if not isinstance(date_from, datetime.date):
        date_from = datetime.datetime.strptime(date_from, format).date()

    if not isinstance(date_to, datetime.date):
        date_to = datetime.datetime.strptime(date_to, format).date()

    diff = date_to - date_from

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


def convert_name_to_key(name):
    return name.strip().lower().replace(' ', '_')


def check_if_last_day_of_month(to_date):
    '''
    Check if date is last day of month
    :param to_date:
    :return: bool
    '''
    delta = datetime.timedelta(days=1)
    next_day = to_date + delta
    if to_date.month != next_day.month:
        return True
    return False


def get_first_transaction(portfolio_id):
    '''
    Get first transaction of portfolio
    :param portfolio_id:
    :return: Transaction
    '''
    from poms.transactions.models import Transaction
    transaction = Transaction.objects.filter(portfolio_id=portfolio_id).order_by('accounting_date')[0]
    return transaction


def last_business_day_in_month(year: int, month: int, to_string=False):
    '''
    Get last business day of month
    :param year:
    :param month:
    :param to_string:
    :return: date or string
    '''
    day = max(calendar.monthcalendar(year, month)[-1:][0][:5])

    d = datetime.datetime(year, month, day).date()

    if to_string:
        return d.strftime('%Y-%m-%d')

    return d


def get_last_bdays_of_months_between_two_dates(date_from, date_to, to_string=False):
    '''
    Get last business day of each month between two dates
    :param date_from:
    :param date_to:
    :param to_string:
    :return: list of dates or strings
    '''
    months = get_list_of_months_between_two_dates(date_from, date_to)
    end_of_months = []

    if not isinstance(date_to, datetime.date):
        d_date_to = datetime.datetime.strptime(date_to, '%Y-%m-%d').date()
    else:
        d_date_to = date_to

    for month in months:

        # _l.info(month)
        # _l.info(d_date_to)

        if last_business_day_in_month(month.year, month.month) > d_date_to:

            if to_string:
                end_of_months.append(d_date_to.strftime('%Y-%m-%d'))
            else:
                end_of_months.append(d_date_to)
        else:
            end_of_months.append(last_business_day_in_month(month.year, month.month, to_string))

    return end_of_months


def str_to_date(d):
    '''
    Convert string to date
    :param d:
    :return:
    '''
    if not isinstance(d, datetime.date):
        d = datetime.datetime.strptime(d, "%Y-%m-%d").date()

    return d


def get_closest_bday_of_yesterday(to_string=False):
    '''
    Get the closest business day of yesterday
    :param to_string:
    :return: date or string
    '''
    yesterday = datetime.date.today() - timedelta(days=1)
    return get_last_business_day(yesterday, to_string=to_string)


def finmars_exception_handler(exc, context):
    """Custom API exception handler."""

    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)

    if response is not None:
        # Using the description's of the HTTPStatus class as error message.
        http_code_to_message = {v.value: v.description for v in HTTPStatus}

        error_payload = {
            "error": {
                "url": context['request'].build_absolute_uri(),
                "status_code": 0,
                "message": "",
                "details": [],
                "datetime": str(datetime.datetime.strftime(now(), '%Y-%m-%d %H:%M:%S')),
                "workspace_id": settings.BASE_API_URL
            }
        }
        error = error_payload["error"]
        status_code = response.status_code

        error["status_code"] = status_code
        error["message"] = http_code_to_message[status_code]
        error["details"] = response.data
        response.data = error_payload
    return response


def get_serializer(content_type_key):
    '''
    Returns serializer for given content type key.
    :param content_type_key:
    :return: serializer class
    '''

    from poms.instruments.serializers import InstrumentSerializer, InstrumentTypeSerializer, PricingPolicySerializer

    from poms.accounts.serializers import AccountSerializer
    from poms.accounts.serializers import AccountTypeSerializer
    from poms.portfolios.serializers import PortfolioSerializer
    from poms.instruments.serializers import PriceHistorySerializer
    from poms.currencies.serializers import CurrencyHistorySerializer
    from poms.counterparties.serializers import CounterpartySerializer
    from poms.counterparties.serializers import ResponsibleSerializer
    from poms.strategies.serializers import Strategy1Serializer
    from poms.strategies.serializers import Strategy2Serializer

    from poms.transactions.serializers import TransactionTypeSerializer
    from poms.csv_import.serializers import CsvImportSchemeSerializer

    from poms.integrations.serializers import ComplexTransactionImportSchemeSerializer, \
        InstrumentDownloadSchemeSerializer
    from poms.procedures.serializers import PricingProcedureSerializer
    from poms.procedures.serializers import ExpressionProcedureSerializer
    from poms.procedures.serializers import RequestDataFileProcedureSerializer
    from poms.schedules.serializers import ScheduleSerializer

    from poms.obj_attrs.serializers import GenericAttributeTypeSerializer
    from poms.ui.serializers import DashboardLayoutSerializer
    from poms.ui.serializers import ListLayoutSerializer
    from poms.ui.serializers import ContextMenuLayoutSerializer
    from poms.ui.serializers import ComplexTransactionUserFieldSerializer
    from poms.ui.serializers import TransactionUserFieldSerializer
    from poms.ui.serializers import InstrumentUserFieldSerializer

    from poms.pricing.serializers import InstrumentPricingSchemeSerializer, CurrencyPricingSchemeSerializer

    serializer_map = {

        'transactions.transactiontype': TransactionTypeSerializer,
        'instruments.instrument': InstrumentSerializer,
        'instruments.instrumenttype': InstrumentTypeSerializer,
        'instruments.pricingpolicy': PricingPolicySerializer,

        'accounts.account': AccountSerializer,
        'accounts.accounttype': AccountTypeSerializer,
        'portfolios.portfolio': PortfolioSerializer,
        'instruments.pricehistory': PriceHistorySerializer,
        'currencies.currencyhistory': CurrencyHistorySerializer,
        'counterparties.counterparty': CounterpartySerializer,
        'counterparties.responsible': ResponsibleSerializer,
        'strategies.strategy1': Strategy1Serializer,
        'strategies.strategy2': Strategy2Serializer,
        'strategies.strategy3': Strategy2Serializer,

        'csv_import.csvimportscheme': CsvImportSchemeSerializer,
        'integrations.complextransactionimportscheme': ComplexTransactionImportSchemeSerializer,
        'integrations.instrumentdownloadscheme': InstrumentDownloadSchemeSerializer,
        'procedures.pricingprocedure': PricingProcedureSerializer,
        'procedures.expressionprocedure': ExpressionProcedureSerializer,
        'procedures.requestdatafileprocedure': RequestDataFileProcedureSerializer,
        'schedules.schedule': ScheduleSerializer,
        'obj_attrs.genericattributetype': GenericAttributeTypeSerializer,

        'ui.dashboardlayout': DashboardLayoutSerializer,
        'ui.listlayout': ListLayoutSerializer,
        'ui.contextmenulayout': ContextMenuLayoutSerializer,
        'ui.complextransactionuserfieldmodel': ComplexTransactionUserFieldSerializer,
        'ui.transactionuserfieldmodel': TransactionUserFieldSerializer,
        'ui.instrumentuserfieldmodel': InstrumentUserFieldSerializer,

        'pricing.instrumentpricingscheme': InstrumentPricingSchemeSerializer,
        'pricing.currencypricingscheme': CurrencyPricingSchemeSerializer

    }

    return serializer_map[content_type_key]


def get_list_of_entity_attributes(content_type_key):
    '''
    Returns a list of attributes for a given entity type.
    :param content_type_key:
    :return: list of attributes
    '''

    content_type = get_content_type_by_name(content_type_key)
    result = []
    from poms.obj_attrs.models import GenericAttributeType
    attribute_types = GenericAttributeType.objects.filter(content_type=content_type)

    for attribute_type in attribute_types:
        result.append({
            "name": attribute_type.name,
            "key": "attributes." + attribute_type.user_code,
            "value_type": attribute_type.value_type,
            "tooltip": attribute_type.tooltip,
            "can_recalculate": attribute_type.can_recalculate
        })

    return result


def compare_versions(version1, version2):
    v1_parts = version1.split('.')
    v2_parts = version2.split('.')

    for v1_part, v2_part in zip(v1_parts, v2_parts):
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


def is_newer_version(version1, version2):
    return compare_versions(version1, version2) > 0