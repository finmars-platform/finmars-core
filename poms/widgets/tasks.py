import logging
import traceback

from poms.celery_tasks import finmars_task
from poms.celery_tasks.models import CeleryTask
from poms.common.models import ProxyUser, ProxyRequest
from poms.common.utils import (
    get_closest_bday_of_yesterday,
    get_list_of_dates_between_two_dates,
)
from poms.currencies.models import Currency
from poms.instruments.models import CostMethod, PricingPolicy
from poms.portfolios.models import Portfolio
from poms.reports.common import Report
from poms.reports.serializers import BalanceReportSerializer, PLReportSerializer
from poms.reports.sql_builders.balance import (
    BalanceReportBuilderSql,
    PLReportBuilderSql,
)
from poms.system_messages.handlers import send_system_message
from poms.users.models import EcosystemDefault, Member
from poms.widgets.handlers import StatsHandler
from poms.widgets.models import (
    BalanceReportHistory,
    BalanceReportHistoryItem,
    PLReportHistory,
    WidgetStats,
    PLReportHistoryItem,
)
from poms.widgets.utils import (
    find_next_date_to_process,
    collect_asset_type_category,
    collect_currency_category,
    collect_country_category,
    collect_sector_category,
    collect_region_category,
    collect_pl_history,
    collect_balance_history,
    collect_widget_stats,
    str_to_date,
)

_l = logging.getLogger("poms.widgets")


def start_new_balance_history_collect(task):
    task = CeleryTask.objects.get(id=task.id)
    task_options_object = task.options_object

    if (
        len(task_options_object["processed_dates"])
        + len(task_options_object["error_dates"])
    ) < len(task_options_object["dates_to_process"]):
        collect_balance_report_history.apply_async(
            kwargs={
                "task_id": task.id,
                "context": {
                    "space_code": task.master_user.space_code,
                    "realm_code": task.master_user.realm_code,
                },
            }
        )

    else:
        send_system_message(
            master_user=task.master_user,
            performed_by=task.member.username,
            section="schedules",
            type="success",
            title="Balance History Collected",
            description="Balances from %s to %s are available for widgets"
            % (task_options_object["date_from"], task_options_object["date_to"]),
        )

        task.status = CeleryTask.STATUS_DONE
        task.save()


