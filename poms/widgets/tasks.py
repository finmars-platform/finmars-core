import traceback

from celery import shared_task



from poms.accounts.models import Account
from poms.celery_tasks.models import CeleryTask
from poms.common.models import ProxyUser, ProxyRequest
from poms.currencies.models import Currency
from poms.instruments.models import CostMethod, PricingPolicy
from poms.obj_attrs.models import GenericClassifier, GenericAttributeType
from poms.portfolios.models import Portfolio
from poms.reports.builders.balance_item import Report
from poms.reports.builders.balance_serializers import BalanceReportSqlSerializer, PLReportSqlSerializer
from poms.reports.sql_builders.balance import BalanceReportBuilderSql, PLReportBuilderSql
from poms.system_messages.handlers import send_system_message
from poms.widgets.handlers import StatsHandler
from poms.widgets.models import BalanceReportHistory, BalanceReportHistoryItem, PLReportHistory, WidgetStats

from poms.widgets.utils import find_next_date_to_process, collect_asset_type_category, collect_currency_category, \
    collect_country_category, collect_sector_category, collect_region_category

import logging
_l = logging.getLogger('poms.widgets')




def start_new_balance_history_collect(task):

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
            "portfolio_id": parent_options_object['portfolio_id'],
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

        portfolio_id = task.options_object.get('portfolio_id')

        portfolio = Portfolio.objects.get(id=portfolio_id)

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
            portfolios=[portfolio],
            pricing_policy=pricing_policy,
        )

        builder = BalanceReportBuilderSql(instance=instance)
        instance = builder.build_balance()

        serializer = BalanceReportSqlSerializer(instance=instance, context=context)

        instance_serialized = serializer.to_representation(instance)

        try:

            balance_report_history = BalanceReportHistory.objects.get(
                master_user=task.master_user,
                date=report_date,
                report_currency=report_currency,
                pricing_policy=pricing_policy,
                cost_method=cost_method,
                portfolio=portfolio
            )

        except Exception as e:

            balance_report_history = BalanceReportHistory.objects.create(
                master_user=task.master_user,
                date=report_date,
                report_currency=report_currency,
                pricing_policy=pricing_policy,
                cost_method=cost_method,
                portfolio=portfolio
            )


        balance_report_history.report_settings_data = task.options_object

        balance_report_history.save()

        # _l.info('instance_serialized %s' % instance_serialized)

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
            collect_asset_type_category(task.master_user, instance_serialized, balance_report_history, 'market_value')
        except Exception as e:
            _l.error("collect_balance_report_history. Could not collect asset type category %s" % e)
        try:
            collect_currency_category(task.master_user, instance_serialized, balance_report_history, 'market_value')
        except Exception as e:
            _l.error("collect_balance_report_history. Could not collect currency category %s" % e)
        try:
            collect_country_category(task.master_user, instance_serialized, balance_report_history, 'market_value')
        except Exception as e:
            _l.error("collect_balance_report_history. Could not collect country category %s" % e)

        try:
            collect_region_category(task.master_user, instance_serialized, balance_report_history, 'market_value')
        except Exception as e:
            _l.error("collect_balance_report_history. Could not collect region category %s" % e)

        try:
            collect_sector_category(task.master_user, instance_serialized, balance_report_history, 'market_value')
        except Exception as e:
            _l.error("collect_balance_report_history. Could not collect sector category %s" % e)

        parent_options_object = parent_task.options_object

        parent_options_object['processed_dates'].append(report_date)

        parent_task.options_object = parent_options_object
        parent_task.save()

        task.status = CeleryTask.STATUS_DONE
        task.save()

        start_new_balance_history_collect(task)

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

        start_new_balance_history_collect(task)



def start_new_pl_history_collect(task):

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
            "pl_first_date": parent_options_object['pl_first_date'],
            "report_date": date,
            "portfolio_id": parent_options_object['portfolio_id'],
            "report_currency_id": parent_options_object['report_currency_id'],
            "cost_method_id": parent_options_object['cost_method_id'],
            "pricing_policy_id": parent_options_object['pricing_policy_id'],
        }

        new_celery_task.options_object = options_object

        new_celery_task.save()

        collect_pl_report_history.apply_async(kwargs={'task_id': new_celery_task.id})

    else:

        send_system_message(master_user=parent_task.master_user,
                            performed_by=parent_task.member.username,
                            section='schedules',
                            type='success',
                            title='PL History Collected',
                            description='PL History from %s to %s are available for widgets' % (parent_options_object['date_from'], parent_options_object['date_to']),
                            )

        parent_task.status = CeleryTask.STATUS_DONE
        parent_task.save()



