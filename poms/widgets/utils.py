import logging

from django.contrib.contenttypes.models import ContentType

from poms.obj_attrs.models import GenericAttributeType, GenericClassifier
from poms.widgets.models import BalanceReportHistoryItem, PLReportHistoryItem

_l = logging.getLogger('poms.widgets')


def get_total_from_report_items(key, report_instance_items):
    result = 0
    try:
        for item in report_instance_items:

            if key in item:
                result = result + item[key]
    except Exception as e:
        _l.error("Could not collect total for %s" % key)

    return result

def collect_asset_type_category(report_type, master_user, instance_serialized, history, key='market_value'):


    instrument_content_type = ContentType.objects.get(app_label="instruments", model='instrument')

    asset_types_attribute_type = GenericAttributeType.objects.get(master_user=master_user,
                                                                  content_type=instrument_content_type,
                                                                  user_code='asset_types')

    asset_types = GenericClassifier.objects.filter(attribute_type=asset_types_attribute_type).values_list('name',
                                                                                                       flat=True)


    for asset_type in asset_types:
        if report_type == 'balance':
            item = BalanceReportHistoryItem()
            item.balance_report_history = history

        if report_type == 'pl':
            item = PLReportHistoryItem()
            item.pl_report_history = history

        item.category = 'Asset Types'
        item.key = key
        item.name = asset_type

        asset_type_items = []

        for _item in instance_serialized['items']:

            if _item.get('instrument_object'):

                for attribute in _item['instrument_object']['attributes']:

                    if attribute['attribute_type'] == asset_types_attribute_type.id:

                        if attribute['classifier_object']:
                            if attribute['classifier_object']['name'] == asset_type:
                                asset_type_items.append(_item)

        item.value = get_total_from_report_items(key, asset_type_items)

        item.save()

    # Do the Null asset type separately

    if report_type == 'balance':
        item = BalanceReportHistoryItem()
        item.balance_report_history = history

    if report_type == 'pl':
        item = PLReportHistoryItem()
        item.pl_report_history = history


    item.category = 'Asset Types'
    item.key = key
    item.name = 'Other'

    null_asset_type_items = []

    for _item in instance_serialized['items']:

        if _item.get('instrument_object'):

            for attribute in _item['instrument_object']['attributes']:

                if attribute['attribute_type'] == asset_types_attribute_type.id:

                    if not attribute.get('classifier_object'):
                        null_asset_type_items.append(_item)

    item.value = get_total_from_report_items(key, null_asset_type_items)

    item.save()

    # Do the CASH & Equivalents separately from user attributes

    if report_type == 'balance':
        item = BalanceReportHistoryItem()
        item.balance_report_history = history

    if report_type == 'pl':
        item = PLReportHistoryItem()
        item.pl_report_history = history


    item.category = 'Asset Types'
    item.key = key
    item.name = 'Cash & Equivalents'

    asset_type_items = []

    for _item in instance_serialized['items']:
        if _item['item_type'] != 1:
            asset_type_items.append(_item)

    item.value = get_total_from_report_items(key, asset_type_items)

    item.save()


def collect_sector_category(report_type, master_user, instance_serialized, history, key='market_value'):

    instrument_content_type = ContentType.objects.get(app_label="instruments", model='instrument')

    sector_attribute_type = GenericAttributeType.objects.get(master_user=master_user,
                                                             content_type=instrument_content_type,
                                                                  user_code='sector')

    sectors = []

    for _item in instance_serialized['items']:

        if _item.get('instrument_object'):

            for attribute in _item['instrument_object']['attributes']:

                if attribute['attribute_type'] == sector_attribute_type.id:

                    if attribute['value_string'] not in sectors:
                        sectors.append(attribute['value_string'])


    for sector in sectors:
        if report_type == 'balance':
            item = BalanceReportHistoryItem()
            item.balance_report_history = history

        if report_type == 'pl':
            item = PLReportHistoryItem()
            item.pl_report_history = history

        item.category = 'Sector'
        item.key = key
        item.name = sector

        sector_items = []

        for _item in instance_serialized['items']:

            if _item.get('instrument_object'):
                for attribute in _item['instrument_object']['attributes']:

                    if attribute['attribute_type'] == sector_attribute_type.id:
                        if sector == attribute['value_string']:
                            sector_items.append(_item)

        item.value = get_total_from_report_items(key, sector_items)

        item.save()

    item.category = 'Sector'
    item.key = key
    item.name = 'Cash & Equivalents'

    asset_type_items = []

    for _item in instance_serialized['items']:
        if _item['item_type'] != 1:
            asset_type_items.append(_item)

    item.value = get_total_from_report_items(key, asset_type_items)

