import logging
import traceback
from collections import defaultdict
from datetime import date, datetime, timedelta

from celery import shared_task
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from poms import notifications
from poms.common.utils import date_now, isclose
from poms.instruments.models import EventSchedule, Instrument, GeneratedEvent
from poms.reports.common import Report, ReportItem
from poms.reports.sql_builders.balance import BalanceReportBuilderSql
from poms.transactions.models import NotificationClass
from poms.users.models import MasterUser, Member

_l = logging.getLogger('poms.instruments')


@transaction.atomic()
def calculate_prices_accrued_price(master_user=None, begin_date=None, end_date=None, instruments=None):
    # _l.debug('process_events: master_user=%s, begin_date=%s, end_date=%s, instruments=%s',
    #          master_user, begin_date, end_date, instruments)
    instruments_qs = Instrument.objects.all()
    if master_user:
        instruments_qs = instruments_qs.filter(master_user=master_user)
    if instruments:
        instruments_qs = instruments_qs.filter(pk__in=instruments)
    # _l.debug('instruments: count=%s', instruments_qs.count())
    for instrument in instruments_qs:
        # _l.debug('calculate_prices_accrued_price: instrument=%s', instrument.id)
        instrument.calculate_prices_accrued_price(begin_date, end_date)


@shared_task(name='instruments.calculate_prices_accrued_price', ignore_result=False)
@transaction.atomic()
def calculate_prices_accrued_price_async(master_user=None, begin_date=None, end_date=None, instruments=None):
    if begin_date:
        begin_date = date.fromordinal(begin_date)
    if end_date:
        end_date = date.fromordinal(end_date)
    calculate_prices_accrued_price(master_user=master_user, begin_date=begin_date, end_date=end_date,
                                   instruments=instruments)


def get_calculated_parameter_by_name_from_event(event_schedule, name, instrument):
    result = None

    for parameter in event_schedule.data['parameters']:

        if parameter['name'] == name:

            if parameter['___switch_state'] == 'attribute_key':

                if 'attributes.' in parameter['attribute_key']:

                    attr_user_code = parameter['attribute_key'].split('attributes.')[1]

                    for attr in instrument.attributes.all():
                        if attr.attribute_type.user_code == attr_user_code:

                            if attr.attribute_type.value_type == 10:
                                result = attr.value_string

                            if attr.attribute_type.value_type == 20:
                                result = attr.value_float

                            if attr.attribute_type.value_type == 40:
                                result = attr.value_date


                else:
                    result = getattr(instrument, parameter['attribute_key'], None)

            else:
                result = parameter['default_value']

    return result


def fill_parameters_from_instrument(event_schedule, instrument):
    result = {}

    for action in event_schedule.actions.all():

        result[action.button_position] = {}

        if action.data and action.data['parameters']:

            for parameter in action.data['parameters']:
                key = 'parameter' + str(parameter['order'])

                result[action.button_position][key] = get_calculated_parameter_by_name_from_event(event_schedule,
                                                                                                  parameter[
                                                                                                      'event_parameter_name'],
                                                                                                  instrument)

    return result


