import logging

from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.db import DEFAULT_DB_ALIAS

_l = logging.getLogger('finmars')

class StandardizedErrorsConfig(AppConfig):
    name = "finmars_standardized_errors"
    verbose_name = "finmars-standardized-errors"

    def ready(self):
        post_migrate.connect(self.delete_old_logs, sender=self)

    def delete_old_logs(self, app_config, verbosity=2, using=DEFAULT_DB_ALIAS, **kwargs):

        _l = logging.getLogger('provision')

        from finmars_standardized_errors.models import ErrorRecord

        import datetime
        from django.utils import timezone
        month_ago = timezone.now() - datetime.timedelta(days=30)

        items = ErrorRecord.objects.filter(created__lt=month_ago).count()

        _l.info('Going to delete %s ErrorRecord' % items)
        ErrorRecord.objects.filter(created__lt=month_ago).delete()