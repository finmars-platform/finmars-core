from django.apps import AppConfig
from django.db import DEFAULT_DB_ALIAS
from django.db.models.signals import post_migrate


class PricingConfig(AppConfig):
    name = "poms.pricing"

    def ready(self):
        post_migrate.connect(self.update_pricing_providers, sender=self)

    def update_pricing_providers(
        self, app_config, verbosity=2, using=DEFAULT_DB_ALIAS, **kwargs
    ):
        from .models import CurrencyPricingSchemeType, InstrumentPricingSchemeType

        currency_scheme_types = [
            {"id": 1, "name": "Skip", "input_type": CurrencyPricingSchemeType.NONE},
            {
                "id": 2,
                "name": "Manual Pricing",
                "input_type": CurrencyPricingSchemeType.SINGLE_PARAMETER,
            },
            {
                "id": 3,
                "name": "Single Parameter Formula",
                "input_type": CurrencyPricingSchemeType.SINGLE_PARAMETER,
            },
            {
                "id": 4,
                "name": "Multiple Parameter Formula",
                "input_type": CurrencyPricingSchemeType.MULTIPLE_PARAMETERS,
            },
            {
                "id": 5,
                "name": "Bloomberg",
                "input_type": CurrencyPricingSchemeType.SINGLE_PARAMETER,
            },
            {
                "id": 6,
                "name": "World Trading Data",
                "input_type": CurrencyPricingSchemeType.SINGLE_PARAMETER,
            },
            {
                "id": 7,
                "name": "Fixer",
                "input_type": CurrencyPricingSchemeType.SINGLE_PARAMETER,
            },
            {
                "id": 9,
                "name": "CBONDS",
                "input_type": InstrumentPricingSchemeType.SINGLE_PARAMETER,
            },
        ]

        instrument_scheme_types = [
            {"id": 1, "name": "Skip", "input_type": InstrumentPricingSchemeType.NONE},
            {
                "id": 2,
                "name": "Manual Pricing",
                "input_type": InstrumentPricingSchemeType.SINGLE_PARAMETER,
            },
            {
                "id": 3,
                "name": "Single Parameter Formula",
                "input_type": InstrumentPricingSchemeType.SINGLE_PARAMETER,
            },
            {
                "id": 4,
                "name": "Multiple Parameter Formula",
                "input_type": InstrumentPricingSchemeType.MULTIPLE_PARAMETERS,
            },
            {
                "id": 5,
                "name": "Bloomberg",
                "input_type": InstrumentPricingSchemeType.SINGLE_PARAMETER,
            },
            {
                "id": 6,
                "name": "World Trading Data",
                "input_type": InstrumentPricingSchemeType.SINGLE_PARAMETER,
            },
            {
                "id": 7,
                "name": "Alpha Vantage",
                "input_type": InstrumentPricingSchemeType.SINGLE_PARAMETER,
            },
            {
                "id": 8,
                "name": "Bloomberg Forwards",
                "input_type": InstrumentPricingSchemeType.MULTIPLE_PARAMETERS,
            },
            {
                "id": 9,
                "name": "CBONDS",
                "input_type": InstrumentPricingSchemeType.SINGLE_PARAMETER,
            },
        ]

        currency_exists = CurrencyPricingSchemeType.objects.using(using).values_list(
            "pk", flat=True
        )
        for type_ in currency_scheme_types:
            if type_["id"] in currency_exists:
                item = CurrencyPricingSchemeType.objects.using(using).get(
                    id=type_["id"]
                )
                item.name = type_["name"]
                item.input_type = type_["input_type"]
                item.save()

            else:
                CurrencyPricingSchemeType.objects.create(**type_)

        instrument_exists = InstrumentPricingSchemeType.objects.using(
            using
        ).values_list("pk", flat=True)
        for type_ in instrument_scheme_types:
            if type_["id"] in instrument_exists:
                item = InstrumentPricingSchemeType.objects.using(using).get(
                    id=type_["id"]
                )
                item.name = type_["name"]
                item.input_type = type_["input_type"]
                item.save()

            else:
                InstrumentPricingSchemeType.objects.create(**type_)