@shared_task(name='instruments.only_generate_events_at_date', bind=True)
def only_generate_events_at_date(self, master_user_id, date):
    try:

        master_user = MasterUser.objects.get(id=master_user_id)

        _l.info('generate_events0: master_user=%s', master_user.id)

        opened_instrument_items = []

        instance = Report(master_user=master_user, allocation_mode=Report.MODE_IGNORE, report_date=date)

        builder = BalanceReportBuilderSql(instance=instance)
        instance = builder.build_balance()

        for i in instance.items:
            if i['item_type'] == ReportItem.TYPE_INSTRUMENT and not isclose(i['position_size'], 0.0):
                opened_instrument_items.append(i)

        if not opened_instrument_items:
            return

        event_schedule_qs = EventSchedule.objects.prefetch_related(
            'instrument',
            'event_class',
            'notification_class',
            'periodicity',
            'actions'
        ).filter(
            # effective_date__lte=(date - F("notify_in_n_days")),
            # final_date__gte=date,
            instrument__in={i['instrument_id'] for i in opened_instrument_items}
        ).order_by(
            'instrument__master_user__id',
            'instrument__id'
        )

        if not event_schedule_qs.exists():
            _l.info('event schedules not found. Date %s' % date)
            return

        result = []

        for event_schedule in event_schedule_qs:

            final_date = datetime.date(datetime.strptime(event_schedule.final_date, '%Y-%m-%d'))
            effective_date = datetime.date(datetime.strptime(event_schedule.effective_date, '%Y-%m-%d'))

            if final_date >= date and effective_date - timedelta(days=event_schedule.notify_in_n_days):
                result.append(event_schedule)

        event_schedules_cache = defaultdict(list)
        # for event_schedule in event_schedule_qs:
        for event_schedule in result:
            event_schedules_cache[event_schedule.instrument_id].append(event_schedule)

        for item in opened_instrument_items:
            portfolio = item['portfolio_id']
            account = item['account_position_id']
            strategy1 = item['strategy1_position_id']
            strategy2 = item['strategy2_position_id']
            strategy3 = item['strategy3_position_id']
            instrument = item['instrument_id']
            position = item['position_size']

            event_schedules = event_schedules_cache.get(instrument, None)
            _l.info('opened instrument: portfolio=%s, account=%s, strategy1=%s, strategy2=%s, strategy3=%s, '
                    'instrument=%s, position=%s, event_schedules=%s',
                    portfolio, account, strategy1, strategy2, strategy3,
                    instrument, position, [e.id for e in event_schedules] if event_schedules else [])

            if not event_schedules:
                continue

            for event_schedule in event_schedules:
                _l.info('event_schedule=%s, event_class=%s, notification_class=%s, periodicity=%s, n=%s',
                        event_schedule.id, event_schedule.event_class, event_schedule.notification_class,
                        event_schedule.periodicity, event_schedule.periodicity_n)

                is_complies, effective_date, notification_date = event_schedule.check_date(date)

                _l.info('is_complies=%s', is_complies)
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
                        position=position
                    )
                    if ge_dup_qs.exists():
                        _l.info('generated event already exist')
                        continue

                    _l.info('event_schedule %s' % event_schedule)

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
                    generated_event.data = {
                        'actions_parameters': parameters
                    }
                    generated_event.save()

    except Exception as e:

        _l.info('only_generate_events_at_date exception occurred %s' % e)
        _l.info(traceback.format_exc())


@shared_task(name='instruments.only_generate_events_at_date_for_single_instrument', bind=True)
def only_generate_events_at_date_for_single_instrument(self, master_user_id, date, instrument_id):
    try:

        date = datetime.date(datetime.strptime(date, '%Y-%m-%d'))
        master_user = MasterUser.objects.get(id=master_user_id)
        instrument = Instrument.objects.get(id=instrument_id)
        _l.debug('only_generate_events_at_date_for_single_instrument: master_user=%s, instrument=%s',
                 (master_user.id, instrument))

        opened_instrument_items = []

        instance = Report(master_user=master_user, allocation_mode=Report.MODE_IGNORE, report_date=date)

        builder = BalanceReportBuilderSql(instance=instance)
        instance = builder.build_balance()

        for i in instance.items:
            if i['item_type'] == ReportItem.TYPE_INSTRUMENT and not isclose(i['position_size'], 0.0):

                if i['instrument_id'] == instrument.id:
                    opened_instrument_items.append(i)

        _l.info('opened_instrument_items len %s' % len(opened_instrument_items))

        if not opened_instrument_items:
            return

        event_schedule_qs = EventSchedule.objects.prefetch_related(
            'instrument',
            'event_class',
            'notification_class',
            'periodicity',
            'actions'
        ).filter(
            # effective_date__lte=(date - F("notify_in_n_days")),
            # final_date__gte=date,
            instrument_id__in={i['instrument_id'] for i in opened_instrument_items}
        ).order_by(
            'instrument__master_user__id',
            'instrument__id'
        )

        if not event_schedule_qs.exists():
            _l.debug('event schedules not found. Date %s' % date)
            return

        result = []

        for event_schedule in event_schedule_qs:

            final_date = datetime.date(datetime.strptime(event_schedule.final_date, '%Y-%m-%d'))
            effective_date = datetime.date(datetime.strptime(event_schedule.effective_date, '%Y-%m-%d'))

            if final_date >= date and effective_date - timedelta(days=event_schedule.notify_in_n_days):
                result.append(event_schedule)

        event_schedules_cache = defaultdict(list)
        # for event_schedule in event_schedule_qs:
        for event_schedule in result:
            event_schedules_cache[event_schedule.instrument_id].append(event_schedule)

        _l.info('event_schedules_cache %s' % event_schedules_cache)

        for item in opened_instrument_items:
            portfolio = item['portfolio_id']
            account = item['account_position_id']
            strategy1 = item['strategy1_position_id']
            strategy2 = item['strategy2_position_id']
            strategy3 = item['strategy3_position_id']
            instrument = item['instrument_id']
            position = item['position_size']

            event_schedules = event_schedules_cache.get(instrument, None)
            _l.info('opened instrument: portfolio=%s, account=%s, strategy1=%s, strategy2=%s, strategy3=%s, '
                    'instrument=%s, position=%s, event_schedules=%s',
                    portfolio, account, strategy1, strategy2, strategy3,
                    instrument, position, [e.id for e in event_schedules] if event_schedules else [])

            if not event_schedules:
                continue

            for event_schedule in event_schedules:
                _l.debug('event_schedule=%s, event_class=%s, notification_class=%s, periodicity=%s, n=%s',
                         event_schedule.id, event_schedule.event_class, event_schedule.notification_class,
                         event_schedule.periodicity, event_schedule.periodicity_n)

                is_complies, effective_date, notification_date = event_schedule.check_date(date)

                _l.debug('is_complies=%s', is_complies)
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
                        position=position
                    )
                    if ge_dup_qs.exists():
                        _l.debug('generated event already exist')
                        continue

                    print('event_schedule %s' % event_schedule)

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
                    generated_event.data = {
                        'actions_parameters': parameters
                    }
                    generated_event.save()

    except Exception as e:

        _l.info('only_generate_events_at_date_for_single_instrument exception occurred %s' % e)
        _l.info(traceback.format_exc())


