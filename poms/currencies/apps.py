from __future__ import unicode_literals

from django.apps import AppConfig
from django.utils.translation import gettext_lazy


class CurrenciesConfig(AppConfig):
    name = "poms.currencies"
    # label = 'poms_currencies'
    verbose_name = gettext_lazy("Currencies")

    # def ready(self):
    #     from poms.currencies.models import defaults_currencies
    #     import pprint
    #
    #     for k, v in defaults_currencies.items():
    #         pprint.pprint(v)
