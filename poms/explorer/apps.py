from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.db import DEFAULT_DB_ALIAS

import logging
_l = logging.getLogger('poms.explorer')

class ExplorerConfig(AppConfig):
    name = 'poms.explorer'


