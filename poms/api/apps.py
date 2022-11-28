from __future__ import unicode_literals

from django.apps import AppConfig
from django.utils.translation import gettext_lazy


class ApiConfig(AppConfig):
    name = 'poms.api'
    verbose_name = gettext_lazy('Rest API')
