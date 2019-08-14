from __future__ import unicode_literals

from django.apps import AppConfig
from django.utils.translation import ugettext_lazy


class ReferenceTablesConfig(AppConfig):
    name = 'poms.reference_tables'
    verbose_name = ugettext_lazy('Reference Tables')
