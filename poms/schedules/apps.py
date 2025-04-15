import json
import logging
import sys

from django.apps import AppConfig
from django.db import DEFAULT_DB_ALIAS
from django.db.models.signals import post_migrate

_l = logging.getLogger("provision")


class SchedulesConfig(AppConfig):
    name = "poms.schedules"
    verbose_name = "Schedules"

    def ready(self):
        post_migrate.connect(self.update_periodic_tasks, sender=self)
        post_migrate.connect(self.sync_user_schedules_with_celery_beat, sender=self)

    # TODO update with auto_cancel_ttl_task
    def update_periodic_tasks(self, app_config, verbosity=2, using=DEFAULT_DB_ALIAS, **kwargs):
        from django_celery_beat.models import CrontabSchedule, PeriodicTask
        from poms.users.models import MasterUser

        if "test" in sys.argv or "makemigrations" in sys.argv or "migrate" in sys.argv:
            _l.info("update_periodic_tasks ignored - TEST MODE")
            return

        _l.info(f"update_periodic_tasks start, using {using} database")

        master = MasterUser.objects.first()

        crontabs = {}
        crontabs["every_30_min"], _ = CrontabSchedule.objects.using(using).get_or_create(
            minute="*/30",
            hour="*",
            day_of_week="*",
            day_of_month="*",
            month_of_year="*",
        )
        crontabs["every_5_min"], _ = CrontabSchedule.objects.using(
            using,
        ).get_or_create(
            minute="*/5",
            hour="*",
            day_of_week="*",
            day_of_month="*",
            month_of_year="*",
        )
        crontabs["daily_morning"], _ = CrontabSchedule.objects.using(
            using,
        ).get_or_create(
            minute="0",
            hour="6",
            day_of_week="*",
            day_of_month="*",
            month_of_year="*",
        )
        crontabs["daily_noon"], _ = CrontabSchedule.objects.using(
            using,
        ).get_or_create(
            minute="0",
            hour="12",
            day_of_week="*",
            day_of_month="*",
            month_of_year="*",
        )
        periodic_tasks = [
            # {
            #     "id": 1,
            #     "name": "Schedules Process",
            #     "task": "schedules.process",
            #     "crontab": crontabs["every_5_min"],
            # },
            # {
            #     "id": 2,
            #     "name": "Generate Events",
            #     "task": "instruments.generate_events",
            #     "crontab": crontabs["daily_morning"],
            # },
            # {
            #     "id": 3,
            #     "name": "Events Process",
            #     "task": "instruments.process_events",
            #     "crontab": crontabs["daily_noon"],
            # },
            # {
            #     "id": 4,
            #     "name": "Calculate Portfolio Register navs",
            #     "task": "portfolios.calculate_portfolio_register_price_history",
            #     "crontab": crontabs["daily_morning"],
            # },
            # {
            #     "id": 5,
            #     "name": "Calculate Historical Metrics",
            #     "task": "widgets.calculate_historical",
            #     "crontab": crontabs["daily_morning"],
            # },
            # {
            #     "id": 6,
            #     "name": "SYSTEM: Clean Old Historical Records",
            #     "task": "history_tasks.clear_old_journal_records",
            #     "crontab": crontabs["daily_morning"],
            # },
            # {
            #     "id": 7,
            #     "name": "SYSTEM: Check for Died Workers",
            #     "task": "celery_tasks.check_for_died_workers",
            #     "crontab": crontabs["every_5_min"],
            # },
            {
                "id": 8,
                "name": "SYSTEM: Export journal to storage",
                "task": "history.common_export_journal_to_storage",
                "crontab": crontabs["daily_morning"],
                "kwargs": json.dumps({"context": {"space_code": master.space_code}}),
            },
        ]

        periodic_tasks_exists = PeriodicTask.objects.using(
            using,
        ).values_list(
            "pk",
            flat=True,
        )

        for task in periodic_tasks:
            if task["id"] in periodic_tasks_exists:
                item = PeriodicTask.objects.using(
                    using,
                ).get(id=task["id"])
                item.name = task["name"]
                item.task = task["task"]
                item.crontab = task["crontab"]
                item.kwargs = task.get("kwargs", {})
                item.save()

            else:
                _l.info(f"create PeriodicTask data={task}")
                PeriodicTask.objects.using(using).create(**task)

    def sync_user_schedules_with_celery_beat(self, app_config, verbosity=2, using=DEFAULT_DB_ALIAS, **kwargs):
        from poms.schedules.utils import sync_schedules

        if "test" in sys.argv or "makemigrations" in sys.argv or "migrate" in sys.argv:
            _l.info("sync_user_schedules_with_celery_beat ignored - TEST MODE")
            return

        _l.info(f"sync_user_schedules_with_celery_beat start, using {using} database")

        sync_schedules(using=using)