@shared_task(name='instruments.generate_events', bind=True)
def generate_events(self):
    from poms.celery_tasks.models import CeleryTask

    master_user = MasterUser.objects.all()[0]  # TODO get by base_api_url

    member = Member.objects.get(master_user=master_user, is_owner=True)

    celery_task = CeleryTask.objects.create(
        master_user=master_user,
        member=member,
        verbose_name="Generate Events",
        type="generate_events"
    )

    try:
        _l.debug('generate_events0: master_user=%s', master_user.id)

        opened_instrument_items = []

        now = date_now()

        instance = Report(master_user=master_user, allocation_mode=Report.MODE_IGNORE, report_date=now)

        builder = BalanceReportBuilderSql(instance=instance)
        instance = builder.build_balance()

        for i in instance.items:
            if i['item_type'] == ReportItem.TYPE_INSTRUMENT and not isclose(i['position_size'], 0.0):
                opened_instrument_items.append(i)

        if not opened_instrument_items:
            return

        event_schedule_qs = EventSchedule.objects.prefetch_related(
            'instrument',
            'event_class',
            'notification_class',
            'periodicity',
            'actions'
        ).filter(
            # effective_date__lte=(now - F("notify_in_n_days")),
            # final_date__gte=now,
            instrument__in={i['instrument_id'] for i in opened_instrument_items}
        ).order_by(
            'instrument__master_user__id',
            'instrument__id'
        )

        result = []
        result_object = {
            "events": []
        }

        generated_events_count = 0

        for event_schedule in event_schedule_qs:

            final_date = datetime.date(datetime.strptime(event_schedule.final_date, '%Y-%m-%d'))
            effective_date = datetime.date(datetime.strptime(event_schedule.effective_date, '%Y-%m-%d'))

            if final_date >= now and effective_date - timedelta(days=event_schedule.notify_in_n_days):
                result.append(event_schedule)

        if not len(result):
            celery_task.status = CeleryTask.STATUS_DONE
            celery_task.verbose_result = 'event schedules not found'
            celery_task.save()

            _l.debug('event schedules not found')
            return

        event_schedules_cache = defaultdict(list)
        for event_schedule in result:
            event_schedules_cache[event_schedule.instrument_id].append(event_schedule)

        for item in opened_instrument_items:
            portfolio = item['portfolio_id']
            account = item['account_position_id']
            strategy1 = item['strategy1_position_id']
            strategy2 = item['strategy2_position_id']
            strategy3 = item['strategy3_position_id']
            instrument = item['instrument_id']
            position = item['position_size']

            event_schedules = event_schedules_cache.get(instrument, None)
            _l.info('opened instrument: portfolio=%s, account=%s, strategy1=%s, strategy2=%s, strategy3=%s, '
                    'instrument=%s, position=%s, event_schedules=%s',
                    portfolio, account, strategy1, strategy2, strategy3,
                    instrument, position, [e.id for e in event_schedules] if event_schedules else [])

            if not event_schedules:
                continue

            for event_schedule in event_schedules:
                _l.debug('event_schedule=%s, event_class=%s, notification_class=%s, periodicity=%s, n=%s',
                         event_schedule.id, event_schedule.event_class, event_schedule.notification_class,
                         event_schedule.periodicity, event_schedule.periodicity_n)

                is_complies, effective_date, notification_date = event_schedule.check_date(now)

                _l.debug('is_complies=%s', is_complies)
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
                        position=position
                    )
                    if ge_dup_qs.exists():
                        _l.debug('generated event already exist')
                        continue

                    print('event_schedule %s' % event_schedule)

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
                    generated_event.data = {
                        'parameters': parameters
                    }
                    generated_event = generated_event.save()

                    result_object['events'].append({
                        "id": generated_event.id,
                        "effective_date": str(generated_event.effective_date),
                        "notification_date": str(generated_event.notification_date),
                        "instrument": {
                            "id": generated_event.instrument.id,
                            "user_code": generated_event.instrument.user_code,
                            "name": generated_event.instrument.name
                        },
                        "status": generated_event.status,
                        "position": generated_event.position

                    })

                    generated_events_count = generated_events_count + 1

        celery_task.result_object = result_object
        celery_task.verbose_result = 'Events generated: %s' % generated_events_count
        celery_task.status = CeleryTask.STATUS_DONE
        celery_task.save()

        process_events.apply_async()

    except Exception as e:

        celery_task.error_message = 'Error %s. Traceback %s' % (e, traceback.format_exc())
        celery_task.status = CeleryTask.STATUS_ERROR
        celery_task.save()

        _l.info('generate_events0 exception occurred %s' % e)
        _l.info(traceback.format_exc())


