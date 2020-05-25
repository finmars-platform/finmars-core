from __future__ import unicode_literals

from django.db import DEFAULT_DB_ALIAS
from django.db.models.signals import post_migrate



from django.apps import AppConfig


class PricingConfig(AppConfig):
    name = "poms.pricing"

    def ready(self):
        post_migrate.connect(self.update_pricing_providers, sender=self)

    def update_pricing_providers(self, app_config, verbosity=2, using=DEFAULT_DB_ALIAS, **kwargs):
        from poms.common.utils import db_class_check_data
        from .models import CurrencyPricingSchemeType, InstrumentPricingSchemeType

        currency_scheme_types = [
            {
                "id": 1,
                "name": "Skip",
                "input_type": CurrencyPricingSchemeType.NONE
            },
            {
                "id": 2,
                "name": "Manual Pricing",
                "input_type": CurrencyPricingSchemeType.SINGLE_PARAMETER
            },
            {
                "id": 3,
                "name": "Single Parameter Formula",
                "input_type": CurrencyPricingSchemeType.SINGLE_PARAMETER
            },
            {
                "id": 4,
                "name": "Multiple Parameter Formula",
                "input_type": CurrencyPricingSchemeType.MULTIPLE_PARAMETERS
            },
            {
                "id": 5,
                "name": "Bloomberg",
                "input_type": CurrencyPricingSchemeType.SINGLE_PARAMETER
            },
            {
                "id": 6,
                "name": "World Trading Data",
                "input_type": CurrencyPricingSchemeType.SINGLE_PARAMETER
            },
            {
                "id": 7,
                "name": "Fixer",
                "input_type": CurrencyPricingSchemeType.SINGLE_PARAMETER
            },

        ]

        instrument_scheme_types = [
            {
                "id": 1,
                "name": "Skip",
                "input_type": InstrumentPricingSchemeType.NONE
            },
            {
                "id": 2,
                "name": "Manual Pricing",
                "input_type": InstrumentPricingSchemeType.SINGLE_PARAMETER
            },
            {
                "id": 3,
                "name": "Single Parameter Formula",
                "input_type": InstrumentPricingSchemeType.SINGLE_PARAMETER
            },
            {
                "id": 4,
                "name": "Multiple Parameter Formula",
                "input_type": InstrumentPricingSchemeType.MULTIPLE_PARAMETERS
            },
            {
                "id": 5,
                "name": "Bloomberg",
                "input_type": InstrumentPricingSchemeType.SINGLE_PARAMETER
            },
            {
                "id": 6,
                "name": "World Trading Data",
                "input_type": InstrumentPricingSchemeType.SINGLE_PARAMETER
            },
            {
                "id": 7,
                "name": "Alpha Vantage",
                "input_type": InstrumentPricingSchemeType.SINGLE_PARAMETER
            },

        ]

        currency_exists = CurrencyPricingSchemeType.objects.values_list('pk', flat=True)
        instrument_exists = InstrumentPricingSchemeType.objects.values_list('pk', flat=True)

        for type in currency_scheme_types:

            if type['id'] in currency_exists:

                item = CurrencyPricingSchemeType.objects.get(id=type['id'])

                item.name = type['name']
                item.input_type = type['input_type']

                item.save()

            else:
                CurrencyPricingSchemeType.objects.create(**type)



        for type in instrument_scheme_types:

            if type['id'] in instrument_exists:

                item = InstrumentPricingSchemeType.objects.get(id=type['id'])

                item.name = type['name']
                item.input_type = type['input_type']

                item.save()

            else:
                InstrumentPricingSchemeType.objects.create(**type)