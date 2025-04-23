from django.apps import AppConfig
from django.db import DEFAULT_DB_ALIAS
from django.db.models.signals import post_migrate


class PricingConfig(AppConfig):
    name = "poms.pricing"

    def ready(self):
        pass
