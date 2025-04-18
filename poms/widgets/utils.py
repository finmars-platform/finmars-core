import datetime
import logging
import traceback

from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from poms.celery_tasks.models import CeleryTask
from poms.common.utils import get_first_transaction
from poms.obj_attrs.models import GenericAttributeType, GenericClassifier
from poms.system_messages.handlers import send_system_message
from poms.widgets.models import BalanceReportHistoryItem, PLReportHistoryItem

_l = logging.getLogger('poms.widgets')


def get_total_from_report_items(key, report_instance_items):
    result = 0
    try:
        for item in report_instance_items:

            if key in item:

                if item[key] or item[key] == 0:
                    result = result + item[key]
    except Exception as e:
        _l.error("Could not collect total for %s e %s" % (key, e))
        _l.error(traceback.format_exc())

    return result


# DEPRECATED, should be move to workflow/olap
def collect_asset_type_category(report_type, master_user, instance_serialized, history, key='market_value'):
    instrument_content_type = ContentType.objects.get(app_label="instruments", model='instrument')

    try:
        asset_types_attribute_type = GenericAttributeType.objects.get(master_user=master_user,
                                                                      content_type=instrument_content_type,
                                                                      user_code='asset_types')
    except Exception as e:
        asset_types_attribute_type = GenericAttributeType.objects.get(master_user=master_user,
                                                                      content_type=instrument_content_type,
                                                                      user_code='com.finmars.marscapital-attribute:instruments.instrument:asset_type')

    asset_types = GenericClassifier.objects.filter(attribute_type=asset_types_attribute_type).values_list('name',
                                                                                                          flat=True)

    # _l.info('collect_asset_type_category.asset_types %s' % asset_types)
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

                        if attribute.get('classifier_object'):
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
    item.name = 'No Category'

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
    item.name = 'Cash'

    asset_type_items = []

    for _item in instance_serialized['items']:
        if _item['item_type'] != 1:
            asset_type_items.append(_item)

    item.value = get_total_from_report_items(key, asset_type_items)

    item.save()


def get_unique_sectors(instance_serialized, master_user):
    instrument_content_type = ContentType.objects.get(app_label="instruments", model='instrument')

    sector_attribute_type = GenericAttributeType.objects.get(master_user=master_user,
                                                             content_type=instrument_content_type,
                                                             user_code='sector')

    sectors = []

    for _item in instance_serialized['items']:

        if _item.get('instrument_object'):

            for attribute in _item['instrument_object']['attributes']:

                if attribute['attribute_type'] == sector_attribute_type.id:

                    if attribute['value_string']:
                        if attribute['value_string'] not in sectors:
                            sectors.append(attribute['value_string'])

    return sectors


def collect_sector_category(report_type, master_user, instance_serialized, history, key='market_value'):
    instrument_content_type = ContentType.objects.get(app_label="instruments", model='instrument')

    try:
        sector_attribute_type = GenericAttributeType.objects.get(master_user=master_user,
                                                                 content_type=instrument_content_type,
                                                                 user_code='sector')
    except Exception as e:

        sector_attribute_type = GenericAttributeType.objects.get(master_user=master_user,
                                                                 content_type=instrument_content_type,
                                                                 user_code='com.finmars.marscapital-attribute:instruments.instrument:sector')

    sectors = get_unique_sectors(instance_serialized, master_user)

    # _l.info('collect_sector_category.sectors %s ' % sectors)

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

    # Get value for No category items

    if report_type == 'balance':
        item = BalanceReportHistoryItem()
        item.balance_report_history = history

    if report_type == 'pl':
        item = PLReportHistoryItem()
        item.pl_report_history = history

    item.category = 'Sector'
    item.key = key
    item.name = 'No category'

    no_category_items = []

    for _item in instance_serialized['items']:

        if _item.get('instrument_object'):

            for attribute in _item['instrument_object']['attributes']:

                if attribute['attribute_type'] == sector_attribute_type.id:
                    if not attribute['value_string']:
                        no_category_items.append(_item)

    item.value = get_total_from_report_items(key, no_category_items)

    item.save()

    # Get value for Cash items (No instruments items)

    if report_type == 'balance':
        item = BalanceReportHistoryItem()
        item.balance_report_history = history

    if report_type == 'pl':
        item = PLReportHistoryItem()
        item.pl_report_history = history

    item.category = 'Sector'
    item.key = key
    item.name = 'Cash'

    asset_type_items = []

    for _item in instance_serialized['items']:
        if _item['item_type'] != 1:
            asset_type_items.append(_item)

    item.value = get_total_from_report_items(key, asset_type_items)

    item.save()


