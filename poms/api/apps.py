from __future__ import unicode_literals

from django.apps import AppConfig
from django.db import DEFAULT_DB_ALIAS
from django.db.models.signals import post_migrate
from django.utils.translation import ugettext_lazy

import requests
import json


import logging

from poms_app import settings

_l = logging.getLogger('poms.api')


class ApiConfig(AppConfig):
    name = 'poms.api'
    # label = 'poms_api'
    verbose_name = ugettext_lazy('Rest API')

    def ready(self):

        post_migrate.connect(self.add_view_and_manage_permissions, sender=self)

        # if 'SIMPLE' in settings.BACKEND_ROLES:
            # post_migrate.connect(self.register_at_authorizer_service, sender=self)

    def add_view_and_manage_permissions(self, app_config, verbosity=2, using=DEFAULT_DB_ALIAS, **kwargs):
        from poms.common.utils import add_view_and_manage_permissions
        add_view_and_manage_permissions()


