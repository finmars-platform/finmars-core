import logging
from collections import defaultdict
from datetime import date

from celery import shared_task
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone

from poms import notifications
from poms.common.utils import date_now, isclose
from poms.instruments.models import EventSchedule, Instrument, GeneratedEvent
from poms.reports.builders.balance_item import Report, ReportItem
from poms.reports.builders.balance_pl import ReportBuilder
from poms.users.models import MasterUser

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


@shared_task(name='instruments.generate_events0', ignore_result=True)
def generate_events0(master_user):
    # _l.debug('generate_events0: master_user=%s', master_user.id)

    opened_instrument_items = []

    now = date_now()

    report = Report(
        master_user=master_user,
        report_date=now,
        allocation_mode=Report.MODE_IGNORE,
    )
    builder = ReportBuilder(instance=report)
    builder.build_position_only()

    for i in report.items:
        if i.type == ReportItem.TYPE_INSTRUMENT and not isclose(i.pos_size, 0.0):
            opened_instrument_items.append(i)

    # _l.debug('opened instruments: %s', sorted(i.instr.id for i in opened_instrument_items))
    if not opened_instrument_items:
        return

    event_schedule_qs = EventSchedule.objects.prefetch_related(
        'instrument',
        'event_class',
        'notification_class',
        'periodicity',
        'actions',
        'actions__transaction_type'
    ).filter(
        effective_date__lte=(now - F("notify_in_n_days")),
        final_date__gte=now,
        instrument__in={i.instr.id for i in opened_instrument_items}
    ).order_by(
        'instrument__master_user__id',
        'instrument__id'
    )

    if not event_schedule_qs.exists():
        # _l.debug('event schedules not found')
        return

    event_schedules_cache = defaultdict(list)
    for event_schedule in event_schedule_qs:
        event_schedules_cache[event_schedule.instrument_id].append(event_schedule)

    for item in opened_instrument_items:
        portfolio = item.prtfl
        account = item.acc
        strategy1 = item.str1
        strategy2 = item.str2
        strategy3 = item.str3
        instrument = item.instr
        position = item.pos_size

        event_schedules = event_schedules_cache.get(instrument.id, None)
        _l.debug('opened instrument: portfolio=%s, account=%s, strategy1=%s, strategy2=%s, strategy3=%s, '
                 'instrument=%s, position=%s, event_schedules=%s',
                 portfolio.id, account.id, strategy1.id, strategy2.id, strategy3.id,
                 instrument.id, position, [e.id for e in event_schedules] if event_schedules else [])

        if not event_schedules:
            continue

        for event_schedule in event_schedules:
            _l.debug('event_schedule=%s, event_class=%s, notification_class=%s, periodicity=%s, n=%s',
                     event_schedule.id, event_schedule.event_class, event_schedule.notification_class,
                     event_schedule.periodicity, event_schedule.periodicity_n)

            is_complies, effective_date, notification_date = event_schedule.check_date(now)

            # _l.debug('is_complies=%s', is_complies)
            if is_complies:
                ge_dup_qs = GeneratedEvent.objects.filter(
                    master_user=master_user,
                    event_schedule=event_schedule,
                    effective_date=effective_date,
                    notification_date=notification_date,
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

                generated_event = GeneratedEvent()
                generated_event.master_user = master_user
                generated_event.event_schedule = event_schedule
                generated_event.status = GeneratedEvent.NEW
                generated_event.status_modified = timezone.now()
                generated_event.effective_date = effective_date
                generated_event.notification_date = notification_date
                generated_event.instrument = instrument
                generated_event.portfolio = portfolio
                generated_event.account = account
                generated_event.strategy1 = strategy1
                generated_event.strategy2 = strategy2
                generated_event.strategy3 = strategy3
                generated_event.position = position
                generated_event.save()

    process_events0.apply_async(kwargs={'master_user': master_user})


@shared_task(name='instruments.generate_events', ignore_result=True)
def generate_events(master_users=None):
    # _l.debug('generate_events: master_users=%s', master_users)

    # now = date_now()

    master_user_qs = MasterUser.objects.all()
    if master_users:
        master_user_qs = master_user_qs.filter(pk__in=master_users)

    for master_user in master_user_qs:
        # _l.debug('generate_events: master_user=%s', master_user.id)
        #
        # opened_instrument_items = []
        # # instruments_pk = set()
        #
        # report = Report(
        #     master_user=master_user,
        #     report_date=now,
        #     allocation_mode=Report.MODE_IGNORE,
        # )
        # builder = ReportBuilder(instance=report)
        # # builder.build_balance()
        # builder.build_position_only()
        #
        # for i in report.items:
        #     if i.type == ReportItem.TYPE_INSTRUMENT and not isclose(i.pos_size, 0.0):
        #         opened_instrument_items.append(i)
        #         # instruments_pk.add(i.instr.id)
        #
        # _l.debug('opened instruments: %s', {i.instr.id for i in opened_instrument_items})
        # if not opened_instrument_items:
        #     return
        #
        # event_schedule_qs = EventSchedule.objects.prefetch_related(
        #     'instrument__master_user',
        #     'instrument',
        #     'event_class',
        #     'notification_class',
        #     'periodicity',
        #     'actions',
        #     'actions__transaction_type'
        # ).filter(
        #     effective_date__lte=(now - F("notify_in_n_days")),
        #     final_date__gte=now,
        #     instrument__in={i.instr.id for i in opened_instrument_items}
        # ).order_by(
        #     'instrument__master_user__id',
        #     'instrument__id'
        # )
        # # event_schedule_qs = event_schedule_qs.filter(instrument__in=instruments_pk)
        #
        # if not event_schedule_qs.exists():
        #     _l.debug('event schedules not found')
        #     return
        #
        # event_schedule_cache = defaultdict(list)
        # for event_schedule in event_schedule_qs:
        #     event_schedule_cache[event_schedule.instrument_id].append(event_schedule)
        #
        # for item in opened_instrument_items:
        #     portfolio = item.prtfl
        #     account = item.acc
        #     strategy1 = item.str1
        #     strategy2 = item.str2
        #     strategy3 = item.str3
        #     instrument = item.instr
        #     position = item.pos_size
        #
        #     event_schedules = event_schedule_cache.get(instrument.id, None) or []
        #
        #     _l.debug('opened instrument: portfolio=%s, account=%s, strategy1=%s, strategy2=%s, strategy3=%s, '
        #              'instrument=%s, position=%s, event_schedules=%s',
        #              portfolio.id, account.id, strategy1.id, strategy2.id, strategy3.id,
        #              instrument.id, position, [e.id for e in event_schedules])
        #
        #     if not event_schedules:
        #         continue
        #
        #     for event_schedule in event_schedules:
        #         _l.debug('event_schedule=%s, event_class=%s, notification_class=%s, periodicity=%s, n=%s',
        #                  event_schedule.id, event_schedule.event_class, event_schedule.notification_class,
        #                  event_schedule.periodicity, event_schedule.periodicity_n)
        #
        #         is_complies, effective_date, notification_date = event_schedule.check_date(now)
        #
        #         _l.debug('is_complies=%s', is_complies)
        #         if is_complies:
        #             ge_dup_qs = GeneratedEvent.objects.filter(
        #                 master_user=master_user,
        #                 event_schedule=event_schedule,
        #                 effective_date=effective_date,
        #                 notification_date=notification_date,
        #                 instrument=instrument,
        #                 portfolio=portfolio,
        #                 account=account,
        #                 strategy1=strategy1,
        #                 strategy2=strategy2,
        #                 strategy3=strategy3,
        #                 position=position
        #             )
        #             if ge_dup_qs.exists():
        #                 _l.debug('generated event already exist')
        #                 continue
        #
        #             generated_event = GeneratedEvent()
        #             generated_event.master_user = master_user
        #             generated_event.event_schedule = event_schedule
        #             generated_event.status = GeneratedEvent.NEW
        #             generated_event.status_modified = timezone.now()
        #             generated_event.effective_date = effective_date
        #             generated_event.notification_date = notification_date
        #             generated_event.instrument = instrument
        #             generated_event.portfolio = portfolio
        #             generated_event.account = account
        #             generated_event.strategy1 = strategy1
        #             generated_event.strategy2 = strategy2
        #             generated_event.strategy3 = strategy3
        #             generated_event.position = position
        #             generated_event.save()
        generate_events0.apply_async(kwargs={'master_user': master_user})

    # process_events.apply_async(kwargs={'master_users': master_users})

    # _l.debug('finished')


@shared_task(name='instruments.process_events0', ignore_result=True)
@transaction.atomic()
def process_events0(master_user):
    from poms.instruments.handlers import GeneratedEventProcess

    # _l.debug('process_events0: master_user=%s', master_user.id)

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

    for gevent in generated_event_qs:
        is_notify_on_notification_date = gevent.is_notify_on_notification_date(now)
        is_notify_on_effective_date = gevent.is_notify_on_effective_date(now)
        is_apply_default_on_notification_date = gevent.is_apply_default_on_notification_date(now)
        is_apply_default_on_effective_date = gevent.is_apply_default_on_effective_date(now)
        is_need_reaction_on_notification_date = gevent.is_need_reaction_on_notification_date(now)
        is_need_reaction_on_effective_date = gevent.is_need_reaction_on_effective_date(now)

        # _l.debug(
        #     'process:'
        #     ' notification_class=%s,'
        #     ' notification_date=%s,'
        #     ' notification_date_notified=%s'
        #     ' effective_date=%s,'
        #     ' effective_date_notified=%s,'
        #     ' is_notify_on_notification_date=%s,'
        #     ' is_notify_on_effective_date=%s,'
        #     ' is_apply_default_on_notification_date=%s,'
        #     ' is_apply_default_on_effective_date=%s,'
        #     ' is_need_reaction_on_notification_date=%s,'
        #     ' is_need_reaction_on_effective_date=%s',
        #     gevent.event_schedule.notification_class.system_code,
        #     gevent.notification_date,
        #     gevent.notification_date_notified,
        #     gevent.effective_date,
        #     gevent.effective_date_notified,
        #     is_notify_on_notification_date,
        #     is_notify_on_effective_date,
        #     is_apply_default_on_notification_date,
        #     is_apply_default_on_effective_date,
        #     is_need_reaction_on_notification_date,
        #     is_need_reaction_on_effective_date)

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
                gevent.status = GeneratedEvent.BOOKED
                gevent.status_date = timezone.now()

        if is_notify_on_notification_date or is_notify_on_effective_date or \
                is_apply_default_on_notification_date or is_apply_default_on_effective_date:
            gevent.save()


@shared_task(name='instruments.process_events', ignore_result=True)
def process_events(master_users=None):
    # from poms.instruments.handlers import GeneratedEventProcess

    # _l.debug('process_events: master_users=%s', master_users)

    # now = date_now()

    master_user_qs = MasterUser.objects.prefetch_related(
        'members'
    )
    if master_users:
        master_user_qs = master_user_qs.filter(pk__in=master_users)

    for master_user in master_user_qs:
        # _l.debug('process_events: master_user=%s', master_user.id)
        # with transaction.atomic():
        #     generated_event_qs = GeneratedEvent.objects.prefetch_related(
        #         'event_schedule',
        #         'event_schedule__notification_class',
        #         'instrument',
        #         'instrument__pricing_currency',
        #         'instrument__accrued_currency',
        #         'portfolio',
        #         'account',
        #         'strategy1',
        #         'strategy2',
        #         'strategy3',
        #     ).filter(
        #         master_user=master_user,
        #         status=GeneratedEvent.NEW,
        #     ).filter(
        #         Q(effective_date=now) | Q(notification_date=now),
        #     )
        #
        #     for gevent in generated_event_qs:
        #         is_notify_on_notification_date = gevent.is_notify_on_notification_date(now)
        #         is_notify_on_effective_date = gevent.is_notify_on_effective_date(now)
        #         is_apply_default_on_notification_date = gevent.is_apply_default_on_notification_date(now)
        #         is_apply_default_on_effective_date = gevent.is_apply_default_on_effective_date(now)
        #         is_need_reaction_on_notification_date = gevent.is_need_reaction_on_notification_date(now)
        #         is_need_reaction_on_effective_date = gevent.is_need_reaction_on_effective_date(now)
        #
        #         _l.debug(
        #             'process:'
        #             ' notification_class=%s,'
        #             ' notification_date=%s,'
        #             ' notification_date_notified=%s'
        #             ' effective_date=%s,'
        #             ' effective_date_notified=%s,'
        #             ' is_notify_on_notification_date=%s,'
        #             ' is_notify_on_effective_date=%s,'
        #             ' is_apply_default_on_notification_date=%s,'
        #             ' is_apply_default_on_effective_date=%s,'
        #             ' is_need_reaction_on_notification_date=%s,'
        #             ' is_need_reaction_on_effective_date=%s',
        #             gevent.event_schedule.notification_class.system_code,
        #             gevent.notification_date,
        #             gevent.notification_date_notified,
        #             gevent.effective_date,
        #             gevent.effective_date_notified,
        #             is_notify_on_notification_date,
        #             is_notify_on_effective_date,
        #             is_apply_default_on_notification_date,
        #             is_apply_default_on_effective_date,
        #             is_need_reaction_on_notification_date,
        #             is_need_reaction_on_effective_date)
        #
        #         owner = next(iter([m for m in gevent.master_user.members.all() if m.is_owner]))
        #
        #         if is_notify_on_notification_date or is_notify_on_effective_date:
        #             if is_notify_on_notification_date:
        #                 gevent.notification_date_notified = True
        #             if is_notify_on_effective_date:
        #                 gevent.effective_date_notified = True
        #
        #             recipients = [m for m in gevent.master_user.members.all() if not m.is_deleted]
        #
        #             expr = gevent.event_schedule.description or gevent.event_schedule.name
        #             if expr:
        #                 for member in recipients:
        #                     message = gevent.generate_text(
        #                         exr=expr,
        #                         context={
        #                             'master_user': master_user,
        #                             'member': member
        #                         })
        #                     notifications.send(recipients=[member],
        #                                        message=message,
        #                                        actor=gevent.event_schedule,
        #                                        verb='event occurred',
        #                                        action_object=gevent.instrument)
        #             else:
        #                 notifications.send(recipients=recipients,
        #                                    actor=gevent.event_schedule,
        #                                    verb='event occurred',
        #                                    action_object=gevent.instrument)
        #
        #         if is_apply_default_on_notification_date or is_apply_default_on_effective_date:
        #             action = next((a for a in gevent.event_schedule.actions.all() if a.is_book_automatic),
        #                           None)
        #             if action:
        #                 ttp = GeneratedEventProcess(
        #                     generated_event=gevent,
        #                     action=action,
        #                     context={
        #                         'master_user': master_user,
        #                         'member': owner,
        #                     }
        #                 )
        #                 ttp.process()
        #                 gevent.processed(None, action, ttp.complex_transaction)
        #             else:
        #                 gevent.status = GeneratedEvent.BOOKED
        #                 gevent.status_date = timezone.now()
        #
        #         if is_notify_on_notification_date or is_notify_on_effective_date or \
        #                 is_apply_default_on_notification_date or is_apply_default_on_effective_date:
        #             gevent.save()
        process_events0.apply_async(kwargs={'master_user': master_user})
