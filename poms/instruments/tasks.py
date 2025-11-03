import json
import logging
import traceback
from collections import defaultdict
from datetime import date, datetime, timedelta
from math import isclose
from typing import Any

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from poms import notifications
from poms.celery_tasks import finmars_task
from poms.common.utils import date_now
from poms.instruments.models import EventSchedule, GeneratedEvent, Instrument, PriceHistory
from poms.reports.common import Report, ReportItem
from poms.reports.sql_builders.balance import BalanceReportBuilderSql
from poms.system_messages.handlers import send_system_message
from poms.transactions.models import NotificationClass
from poms.users.models import MasterUser, Member

_l = logging.getLogger("poms.instruments")


@transaction.atomic()
def calculate_prices_accrued_price(master_user=None, begin_date=None, end_date=None, instruments=None):
    instruments_qs = Instrument.objects.all()
    if master_user:
        instruments_qs = instruments_qs.filter(master_user=master_user)
    if instruments:
        instruments_qs = instruments_qs.filter(pk__in=instruments)
    for instrument in instruments_qs:
        instrument.calculate_prices_accrued_price(begin_date, end_date)


@finmars_task(name="instruments.calculate_prices_accrued_price", ignore_result=False, bind=True)
@transaction.atomic()
def calculate_prices_accrued_price_async(
    self,
    master_user=None,
    begin_date=None,
    end_date=None,
    instruments=None,
    *args,
    **kwargs,
):
    if begin_date:
        begin_date = date.fromordinal(begin_date)
    if end_date:
        end_date = date.fromordinal(end_date)
    calculate_prices_accrued_price(
        master_user=master_user,
        begin_date=begin_date,
        end_date=end_date,
        instruments=instruments,
    )


def get_calculated_parameter_by_name_from_event(event_schedule, name, instrument):
    result = None

    for parameter in event_schedule.data["parameters"]:
        if parameter["name"] == name:
            if parameter["___switch_state"] == "attribute_key":
                if "attributes." in parameter["attribute_key"]:
                    attr_user_code = parameter["attribute_key"].split("attributes.")[1]

                    for attr in instrument.attributes.all():
                        if attr.attribute_type.user_code == attr_user_code:
                            if attr.attribute_type.value_type == 10:
                                result = attr.value_string

                            elif attr.attribute_type.value_type == 20:
                                result = attr.value_float

                            elif attr.attribute_type.value_type == 40:
                                result = attr.value_date

                else:
                    result = getattr(instrument, parameter["attribute_key"], None)

            else:
                result = parameter["default_value"]

    return result


def fill_parameters_from_instrument(event_schedule, instrument):
    result = {}

    for action in event_schedule.actions.all():
        result[action.button_position] = {}

        if action.data and action.data["parameters"]:
            for parameter in action.data["parameters"]:
                key = "parameter" + str(parameter["order"])

                result[action.button_position][key] = get_calculated_parameter_by_name_from_event(
                    event_schedule, parameter["event_parameter_name"], instrument
                )

    return result


