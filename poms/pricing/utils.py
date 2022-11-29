import logging
from datetime import timedelta

from dateutil.relativedelta import relativedelta

from poms.common import formula
from poms.common.utils import date_now
from poms.currencies.models import CurrencyHistory
from poms.instruments.models import PriceHistory
from poms.obj_attrs.models import GenericAttribute
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


def get_parameter_from_scheme_parameters(item, pricing_policy, scheme_parameters):
    parameter = None

    try:

        if pricing_policy.default_value:

            if scheme_parameters.value_type == 10:

                parameter = str(pricing_policy.default_value)

            elif scheme_parameters.value_type == 20:

                parameter = float(pricing_policy.default_value)

            elif scheme_parameters.value_type == 40:

                parameter = formula._parse_date(str(pricing_policy.default_value))

            else:

                parameter = pricing_policy.default_value

        elif pricing_policy.attribute_key:

            if 'attributes' in pricing_policy.attribute_key:

                user_code = pricing_policy.attribute_key.split('attributes.')[1]

                attribute = GenericAttribute.objects.get(object_id=item.instrument.id,
                                                         attribute_type__user_code=user_code)

                if scheme_parameters.value_type == 10:
                    parameter = attribute.value_string

                if scheme_parameters.value_type == 20:
                    parameter = attribute.value_float

                if scheme_parameters.value_type == 40:
                    parameter = attribute.value_date

            else:

                parameter = getattr(item.instrument, pricing_policy.attribute_key, None)

    except Exception as e:

        _l.debug("Cant find parameter value. Error: %s" % e)

        parameter = None

    return parameter


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
    _l.debug("Roll Currency History for %s " % last_price)

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

            if last_price.fx_rate is not None:
                price.fx_rate = last_price.fx_rate

            # if can_write and price.fx_rate != 0:
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
                    created=procedure_instance.created
                )

                error.error_text = "Prices already exists. Fx rate: " + str(price.fx_rate) + "."

                # _l.debug('Roll Currency History Error Skip %s ' % error)

                error.status = CurrencyHistoryError.STATUS_SKIP
                error.save()

    return successful_prices_count, error_prices_count


def roll_price_history_for_n_day_forward(item, procedure, last_price, master_user, procedure_instance, instrument_pp):
    scheme_parameters = item.pricing_scheme.get_parameters()
    accrual_expr = scheme_parameters.accrual_expr
    _l.debug("Roll Price History for  %s for %s days" % (last_price, procedure.price_fill_days))

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
                    # _l.debug('Roll Price History Skip %s ' % price)
                # else:
                # _l.debug('Roll Price History Overwrite %s ' % price)

            except PriceHistory.DoesNotExist:

                price = PriceHistory(
                    instrument=last_price.instrument,
                    pricing_policy=last_price.pricing_policy,
                    date=new_date
                )

                # _l.debug('Roll Price History Create new %s ' % price)

            price.principal_price = 0
            price.accrued_price = 0

            parameter = get_parameter_from_scheme_parameters(item, instrument_pp, scheme_parameters)

            values = {
                'd': new_date,
                'instrument': last_price.instrument,
                'parameter': parameter
            }

            if last_price.principal_price is not None:
                price.principal_price = last_price.principal_price

            if scheme_parameters.accrual_calculation_method == 2:  # ACCRUAL_PER_SCHEDULE
                try:
                    price.accrued_price = item.instrument.get_accrued_price(new_date)
                except Exception:
                    price.accrued_price = 0

            elif scheme_parameters.accrual_calculation_method == 3:  # ACCRUAL_PER_FORMULA

                try:
                    price.accrued_price = formula.safe_eval(accrual_expr, names=values)
                except Exception:
                    price.accrued_price = 0
            else:

                if last_price.accrued_price is not None:
                    price.accrued_price = last_price.accrued_price

            # if can_write and not (price.accrued_price == 0 and price.principal_price == 0):
            if can_write:

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
                    created=procedure_instance.created

                )

                error.error_text = "Prices already exists. Principal Price: " + str(
                    price.principal_price) + "; Accrued: " + str(price.accrued_price) + "."

                # _l.debug('Roll Price History Error Skip %s ' % error)

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

