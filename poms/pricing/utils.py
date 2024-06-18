import logging
from datetime import timedelta

from dateutil.relativedelta import relativedelta

from poms.expressions_engine import formula
from poms.common.utils import date_now
from poms.currencies.models import CurrencyHistory
from poms.instruments.models import PriceHistory
from poms.obj_attrs.models import GenericAttribute

_l = logging.getLogger('poms.pricing')


def get_empty_values_for_dates(dates):
    result = []

    for date in dates:
        result.append({
            "date": str(date),
            "value": None
        })

    return result


def get_list_of_dates_between_two_dates(date_from, date_to):
    result = []

    diff = date_to - date_from

    for i in range(diff.days + 1):
        day = date_from + timedelta(days=i)
        result.append(day)

    return result


def group_instrument_items_by_provider(items, groups):
    result = {}

    for group in groups:
        result[group.type.id] = []

    result['has_linked_with_portfolio'] = []

    for item in items:
        if item.policy.pricing_scheme:

            if item.instrument.has_linked_with_portfolio == True:
                result['has_linked_with_portfolio'].append(item)
            else:
                result[item.policy.pricing_scheme.type.id].append(item)
        else:
            _l.debug('Pricing scheme is not set in policy %s' % item.policy.id)

    return result


def group_currency_items_by_provider(items, groups):
    result = {}

    for item in groups:
        result[item.type.id] = []

    for item in items:
        if item.policy.pricing_scheme:
            result[item.policy.pricing_scheme.type.id].append(item)
        else:
            _l.debug('Pricing scheme is not set in policy %s' % item.policy.id)

    return result


def get_is_yesterday(date_from, date_to):
    if date_from == date_to:

        yesterday = date_now() - timedelta(days=1)

        if yesterday == date_from:
            return True

    return False