@finmars_task(name="widgets.collect_balance_report_history", bind=True)
def collect_balance_report_history(self, task_id, *args, **kwargs):
    """

    ==== Hope this thing will move into workflow/olap ASAP ====

    Purpose of this task is collect Balance Reports for specific period of dates
    Important notice. Some results of aggregations (such as sectors, asset types, currencies, etc) is HARDCODED
    So whole this code is a temporary solution for Widget Dashboard

    """

    _l.info("collect_balance_report_history init task_id %s" % task_id)

    task = CeleryTask.objects.get(id=task_id)
    report_date = str_to_date(find_next_date_to_process(task))

    try:
        _l.info("task.options_object %s" % task.options_object)

        report_currency = Currency.objects.get(
            id=task.options_object.get("report_currency_id", None)
        )

        cost_method = CostMethod.objects.get(
            id=task.options_object.get("cost_method_id", None)
        )
        pricing_policy = PricingPolicy.objects.get(
            id=task.options_object.get("pricing_policy_id", None)
        )

        portfolio_id = task.options_object.get("portfolio_id")

        portfolio = Portfolio.objects.get(id=portfolio_id)

        proxy_user = ProxyUser(task.member, task.master_user)
        proxy_request = ProxyRequest(proxy_user)

        context = {"request": proxy_request}

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

        serializer = BalanceReportSerializer(instance=instance, context=context)

        instance_serialized = serializer.to_representation(instance)

        try:
            balance_report_history = BalanceReportHistory.objects.get(
                master_user=task.master_user, date=report_date, portfolio=portfolio
            )

        except Exception as e:
            balance_report_history = BalanceReportHistory.objects.create(
                master_user=task.master_user,
                date=report_date,
                report_currency=report_currency,
                pricing_policy=pricing_policy,
                cost_method=cost_method,
                portfolio=portfolio,
            )

        balance_report_history.report_settings_data = task.options_object

        balance_report_history.save()

        BalanceReportHistoryItem.objects.filter(
            balance_report_history=balance_report_history
        ).delete()

        # _l.info('instance_serialized %s' % instance_serialized)
        _l.info("instance_serialized len items %s" % len(instance_serialized["items"]))

        nav = 0
        for item in instance_serialized["items"]:
            if item["market_value"] is not None:
                nav = nav + item["market_value"]

        balance_report_history.nav = nav
        balance_report_history.save()

        for _item in instance_serialized["items"]:
            for instrument in instance_serialized["item_instruments"]:
                if _item["instrument"] == instrument["id"]:
                    _item["instrument_object"] = instrument

        try:
            collect_asset_type_category(
                "balance",
                task.master_user,
                instance_serialized,
                balance_report_history,
                "market_value",
            )
        except Exception as e:
            _l.error(
                "collect_balance_report_history. Could not collect asset type category %s"
                % e
            )
        try:
            collect_currency_category(
                "balance",
                task.master_user,
                instance_serialized,
                balance_report_history,
                "market_value",
            )
        except Exception as e:
            _l.error(
                "collect_balance_report_history. Could not collect currency category %s"
                % e
            )
        try:
            collect_country_category(
                "balance",
                task.master_user,
                instance_serialized,
                balance_report_history,
                "market_value",
            )
        except Exception as e:
            _l.error(
                "collect_balance_report_history. Could not collect country category %s"
                % e
            )

        try:
            collect_region_category(
                "balance",
                task.master_user,
                instance_serialized,
                balance_report_history,
                "market_value",
            )
        except Exception as e:
            _l.error(
                "collect_balance_report_history. Could not collect region category %s"
                % e
            )

        try:
            collect_sector_category(
                "balance",
                task.master_user,
                instance_serialized,
                balance_report_history,
                "market_value",
            )
        except Exception as e:
            _l.error(
                "collect_balance_report_history. Could not collect sector category %s"
                % e
            )

        task_options_object = task.options_object

        task_options_object["processed_dates"].append(report_date)

        task.options_object = task_options_object

        result_object = task.result_object

        if not result_object:
            result_object = {"results": []}

        result_object["results"].append(
            {
                "date": str(report_date),
                "status": "success",
                "id": balance_report_history.id,
            }
        )

        task.result_object = result_object

        task.save()

        start_new_balance_history_collect(task)

    except Exception as e:
        _l.error("collect_balance_report_history. error %s" % e)
        _l.error(
            "collect_balance_report_history. traceback %s" % traceback.format_exc()
        )

        task_options_object = task.options_object

        task_options_object["error_dates"].append(task.options_object["report_date"])

        task.options_object = task_options_object

        task.status = CeleryTask.STATUS_ERROR
        if not task.error_message:
            task.error_message = str(e)
        else:
            task.error_message = task.error_message + "\n" + str(e)
        task.save()

        start_new_balance_history_collect(task)


def start_new_pl_history_collect(task):
    task = CeleryTask.objects.get(id=task.id)
    task_options_object = task.options_object

    if (
        len(task_options_object["processed_dates"])
        + len(task_options_object["error_dates"])
    ) < len(task_options_object["dates_to_process"]):
        collect_pl_report_history.apply_async(
            kwargs={
                "task_id": task.id,
                "context": {
                    "space_code": task.master_user.space_code,
                    "realm_code": task.master_user.realm_code,
                },
            }
        )

    else:
        send_system_message(
            master_user=task.master_user,
            performed_by=task.member.username,
            section="schedules",
            type="success",
            title="PL History Collected",
            description="PL History from %s to %s are available for widgets"
            % (task_options_object["date_from"], task_options_object["date_to"]),
        )

        task.status = CeleryTask.STATUS_DONE
        task.save()