relative_tenor_map = {
    "overnight": {
        "days": 1
    },
    "tomorrow_next": {
        "days": 2
    },
    "spot": {
        "days": 2
    },
    "spot_next": {
        "days": 3
    },
    "1w": {
        "days": 7
    },
    "2w": {
        "days": 12
    },
    "3w": {
        "days": 17
    },
    "1m": {
        "days": 2,
        "months": 1
    },
    "2m": {
        "days": 2,
        "months": 2
    },
    "3m": {
        "days": 2,
        "months": 3
    },
    "4m": {
        "days": 2,
        "months": 4
    },
    "5m": {
        "days": 2,
        "months": 5
    },
    "6m": {
        "days": 2,
        "months": 6
    },
    "7m": {
        "days": 2,
        "months": 7
    },
    "8m": {
        "days": 2,
        "months": 8
    },
    "9m": {
        "days": 2,
        "months": 9
    },
    "10m": {
        "days": 2,
        "months": 10
    },
    "11m": {
        "days": 2,
        "months": 11
    },
    "12m": {
        "days": 2,
        "months": 12
    },
    "1y": {
        "days": 2,
        "years": 1
    },
    "15m": {
        "days": 2,
        "months": 15
    },
    "18m": {
        "days": 2,
        "months": 18
    },
    "21m": {
        "days": 2,
        "months": 21
    },
    "2y": {
        "days": 2,
        "years": 2
    },
    "3y": {
        "days": 2,
        "years": 3
    },
    "4y": {
        "days": 2,
        "years": 4
    },
    "5y": {
        "days": 2,
        "years": 5
    },
    "6y": {
        "days": 2,
        "years": 6
    },
    "7y": {
        "days": 2,
        "years": 7
    },
    "8y": {
        "days": 2,
        "years": 8
    },
    "9y": {
        "days": 2,
        "years": 9
    },
    "10y": {
        "days": 2,
        "years": 10
    },
    "15y": {
        "days": 2,
        "years": 15
    },
    "20y": {
        "days": 2,
        "years": 20
    },
    "25y": {
        "days": 2,
        "years": 25
    },
    "30y": {
        "days": 2,
        "years": 30
    },
}


def find_tenor_date(date, tenor_type):
    result_date = date

    delta = relativedelta(**relative_tenor_map[tenor_type])

    result_date = result_date + delta

    if result_date.weekday == 5:  # saturday
        result_date = result_date + relativedelta(days=2)
    elif result_date.weekday == 6:  # sunday
        result_date = result_date + relativedelta(days=1)

    return result_date


def get_closest_tenors(maturity_date, date, tenors):
    result = []

    diff = maturity_date - date

    tenor_from = None
    tenor_to = None

    # TODO add check for weekends

    # _l.debug('tenors %s' % tenors)

    # looking for tenor from

    for tenor in tenors:

        tenor_type = tenor["tenor_type"]
        days = tenor_map[tenor_type]

        # current_tenor_from_date = timedelta(days=days) + date
        current_tenor_from_date = find_tenor_date(date, tenor_type)

        if tenor_from is None:

            if current_tenor_from_date < maturity_date:
                tenor_from = tenor

        else:

            # last_tenor_from_date = timedelta(days=tenor_map[tenor_from["tenor_type"]]) + date
            last_tenor_from_date = find_tenor_date(date, tenor_type)

            if current_tenor_from_date > last_tenor_from_date and current_tenor_from_date < maturity_date:
                tenor_from = tenor

    # looking for tenor to

    for tenor in tenors:

        tenor_type = tenor["tenor_type"]

        days = tenor_map[tenor_type]
        # current_tenor_to_date = timedelta(days=days) + date
        current_tenor_to_date = find_tenor_date(date, tenor_type)

        if tenor_to is None:

            if current_tenor_to_date > maturity_date:
                tenor_to = tenor

        else:

            # last_tenor_to_date = timedelta(days=tenor_map[tenor_to["tenor_type"]]) + date
            last_tenor_to_date = find_tenor_date(date, tenor_type)

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

    _l.info('date %s' % date)
    _l.info('tenor_from %s' % tenor_from)
    _l.info('tenor_to %s' % tenor_to)

    return result


def convert_results_for_calc_avg_price(records):
    result = []

    unique_rows = {}

    for item in records:

        pattern_list = [str(item.master_user_id), str(item.procedure_id), str(item.instrument_id),
                        str(item.pricing_policy_id), str(item.date)]
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

        _l.debug('item.tenor_from_price %s' % item.tenor_from_price)
        _l.debug('item.tenor_from_type %s' % item.tenor_from_type)

        _l.debug('item.tenor_to_price %s' % item.tenor_to_price)
        _l.debug('item.tenor_to_type %s' % item.tenor_to_type)

        if item.tenor_from_price and item.tenor_to_price:

            date_from = item.date + timedelta(days=tenor_map[item.tenor_from_type])
            date_to = item.date + timedelta(days=tenor_map[item.tenor_to_type])
            maturity_date = item.instrument.maturity_date

            w = (date_to - maturity_date) / (date_to - date_from)

            _l.debug("w %s" % w)

            average_weighted_price = item.tenor_from_price * w + item.tenor_to_price * (1 - w)

            setattr(item, 'average_weighted_price', average_weighted_price)

        elif item.tenor_from_price and not item.tenor_to_price:

            setattr(item, 'average_weighted_price', item.tenor_from_price)

        elif not item.tenor_from_price and item.tenor_to_price:

            setattr(item, 'average_weighted_price', item.tenor_to_price)

        else:

            setattr(item, 'average_weighted_price', None)

        result.append(item)

    return result
