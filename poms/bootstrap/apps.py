from __future__ import unicode_literals

import json
import logging
import traceback

import requests
from django.apps import AppConfig
from django.db import DEFAULT_DB_ALIAS
from django.db.models.signals import post_migrate
from django.utils.translation import gettext_lazy

from poms_app import settings

_l = logging.getLogger('poms.bootstrap')


class BootstrapConfig(AppConfig):
    name = 'poms.bootstrap'
    verbose_name = gettext_lazy('Bootstrap')

    def ready(self):
        post_migrate.connect(self.bootstrap, sender=self)

    def bootstrap(self, app_config, verbosity=2, using=DEFAULT_DB_ALIAS, **kwargs):
        '''
        In idea it should be the first methods that should be executed on backend server startup


        :param app_config:
        :param verbosity:
        :param using:
        :param kwargs:
        :return:
        '''

        _l.info("Bootstrapping Finmars Application")


        self.add_view_and_manage_permissions()
        self.load_master_user_data()
        self.create_finmars_bot()
        self.sync_users_at_authorizer_service()
        self.load_init_configuration()
        self.create_base_folders()
        self.register_at_authorizer_service()

    def create_finmars_bot(self):

        from django.contrib.auth.models import User

        try:

            user = User.objects.get(username='finmars_bot')

        except Exception as e:

            user = User.objects.create(username='finmars_bot')


        try:
            from poms.users.models import Member
            member = Member.objects.get(user__username='finmars_bot')
        except Exception as e:
            _l.info("Member not found, going to create it")

            from poms.users.models import MasterUser
            master_user = MasterUser.objects.get(base_api_url=settings.BASE_API_URL)

            member = Member.objects.create(user=user, master_user=master_user)

        _l.info("Finmars bot created")

    def add_view_and_manage_permissions(self):
        from poms.common.utils import add_view_and_manage_permissions
        add_view_and_manage_permissions()

    def load_master_user_data(self):

        from django.contrib.auth.models import User
        from poms.users.models import Member, MasterUser, Group, UserProfile

        try:
            _l.info("load_master_user_data processing")

            headers = {'Content-type': 'application/json', 'Accept': 'application/json'}

            data = {
                "base_api_url": settings.BASE_API_URL,
            }

            url = settings.AUTHORIZER_URL + '/backend-master-user-data/'

            _l.info("load_master_user_data url %s" % url)

            response = requests.post(url=url, data=json.dumps(data), headers=headers, verify=settings.VERIFY_SSL)

            _l.info(
                "load_master_user_data  response.status_code %s" % response.status_code)
            _l.info("load_master_user_data response.text %s" % response.text)

            response_data = response.json()

            name = response_data['name']

            user = None

            try:
                user = User.objects.get(username=response_data['owner']['username'])

                _l.info("Owner exists")

            except User.DoesNotExist:

                try:

                    from poms.auth_tokens.utils import generate_random_string
                    password = generate_random_string(10)

                    user = User.objects.create(email=response_data['owner']['email'],
                                               username=response_data['owner']['username'], password=password)
                    user.save()

                    _l.info("Create owner %s" % response_data['owner']['username'])

                except Exception as e:
                    _l.info("Create user error %s" % e)

            if user:
                user_profile, created = UserProfile.objects.get_or_create(user_id=user.pk)

                _l.info("Owner User Profile Updated")

                user_profile.save()

            try:
                if 'old_backup_name' in response_data and response_data['old_backup_name']:
                    # If From backup
                    master_user = MasterUser.objects.get(name=response_data['old_backup_name'])

                    master_user.name = name
                    master_user.base_api_url = response_data['base_api_url']

                    master_user.save()

                    _l.info("Master User From Backup Renamed to new Name %s and Base API URL %s" % (master_user.name, master_user.base_api_url))
                    # Member.objects.filter(is_owner=False).delete()

            except Exception as e:
                _l.error("Old backup name error %s" % e)

            if MasterUser.objects.all().count() == 0:
                _l.info("Empty database, create new master user")

                master_user = MasterUser.objects.create_master_user(
                    user=user,
                    language='en', name=name)

                master_user.base_api_url = response_data['base_api_url']

                master_user.save()

                _l.info("Master user with name %s and base_api_url %s created" % (master_user.name, master_user.base_api_url))

                member = Member.objects.create(user=user, master_user=master_user, is_owner=True, is_admin=True)
                member.save()

                _l.info("Owner Member created")

                admin_group = Group.objects.get(master_user=master_user, role=Group.ADMIN)
                admin_group.members.add(member.id)
                admin_group.save()

                _l.info("Admin Group Created")


        except Exception as e:
            _l.error("load_master_user_data error %s" % e)
            _l.error("load_master_user_data traceback %s" % traceback.format_exc())

    def register_at_authorizer_service(self):

        try:
            _l.info("register_at_authorizer_service processing")

            headers = {'Content-type': 'application/json', 'Accept': 'application/json'}

            data = {
                "base_api_url": settings.BASE_API_URL,
            }

            url = settings.AUTHORIZER_URL + '/backend-is-ready/'

            _l.info("register_at_authorizer_service url %s" % url)

            response = requests.post(url=url, data=json.dumps(data), headers=headers, verify=settings.VERIFY_SSL)

            _l.info(
                "register_at_authorizer_service backend-is-ready response.status_code %s" % response.status_code)
            _l.info("register_at_authorizer_service backend-is-ready response.text %s" % response.text)

        except Exception as e:
            _l.info("register_at_authorizer_service error %s" % e)

    def sync_users_at_authorizer_service(self):

        from django.contrib.auth.models import User

        from poms.users.models import Member, MasterUser

        try:
            _l.info("sync_users_at_authorizer_service processing")

            headers = {'Content-type': 'application/json', 'Accept': 'application/json'}

            data = {
                "base_api_url": settings.BASE_API_URL,
            }

            try:

                url = settings.AUTHORIZER_URL + '/backend-sync-users/'

                response = requests.post(url=url, data=json.dumps(data), headers=headers, verify=settings.VERIFY_SSL)
                _l.info(
                    "sync_users_at_authorizer_service backend-sync-users response.status_code %s" % response.status_code)
                # _l.info("sync_users_at_authorizer_service backend-sync-users response.text %s" % response.text)

                response_data = response.json()

                members = response_data['members']

                master_user = MasterUser.objects.all()[0]

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

                        _member = Member.objects.get(user=user, master_user=master_user)

                        _member.is_owner = member['is_owner']
                        _member.is_admin = member['is_admin']
                        _member.save()

                    except Exception as e:

                        _member = Member.objects.create(user=user,
                                                        username=member['username'],
                                                        master_user=master_user,
                                                        is_owner=member['is_owner'],
                                                        is_admin=member['is_admin'])

                        _l.info("Member %s created " % member['username'])

            except Exception as e:
                _l.error("Could not sync users %s" % e)


        except Exception as e:
            _l.info("sync_users_at_authorizer_service error %s" % e)

    def load_init_configuration(self):
        from poms.users.models import Member, MasterUser
        from poms.celery_tasks.models import CeleryTask
        from django.db import transaction
        from poms.configuration_import.tasks import configuration_import_as_json

        try:
            _l.info("load_init_configuration processing")

            headers = {'Content-type': 'application/json', 'Accept': 'application/json'}

            try:

                url = settings.AUTHORIZER_URL + '/backend-get-init-configuration/'

                response = requests.get(url=url, headers=headers, verify=settings.VERIFY_SSL)
                _l.info("load_init_configuration backend-sync-users response.status_code %s" % response.status_code)
                # _l.info("sync_users_at_authorizer_service backend-sync-users response.text %s" % response.text)

                response_data = response.json()

                master_user = MasterUser.objects.filter()[0]
                member = Member.objects.get(master_user=master_user, is_owner=True)

                celery_task = CeleryTask.objects.create(master_user=master_user,
                                                        member=member,
                                                        verbose_name="Inital Finmars Configuration Import",
                                                        type='configuration_import')

                options_object = {
                    'data': response_data['data'],
                    'mode': 'skip'
                }

                celery_task.options_object = options_object
                celery_task.save()

                transaction.on_commit(
                    lambda: configuration_import_as_json.apply_async(kwargs={'task_id': celery_task.id}))



            except Exception as e:
                _l.error("Could not init configuration %s" % e)


        except Exception as e:
            _l.info("load_init_configuration error %s" % e)

    def create_base_folders(self):

        try:

            from poms.common.storage import get_storage
            from tempfile import NamedTemporaryFile
            storage = get_storage()
            from poms_app import settings
            from poms.users.models import Member

            _l.info("create base folders if not exists")


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

            if not storage.exists(settings.BASE_API_URL + '/workflows/.init'):
                path = settings.BASE_API_URL + '/workflows/.init'

                with NamedTemporaryFile() as tmpf:
                    tmpf.write(b'')
                    tmpf.flush()
                    storage.save(path, tmpf)

                    _l.info("create workflows folder")

            if not storage.exists(settings.BASE_API_URL + '/workflows/schemas/.init'):
                path = settings.BASE_API_URL + '/workflows/schemas/.init'

                with NamedTemporaryFile() as tmpf:
                    tmpf.write(b'')
                    tmpf.flush()
                    storage.save(path, tmpf)

                    _l.info("create workflows schemas folder")

            if not storage.exists(settings.BASE_API_URL + '/workflows/tasks/.init'):
                path = settings.BASE_API_URL + '/workflows/tasks/.init'

                with NamedTemporaryFile() as tmpf:
                    tmpf.write(b'')
                    tmpf.flush()
                    storage.save(path, tmpf)

                    _l.info("create workflows tasks folder")

            members = Member.objects.all()

            for member in members:

                if not storage.exists(settings.BASE_API_URL + '/' + member.username + '/.init'):
                    path = settings.BASE_API_URL + '/' + member.username + '/.init'

                    with NamedTemporaryFile() as tmpf:
                        tmpf.write(b'')
                        tmpf.flush()
                        storage.save(path, tmpf)

        except Exception as e:
            _l.info("create_base_folders error %s" % e)
            _l.info("create_base_folders traceback %s" % traceback.format_exc())