@finmars_task(name="widgets.collect_pl_report_history", bind=True)
def collect_pl_report_history(self, task_id, *args, **kwargs):
    """

    ==== Hope this thing will move into workflow/olap ASAP ====

    Purpose of this task is collect PL Reports for specific period of dates
    Important notice. Some results of aggregations (such as sectors, asset types, currencies, etc) is HARDCODED
    So whole this code is a temporary solution for Widget Dashboard

    It same logic as Collect Balance Report

    """
    _l.info("collect_pl_report_history init task_id %s" % task_id)

    task = CeleryTask.objects.get(id=task_id)
    report_date = str_to_date(find_next_date_to_process(task))

    try:
        _l.info("task.options_object %s" % task.options_object)

        report_currency = Currency.objects.get(
            id=task.options_object.get("report_currency_id", None)
        )
        pl_first_date = str_to_date(task.options_object["pl_first_date"])
        cost_method = CostMethod.objects.get(
            id=task.options_object.get("cost_method_id", None)
        )
        pricing_policy = PricingPolicy.objects.get(
            id=task.options_object.get("pricing_policy_id", None)
        )

        portfolio_id = task.options_object.get("portfolio_id")

        portfolio = Portfolio.objects.get(id=portfolio_id)

        proxy_user = ProxyUser(task.member, task.master_user)
        proxy_request = ProxyRequest(proxy_user)

        context = {"request": proxy_request}

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
        instance = builder.build_report()

        serializer = PLReportSerializer(instance=instance, context=context)

        instance_serialized = serializer.to_representation(instance)

        try:
            pl_report_history = PLReportHistory.objects.get(
                master_user=task.master_user, date=report_date, portfolio=portfolio
            )

        except Exception as e:
            pl_report_history = PLReportHistory.objects.create(
                master_user=task.master_user,
                date=report_date,
                pl_first_date=pl_first_date,
                report_currency=report_currency,
                pricing_policy=pricing_policy,
                cost_method=cost_method,
                portfolio=portfolio,
            )

        pl_report_history.report_settings_data = task.options_object

        pl_report_history.save()

        PLReportHistoryItem.objects.filter(pl_report_history=pl_report_history).delete()

        # _l.info('instance_serialized %s' % instance_serialized)

        total = 0
        for item in instance_serialized["items"]:
            if item["total"] is not None:
                total = total + item["total"]

        pl_report_history.total = total
        pl_report_history.save()

        for _item in instance_serialized["items"]:
            for instrument in instance_serialized["item_instruments"]:
                if _item["instrument"] == instrument["id"]:
                    _item["instrument_object"] = instrument

        try:
            collect_asset_type_category(
                "pl", task.master_user, instance_serialized, pl_report_history, "total"
            )
        except Exception as e:
            _l.error(
                "collect_pl_report_history. Could not collect asset type category %s"
                % e
            )
        try:
            collect_currency_category(
                "pl", task.master_user, instance_serialized, pl_report_history, "total"
            )
        except Exception as e:
            _l.error(
                "collect_pl_report_history. Could not collect currency category %s" % e
            )
        try:
            collect_country_category(
                "pl", task.master_user, instance_serialized, pl_report_history, "total"
            )
        except Exception as e:
            _l.error(
                "collect_pl_report_history. Could not collect country category %s" % e
            )

        try:
            collect_region_category(
                "pl", task.master_user, instance_serialized, pl_report_history, "total"
            )
        except Exception as e:
            _l.error(
                "collect_pl_report_history. Could not collect region category %s" % e
            )

        try:
            collect_sector_category(
                "pl", task.master_user, instance_serialized, pl_report_history, "total"
            )
        except Exception as e:
            _l.error(
                "collect_pl_report_history. Could not collect sector category %s" % e
            )

        task_options_object = task.options_object

        task_options_object["processed_dates"].append(report_date)

        task.options_object = task_options_object

        result_object = task.result_object

        if not result_object:
            result_object = {"results": []}

        result_object["results"].append(
            {"date": str(report_date), "status": "success", "id": pl_report_history.id}
        )

        task.result_object = result_object

        task.save()

        start_new_pl_history_collect(task)

    except Exception as e:
        _l.error("collect_pl_report_history. error %s" % e)
        _l.error("collect_pl_report_history. traceback %s" % traceback.format_exc())

        task_options_object = task.options_object

        task_options_object["error_dates"].append(task.options_object["report_date"])

        task.options_object = task_options_object

        task.status = CeleryTask.STATUS_ERROR

        if not task.error_message:
            task.error_message = str(e)
        else:
            task.error_message = task.error_message + "\n" + str(e)

        task.save()

        start_new_pl_history_collect(task)


