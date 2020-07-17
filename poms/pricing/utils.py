from datetime import timedelta

from poms.common.utils import date_now
from poms.currencies.models import CurrencyHistory
from poms.instruments.models import PriceHistory

import logging

from poms.pricing.models import PriceHistoryError, CurrencyHistoryError

_l = logging.getLogger('poms.pricing')


def get_empty_values_for_dates(dates):

    result = []

    for date in dates:

        result.append({
            "date": str(date),
            "value": None
        })

    return result


def get_unique_pricing_schemes(items):

    unique_ids = []
    result = []

    for item in items:

        for policy in item.pricing_policies.all():

            if policy.pricing_scheme:

                if policy.pricing_scheme.id not in unique_ids:
                    unique_ids.append(policy.pricing_scheme.id)
                    result.append(policy.pricing_scheme)

    return result


def get_list_of_dates_between_two_dates(date_from, date_to):
    result = []

    diff = date_to - date_from

    for i in range(diff.days + 1):
        day = date_from + timedelta(days=i)
        result.append(day)

    return result


def group_items_by_provider(items, groups):

    result = {}

    for item in groups:
        result[item.type.id] = []

    for item in items:
        if item.policy.pricing_scheme:
            result[item.policy.pricing_scheme.type.id].append(item)
        else:
            _l.info('Pricing scheme is not set in policy %s' % item.policy.id)

    return result


def get_is_yesterday(date_from, date_to):

    if date_from == date_to:

        yesterday = date_now() - timedelta(days=1)

        if yesterday == date_from:
            return True

    return False


def optimize_items(items):

    unique_references = []
    unique_codes = {}

    result_dict = {}
    result = []

    for item in items:

        reference_identifier = item['reference'] + ','.join(item['parameters'])

        if reference_identifier not in unique_references:

            result_item = {}

            result_item['reference'] = item['reference']
            result_item['parameters'] = item['parameters']
            result_item['fields'] = []

            unique_references.append(reference_identifier)

            unique_codes[reference_identifier] = []

            for field in item['fields']:

                code_identifier = field['code'] + ','.join(field['parameters'])

                if code_identifier not in unique_codes[reference_identifier]:
                    unique_codes[reference_identifier].append(code_identifier)

                    result_item['fields'].append(field)

            result_dict[reference_identifier] = result_item

        else:

            for field in item['fields']:

                code_identifier = field['code'] + ','.join(field['parameters'])

                if code_identifier not in unique_codes[reference_identifier]:
                    unique_codes[reference_identifier].append(code_identifier)

                    result_dict[reference_identifier]['fields'].append(field)

    for key, value in result_dict.items():
        result.append(value)

    return result


def roll_currency_history_for_n_day_forward(item, procedure, last_price, master_user, procedure_instance):

    _l.info("Roll Currency History for %s " % last_price)

    successful_prices_count = 0
    error_prices_count = 0

    if procedure.price_fill_days:

        for i in range(procedure.price_fill_days):

            i = i + 1

            can_write = True

            new_date = last_price.date + timedelta(days=i)

            try:

                price = CurrencyHistory.objects.get(
                    currency=last_price.currency,
                    pricing_policy=last_price.pricing_policy,
                    date=new_date
                )

                if not procedure.price_overwrite_fx_rates:
                    can_write = False

            except CurrencyHistory.DoesNotExist:

                price = CurrencyHistory(
                    currency=last_price.currency,
                    pricing_policy=last_price.pricing_policy,
                    date=new_date
                )

            price.fx_rate = 0

            if last_price.fx_rate:
                price.fx_rate = last_price.fx_rate

            if can_write and price.fx_rate != 0:

                successful_prices_count = successful_prices_count + 1

                price.save()

            else:

                error_prices_count = error_prices_count + 1

                error = CurrencyHistoryError(
                    master_user=master_user,
                    procedure_instance=procedure_instance,
                    currency=item.currency,
                    pricing_scheme=item.pricing_scheme,
                    pricing_policy=last_price.pricing_policy,
                    date=new_date,
                )

                error.error_text = "Prices already exists. Fx rate: " + str(price.fx_rate) + "."

                # _l.info('Roll Currency History Error Skip %s ' % error)

                error.status = CurrencyHistoryError.STATUS_SKIP
                error.save()

    return successful_prices_count, error_prices_count