def collect_country_category(report_type, master_user, instance_serialized, history, key='market_value'):

    countries = []

    for _item in instance_serialized['items']:

        if _item.get('instrument_object'):

            if _item['instrument_object'].get('country_object'):

                if _item['instrument_object']['country_object']['name'] not in countries:
                    countries.append(_item['instrument_object']['country_object']['name'])

    for country in countries:
        if report_type == 'balance':
            item = BalanceReportHistoryItem()
            item.balance_report_history = history

        if report_type == 'pl':
            item = PLReportHistoryItem()
            item.pl_report_history = history

        item.category = 'Country'
        item.key = key
        item.name = country

        country_items = []

        for _item in instance_serialized['items']:

            if _item.get('instrument_object'):

                if _item['instrument_object'].get('country_object'):

                    if _item['instrument_object']['country_object']['name'] == country:
                        country_items.append(_item)

        item.value = get_total_from_report_items(key, country_items)

        item.save()

    item.category = 'Country'
    item.key = key
    item.name = 'Cash & Equivalents'

    asset_type_items = []

    for _item in instance_serialized['items']:
        if _item['item_type'] != 1:
            asset_type_items.append(_item)

    item.value = get_total_from_report_items(key, asset_type_items)

def collect_region_category(report_type, master_user, instance_serialized, history, key='market_value'):

    regions = []

    for _item in instance_serialized['items']:

        if _item.get('instrument_object'):

            if _item['instrument_object'].get('country_object'):

                if _item['instrument_object']['country_object']['region'] not in regions:
                    regions.append(_item['instrument_object']['country_object']['region'])

    for region in regions:
        if report_type == 'balance':
            item = BalanceReportHistoryItem()
            item.balance_report_history = history

        if report_type == 'pl':
            item = PLReportHistoryItem()
            item.pl_report_history = history

        item.category = 'Region'
        item.key = key
        item.name = region

        region_items = []

        for _item in instance_serialized['items']:

            if _item.get('instrument_object'):

                if _item['instrument_object'].get('country_object'):

                    if _item['instrument_object']['country_object']['region'] == region:
                        region_items.append(_item)

        item.value = get_total_from_report_items(key, region_items)

        item.save()

    item.category = 'Region'
    item.key = key
    item.name = 'Cash & Equivalents'

    asset_type_items = []

    for _item in instance_serialized['items']:
        if _item['item_type'] != 1:
            asset_type_items.append(_item)

    item.value = get_total_from_report_items(key, asset_type_items)

def collect_currency_category(report_type, master_user, instance_serialized, history, key='market_value'):
    currencies_ids = []
    currencies = []

    for _item in instance_serialized['items']:

        if _item['exposure_currency']:
            if _item['exposure_currency'] not in currencies_ids:
                currencies_ids.append(_item['exposure_currency'])

    for currency_id in currencies_ids:
        for currency in instance_serialized['item_currencies']:
            if currency_id == currency['id']:
                currencies.append(currency)

    for currency in currencies:

        if report_type == 'balance':
            item = BalanceReportHistoryItem()
            item.balance_report_history = history

        if report_type == 'pl':
            item = PLReportHistoryItem()
            item.pl_report_history = history

        item.category = 'Currency'
        item.key = key
        item.name = currency['name']

        currency_items = []

        for _item in instance_serialized['items']:

            if _item['exposure_currency'] == currency['id']:
                currency_items.append(_item)

        item.value = get_total_from_report_items(key, currency_items)

        item.save()

def find_next_date_to_process(parent_task):

    result = None

    parent_options_object = parent_task.options_object

    i = 0

    found = False

    while not found:

        result = parent_options_object['dates_to_process'][i]

        found = True

        i = i + 1

        if i < len(parent_options_object['dates_to_process']):

            if result in parent_options_object['processed_dates']:
                found = False

            if result in parent_options_object['error_dates']:
                found = False

    return result
