from django.apps import AppConfig
from django.utils.translation import gettext_lazy


class CurrenciesConfig(AppConfig):
    name = "poms.currencies"
    verbose_name = gettext_lazy("Currencies")