@finmars_task(name="instruments.only_generate_events_at_date", bind=True)
def only_generate_events_at_date(self, master_user_id, date, *args, **kwargs):  # noqa: PLR0915
    try:
        master_user = MasterUser.objects.get(id=master_user_id)

        _l.info("generate_events0: master_user=%s", master_user.id)

        instance = Report(
            master_user=master_user,
            allocation_mode=Report.MODE_IGNORE,
            report_date=date,
        )

        builder = BalanceReportBuilderSql(instance=instance)
        instance = builder.build_balance()

        opened_instrument_items = [
            item
            for item in instance.items
            if item["item_type"] == ReportItem.TYPE_INSTRUMENT and not isclose(item["position_size"], 0.0)
        ]
        if not opened_instrument_items:
            return

        event_schedule_qs = (
            EventSchedule.objects.prefetch_related(
                "instrument",
                "event_class",
                "notification_class",
                "periodicity",
                "actions",
            )
            .filter(instrument__in={i["instrument_id"] for i in opened_instrument_items})
            .order_by("instrument__master_user__id", "instrument__id")
        )

        if not event_schedule_qs.exists():
            _l.info(f"event schedules not found. Date {date}")
            return

        result = []

        for event_schedule in event_schedule_qs:
            final_date = datetime.date(datetime.strptime(event_schedule.final_date, "%Y-%m-%d"))
            effective_date = datetime.date(datetime.strptime(event_schedule.effective_date, "%Y-%m-%d"))

            if final_date >= date and effective_date - timedelta(days=event_schedule.notify_in_n_days):
                result.append(event_schedule)

        event_schedules_cache = defaultdict(list)
        for event_schedule in result:
            event_schedules_cache[event_schedule.instrument_id].append(event_schedule)

        for item in opened_instrument_items:
            portfolio = item["portfolio_id"]
            account = item["account_position_id"]
            strategy1 = item["strategy1_position_id"]
            strategy2 = item["strategy2_position_id"]
            strategy3 = item["strategy3_position_id"]
            instrument = item["instrument_id"]
            position = item["position_size"]

            event_schedules = event_schedules_cache.get(instrument, None)
            _l.info(
                "opened instrument: portfolio=%s, account=%s, strategy1=%s, strategy2=%s, strategy3=%s, "
                "instrument=%s, position=%s, event_schedules=%s",
                portfolio,
                account,
                strategy1,
                strategy2,
                strategy3,
                instrument,
                position,
                [e.id for e in event_schedules] if event_schedules else [],
            )

            if not event_schedules:
                continue

            for event_schedule in event_schedules:
                _l.info(
                    "event_schedule=%s, event_class=%s, notification_class=%s, periodicity=%s, n=%s",
                    event_schedule.id,
                    event_schedule.event_class,
                    event_schedule.notification_class,
                    event_schedule.periodicity,
                    event_schedule.periodicity_n,
                )

                (
                    is_complies,
                    effective_date,
                    notification_date,
                ) = event_schedule.check_date(date)

                _l.info("is_complies=%s", is_complies)
                if is_complies:
                    ge_dup_qs = GeneratedEvent.objects.filter(
                        master_user=master_user,
                        event_schedule=event_schedule,
                        effective_date=effective_date,
                        # notification_date=notification_date,
                        instrument=instrument,
                        portfolio=portfolio,
                        account=account,
                        strategy1=strategy1,
                        strategy2=strategy2,
                        strategy3=strategy3,
                        position=position,
                    )
                    if ge_dup_qs.exists():
                        _l.info("generated event already exist")
                        continue

                    _l.info(f"event_schedule {event_schedule}")

                    parameters = fill_parameters_from_instrument(event_schedule, instrument)

                    generated_event = GeneratedEvent()
                    generated_event.master_user = master_user
                    generated_event.event_schedule = event_schedule
                    generated_event.status = GeneratedEvent.NEW
                    generated_event.status_modified = timezone.now()
                    generated_event.effective_date = effective_date
                    generated_event.notification_date = notification_date
                    generated_event.instrument_id = instrument
                    generated_event.portfolio_id = portfolio
                    generated_event.account_id = account
                    generated_event.strategy1_id = strategy1
                    generated_event.strategy2_id = strategy2
                    generated_event.strategy3_id = strategy3
                    generated_event.position_id = position
                    generated_event.data = {"actions_parameters": parameters}
                    generated_event.save()

    except Exception as e:
        _l.info(f"only_generate_events_at_date exception occurred {e}\n {traceback.format_exc()}")


