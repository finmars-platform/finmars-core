from django.apps import AppConfig
from django.db import DEFAULT_DB_ALIAS
from django.db.models.signals import post_migrate


class SchedulesConfig(AppConfig):
    name = "poms.schedules"

    def ready(self):
        post_migrate.connect(self.update_periodic_tasks, sender=self)
        post_migrate.connect(self.sync_user_schedules_with_celery_beat, sender=self)

    # TODO update with auto_cancel_ttl_task
    def update_periodic_tasks(
            self, app_config, verbosity=2, using=DEFAULT_DB_ALIAS, **kwargs
    ):
        from django_celery_beat.models import CrontabSchedule, PeriodicTask

        crontabs = {}
        crontabs["every_30_min"], _ = CrontabSchedule.objects.get_or_create(
            minute="*/30",
            hour="*",
            day_of_week="*",
            day_of_month="*",
            month_of_year="*",
        )
        crontabs["every_5_min"], _ = CrontabSchedule.objects.get_or_create(
            minute="*/5",
            hour="*",
            day_of_week="*",
            day_of_month="*",
            month_of_year="*",
        )
        crontabs["daily_morning"], _ = CrontabSchedule.objects.get_or_create(
            minute="0",
            hour="6",
            day_of_week="*",
            day_of_month="*",
            month_of_year="*",
        )
        crontabs["daily_noon"], _ = CrontabSchedule.objects.get_or_create(
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
            {
                "id": 6,
                "name": "SYSTEM: Clean Old Historical Records",
                "task": "history_tasks.clear_old_journal_records",
                "crontab": crontabs["daily_morning"],
            },
            {
                "id": 7,
                "name": "SYSTEM: Check for Died Workers",
                "task": "celery_tasks.check_for_died_workers",
                "crontab": crontabs["every_5_min"],
            },
        ]

        periodic_tasks_exists = PeriodicTask.objects.values_list("pk", flat=True)

        for task in periodic_tasks:
            if task["id"] in periodic_tasks_exists:
                item = PeriodicTask.objects.get(id=task["id"])
                item.name = task["name"]
                item.task = task["task"]
                item.crontab = task["crontab"]
                item.save()

            else:
                PeriodicTask.objects.create(**task)

    def sync_user_schedules_with_celery_beat(
            self, app_config, verbosity=2, using=DEFAULT_DB_ALIAS, **kwargs
    ):
        from poms.schedules.utils import sync_schedules

        sync_schedules()
