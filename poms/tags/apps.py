from __future__ import unicode_literals

from django.apps import AppConfig
from django.utils.translation import gettext_lazy


class TagsConfig(AppConfig):
    name = 'poms.tags'
    verbose_name = gettext_lazy('Tags')