@finmars_task(name="instruments.only_generate_events_at_date_for_single_instrument", bind=True)
def only_generate_events_at_date_for_single_instrument(self, master_user_id, date, instrument_id, *args, **kwargs):  # noqa: PLR0915
    try:
        date = datetime.date(datetime.strptime(date, "%Y-%m-%d"))
        master_user = MasterUser.objects.get(id=master_user_id)
        instrument = Instrument.objects.get(id=instrument_id)
        _l.debug(
            "only_generate_events_at_date_for_single_instrument: master_user=%s, instrument=%s",
            (master_user.id, instrument),
        )

        instance = Report(
            master_user=master_user,
            allocation_mode=Report.MODE_IGNORE,
            report_date=date,
        )

        builder = BalanceReportBuilderSql(instance=instance)
        instance = builder.build_balance()

        opened_instrument_items = [
            item
            for item in instance.items
            if (
                item["item_type"] == ReportItem.TYPE_INSTRUMENT
                and not isclose(item["position_size"], 0.0)
                and item["instrument_id"] == instrument.id
            )
        ]
        _l.info(f"opened_instrument_items len {len(opened_instrument_items)}")

        if not opened_instrument_items:
            return

        event_schedule_qs = (
            EventSchedule.objects.prefetch_related(
                "instrument",
                "event_class",
                "notification_class",
                "periodicity",
                "actions",
            )
            .filter(instrument_id__in={i["instrument_id"] for i in opened_instrument_items})
            .order_by("instrument__master_user__id", "instrument__id")
        )

        if not event_schedule_qs.exists():
            _l.debug(f"event schedules not found. Date {date}")
            return

        result = []

        for event_schedule in event_schedule_qs:
            final_date = datetime.date(datetime.strptime(event_schedule.final_date, "%Y-%m-%d"))
            effective_date = datetime.date(datetime.strptime(event_schedule.effective_date, "%Y-%m-%d"))

            if final_date >= date and effective_date - timedelta(days=event_schedule.notify_in_n_days):
                result.append(event_schedule)

        event_schedules_cache = defaultdict(list)
        for event_schedule in result:
            event_schedules_cache[event_schedule.instrument_id].append(event_schedule)

        _l.info(f"event_schedules_cache {event_schedules_cache}")

        for item in opened_instrument_items:
            portfolio = item["portfolio_id"]
            account = item["account_position_id"]
            strategy1 = item["strategy1_position_id"]
            strategy2 = item["strategy2_position_id"]
            strategy3 = item["strategy3_position_id"]
            instrument = item["instrument_id"]
            position = item["position_size"]

            event_schedules = event_schedules_cache.get(instrument, None)
            _l.info(
                "opened instrument: portfolio=%s, account=%s, strategy1=%s, strategy2=%s, strategy3=%s, "
                "instrument=%s, position=%s, event_schedules=%s",
                portfolio,
                account,
                strategy1,
                strategy2,
                strategy3,
                instrument,
                position,
                [e.id for e in event_schedules] if event_schedules else [],
            )

            if not event_schedules:
                continue

            for event_schedule in event_schedules:
                _l.debug(
                    "event_schedule=%s, event_class=%s, notification_class=%s, periodicity=%s, n=%s",
                    event_schedule.id,
                    event_schedule.event_class,
                    event_schedule.notification_class,
                    event_schedule.periodicity,
                    event_schedule.periodicity_n,
                )

                (
                    is_complies,
                    effective_date,
                    notification_date,
                ) = event_schedule.check_date(date)

                _l.debug("is_complies=%s", is_complies)
                if is_complies:
                    ge_dup_qs = GeneratedEvent.objects.filter(
                        master_user=master_user,
                        event_schedule=event_schedule,
                        effective_date=effective_date,
                        # notification_date=notification_date,
                        instrument=instrument,
                        portfolio=portfolio,
                        account=account,
                        strategy1=strategy1,
                        strategy2=strategy2,
                        strategy3=strategy3,
                        position=position,
                    )
                    if ge_dup_qs.exists():
                        _l.debug("generated event already exist")
                        continue

                    print(f"event_schedule {event_schedule}")

                    parameters = fill_parameters_from_instrument(event_schedule, instrument)

                    generated_event = GeneratedEvent()
                    generated_event.master_user = master_user
                    generated_event.event_schedule = event_schedule
                    generated_event.status = GeneratedEvent.NEW
                    generated_event.status_modified = timezone.now()
                    generated_event.effective_date = effective_date
                    generated_event.notification_date = notification_date
                    generated_event.instrument_id = instrument
                    generated_event.portfolio_id = portfolio
                    generated_event.account_id = account
                    generated_event.strategy1_id = strategy1
                    generated_event.strategy2_id = strategy2
                    generated_event.strategy3_id = strategy3
                    generated_event.position = position
                    generated_event.data = {"actions_parameters": parameters}
                    generated_event.save()

    except Exception as e:
        _l.info(f"only_generate_events_at_date_for_single_instrument exception occurred {e}")
        _l.info(traceback.format_exc())


