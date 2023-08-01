from django.apps import AppConfig
from django.utils.translation import gettext_lazy


class CounterpartiesConfig(AppConfig):
    name = "poms.counterparties"
    verbose_name = gettext_lazy("Counterparties")