@shared_task(name='widgets.collect_pl_report_history', bind=True)
def collect_pl_report_history(self, task_id):

    _l.info('collect_pl_report_history init task_id %s' % task_id)

    task = CeleryTask.objects.get(id=task_id)
    parent_task = task.parent

    try:

        _l.info('task.options_object %s' % task.options_object)

        report_currency = Currency.objects.get(id=task.options_object.get('report_currency_id', None))
        report_date = task.options_object['report_date']
        pl_first_date = task.options_object['pl_first_date']
        cost_method = CostMethod.objects.get(id=task.options_object.get('cost_method_id', None))
        pricing_policy = PricingPolicy.objects.get(id=task.options_object.get('pricing_policy_id', None))

        portfolio_id = task.options_object.get('portfolio_id')

        portfolio = Portfolio.objects.get(id=portfolio_id)

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
            pl_first_date=pl_first_date,
            cost_method=cost_method,
            portfolios=[portfolio],
            pricing_policy=pricing_policy,
        )

        builder = PLReportBuilderSql(instance=instance)
        instance = builder.build_balance()

        serializer = PLReportSqlSerializer(instance=instance, context=context)

        instance_serialized = serializer.to_representation(instance)

        try:

            pl_report_history = PLReportHistory.objects.get(
                master_user=task.master_user,
                date=report_date,
                pl_first_date=pl_first_date,
                report_currency=report_currency,
                pricing_policy=pricing_policy,
                cost_method=cost_method,
                portfolio=portfolio
            )

        except Exception as e:

            pl_report_history = PLReportHistory.objects.create(
                master_user=task.master_user,
                date=report_date,
                pl_first_date=pl_first_date,
                report_currency=report_currency,
                pricing_policy=pricing_policy,
                cost_method=cost_method,
                portfolio=portfolio
            )

        pl_report_history.report_settings_data = task.options_object


        pl_report_history.save()

        # _l.info('instance_serialized %s' % instance_serialized)

        total = 0
        for item in instance_serialized['items']:
            if item['total'] is not None:
                total = total + item['total']

        pl_report_history.total = total
        pl_report_history.save()

        for _item in instance_serialized['items']:

            for instrument in instance_serialized['item_instruments']:

                if _item['instrument'] == instrument['id']:
                    _item['instrument_object'] = instrument

        try:
            collect_asset_type_category(task.master_user, instance_serialized, pl_report_history, 'total')
        except Exception as e:
            _l.error("collect_pl_report_history. Could not collect asset type category %s" %e)
        try:
            collect_currency_category(task.master_user, instance_serialized, pl_report_history, 'total')
        except Exception as e:
            _l.error("collect_pl_report_history. Could not collect currency category %s" %e)
        try:
            collect_country_category(task.master_user, instance_serialized, pl_report_history, 'total')
        except Exception as e:
            _l.error("collect_pl_report_history. Could not collect country category %s" %e)

        try:
            collect_region_category(task.master_user, instance_serialized, pl_report_history, 'total')
        except Exception as e:
            _l.error("collect_pl_report_history. Could not collect region category %s" %e)

        try:
            collect_sector_category(task.master_user, instance_serialized, pl_report_history, 'total')
        except Exception as e:
            _l.error("collect_pl_report_history. Could not collect sector category %s" %e)

        parent_options_object = parent_task.options_object

        parent_options_object['processed_dates'].append(report_date)

        parent_task.options_object = parent_options_object
        parent_task.save()

        task.status = CeleryTask.STATUS_DONE
        task.save()

        start_new_pl_history_collect(task)

    except Exception as e:

        _l.error("collect_pl_report_history. error %s" % e)
        _l.error("collect_pl_report_history. traceback %s" % traceback.format_exc())

        parent_options_object = parent_task.options_object

        parent_options_object['error_dates'].append(task.options_object['report_date'])

        parent_task.options_object = parent_options_object
        parent_task.save()

        task.status = CeleryTask.STATUS_ERROR
        task.error_message = str(e)
        task.save()

        start_new_pl_history_collect(task)