@finmars_task(name="instruments.generate_events", bind=True)
def generate_events(self, task_id, *args, **kwargs):  # noqa: PLR0915
    from poms.celery_tasks.models import CeleryTask

    # member = Member.objects.get(master_user=master_user, is_owner=True)
    # finmars_bot = Member.objects.get(username="finmars_bot")

    celery_task = CeleryTask.objects.get(id=task_id)
    celery_task.celery_task_id = self.request.id
    celery_task.save()

    master_user = celery_task.master_user

    # celery_task = CeleryTask.objects.create(
    #     master_user=master_user,
    #     member=finmars_bot,
    #     verbose_name="Generate Events",
    #     type="generate_events",
    # )

    try:
        _l.debug(f"generate_events0: master_user={master_user.id}")

        now = date_now()

        instance = Report(master_user=master_user, allocation_mode=Report.MODE_IGNORE, report_date=now)

        builder = BalanceReportBuilderSql(instance=instance)
        instance = builder.build_balance()

        opened_instrument_items = [
            item
            for item in instance.items
            if item["item_type"] == ReportItem.TYPE_INSTRUMENT and not isclose(item["position_size"], 0.0)
        ]
        if not opened_instrument_items:
            return

        event_schedule_qs = (
            EventSchedule.objects.prefetch_related(
                "instrument",
                "event_class",
                "notification_class",
                "periodicity",
                "actions",
            )
            .filter(instrument__in={i["instrument_id"] for i in opened_instrument_items})
            .order_by("instrument__master_user__id", "instrument__id")
        )

        result = []
        result_object = {"events": []}

        generated_events_count = 0

        for event_schedule in event_schedule_qs:
            final_date = datetime.date(datetime.strptime(event_schedule.final_date, "%Y-%m-%d"))
            effective_date = datetime.date(datetime.strptime(event_schedule.effective_date, "%Y-%m-%d"))

            if final_date >= now and effective_date - timedelta(days=event_schedule.notify_in_n_days):
                result.append(event_schedule)

        if not result:
            celery_task.status = CeleryTask.STATUS_DONE
            celery_task.verbose_result = "event schedules not found"
            celery_task.save()

            _l.debug("event schedules not found")
            return

        event_schedules_cache = defaultdict(list)
        for event_schedule in result:
            event_schedules_cache[event_schedule.instrument_id].append(event_schedule)

        for item in opened_instrument_items:
            portfolio = item["portfolio_id"]
            account = item["account_position_id"]
            strategy1 = item["strategy1_position_id"]
            strategy2 = item["strategy2_position_id"]
            strategy3 = item["strategy3_position_id"]
            instrument = item["instrument_id"]
            position = item["position_size"]

            event_schedules = event_schedules_cache.get(instrument, None)
            _l.info(
                "opened instrument: portfolio=%s, account=%s, strategy1=%s, strategy2=%s, strategy3=%s, "
                "instrument=%s, position=%s, event_schedules=%s",
                portfolio,
                account,
                strategy1,
                strategy2,
                strategy3,
                instrument,
                position,
                [e.id for e in event_schedules] if event_schedules else [],
            )

            if not event_schedules:
                continue

            for event_schedule in event_schedules:
                _l.debug(
                    "event_schedule=%s, event_class=%s, notification_class=%s, periodicity=%s, n=%s",
                    event_schedule.id,
                    event_schedule.event_class,
                    event_schedule.notification_class,
                    event_schedule.periodicity,
                    event_schedule.periodicity_n,
                )

                (
                    is_complies,
                    effective_date,
                    notification_date,
                ) = event_schedule.check_date(now)

                _l.debug("is_complies=%s", is_complies)
                if is_complies:
                    ge_dup_qs = GeneratedEvent.objects.filter(
                        master_user=master_user,
                        event_schedule=event_schedule,
                        effective_date=effective_date,
                        instrument=instrument,
                        portfolio=portfolio,
                        account=account,
                        strategy1=strategy1,
                        strategy2=strategy2,
                        strategy3=strategy3,
                        position=position,
                    )
                    if ge_dup_qs.exists():
                        _l.debug("generated event already exist")
                        continue

                    print(f"event_schedule {event_schedule}")

                    parameters = fill_parameters_from_instrument(event_schedule, instrument)

                    generated_event = GeneratedEvent()
                    generated_event.master_user = master_user
                    generated_event.event_schedule = event_schedule
                    generated_event.status = GeneratedEvent.NEW
                    generated_event.status_modified = timezone.now()
                    generated_event.effective_date = effective_date
                    generated_event.notification_date = notification_date
                    generated_event.instrument_id = instrument
                    generated_event.portfolio_id = portfolio
                    generated_event.account_id = account
                    generated_event.strategy1_id = strategy1
                    generated_event.strategy2_id = strategy2
                    generated_event.strategy3_id = strategy3
                    generated_event.position = position
                    generated_event.data = {"parameters": parameters}
                    generated_event = generated_event.save()

                    result_object["events"].append(
                        {
                            "id": generated_event.id,
                            "effective_date": str(generated_event.effective_date),
                            "notification_date": str(generated_event.notification_date),
                            "instrument": {
                                "id": generated_event.instrument.id,
                                "user_code": generated_event.instrument.user_code,
                                "name": generated_event.instrument.name,
                            },
                            "status": generated_event.status,
                            "position": generated_event.position,
                        }
                    )

                    generated_events_count = generated_events_count + 1

        celery_task.result_object = result_object
        celery_task.verbose_result = f"Events generated: {generated_events_count}"
        celery_task.status = CeleryTask.STATUS_DONE
        celery_task.save()

        process_events.apply_async()

    except Exception as e:
        send_system_message(
            master_user=master_user,
            action_status="required",
            type="warning",
            title="Generate Events Failed.",
            description=str(e),
        )

        celery_task.error_message = f"Error {e}. Traceback {traceback.format_exc()}"
        celery_task.status = CeleryTask.STATUS_ERROR
        celery_task.save()

        _l.info(f"generate_events0 exception occurred {e}")
        _l.info(traceback.format_exc())
        raise RuntimeError(celery_task.error_message) from e