def start_new_collect_stats(task):
    task = CeleryTask.objects.get(id=task.id)
    task_options_object = task.options_object

    if (
        len(task_options_object["processed_dates"])
        + len(task_options_object["error_dates"])
    ) < len(task_options_object["dates_to_process"]):
        collect_stats.apply_async(
            kwargs={
                "task_id": task.id,
                "context": {
                    "space_code": task.master_user.space_code,
                    "realm_code": task.master_user.realm_code,
                },
            }
        )

    else:
        send_system_message(
            master_user=task.master_user,
            performed_by=task.member.username,
            section="schedules",
            type="success",
            title="Stats Collected",
            description="Stats from %s to %s are available for widgets"
            % (task_options_object["date_from"], task_options_object["date_to"]),
        )

        task.status = CeleryTask.STATUS_DONE
        task.save()


@finmars_task(name="widgets.collect_stats", bind=True)
def collect_stats(self, task_id, *args, **kwargs):
    """

    Task that calculates metrics on portfolio for each day
    It has some heavy calculations such as  'max_annualized_drawdown_month' or 'betta'

    Serve the same purpose as tasks above, demo for Widgets Dashboard

    """

    task = CeleryTask.objects.get(id=task_id)

    task.celery_tasks_id = self.request.id
    task.status = CeleryTask.STATUS_PENDING
    task.save()

    date = find_next_date_to_process(task)

    try:
        stats_handler = StatsHandler(
            master_user=task.master_user,
            member=task.member,
            date=date,
            portfolio_id=task.options_object["portfolio_id"],
            benchmark=task.options_object["benchmark"],
        )

        max_annualized_drawdown, max_annualized_drawdown_month = (
            stats_handler.get_max_annualized_drawdown()
        )

        result = {
            "nav": stats_handler.get_balance_nav(),  # done
            "total": stats_handler.get_pl_total(),  # done
            "cumulative_return": stats_handler.get_cumulative_return(),  # done
            "annualized_return": stats_handler.get_annualized_return(),  # done
            "portfolio_volatility": stats_handler.get_portfolio_volatility(),  # done
            "annualized_portfolio_volatility": stats_handler.get_annualized_portfolio_volatility(),  # done
            "sharpe_ratio": stats_handler.get_sharpe_ratio(),  # done
            "max_annualized_drawdown": max_annualized_drawdown,
            "max_annualized_drawdown_month": max_annualized_drawdown_month,
            "betta": stats_handler.get_betta(),
            "alpha": stats_handler.get_alpha(),
            "correlation": stats_handler.get_correlation(),
        }

        widget_stats_instance = None

        try:
            widget_stats_instance = WidgetStats.objects.get(
                master_user=task.master_user,
                date=date,
                portfolio_id=task.options_object["portfolio_id"],
                benchmark=task.options_object["benchmark"],
            )
        except Exception as e:
            widget_stats_instance = WidgetStats.objects.create(
                master_user=task.master_user,
                date=date,
                portfolio_id=task.options_object["portfolio_id"],
                benchmark=task.options_object["benchmark"],
            )

        widget_stats_instance.nav = result["nav"]
        widget_stats_instance.total = result["total"]
        widget_stats_instance.cumulative_return = result["cumulative_return"]
        widget_stats_instance.annualized_return = result["annualized_return"]
        widget_stats_instance.portfolio_volatility = result["portfolio_volatility"]
        widget_stats_instance.annualized_portfolio_volatility = result[
            "annualized_portfolio_volatility"
        ]
        widget_stats_instance.sharpe_ratio = result["sharpe_ratio"]
        widget_stats_instance.max_annualized_drawdown = result[
            "max_annualized_drawdown"
        ]
        widget_stats_instance.betta = result["betta"]
        widget_stats_instance.alpha = result["alpha"]
        widget_stats_instance.correlation = result["correlation"]

        widget_stats_instance.save()

        task_options_object = task.options_object

        task_options_object["processed_dates"].append(date)

        task.options_object = task_options_object

        task_result_object = task.result_object

        if not task_result_object:
            task_result_object = {"results": []}

        task_result_object["results"].append(
            {"date": str(date), "status": "success", "id": widget_stats_instance.id}
        )

        task.result_object = task_result_object
        task.save()

        start_new_collect_stats(task)

    except Exception as e:
        _l.error("collect_stats.error %s" % e)
        _l.error("collect_stats.traceback %s" % traceback.format_exc())

        task_options_object = task.options_object

        task_options_object["error_dates"].append(date)

        task.options_object = task_options_object

        task.status = CeleryTask.STATUS_ERROR
        if not task.error_message:
            task.error_message = str(e)
        else:
            task.error_message = task.error_message + "\n" + str(e)

        task.save()

        start_new_collect_stats(task)


