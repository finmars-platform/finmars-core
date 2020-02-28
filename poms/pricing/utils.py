from datetime import timedelta

from poms.common.utils import date_now


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