@finmars_task(name="instruments.generate_events_do_not_inform_apply_default", bind=True)
def generate_events_do_not_inform_apply_default(self, *args, **kwargs):  # noqa: PLR0915
    try:
        master_user = MasterUser.objects.all()[0]

        _l.debug(f"generate_events0: master_user={master_user.id}")

        now = date_now()

        instance = Report(master_user=master_user, allocation_mode=Report.MODE_IGNORE, report_date=now)

        builder = BalanceReportBuilderSql(instance=instance)
        instance = builder.build_balance()

        opened_instrument_items = [
            item
            for item in instance.items
            if item["item_type"] == ReportItem.TYPE_INSTRUMENT and not isclose(item["position_size"], 0.0)
        ]
        _l.info(f"opened_instrument_items len {len(opened_instrument_items)}")

        if not opened_instrument_items:
            return

        event_schedule_qs = (
            EventSchedule.objects.prefetch_related(
                "instrument",
                "event_class",
                "notification_class",
                "periodicity",
                "actions",
            )
            .filter(instrument__in={i["instrument_id"] for i in opened_instrument_items})
            .order_by("instrument__master_user__id", "instrument__id")
        )

        result = []

        for event_schedule in event_schedule_qs:
            final_date = datetime.date(datetime.strptime(event_schedule.final_date, "%Y-%m-%d"))
            effective_date = datetime.date(datetime.strptime(event_schedule.effective_date, "%Y-%m-%d"))

            if final_date >= now and effective_date - timedelta(days=event_schedule.notify_in_n_days):
                result.append(event_schedule)

        if not result:
            _l.debug("event schedules not found")
            return

        event_schedules_cache = defaultdict(list)
        for event_schedule in result:
            event_schedules_cache[event_schedule.instrument_id].append(event_schedule)

        for item in opened_instrument_items:
            portfolio = item["portfolio_id"]
            account = item["account_position_id"]
            strategy1 = item["strategy1_position_id"]
            strategy2 = item["strategy2_position_id"]
            strategy3 = item["strategy3_position_id"]
            instrument = item["instrument_id"]
            position = item["position_size"]

            event_schedules = event_schedules_cache.get(instrument, None)
            _l.info(
                "opened instrument: portfolio=%s, account=%s, strategy1=%s, strategy2=%s, strategy3=%s, "
                "instrument=%s, position=%s, event_schedules=%s",
                portfolio,
                account,
                strategy1,
                strategy2,
                strategy3,
                instrument,
                position,
                [e.id for e in event_schedules] if event_schedules else [],
            )

            if not event_schedules:
                continue

            for event_schedule in event_schedules:
                _l.debug(
                    "event_schedule=%s, event_class=%s, notification_class=%s, periodicity=%s, n=%s",
                    event_schedule.id,
                    event_schedule.event_class,
                    event_schedule.notification_class,
                    event_schedule.periodicity,
                    event_schedule.periodicity_n,
                )

                (
                    is_complies,
                    effective_date,
                    notification_date,
                ) = event_schedule.check_date(now)

                is_apply_default = event_schedule.notification_class in (
                    NotificationClass.APPLY_DEF_ON_EDATE,
                    NotificationClass.APPLY_DEF_ON_NDATE,
                )

                _l.debug(f"is_complies={is_complies}")

                if is_complies and is_apply_default:
                    ge_dup_qs = GeneratedEvent.objects.filter(
                        master_user=master_user,
                        event_schedule=event_schedule,
                        effective_date=effective_date,
                        instrument=instrument,
                        portfolio=portfolio,
                        account=account,
                        strategy1=strategy1,
                        strategy2=strategy2,
                        strategy3=strategy3,
                        position=position,
                    )
                    if ge_dup_qs.exists():
                        _l.debug("generated event already exist")
                        continue

                    print(f"event_schedule {event_schedule}")

                    parameters = fill_parameters_from_instrument(event_schedule, instrument)

                    generated_event = GeneratedEvent()
                    generated_event.master_user = master_user
                    generated_event.event_schedule = event_schedule
                    generated_event.status = GeneratedEvent.NEW
                    generated_event.status_modified = timezone.now()
                    generated_event.effective_date = effective_date
                    generated_event.notification_date = notification_date
                    generated_event.instrument_id = instrument
                    generated_event.portfolio_id = portfolio
                    generated_event.account_id = account
                    generated_event.strategy1_id = strategy1
                    generated_event.strategy2_id = strategy2
                    generated_event.strategy3_id = strategy3
                    generated_event.position = position
                    generated_event.data = {"actions_parameters": parameters}
                    generated_event.save()

        process_events.apply_async()

    except Exception as e:
        _l.info(f"generate_events exception occurred {repr(e)}\n {traceback.format_exc()}")