def get_unique_countries(instance_serialized):
    countries = []

    for _item in instance_serialized['items']:

        if _item.get('instrument_object'):

            if _item['instrument_object'].get('country_object'):

                if _item['instrument_object']['country_object']['name'] not in countries:
                    countries.append(_item['instrument_object']['country_object']['name'])

    return countries


def collect_country_category(report_type, master_user, instance_serialized, history, key='market_value'):
    countries = get_unique_countries(instance_serialized)

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

    # Get value for No category items

    if report_type == 'balance':
        item = BalanceReportHistoryItem()
        item.balance_report_history = history

    if report_type == 'pl':
        item = PLReportHistoryItem()
        item.pl_report_history = history

    item.category = 'Country'
    item.key = key
    item.name = 'No category'

    no_category_items = []

    for _item in instance_serialized['items']:

        if _item.get('instrument_object'):

            if not _item['instrument_object'].get('country_object'):
                no_category_items.append(_item)

    item.value = get_total_from_report_items(key, no_category_items)

    item.save()

    # Get value for Cash items (No instruments items)

    if report_type == 'balance':
        item = BalanceReportHistoryItem()
        item.balance_report_history = history

    if report_type == 'pl':
        item = PLReportHistoryItem()
        item.pl_report_history = history

    item.category = 'Country'
    item.key = key
    item.name = 'Cash'

    asset_type_items = []

    for _item in instance_serialized['items']:
        if _item['item_type'] != 1:
            asset_type_items.append(_item)

    item.value = get_total_from_report_items(key, asset_type_items)
    item.save()


def get_unique_regions(instance_serialized):
    regions = []

    for _item in instance_serialized['items']:

        if _item.get('instrument_object'):

            if _item['instrument_object'].get('country_object'):

                if _item['instrument_object']['country_object']['region'] not in regions:
                    regions.append(_item['instrument_object']['country_object']['region'])

    return regions


def collect_region_category(report_type, master_user, instance_serialized, history, key='market_value'):
    # Get values for instrument categorized by region

    regions = get_unique_regions(instance_serialized)

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

    # Get value for No Category items

    if report_type == 'balance':
        item = BalanceReportHistoryItem()
        item.balance_report_history = history

    if report_type == 'pl':
        item = PLReportHistoryItem()
        item.pl_report_history = history

    item.category = 'Region'
    item.key = key
    item.name = 'No Category'

    no_category_items = []

    for _item in instance_serialized['items']:

        if _item.get('instrument_object'):

            if not _item['instrument_object'].get('country_object'):
                no_category_items.append(_item)

    item.value = get_total_from_report_items(key, no_category_items)

    item.save()

    # Get value for Cash items (No instruments items)

    if report_type == 'balance':
        item = BalanceReportHistoryItem()
        item.balance_report_history = history

    if report_type == 'pl':
        item = PLReportHistoryItem()
        item.pl_report_history = history

    item.category = 'Region'
    item.key = key
    item.name = 'Cash'

    asset_type_items = []

    for _item in instance_serialized['items']:
        if _item['item_type'] != 1:
            asset_type_items.append(_item)

    item.value = get_total_from_report_items(key, asset_type_items)
    item.save()


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

            if _item.get('exposure_currency') == currency['id']:
                currency_items.append(_item)

        item.value = get_total_from_report_items(key, currency_items)

        item.save()

    # Get value for No Category items

    if report_type == 'balance':
        item = BalanceReportHistoryItem()
        item.balance_report_history = history

    if report_type == 'pl':
        item = PLReportHistoryItem()
        item.pl_report_history = history

    item.category = 'Currency'
    item.key = key
    item.name = 'No Category'

    no_category_items = []

    for _item in instance_serialized['items']:

        if not _item.get('exposure_currency'):
            no_category_items.append(_item)

    item.value = get_total_from_report_items(key, no_category_items)

    item.save()


def str_to_date(date_string):
    return datetime.datetime.strptime(date_string, '%Y-%m-%d').date()


def find_next_date_to_process(task):
    result = None

    task_options_object = task.options_object

    i = 0

    found = False

    while not found:

        result = task_options_object['dates_to_process'][i]

        found = True

        i = i + 1

        if i < len(task_options_object['dates_to_process']):

            if result in task_options_object['processed_dates']:
                found = False

            if result in task_options_object['error_dates']:
                found = False

    return result