def roll_price_history_for_n_day_forward(item, procedure, last_price, master_user, procedure_instance):

    _l.info("Roll Price History for  %s for %s days" % (last_price, procedure.price_fill_days))

    successful_prices_count = 0
    error_prices_count = 0

    if procedure.price_fill_days:

        for i in range(procedure.price_fill_days):

            i = i + 1

            can_write = True

            new_date = last_price.date + timedelta(days=i)

            try:

                price = PriceHistory.objects.get(
                    instrument=last_price.instrument,
                    pricing_policy=last_price.pricing_policy,
                    date=new_date
                )

                if not procedure.price_overwrite_principal_prices and not procedure.price_overwrite_accrued_prices:
                    can_write = False
                    # _l.info('Roll Price History Skip %s ' % price)
                # else:
                    # _l.info('Roll Price History Overwrite %s ' % price)

            except PriceHistory.DoesNotExist:

                price = PriceHistory(
                    instrument=last_price.instrument,
                    pricing_policy=last_price.pricing_policy,
                    date=new_date
                )

                # _l.info('Roll Price History Create new %s ' % price)

            price.principal_price = 0
            price.accrued_price = 0

            if last_price.principal_price:
                price.principal_price = last_price.principal_price

            if last_price.accrued_price:
                price.accrued_price = last_price.accrued_price

            if can_write and not (price.accrued_price == 0 and price.principal_price == 0):

                successful_prices_count = successful_prices_count + 1

                price.save()

            else:

                error_prices_count = error_prices_count + 1

                error = PriceHistoryError(
                    master_user=master_user,
                    procedure_instance=procedure_instance,
                    instrument=item.instrument,
                    pricing_scheme=item.pricing_scheme,
                    pricing_policy=last_price.pricing_policy,
                    date=new_date,
                )

                error.error_text = "Prices already exists. Principal Price: " + str(price.principal_price) +"; Accrued: "+ str(price.accrued_price) +"."

                # _l.info('Roll Price History Error Skip %s ' % error)

                error.status = PriceHistoryError.STATUS_SKIP
                error.save()

    return successful_prices_count, error_prices_count

tenor_map = {
    "overnight": 1,
    "tomorrow_next": 2,
    "spot": 2,
    "spot_next": 2 + 1,
    "1w": 2 + 7,
    "2w": 2 + 14,
    "3w": 2 + 21,
    "1m": 2 + 30,
    "2m": 2 + 60,
    "3m": 2 + 90,
    "4m": 2 + 120,
    "5m": 2 + 150,
    "6m": 2 + 180,
    "7m": 2 + 210,
    "8m": 2 + 240,
    "9m": 2 + 270,
    "10m": 2 + 300,
    "11m": 2 + 330,
    "12m": 2 + 360,
    "1y": 2 + 365,
    "15m": 2 + 450,
    "18m": 2 + 540
}

