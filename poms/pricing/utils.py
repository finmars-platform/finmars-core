from datetime import timedelta

from poms.common.utils import date_now
from poms.currencies.models import CurrencyHistory
from poms.instruments.models import PriceHistory


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
            print('Pricing scheme is not set in policy %s' % item.policy.id)

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


def roll_currency_history_for_n_day_forward(procedure, last_price):

    print("Roll Currency History for %s " % last_price)

    if procedure.price_fill_days:

        for i in range(procedure.price_fill_days):

            can_write = True

            new_date = last_price.date + timedelta(days=i)

            try:

                price = CurrencyHistory.objects.get(
                    currency=last_price.currency,
                    pricing_policy=last_price.pricing_policy,
                    date=new_date
                )

                if not procedure.price_override_existed:
                    can_write = False

            except CurrencyHistory.DoesNotExist:

                price = CurrencyHistory(
                    currency=last_price.currency,
                    pricing_policy=last_price.pricing_policy,
                    date=new_date
                )

            if can_write:

                if last_price.fx_rate:
                    price.fx_rate = last_price.fx_rate

                price.save()


def roll_price_history_for_n_day_forward(procedure, last_price):

    print("Roll Price History for  %s for %s days" % (last_price, procedure.price_fill_days))

    if procedure.price_fill_days:

        for i in range(procedure.price_fill_days):

            can_write = True

            new_date = last_price.date + timedelta(days=i)

            try:

                price = PriceHistory.objects.get(
                    instrument=last_price.instrument,
                    pricing_policy=last_price.pricing_policy,
                    date=new_date
                )

                if not procedure.price_override_existed:
                    can_write = False
                    print('Roll Price History Skip %s ' % price)
                else:
                    print('Roll Price History Overwrite %s ' % price)

            except PriceHistory.DoesNotExist:

                price = PriceHistory(
                    instrument=last_price.instrument,
                    pricing_policy=last_price.pricing_policy,
                    date=new_date
                )

                print('Roll Price History Create new %s ' % price)

            if can_write:

                price.principal_price = 0
                price.accrued_price = 0

                if last_price.principal_price:
                    price.principal_price = last_price.principal_price

                if last_price.accrued_price:
                    price.accrued_price = last_price.accrued_price

                price.save()
