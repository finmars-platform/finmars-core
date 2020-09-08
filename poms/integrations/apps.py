from __future__ import unicode_literals, print_function

from django.apps import AppConfig
from django.db import DEFAULT_DB_ALIAS
from django.db.models.signals import post_migrate
from django.utils.translation import ugettext_lazy


class IntegrationsConfig(AppConfig):
    name = 'poms.integrations'
    verbose_name = ugettext_lazy('Integrations')

    def ready(self):
        post_migrate.connect(self.update_transaction_classes, sender=self)
        post_migrate.connect(self.update_data_providers, sender=self)

        # noinspection PyUnresolvedReferences
        import poms.integrations.handlers

    def update_transaction_classes(self, app_config, verbosity=2, using=DEFAULT_DB_ALIAS, **kwargs):
        from poms.common.utils import db_class_check_data
        from .models import ProviderClass, FactorScheduleDownloadMethod, AccrualScheduleDownloadMethod

        # if not isinstance(app_config, IntegrationsConfig):
        #     return

        db_class_check_data(ProviderClass, verbosity, using)
        db_class_check_data(FactorScheduleDownloadMethod, verbosity, using)
        db_class_check_data(AccrualScheduleDownloadMethod, verbosity, using)


    def update_data_providers(self, app_config, verbosity=2, using=DEFAULT_DB_ALIAS, **kwargs):

        from poms.common.utils import db_class_check_data
        from .models import DataProvider

        provider_types = [
            {
                "id": 1,
                "name": "CIM bank",
                "user_code": "cim_bank",
            },
            {
                "id": 2,
                "name": "Julius Baer",
                "user_code": "julius_baer",
            },
            {
                "id": 3,
                "name": "Lombard Odier",
                "user_code": "lombard_odier",
            },
            {
                "id": 4,
                "name": "Revolut",
                "user_code": "revolut",
            },
        ]

        providers_exists = DataProvider.objects.values_list('pk', flat=True)

        for type in provider_types:

            if type['id'] in providers_exists:

                item = DataProvider.objects.get(id=type['id'])

                item.name = type['name']
                item.user_code = type['user_code']

                item.save()

            else:
                DataProvider.objects.create(**type)

