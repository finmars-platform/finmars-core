import traceback


def sync_schedules():
    import logging
    _l = logging.getLogger('provision')

    try:

        _l.info('sync_schedules start')

        from django_celery_beat.models import CrontabSchedule, PeriodicTask
        from poms.schedules.models import Schedule

        existing_ids = []

        schedules = Schedule.objects.all()

        for schedule in schedules:

            periodic_task = None

            try:
                periodic_task = PeriodicTask.objects.get(name=schedule.user_code)
            except Exception as e:
                periodic_task = PeriodicTask(name=schedule.user_code)

            cron_pieces = schedule.cron_expr.split(' ')

            crontab, _ = CrontabSchedule.objects.get_or_create(minute=cron_pieces[0],
                                                               hour=cron_pieces[1],
                                                               day_of_week=cron_pieces[2],
                                                               day_of_month=cron_pieces[3],
                                                               month_of_year=cron_pieces[4])

            periodic_task.task = 'schedules.process'
            periodic_task.crontab = crontab

            periodic_task.kwargs = '{"schedule_user_code": "%s"}' % schedule.user_code

            periodic_task.save()
            existing_ids.append(periodic_task.id)

        _l.info('sync_schedules: existing_ids %s' % existing_ids)

        _l.info("sync_schedules: schedules updated %s" % len(schedules))
        _l.info("sync_schedules: schedules deleted %s" % PeriodicTask.objects.exclude(id__in=existing_ids).count())

        PeriodicTask.objects.exclude(id__in=existing_ids).delete()

    except Exception as e:
        _l.error('sync_schedules error %s' % e)
        _l.error('sync_schedules traceback %s' % traceback.format_exc())
