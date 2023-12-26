import logging
import traceback

from django.conf import settings

_l = logging.getLogger("provision")


def handle_schedules(using=settings.DB_DEFAULT):
    from django_celery_beat.models import CrontabSchedule, PeriodicTask

    from poms.schedules.models import Schedule

    existing_ids = []

    schedules = Schedule.objects.using(using).all()

    for schedule in schedules:
        try:
            periodic_task = PeriodicTask.objects.using(using).get(
                name=schedule.user_code
            )
        except PeriodicTask.DoesNotExist:
            periodic_task = PeriodicTask(name=schedule.user_code)

        cron_pieces = schedule.cron_expr.split(" ")

        crontab, _ = CrontabSchedule.objects.using(using).get_or_create(
            minute=cron_pieces[0],
            hour=cron_pieces[1],
            day_of_week=cron_pieces[2],
            day_of_month=cron_pieces[3],
            month_of_year=cron_pieces[4],
        )

        periodic_task.task = "schedules.process"
        periodic_task.crontab = crontab
        periodic_task.kwargs = '{"schedule_user_code": "%s"}' % schedule.user_code
        periodic_task.save()

        existing_ids.append(periodic_task.id)

    _l.info(
        f"sync_schedules: existing_ids {existing_ids} "
        f"updated {len(schedules)} deleted "
        f"{PeriodicTask.objects.using(using).exclude(id__in=existing_ids).count()}"
    )

    PeriodicTask.objects.using(using).exclude(
        id__in=existing_ids,
    ).exclude(
        name__icontains="SYSTEM",
    ).delete()


def sync_schedules(using=settings.DB_DEFAULT):
    try:
        handle_schedules(using=using)

    except Exception as e:
        _l.error(f"sync_schedules error {repr(e)} traceback {traceback.format_exc()}")
