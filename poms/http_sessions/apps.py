from __future__ import unicode_literals

from django.apps import AppConfig
from django.utils.translation import gettext_lazy


class HttpSessionsConfig(AppConfig):
    name = 'poms.http_sessions'
    # label = 'poms_sessions'
    verbose_name = gettext_lazy('Sessions')
