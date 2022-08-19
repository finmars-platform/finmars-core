from __future__ import unicode_literals

from django.apps import AppConfig
from django.db import DEFAULT_DB_ALIAS
from django.db.models.signals import post_migrate
from django.utils.translation import gettext_lazy

import requests
import json

import logging

from poms_app import settings

_l = logging.getLogger('poms.api')


class ApiConfig(AppConfig):
    name = 'poms.api'
    # label = 'poms_api'
    verbose_name = gettext_lazy('Rest API')

    def ready(self):

        post_migrate.connect(self.add_view_and_manage_permissions, sender=self)
        post_migrate.connect(self.register_at_authorizer_service, sender=self)

    def add_view_and_manage_permissions(self, app_config, verbosity=2, using=DEFAULT_DB_ALIAS, **kwargs):
        from poms.common.utils import add_view_and_manage_permissions
        add_view_and_manage_permissions()

    def register_at_authorizer_service(self, app_config, verbosity=2, using=DEFAULT_DB_ALIAS, **kwargs):

        if settings.AUTHORIZER_URL:

            try:
                _l.info("register_at_authorizer_service processing")

                headers = {'Content-type': 'application/json', 'Accept': 'application/json'}

                data = {
                    "base_api_url": settings.BASE_API_URL,
                }

                url = settings.AUTHORIZER_URL + '/backend-is-ready/'

                _l.info("register_at_authorizer_service url %s" % url)

                response = requests.post(url=url, data=json.dumps(data), headers=headers)

                _l.info("register_at_authorizer_service processing response.status_code %s" % response.status_code)
                _l.info("register_at_authorizer_service processing response.text %s" % response.text)

            except Exception as e:
                _l.info("register_at_authorizer_service error %s" % e)

        else:
            _l.info('settings.AUTHORIZER_URL is not set')
