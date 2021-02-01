from django.apps import AppConfig


from django.db import DEFAULT_DB_ALIAS
from django.db.models.signals import post_migrate


class SchedulesConfig(AppConfig):
    name = 'poms.schedules'

    def ready(self):
        post_migrate.connect(self.update_periodic_tasks, sender=self)

    def update_periodic_tasks(self, app_config, verbosity=2, using=DEFAULT_DB_ALIAS, **kwargs):

        from django_celery_beat.models import CrontabSchedule, PeriodicTask

        crontabs = {}

        crontabs['every_30_min'], _ = CrontabSchedule.objects.get_or_create(minute='*/30',
                                                         hour='*',
                                                         day_of_week='*',
                                                         day_of_month='*',
                                                         month_of_year='*'
                                                         )

        crontabs['every_5_min'], _ = CrontabSchedule.objects.get_or_create(minute='*/5',
                                                                            hour='*',
                                                                            day_of_week='*',
                                                                            day_of_month='*',
                                                                            month_of_year='*'
                                                                            )

        periodic_tasks = [
            {
                "id": 1,
                "name": "Shedules Process",
                "task": 'schedules.process',
                "crontab": crontabs['every_5_min']
            }
        ]

        periodic_tasks_exists = PeriodicTask.objects.values_list('pk', flat=True)

        for task in periodic_tasks:

            if task['id'] in periodic_tasks_exists:

                item = PeriodicTask.objects.get(id=task['id'])

                item.name = task['name']
                item.task = task['task']
                item.crontab = task['crontab']

                item.save()

            else:
                PeriodicTask.objects.create(**task)
