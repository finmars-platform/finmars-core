import datetime
import logging

from django.apps import AppConfig
from django.db import DEFAULT_DB_ALIAS
from django.db.models.signals import post_migrate
from django.utils import timezone

_l = logging.getLogger("provision")


class StandardizedErrorsConfig(AppConfig):
    name = "finmars_standardized_errors"
    verbose_name = "finmars-standardized-errors"

    def ready(self):
        post_migrate.connect(self.delete_old_logs, sender=self)

    def delete_old_logs(
        self, app_config, verbosity=2, using=DEFAULT_DB_ALIAS, **kwargs
    ):
        from finmars_standardized_errors.models import ErrorRecord

        month_ago = timezone.now() - datetime.timedelta(days=30)

        count = ErrorRecord.objects.using(using).filter(created_at__lt=month_ago).count()

        _l.info(f"Going to delete {count} ErrorRecord")

        ErrorRecord.objects.using(using).filter(created_at__lt=month_ago).delete()
