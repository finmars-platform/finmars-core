from __future__ import unicode_literals

from django.apps import AppConfig
from django.utils.translation import gettext_lazy


class StrategiesConfig(AppConfig):
    name = "poms.strategies"
    # label = 'poms'
    verbose_name = gettext_lazy("Strategies")