@finmars_task(name="instruments.process_events", bind=True)
@transaction.atomic()
def process_events(self, *args, **kwargs):  # noqa: PLR0915
    from poms.celery_tasks.models import CeleryTask
    from poms.instruments.handlers import GeneratedEventProcess

    master_user = MasterUser.objects.all().first()  # TODO refactor to get by space_code
    # member = Member.objects.get(master_user=master_user, is_owner=True)
    finmars_bot = Member.objects.get(username="finmars_bot")

    celery_task = CeleryTask.objects.create(
        master_user=master_user,
        member=finmars_bot,
        verbose_name="Process Events",
        type="process_events",
    )

    try:
        _l.debug("process_events0: master_user=%s", master_user.id)

        now = date_now()

        generated_event_qs = (
            GeneratedEvent.objects.prefetch_related(
                "event_schedule",
                "event_schedule__notification_class",
                "instrument",
                "instrument__pricing_currency",
                "instrument__accrued_currency",
                "portfolio",
                "account",
                "strategy1",
                "strategy2",
                "strategy3",
            )
            .filter(
                master_user=master_user,
                status=GeneratedEvent.NEW,
            )
            .filter(
                Q(effective_date=now) | Q(notification_date=now),
            )
        )

        processed_count = 0

        for gevent in generated_event_qs:
            is_notify_on_notification_date = gevent.is_notify_on_notification_date(now)
            is_notify_on_effective_date = gevent.is_notify_on_effective_date(now)
            is_apply_default_on_notification_date = gevent.is_apply_default_on_notification_date(now)
            is_apply_default_on_effective_date = gevent.is_apply_default_on_effective_date(now)
            is_need_reaction_on_notification_date = gevent.is_need_reaction_on_notification_date(now)
            is_need_reaction_on_effective_date = gevent.is_need_reaction_on_effective_date(now)

            _l.debug(
                "process:"
                " notification_class=%s,"
                " notification_date=%s,"
                " notification_date_notified=%s"
                " effective_date=%s,"
                " effective_date_notified=%s,"
                " is_notify_on_notification_date=%s,"
                " is_notify_on_effective_date=%s,"
                " is_apply_default_on_notification_date=%s,"
                " is_apply_default_on_effective_date=%s,"
                " is_need_reaction_on_notification_date=%s,"
                " is_need_reaction_on_effective_date=%s",
                gevent.event_schedule.notification_class.user_code,
                gevent.notification_date,
                gevent.notification_date_notified,
                gevent.effective_date,
                gevent.effective_date_notified,
                is_notify_on_notification_date,
                is_notify_on_effective_date,
                is_apply_default_on_notification_date,
                is_apply_default_on_effective_date,
                is_need_reaction_on_notification_date,
                is_need_reaction_on_effective_date,
            )

            owner = next(iter([m for m in gevent.master_user.members.all() if m.is_owner]))

            if is_notify_on_notification_date or is_notify_on_effective_date:
                if is_notify_on_notification_date:
                    gevent.notification_date_notified = True
                if is_notify_on_effective_date:
                    gevent.effective_date_notified = True

                recipients = [m for m in gevent.master_user.members.all() if not m.is_deleted]

                expr = gevent.event_schedule.description or gevent.event_schedule.name
                if expr:
                    for member in recipients:
                        message = gevent.generate_text(
                            exr=expr,
                            context={"master_user": master_user, "member": member},
                        )
                        notifications.send(
                            recipients=[member],
                            message=message,
                            actor=gevent.event_schedule,
                            verb="event occurred",
                            action_object=gevent.instrument,
                        )
                else:
                    notifications.send(
                        recipients=recipients,
                        actor=gevent.event_schedule,
                        verb="event occurred",
                        action_object=gevent.instrument,
                    )

            if is_apply_default_on_notification_date or is_apply_default_on_effective_date:
                action = next(
                    (a for a in gevent.event_schedule.actions.all() if a.is_book_automatic),
                    None,
                )
                if action:
                    ttp = GeneratedEventProcess(
                        generated_event=gevent,
                        action=action,
                        context={
                            "master_user": master_user,
                            "member": owner,
                        },
                    )
                    ttp.process()
                    gevent.processed(None, action, ttp.complex_transaction)
                else:
                    gevent.status = GeneratedEvent.BOOKED_SYSTEM_DEFAULT
                    gevent.status_date = timezone.now()

                processed_count = processed_count + 1

            if (
                is_notify_on_notification_date
                or is_notify_on_effective_date
                or is_apply_default_on_notification_date
                or is_apply_default_on_effective_date
            ):
                gevent.save()

        celery_task.verbose_result = f"Events Processed: {processed_count}"
        celery_task.status = CeleryTask.STATUS_DONE
        celery_task.save()

    except Exception as e:
        send_system_message(
            master_user=master_user,
            action_status="required",
            type="warning",
            title="Process Events Failed.",
            description=repr(e),
        )

        err_msg = f"process_events0 exception {repr(e)}\n {traceback.format_exc()}"
        _l.error(err_msg)

        celery_task.error_message = err_msg
        celery_task.status = CeleryTask.STATUS_ERROR
        celery_task.save()
        raise RuntimeError(err_msg) from e