def collect_balance_history(master_user, member, date_from, date_to, dates, segmentation_type, portfolio_id,
                            report_currency_id,
                            cost_method_id, pricing_policy_id, sync=False):
    from poms.widgets.tasks import collect_balance_report_history

    from poms.portfolios.models import Portfolio
    portfolio = Portfolio.objects.get(id=portfolio_id)

    task = CeleryTask.objects.create(
        master_user=master_user,
        member=member,
        type='collect_history',
        verbose_name="Collect Nav History for %s portfolio" % (portfolio.name),
    )

    options_object = {
        "report_date": dates[0],
        'date_from': date_from,
        'date_to': date_to,
        'portfolio_id': portfolio_id,
        'segmentation_type': segmentation_type,
        'report_currency_id': report_currency_id,
        'cost_method_id': cost_method_id,
        'pricing_policy_id': pricing_policy_id,
        'dates_to_process': dates,
        'error_dates': [],
        'processed_dates': []
    }

    task.options_object = options_object

    task.save()

    if sync:

        send_system_message(master_user=task.master_user,
                            performed_by=task.member.username,
                            section='schedules',
                            type='info',
                            title='Balance History is start collecting',
                            description='Balance History from %s to %s will be soon available' % (
                                options_object['date_from'], options_object['date_to']),
                            )

        collect_balance_report_history.apply(kwargs={'task_id': task.id, "context": {"realm_code": task.realm_code, "space_code": task.space_code}})

    else:

        transaction.on_commit(lambda: collect_balance_report_history.apply_async(kwargs={'task_id': task.id, 'context': {
            'space_code': task.master_user.space_code,
            'realm_code': task.master_user.realm_code
        }}))

        send_system_message(master_user=task.master_user,
                            performed_by=task.member.username,
                            section='schedules',
                            type='info',
                            title='Balance History is start collecting',
                            description='Balance History from %s to %s will be soon available' % (
                                options_object['date_from'], options_object['date_to']),
                            )

    return task


def collect_pl_history(master_user, member, date_from, date_to, dates, segmentation_type, portfolio_id,
                       report_currency_id, cost_method_id,
                       pricing_policy_id, sync=False):
    from poms.widgets.tasks import collect_pl_report_history

    from poms.portfolios.models import Portfolio
    portfolio = Portfolio.objects.get(id=portfolio_id)

    pl_first_date = str(get_first_transaction(portfolio_id).accounting_date)

    task = CeleryTask.objects.create(
        master_user=master_user,
        member=member,
        verbose_name="Collect Pl History for %s portfolio" % (portfolio.name),
        type='collect_history'
    )

    options_object = {
        'date_from': date_from,
        'date_to': date_to,
        'segmentation_type': segmentation_type,
        'portfolio_id': portfolio_id,
        'report_currency_id': report_currency_id,
        'cost_method_id': cost_method_id,
        'pricing_policy_id': pricing_policy_id,
        'dates_to_process': dates,
        'error_dates': [],
        'processed_dates': [],
        'pl_first_date': pl_first_date,
        'report_date': dates[0],

    }

    task.options_object = options_object

    task.save()

    if sync:
        send_system_message(master_user=task.master_user,
                            performed_by=task.member.username,
                            section='schedules',
                            type='info',
                            title='PL History is start collecting',
                            description='PL History from %s to %s will be soon available' % (
                                options_object['date_from'], options_object['date_to']),
                            )
        collect_pl_report_history.apply(kwargs={'task_id': task.id, "context": {"realm_code": task.realm_code, "space_code": task.space_code}})

    else:
        transaction.on_commit(lambda: collect_pl_report_history.apply_async(kwargs={'task_id': task.id, 'context': {
            'space_code': task.master_user.space_code,
            'realm_code': task.master_user.realm_code
        }}))

        send_system_message(master_user=task.master_user,
                            performed_by=task.member.username,
                            section='schedules',
                            type='info',
                            title='PL History is start collecting',
                            description='PL History from %s to %s will be soon available' % (
                                options_object['date_from'], options_object['date_to']),
                            )
    return task


def collect_widget_stats(master_user, member, date_from, date_to, dates, segmentation_type, portfolio_id, benchmark,
                         sync=False):
    from poms.widgets.tasks import collect_stats

    from poms.portfolios.models import Portfolio
    portfolio = Portfolio.objects.get(id=portfolio_id)

    task = CeleryTask.objects.create(
        master_user=master_user,
        member=member,
        verbose_name="Collect Widget Stats for %s portfolio" % (portfolio.name),
    )

    options_object = {
        'date_from': date_from,
        'date_to': date_to,
        'segmentation_type': segmentation_type,
        'portfolio_id': portfolio_id,
        'benchmark': benchmark,
        'dates_to_process': dates,
        'error_dates': [],
        'processed_dates': [],
        'date': dates[0]
    }

    task.options_object = options_object

    task.save()

    if sync:
        collect_stats.apply(kwargs={'task_id': task.id, "context": {"realm_code": task.realm_code, "space_code": task.space_code}})
    else:
        transaction.on_commit(lambda: collect_stats.apply_async(kwargs={'task_id': task.id, 'context': {
            'space_code': task.master_user.space_code,
            'realm_code': task.master_user.realm_code
        }}))

    return task
