import traceback

from celery import shared_task

import logging

from poms.accounts.models import Account
from poms.celery_tasks.models import CeleryTask
from poms.common.models import ProxyUser, ProxyRequest
from poms.currencies.models import Currency
from poms.instruments.models import CostMethod, PricingPolicy
from poms.obj_attrs.models import GenericClassifier, GenericAttributeType
from poms.portfolios.models import Portfolio
from poms.reports.builders.balance_item import Report
from poms.reports.builders.balance_serializers import BalanceReportSqlSerializer
from poms.reports.sql_builders.balance import BalanceReportBuilderSql
from poms.system_messages.handlers import send_system_message
from poms.widgets.models import BalanceReportHistory, BalanceReportHistoryItem

_l = logging.getLogger('poms.widgets')


def get_total_from_report_items(key, report_instance_items):
    result = 0
    try:
        for item in report_instance_items:
            result = result + item[key]
    except Exception as e:
        _l.error("Could not collect total for %s" % key)

    return result


def filter_report_items_by_instrument_attribute_type(attribute_type_id, value, instance_serialized):
    results = []

    for _item in instance_serialized['items']:

        if _item.get('instrument_object'):

            for attribute in _item['instrument_object']['attributes']:

                if attribute['attribute_type'] == attribute_type_id:

                    if attribute['classifier_object']:
                        if attribute['classifier_object'] == value:
                            results.append(_item)

    return results


def collect_asset_type_category(instance_serialized, balance_report_history):
    asset_types_attribute_type = GenericAttributeType.objects.get(master_user_id=instance_serialized['master_user'],
                                                                  user_code='asset_types')

    asset_types = GenericClassifier.objects.get(attribute_type=asset_types_attribute_type).values_list('name',
                                                                                                       flat=True)

    for asset_type in asset_types:
        item = BalanceReportHistoryItem()
        item.balance_report_history = balance_report_history
        item.category = 'Asset Types'
        item.key = 'nav'
        item.name = asset_type

        asset_type_items = filter_report_items_by_instrument_attribute_type(asset_types_attribute_type.id, asset_type,
                                                                            instance_serialized)

        item.value = get_total_from_report_items('market_value', asset_type_items)

        item.save()

    # Do the CASH & Equivalents separately from user attributes

    item = BalanceReportHistoryItem()
    item.balance_report_history = balance_report_history
    item.category = 'Asset Types'
    item.key = 'nav'
    item.name = 'Cash & Equivalents'

    asset_type_items = []

    for _item in instance_serialized['items']:
        if _item['item_type'] == 2:
            asset_type_items.append(_item)

    item.value = get_total_from_report_items('market_value', asset_type_items)

    item.save()


def collect_country_category(instance_serialized, balance_report_history):
    asset_types_attribute_type = GenericAttributeType.objects.get(master_user_id=instance_serialized['master_user'],
                                                                  user_code='country')

    asset_types = GenericClassifier.objects.get(attribute_type=asset_types_attribute_type).values_list('name',
                                                                                                       flat=True)

    for asset_type in asset_types:
        item = BalanceReportHistoryItem()
        item.balance_report_history = balance_report_history
        item.category = 'Country'
        item.key = 'nav'
        item.name = asset_type

        asset_type_items = filter_report_items_by_instrument_attribute_type(asset_types_attribute_type.id, asset_type,
                                                                            instance_serialized)

        item.value = get_total_from_report_items('market_value', asset_type_items)

        item.save()


def collect_currency_category(instance_serialized, balance_report_history):
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

        item = BalanceReportHistoryItem()
        item.balance_report_history = balance_report_history
        item.category = 'Currency'
        item.key = 'nav'
        item.name = currency['name']

        currency_items = []

        for _item in instance_serialized['items']:

            if _item['exposure_currency'] == currency['id']:
                currency_items.append(_item)

        item.value = get_total_from_report_items('market_value', currency_items)

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



