from __future__ import unicode_literals

from django.apps import AppConfig
from django.db import DEFAULT_DB_ALIAS
from django.db.models.signals import post_migrate
from django.utils.translation import gettext_lazy


class TransactionsConfig(AppConfig):
    name = 'poms.transactions'
    verbose_name = gettext_lazy('Transactions')

    def ready(self):
        post_migrate.connect(self.update_transaction_classes, sender=self)

    def update_transaction_classes(self, app_config, verbosity=2, using=DEFAULT_DB_ALIAS, **kwargs):
        from poms.common.utils import db_class_check_data
        from .models import TransactionClass, ActionClass, NotificationClass, EventClass, PeriodicityGroup, \
            ComplexTransactionStatus

        db_class_check_data(TransactionClass, verbosity, using)
        db_class_check_data(ComplexTransactionStatus, verbosity, using)
        db_class_check_data(ActionClass, verbosity, using)
        db_class_check_data(NotificationClass, verbosity, using)
        db_class_check_data(EventClass, verbosity, using)
        db_class_check_data(PeriodicityGroup, verbosity, using)
