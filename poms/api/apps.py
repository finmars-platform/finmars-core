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
        post_migrate.connect(self.create_base_folders, sender=self)

    def add_view_and_manage_permissions(self, app_config, verbosity=2, using=DEFAULT_DB_ALIAS, **kwargs):
        from poms.common.utils import add_view_and_manage_permissions
        add_view_and_manage_permissions()

    def register_at_authorizer_service(self, app_config, verbosity=2, using=DEFAULT_DB_ALIAS, **kwargs):

        from poms.users.models import User, Member, MasterUser

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

                _l.info(
                    "register_at_authorizer_service backend-is-ready response.status_code %s" % response.status_code)
                _l.info("register_at_authorizer_service backend-is-ready response.text %s" % response.text)

                try:

                    url = settings.AUTHORIZER_URL + '/backend-sync-users/'

                    response = requests.post(url=url, data=json.dumps(data), headers=headers)
                    _l.info(
                        "register_at_authorizer_service backend-sync-users response.status_code %s" % response.status_code)
                    _l.info("register_at_authorizer_service backend-sync-users response.text %s" % response.text)

                    response_data = response.json()

                    members = response_data['members']

                    master_user = MasterUser.objects.filter()[0]

                    _members = Member.objects.all()

                    for _member in _members:
                        _member.is_owner = False
                        _member.save()

                    for member in members:

                        user = None
                        _member = None

                        try:

                            user = User.objects.get(username=member['username'])

                        except Exception as e:

                            user = User.objects.create(username=member['username'])

                            _l.info("User %s created " % member['username'])

                        try:

                            _member = Member.objects.get(username=member['username'])

                        except Exception as e:

                            _member = Member.objects.create(user=user,
                                                            master_user=master_user,
                                                            is_owner=member['is_owner'],
                                                            is_admin=member['is_admin'])

                            _l.info("Member %s created " % member['username'])

                except Exception as e:
                    _l.error("Could not sync users %s" % e)


            except Exception as e:
                _l.info("register_at_authorizer_service error %s" % e)

        else:
            _l.info('settings.AUTHORIZER_URL is not set')

    def create_base_folders(self, app_config, verbosity=2, using=DEFAULT_DB_ALIAS, **kwargs):

        from poms.common.storage import get_storage
        from tempfile import NamedTemporaryFile
        storage = get_storage()
        from poms_app import settings
        from poms.users.models import Member

        _l.info("create base folders if not exists")

        _l.info('storage %s' % storage)

        if not storage.exists(settings.BASE_API_URL + '/.system/.init'):
            path = settings.BASE_API_URL + '/.system/.init'

            with NamedTemporaryFile() as tmpf:
                tmpf.write(b'')
                tmpf.flush()
                storage.save(path, tmpf)

                _l.info("create .system folder")

        if not storage.exists(settings.BASE_API_URL + '/public/.init'):
            path = settings.BASE_API_URL + '/public/.init'

            with NamedTemporaryFile() as tmpf:
                tmpf.write(b'')
                tmpf.flush()
                storage.save(path, tmpf)

                _l.info("create public folder")

        if not storage.exists(settings.BASE_API_URL + '/import/.init'):
            path = settings.BASE_API_URL + '/import/.init'

            with NamedTemporaryFile() as tmpf:
                tmpf.write(b'')
                tmpf.flush()
                storage.save(path, tmpf)

                _l.info("create import folder")

        members = Member.objects.all()

        for member in members:

            if not storage.exists(settings.BASE_API_URL + '/' + member.username + '/.init'):
                path = settings.BASE_API_URL + '/' + member.username + '/.init'

                with NamedTemporaryFile() as tmpf:
                    tmpf.write(b'')
                    tmpf.flush()
                    storage.save(path, tmpf)