@finmars_task(name="widgets.calculate_historical", bind=True)
def calculate_historical(self, task_id, *args, **kwargs):
    task = CeleryTask.objects.get(id=task_id)

    date_from = None
    date_to = None
    portfolios = None

    if task.options_object:
        date_from = task.options_object.get("date_from", None)
        date_to = task.options_object.get("date_to", None)
        portfolios = task.options_object.get("portfolios", None)

    # member = Member.objects.get(is_owner=True)
    member = Member.objects.get(username="finmars_bot")
    master_user = member.master_user

    try:
        from poms.transactions.models import Transaction

        if portfolios:
            portfolios = Portfolio.objects.filter(id__in=portfolios)
        else:
            portfolios = Portfolio.objects.all()

        bday_yesterday = get_closest_bday_of_yesterday()

        _l.info(
            "widgets.calculate_historical for %s portfolios for %s"
            % (len(portfolios), bday_yesterday)
        )

        if not date_from:
            date_from = bday_yesterday

        if not date_to:
            date_to = bday_yesterday

        # dates = [bday_yesterday]
        dates = get_list_of_dates_between_two_dates(date_from, date_to)

        ecosystem_default = EcosystemDefault.cache.get_cache(
            master_user_pk=master_user.pk
        )

        report_currency_id = ecosystem_default.currency_id
        pricing_policy_id = ecosystem_default.pricing_policy_id
        cost_method_id = CostMethod.AVCO
        segmentation_type = "days"

        # Widget Stats settings
        benchmark = "sp_500"

        sync = True

        index = 0

        for portfolio in portfolios:
            # Run Collect History

            has_transaction = False

            if Transaction.objects.filter(portfolio=portfolio).count():
                has_transaction = True

            if has_transaction:
                try:
                    collect_balance_history(
                        master_user,
                        member,
                        date_from,
                        date_to,
                        dates,
                        segmentation_type,
                        portfolio.id,
                        report_currency_id,
                        cost_method_id,
                        pricing_policy_id,
                        sync,
                    )

                    collect_pl_history(
                        master_user,
                        member,
                        date_from,
                        date_to,
                        dates,
                        segmentation_type,
                        portfolio.id,
                        report_currency_id,
                        cost_method_id,
                        pricing_policy_id,
                        sync,
                    )

                    # Run Collect Widget Stats

                    collect_widget_stats(
                        master_user,
                        member,
                        date_from,
                        date_to,
                        dates,
                        segmentation_type,
                        portfolio.id,
                        benchmark,
                        sync,
                    )

                    index = index + 1
                except Exception as e:
                    send_system_message(
                        master_user=master_user,
                        action_status="required",
                        type="warning",
                        title="Calculate Historical Partial Failed.",
                        description=str(e),
                    )

                    _l.error(
                        "Portfolio %s index %s widget calculation error %s"
                        % (portfolio.name, index, e)
                    )
                    _l.error(traceback.format_exc())
                    pass

    except Exception as e:
        _l.error("widgets.calculate_historical %s" % e)
        _l.error("widgets.calculate_historical %s" % traceback.format_exc())

        send_system_message(
            master_user=master_user,
            action_status="required",
            type="error",
            title="Calculate Historical Failed.",
            description=str(e),
        )
