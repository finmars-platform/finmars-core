from __future__ import unicode_literals

from django.apps import AppConfig
from django.utils.translation import gettext_lazy


class PortfoliosConfig(AppConfig):
    name = 'poms.portfolios'
    # label = 'poms'
    verbose_name = gettext_lazy('Portfolios')
