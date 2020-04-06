from __future__ import unicode_literals

from django.apps import AppConfig
from django.db import DEFAULT_DB_ALIAS
from django.db.models.signals import post_migrate
from django.utils.translation import ugettext_lazy


class InstrumentsConfig(AppConfig):
    name = 'poms.instruments'
    # label = 'poms'
    verbose_name = ugettext_lazy('Instruments')

    def ready(self):
        post_migrate.connect(self.update_transaction_classes, sender=self)

    def update_transaction_classes(self, app_config, verbosity=2, using=DEFAULT_DB_ALIAS, **kwargs):
        from poms.common.utils import db_class_check_data
        from .models import InstrumentClass, DailyPricingModel, AccrualCalculationModel, Periodicity, \
            CostMethod, PaymentSizeDetail, PricingCondition

        db_class_check_data(InstrumentClass, verbosity, using)
        db_class_check_data(DailyPricingModel, verbosity, using)
        db_class_check_data(AccrualCalculationModel, verbosity, using)
        db_class_check_data(Periodicity, verbosity, using)
        db_class_check_data(CostMethod, verbosity, using)
        db_class_check_data(PaymentSizeDetail, verbosity, using)
        db_class_check_data(PricingCondition, verbosity, using)