@finmars_task(name="instruments.calculate_pricehistory", bind=True)
def calculate_pricehistory(self, task_id: int, *args, **kwargs) -> str:
    from poms.celery_tasks.models import CeleryTask

    celery_task = CeleryTask.objects.get(id=task_id)
    celery_task.celery_task_id = self.request.id
    celery_task.status = CeleryTask.STATUS_PENDING
    celery_task.save()

    data = celery_task.options_object
    date_from = data["date_from"]
    date_to = data["date_to"]
    instruments = data.get("instruments", [])
    pricing_policies = data.get("pricing_policies", [])

    queryset = PriceHistory.objects.select_related(
        "instrument",
        "instrument__instrument_type",
        "instrument__instrument_type__instrument_class",
        "pricing_policy",
    )

    queryset = queryset.filter(
        date__gte=date_from,
        date__lte=date_to,
    )

    if instruments:
        queryset = queryset.filter(instrument__user_code__in=instruments)

    if pricing_policies:
        queryset = queryset.filter(pricing_policy__user_code__in=pricing_policies)

    total = queryset.count()

    _l.info("Start calculate price_history for %s pieces", total)

    result: dict[str, Any] = {"items": []}
    has_error = False

    for count, price_history in enumerate(queryset):
        try:
            price_history.run_auto_calculation()

            err_msg = None
            status = "success"
        except Exception as e:
            status = "error"
            err_msg = repr(e)
            _l.warning(f"calculate_pricehistory exception {repr(e)} {traceback.format_exc()}")
            has_error = True
        finally:
            celery_task.update_progress(
                {
                    "current": count,
                    "total": total,
                    "percent": round((count / total) * 100),
                    "description": f"price_history {price_history.id} was calculated",
                }
            )
            result["items"].append({"status": status, "id": price_history.id, "error_message": err_msg})

    result["error_message"] = "calculate_pricehistory error" if has_error else None
    celery_task.status = CeleryTask.STATUS_ERROR if has_error else CeleryTask.STATUS_DONE

    _l.info("Calculation for price_history was compleated")
    celery_task.save()
    return json.dumps(result)