def get_closest_tenors(maturity_date, date, tenors):

    result = []

    diff = maturity_date - date

    tenor_from = None
    tenor_to = None

    # TODO add check for weekends

    # _l.info('tenors %s' % tenors)

    # looking for tenor from

    for tenor in tenors:

        tenor_type = tenor["tenor_type"]
        days = tenor_map[tenor_type]

        current_tenor_from_date = timedelta(days=days) + date

        if tenor_from is None:

            if current_tenor_from_date < maturity_date:

                tenor_from = tenor

        else:

            last_tenor_from_date = timedelta(days=tenor_map[tenor_from["tenor_type"]]) + date

            if current_tenor_from_date > last_tenor_from_date and current_tenor_from_date < maturity_date:
                tenor_from = tenor


    # looking for tenor to

    for tenor in tenors:

        tenor_type = tenor["tenor_type"]

        days = tenor_map[tenor_type]
        current_tenor_to_date = timedelta(days=days) + date

        if tenor_to is None:

            if current_tenor_to_date > maturity_date:

                tenor_to = tenor

        else:

            last_tenor_to_date = timedelta(days=tenor_map[tenor_to["tenor_type"]]) + date

            if current_tenor_to_date < last_tenor_to_date and current_tenor_to_date > maturity_date:
                tenor_to = tenor

    if tenor_from and tenor_to:

        tenor_from['tenor_clause'] = 'from'
        tenor_to['tenor_clause'] = 'to'

        result.append(tenor_from)
        result.append(tenor_to)

    if tenor_from and not tenor_to:
        tenor_from['tenor_clause'] = 'from'
        result.append(tenor_from)
        tenor_from['tenor_clause'] = 'to'
        result.append(tenor_from)

    if not tenor_from and tenor_to:
        tenor_to['tenor_clause'] = 'from'
        result.append(tenor_to)
        tenor_to['tenor_clause'] = 'to'
        result.append(tenor_to)

    return result


def convert_results_for_calc_avg_price(records):

    result = []

    unique_rows = {}

    for item in records:

        pattern_list = [str(item.master_user_id), str(item.procedure_id), str(item.instrument_id), str(item.pricing_policy_id), str(item.reference), str(item.date)]
        pattern_key = ".".join(pattern_list)

        if pattern_key in unique_rows:

            if (item.tenor_clause == 'from'):
                setattr(unique_rows[pattern_key], 'tenor_from_price', item.price_code_value)
                setattr(unique_rows[pattern_key], 'tenor_from_type', item.tenor_type)
            else:
                setattr(unique_rows[pattern_key], 'tenor_to_price', item.price_code_value)
                setattr(unique_rows[pattern_key], 'tenor_to_type', item.tenor_type)

        else:

            unique_rows[pattern_key] = item

            setattr(unique_rows[pattern_key], 'tenor_from_price', None)
            setattr(unique_rows[pattern_key], 'tenor_from_type', None)
            setattr(unique_rows[pattern_key], 'tenor_to_price', None)
            setattr(unique_rows[pattern_key], 'tenor_to_type', None)

            if (item.tenor_clause == 'from'):
                setattr(unique_rows[pattern_key], 'tenor_from_price', item.price_code_value)
                setattr(unique_rows[pattern_key], 'tenor_from_type', item.tenor_type)
            else:
                setattr(unique_rows[pattern_key], 'tenor_to_price', item.price_code_value)
                setattr(unique_rows[pattern_key], 'tenor_to_type', item.tenor_type)

    for key in unique_rows:

        item = unique_rows[key]

        average_weighted_price = None

        _l.info('item.tenor_from_price %s' % item.tenor_from_price)
        _l.info('item.tenor_from_type %s' % item.tenor_from_type)

        _l.info('item.tenor_to_price %s' % item.tenor_to_price)
        _l.info('item.tenor_to_type %s' % item.tenor_to_type)

        if item.tenor_from_price and item.tenor_to_price:

            date_from = item.date + timedelta(days=tenor_map[item.tenor_from_type])
            date_to = item.date + timedelta(days=tenor_map[item.tenor_to_type])
            maturity_date = item.instrument.maturity_date

            w = (date_to - maturity_date) / (date_to - date_from)

            _l.info("w %s" % w)

            average_weighted_price = item.tenor_from_price * w + item.tenor_to_price * (1 - w)

            setattr(item, 'average_weighted_price', average_weighted_price)

        elif item.tenor_from_price and not item.tenor_to_price:

            setattr(item, 'average_weighted_price', item.tenor_from_price)

        elif not item.tenor_from_price and item.tenor_to_price:

            setattr(item, 'average_weighted_price', item.tenor_to_price)

        result.append(item)

    return result