def start_new_collect_stats(task):

    parent_task = CeleryTask.objects.get(id=task.parent_id)
    parent_options_object = parent_task.options_object

    if (len(parent_options_object['processed_dates']) + len(parent_options_object['error_dates'])) != len(parent_options_object['dates_to_process']):
        new_celery_task = CeleryTask.objects.create(
            master_user=task.master_user,
            member=task.member,
            type='collect_stats',
            parent=parent_task
        )

        date = find_next_date_to_process(parent_task)

        options_object = {

            'portfolio_id': parent_options_object['portfolio_id'],
            'benchmark': parent_options_object['benchmark'],
            'date': date
        }

        new_celery_task.options_object = options_object

        new_celery_task.save()

        collect_stats.apply_async(kwargs={'task_id': new_celery_task.id})

    else:

        send_system_message(master_user=parent_task.master_user,
                            performed_by=parent_task.member.username,
                            section='schedules',
                            type='success',
                            title='Stats Collected',
                            description='Stats from %s to %s are available for widgets' % (parent_options_object['date_from'], parent_options_object['date_to']),
                            )

        parent_task.status = CeleryTask.STATUS_DONE
        parent_task.save()



@shared_task(name='widgets.collect_stats', bind=True)
def collect_stats(self, task_id):

    task = CeleryTask.objects.get(id=task_id)
    parent_task = task.parent

    try:

        stats_handler = StatsHandler(
            master_user=task.master_user,
            member=task.member,
            date=task.options_object['date'],
            portfolio_id=task.options_object['portfolio_id'],
            benchmark=task.options_object['benchmark']
        )

        result = {
            "nav": stats_handler.get_balance_nav(),  # done
            "total": stats_handler.get_pl_total(),  # done
            "cumulative_return": stats_handler.get_cumulative_return(),  # done
            "annualized_return": stats_handler.get_annualized_return(),  # done
            "portfolio_volatility": stats_handler.get_portfolio_volatility(), # done
            "annualized_portfolio_volatility": stats_handler.get_annualized_portfolio_volatility(), # done
            "sharpe_ratio": stats_handler.get_sharpe_ratio(), # done
            "max_annualized_drawdown": stats_handler.get_max_annualized_drawdown(),
            "betta": stats_handler.get_betta(),
            "alpha": stats_handler.get_alpha(),
            "correlation": stats_handler.get_correlation()
        }

        widget_stats_instance = None

        try:
            widget_stats_instance = WidgetStats.objects.get(master_user=task.master_user,
                                                             date=task.options_object['date'],
                                                             portfolio_id=task.options_object['portfolio_id'],
                                                             benchmark=task.options_object['benchmark'])
        except Exception as e:

            widget_stats_instance = WidgetStats.objects.create(
                master_user=task.master_user,
                date=task.options_object['date'],
                portfolio_id=task.options_object['portfolio_id'],
                benchmark=task.options_object['benchmark'])


        widget_stats_instance.nav = result['nav']
        widget_stats_instance.total = result['total']
        widget_stats_instance.cumulative_return = result['cumulative_return']
        widget_stats_instance.annualized_return = result['annualized_return']
        widget_stats_instance.portfolio_volatility = result['portfolio_volatility']
        widget_stats_instance.annualized_portfolio_volatility = result['annualized_portfolio_volatility']
        widget_stats_instance.sharpe_ratio = result['sharpe_ratio']
        widget_stats_instance.max_annualized_drawdown = result['max_annualized_drawdown']
        widget_stats_instance.betta = result['betta']
        widget_stats_instance.alpha = result['alpha']
        widget_stats_instance.correlation = result['correlation']

        widget_stats_instance.save()




        task.result_object = result

        task.status = CeleryTask.STATUS_DONE
        task.save()

        parent_options_object = parent_task.options_object

        parent_options_object['processed_dates'].append(task.options_object['date'])

        parent_task.options_object = parent_options_object
        parent_task.save()

        start_new_collect_stats(task)

    except Exception as e:

        _l.error("collect_stats.error %s" % e)
        _l.error("collect_stats.traceback %s" % traceback.format_exc())

        parent_options_object = parent_task.options_object

        parent_options_object['error_dates'].append(task.options_object['date'])

        parent_task.options_object = parent_options_object
        parent_task.save()

        task.status = CeleryTask.STATUS_ERROR
        task.error_message = str(e)
        task.save()

        start_new_collect_stats(task)