def start_new_collect(task):

    parent_task = CeleryTask.objects.get(id=task.parent_id)
    parent_options_object = parent_task.options_object

    if (len(parent_options_object['processed_dates']) + len(parent_options_object['error_dates'])) != len(parent_options_object['dates_to_process']):
        new_celery_task = CeleryTask.objects.create(
            master_user=task.master_user,
            member=task.member,
            type='collect_history',
            parent=parent_task
        )

        date = find_next_date_to_process(parent_task)

        options_object = {
            "report_date": date,
            "accounts": parent_options_object['accounts'],
            "portfolios": parent_options_object['portfolios'],
            "report_currency_id": parent_options_object['report_currency_id'],
            "cost_method_id": parent_options_object['cost_method_id'],
            "pricing_policy_id": parent_options_object['pricing_policy_id'],
        }

        new_celery_task.options_object = options_object

        new_celery_task.save()

        collect_balance_report_history.apply_async(kwargs={'task_id': new_celery_task.id})

    else:

        send_system_message(master_user=parent_task.master_user,
                            performed_by=parent_task.member.username,
                            section='schedules',
                            type='success',
                            title='Balance History Collected',
                            description='Balances from %s to %s are available for widgets' % (parent_options_object['date_from'], parent_options_object['date_to']),
                            )

        parent_task.status = CeleryTask.STATUS_DONE
        parent_task.save()


@shared_task(name='widgets.collect_balance_report_history', bind=True)
def collect_balance_report_history(self, task_id):

    _l.info('collect_balance_report_history init task_id %s' % task_id)

    task = CeleryTask.objects.get(id=task_id)
    parent_task = task.parent

    try:

        _l.info('task.options_object %s' % task.options_object)

        report_currency = Currency.objects.get(id=task.options_object.get('report_currency_id', None))
        report_date = task.options_object['report_date']
        cost_method = CostMethod.objects.get(id=task.options_object.get('cost_method_id', None))
        pricing_policy = PricingPolicy.objects.get(id=task.options_object.get('pricing_policy_id', None))

        portfolios_ids = task.options_object.get('portfolios')
        if not portfolios_ids:
            portfolios_ids = []

        accounts_ids = task.options_object.get('accounts')
        if not accounts_ids:
            accounts_ids = []

        portfolios = list(Portfolio.objects.filter(id__in=portfolios_ids))
        accounts = list(Account.objects.filter(id__in=accounts_ids))

        proxy_user = ProxyUser(task.member, task.master_user)
        proxy_request = ProxyRequest(proxy_user)

        context = {
            'request': proxy_request
        }

        instance = Report(
            master_user=task.master_user,
            member=task.member,
            report_currency=report_currency,
            report_date=report_date,
            cost_method=cost_method,
            portfolios=portfolios,
            accounts=accounts,
            pricing_policy=pricing_policy,
        )

        builder = BalanceReportBuilderSql(instance=instance)
        instance = builder.build_balance()

        serializer = BalanceReportSqlSerializer(instance=instance, context=context)

        instance_serialized = serializer.to_representation(instance)

        balance_report_history = BalanceReportHistory.objects.create(
            master_user=task.master_user,
            date=report_date,
            report_currency=report_currency,
            pricing_policy=pricing_policy,
            cost_method=cost_method,
        )

        balance_report_history.report_settings_data = task.options_object
        balance_report_history.portfolios.set(portfolios)
        balance_report_history.accounts.set(accounts)

        balance_report_history.save()

        _l.info('instance_serialized %s' % instance_serialized)

        nav = 0
        for item in instance_serialized['items']:
            if item['market_value'] is not None:
                nav = nav + item['market_value']

        balance_report_history.nav = nav
        balance_report_history.save()

        for _item in instance_serialized['items']:

            for instrument in instance_serialized['item_instruments']:

                if _item['instrument'] == instrument['id']:
                    _item['instrument_object'] = instrument

        try:
            collect_asset_type_category(instance_serialized, balance_report_history)
        except Exception as e:
            _l.error("collect_balance_report_history. Could not collect asset type category")
        try:
            collect_currency_category(instance_serialized, balance_report_history)
        except Exception as e:
            _l.error("collect_balance_report_history. Could not collect currency category")
        try:
            collect_country_category(instance_serialized, balance_report_history)
        except Exception as e:
            _l.error("collect_balance_report_history. Could not collect country category")
        # collect_category('Sector', instance_serialized, balance_report_history)

        parent_options_object = parent_task.options_object

        parent_options_object['processed_dates'].append(report_date)

        parent_task.options_object = parent_options_object
        parent_task.save()

        task.status = CeleryTask.STATUS_DONE
        task.save()

        start_new_collect(task)

    except Exception as e:

        _l.error("collect_balance_report_history. error %s" % e)
        _l.error("collect_balance_report_history. traceback %s" % traceback.format_exc())

        parent_options_object = parent_task.options_object

        parent_options_object['error_dates'].append(task.options_object['report_date'])

        parent_task.options_object = parent_options_object
        parent_task.save()

        task.status = CeleryTask.STATUS_ERROR
        task.error_message = str(e)
        task.save()

        start_new_collect(task)