@shared_task(name='instruments.generate_events_do_not_inform_apply_default', bind=True)
def generate_events_do_not_inform_apply_default(self):
    try:

        master_user = MasterUser.objects.all()[0]

        _l.debug('generate_events0: master_user=%s', master_user.id)

        opened_instrument_items = []

        now = date_now()

        instance = Report(master_user=master_user, allocation_mode=Report.MODE_IGNORE, report_date=now)

        builder = BalanceReportBuilderSql(instance=instance)
        instance = builder.build_balance()

        for i in instance.items:
            if i['item_type'] == ReportItem.TYPE_INSTRUMENT and not isclose(i['position_size'], 0.0):
                opened_instrument_items.append(i)

        _l.info('opened_instrument_items len %s' % len(opened_instrument_items))

        if not opened_instrument_items:
            return

        event_schedule_qs = EventSchedule.objects.prefetch_related(
            'instrument',
            'event_class',
            'notification_class',
            'periodicity',
            'actions'
        ).filter(
            # effective_date__lte=(now - F("notify_in_n_days")),
            # final_date__gte=now,
            instrument__in={i['instrument_id'] for i in opened_instrument_items}
        ).order_by(
            'instrument__master_user__id',
            'instrument__id'
        )

        result = []

        for event_schedule in event_schedule_qs:

            final_date = datetime.date(datetime.strptime(event_schedule.final_date, '%Y-%m-%d'))
            effective_date = datetime.date(datetime.strptime(event_schedule.effective_date, '%Y-%m-%d'))

            if final_date >= now and effective_date - timedelta(days=event_schedule.notify_in_n_days):
                result.append(event_schedule)

        if not len(result):
            _l.debug('event schedules not found')
            return

        event_schedules_cache = defaultdict(list)
        for event_schedule in result:
            event_schedules_cache[event_schedule.instrument_id].append(event_schedule)

        for item in opened_instrument_items:
            portfolio = item['portfolio_id']
            account = item['account_position_id']
            strategy1 = item['strategy1_position_id']
            strategy2 = item['strategy2_position_id']
            strategy3 = item['strategy3_position_id']
            instrument = item['instrument_id']
            position = item['position_size']

            event_schedules = event_schedules_cache.get(instrument, None)
            _l.info('opened instrument: portfolio=%s, account=%s, strategy1=%s, strategy2=%s, strategy3=%s, '
                    'instrument=%s, position=%s, event_schedules=%s',
                    portfolio, account, strategy1, strategy2, strategy3,
                    instrument, position, [e.id for e in event_schedules] if event_schedules else [])

            if not event_schedules:
                continue

            for event_schedule in event_schedules:
                _l.debug('event_schedule=%s, event_class=%s, notification_class=%s, periodicity=%s, n=%s',
                         event_schedule.id, event_schedule.event_class, event_schedule.notification_class,
                         event_schedule.periodicity, event_schedule.periodicity_n)

                is_complies, effective_date, notification_date = event_schedule.check_date(now)

                is_apply_default = event_schedule.notification_class == NotificationClass.APPLY_DEF_ON_EDATE or event_schedule.notification_class == NotificationClass.APPLY_DEF_ON_NDATE

                _l.debug('is_complies=%s', is_complies)
                if is_complies and is_apply_default:
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
                        position=position
                    )
                    if ge_dup_qs.exists():
                        _l.debug('generated event already exist')
                        continue

                    print('event_schedule %s' % event_schedule)

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
                    generated_event.data = {
                        'actions_parameters': parameters
                    }
                    generated_event.save()

        process_events.apply_async()

    except Exception as e:

        _l.info('generate_events exception occurred %s' % e)
        _l.info(traceback.format_exc())


@shared_task(name='instruments.process_events', bind=True)
@transaction.atomic()
def process_events(self):
    from poms.celery_tasks.models import CeleryTask

    master_user = MasterUser.objects.all()[0]  # TODO refactor to get by base_api_url
    member = Member.objects.get(master_user=master_user, is_owner=True)
    celery_task = CeleryTask.objects.create(
        master_user=master_user,
        member=member,
        verbose_name="Process Events",
        type="process_events"
    )

    try:
        from poms.instruments.handlers import GeneratedEventProcess

        _l.debug('process_events0: master_user=%s', master_user.id)

        now = date_now()

        generated_event_qs = GeneratedEvent.objects.prefetch_related(
            'event_schedule',
            'event_schedule__notification_class',
            'instrument',
            'instrument__pricing_currency',
            'instrument__accrued_currency',
            'portfolio',
            'account',
            'strategy1',
            'strategy2',
            'strategy3',
        ).filter(
            master_user=master_user,
            status=GeneratedEvent.NEW,
        ).filter(
            Q(effective_date=now) | Q(notification_date=now),
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
                'process:'
                ' notification_class=%s,'
                ' notification_date=%s,'
                ' notification_date_notified=%s'
                ' effective_date=%s,'
                ' effective_date_notified=%s,'
                ' is_notify_on_notification_date=%s,'
                ' is_notify_on_effective_date=%s,'
                ' is_apply_default_on_notification_date=%s,'
                ' is_apply_default_on_effective_date=%s,'
                ' is_need_reaction_on_notification_date=%s,'
                ' is_need_reaction_on_effective_date=%s',
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
                is_need_reaction_on_effective_date)

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
                            context={
                                'master_user': master_user,
                                'member': member
                            })
                        notifications.send(recipients=[member],
                                           message=message,
                                           actor=gevent.event_schedule,
                                           verb='event occurred',
                                           action_object=gevent.instrument)
                else:
                    notifications.send(recipients=recipients,
                                       actor=gevent.event_schedule,
                                       verb='event occurred',
                                       action_object=gevent.instrument)

            if is_apply_default_on_notification_date or is_apply_default_on_effective_date:
                action = next((a for a in gevent.event_schedule.actions.all() if a.is_book_automatic), None)
                if action:
                    ttp = GeneratedEventProcess(
                        generated_event=gevent,
                        action=action,
                        context={
                            'master_user': master_user,
                            'member': owner,
                        }
                    )
                    ttp.process()
                    gevent.processed(None, action, ttp.complex_transaction)
                else:
                    gevent.status = GeneratedEvent.BOOKED_SYSTEM_DEFAULT
                    gevent.status_date = timezone.now()

                processed_count = processed_count + 1

            if is_notify_on_notification_date or is_notify_on_effective_date or \
                    is_apply_default_on_notification_date or is_apply_default_on_effective_date:
                gevent.save()

        celery_task.verbose_result = 'Events Processed: %s' % processed_count
        celery_task.status = CeleryTask.STATUS_DONE
        celery_task.save()

    except Exception as e:

        _l.error('process_events0 exception occurred %s' % e)
        _l.error(traceback.format_exc())
        celery_task.error_message = 'Error %s. Traceback %s' % (e, traceback.format_exc())
        celery_task.status = CeleryTask.STATUS_ERROR
        celery_task.save()
