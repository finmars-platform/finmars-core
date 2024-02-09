import json
import logging
import sys
import traceback

from django.apps import AppConfig
from django.conf import settings
from django.db import DEFAULT_DB_ALIAS
from django.db.models.signals import post_migrate
from django.utils.translation import gettext_lazy

import requests

_l = logging.getLogger("provision")

HEADERS = {
    "Content-type": "application/json",
    "Accept": "application/json",
}
FINMARS_BOT = "finmars_bot"


class BootstrapConfig(AppConfig):
    name = "poms.bootstrap"
    verbose_name = gettext_lazy("Bootstrap")

    def ready(self):
        _l.info("Bootstrapping Finmars Application")

        if settings.PROFILER:
            _l.info("Profiler enabled")

        if settings.SERVER_TYPE == "local":
            _l.info("LOCAL development. CORS disabled")

        if settings.SEND_LOGS_TO_FINMARS:
            _l.info("Logs will be sending to Finmars")

        _l.info(f"space_code: {settings.BASE_API_URL}")

        post_migrate.connect(self.bootstrap, sender=self)

        _l.info("Finmars Application is running 💚")

    def bootstrap(self, app_config, verbosity=2, using=DEFAULT_DB_ALIAS, **kwargs):
        """
        It should be the first methods that should be executed
        on backend server startup

        :param app_config:
        :param verbosity:
        :param using:
        :param kwargs:
        :return:
        """
        # Do not disable bootstrap code, its important to be executed on every startup
        if "test" not in sys.argv:
            self.create_local_configuration()
            self.add_view_and_manage_permissions()
            self.load_master_user_data()
            self.create_finmars_bot()
            self.create_member_layouts()
            self.create_base_folders()
            self.register_at_authorizer_service()
            self.sync_celery_workers()
            self.create_iam_access_policies_templates()

    @staticmethod
    def create_finmars_bot():
        from django.contrib.auth.models import User

        from poms.users.models import MasterUser, Member

        try:
            user = User.objects.using(settings.DB_DEFAULT).get(username=FINMARS_BOT)

        except Exception:
            user = User.objects.using(settings.DB_DEFAULT).create(username=FINMARS_BOT)

        try:
            Member.objects.using(settings.DB_DEFAULT).get(user__username=FINMARS_BOT)
            _l.info(f"{FINMARS_BOT} already exists")

        except Exception:
            try:
                _l.info("Member not found, going to create it")

                master_user = MasterUser.objects.using(settings.DB_DEFAULT).get(
                    base_api_url=settings.BASE_API_URL
                )

                Member.objects.using(settings.DB_DEFAULT).create(
                    user=user,
                    username=FINMARS_BOT,
                    master_user=master_user,
                    is_admin=True,
                )

                _l.info(f"{FINMARS_BOT} created")

            except Exception as e:
                _l.error(f"Warning. Could not create {FINMARS_BOT} {e}")

    @staticmethod
    def create_iam_access_policies_templates():
        from poms.iam.policy_generator import create_base_iam_access_policies_templates

        _l.info("create_iam_access_policies_templates")

        create_base_iam_access_policies_templates()

        _l.info("create_iam_access_policies_templates done")

    # Probably deprecated
    @staticmethod
    def add_view_and_manage_permissions():
        from poms.common.utils import add_view_and_manage_permissions

        add_view_and_manage_permissions()

    @staticmethod
    def remove_old_members():
        from poms.users.models import Member

        old_members = Member.objects.filter(is_owner=False)
        old_members.update(is_deleted=True)
        _l.info(f"{old_members.count()} old members were marked as deleted")

    @staticmethod
    def load_master_user_data():
        from django.contrib.auth.models import User

        from poms.auth_tokens.utils import generate_random_string
        from poms.users.models import MasterUser, Member, UserProfile

        if not settings.AUTHORIZER_URL:
            _l.info("load_master_user_data exited, AUTHORIZER_URL is not defined")
            return

        _l.info("load_master_user_data started ...")

        try:
            data = {"base_api_url": settings.BASE_API_URL}
            url = f"{settings.AUTHORIZER_URL}/backend-master-user-data/"

            _l.info(f"load_master_user_data url {url}")

            response = requests.post(
                url=url,
                data=json.dumps(data),
                headers=HEADERS,
                verify=settings.VERIFY_SSL,
            )

            _l.info(f"status_code={response.status_code} text={response.text}")

            response.raise_for_status()

            response_data = response.json()
            username = response_data["owner"]["username"]

            try:
                user = User.objects.using(settings.DB_DEFAULT).get(username=username)

                _l.info(f"Owner {username} exists")

            except User.DoesNotExist:
                try:
                    password = generate_random_string(10)
                    user = User.objects.using(settings.DB_DEFAULT).create(
                        email=response_data["owner"]["email"],
                        username=username,
                        password=password,
                    )
                    user.save()

                    _l.info(f'Create owner {response_data["owner"]["username"]}')

                except Exception as e:
                    _l.info(f"Create user error {e} trace {traceback.format_exc()}")
                    raise e

            user_profile, created = UserProfile.objects.using(
                settings.DB_DEFAULT
            ).get_or_create(user_id=user.pk)

            _l.info(f"Owner User Profile {'created' if created else 'exist'}")

            name = response_data["name"]

            # check if the status is initial (just created)
            if response_data["status"] == 0:
                BootstrapConfig.remove_old_members()

            if (  # check if restored from backup
                "old_backup_name" in response_data and response_data["old_backup_name"]
            ):
                try:
                    master_user = MasterUser.objects.using(settings.DB_DEFAULT).get(
                        name=response_data["old_backup_name"]
                    )
                    master_user.name = name
                    master_user.base_api_url = response_data["base_api_url"]
                    master_user.save()

                    BootstrapConfig.remove_old_members()

                    _l.info(
                        f"Master User From Backup Renamed to Name {master_user.name}"
                        f"and Base API URL {master_user.base_api_url}"
                    )

                except Exception as e:
                    _l.error(f"Old backup name error {repr(e)}")

            if MasterUser.objects.using(settings.DB_DEFAULT).all().count() == 0:
                _l.info("Empty database, create new master user")

                master_user = MasterUser.objects.create_master_user(
                    user=user,
                    language="en",
                    name=name,
                )

                master_user.base_api_url = response_data["base_api_url"]

                master_user.save()

                _l.info(
                    f"Master user with name {master_user.name} and "
                    f"base_api_url {master_user.base_api_url} created"
                )

                member = Member.objects.using(settings.DB_DEFAULT).create(
                    user=user,
                    username=username,
                    master_user=master_user,
                    is_owner=True,
                    is_admin=True,
                )
                member.save()

                _l.info("Owner Member & Admin Group created")

            try:
                # TODO, carefull if someday return to multi master user inside one db
                master_user = (
                    MasterUser.objects.using(settings.DB_DEFAULT).all().first()
                )
                master_user.base_api_url = settings.BASE_API_URL
                master_user.save()

                _l.info("Master User base_api_url synced")

            except Exception as e:
                _l.error(f"Could not sync base_api_url {e}")
                raise e

            try:
                current_owner_member = Member.objects.using(settings.DB_DEFAULT).get(
                    username=username,
                    master_user=master_user,
                )
                if (
                    not current_owner_member.is_owner
                    or not current_owner_member.is_admin
                ):
                    current_owner_member.is_owner = True
                    current_owner_member.is_admin = True
                    current_owner_member.save()

            except Exception as e:
                _l.error(f"Could not find current owner member {e} ")

                Member.objects.using(settings.DB_DEFAULT).create(
                    username=username,
                    user=user,
                    master_user=master_user,
                    is_owner=True,
                    is_admin=True,
                )

        except Exception as e:
            _l.error(
                f"load_master_user_data error {e} traceback {traceback.format_exc()}"
            )

        # Looks like tests itself create master user and other things
        # else:
        #     _l.info("load_master_user_data in test mode, creating temp master_user")
        #
        #     master_user = MasterUser.objects.create_master_user(
        #         language="en",
        #         name='Test Database',
        #     )
        #
        #     master_user.base_api_url = settings.BASE_API_URL;
        #
        #     master_user.save()
        #
        #     _l.info('load_master_user_data test mode: master_user %s created' % master_user)

    @staticmethod
    def register_at_authorizer_service():
        if not settings.AUTHORIZER_URL:
            return

        _l.info("register_at_authorizer_service processing")

        data = {
            "base_api_url": settings.BASE_API_URL,
        }
        url = f"{settings.AUTHORIZER_URL}/backend-is-ready/"

        _l.info(f"register_at_authorizer_service url {url}")

        try:
            response = requests.post(
                url=url,
                data=json.dumps(data),
                headers=HEADERS,
                verify=settings.VERIFY_SSL,
            )
            _l.info(
                f"register_at_authorizer_service backend-is-ready "
                f"response.status_code {response.status_code}"
                f"response.text {response.text}"
            )

            response.raise_for_status()

        except Exception as e:
            _l.info(
                f"register_at_authorizer_service error {repr(e)} "
                f"traceback {traceback.format_exc()}"
            )

    # Creating worker in case if deployment is missing (e.g. from backup?)
    @staticmethod
    def sync_celery_workers():
        from poms.celery_tasks.models import CeleryWorker
        from poms.common.finmars_authorizer import AuthorizerService

        if not settings.AUTHORIZER_URL:
            return

        try:
            _l.info("sync_celery_workers processing")

            authorizer_service = AuthorizerService()

            workers = CeleryWorker.objects.using(settings.DB_DEFAULT).all()

            for worker in workers:
                try:
                    worker_status = authorizer_service.get_worker_status(worker)

                    if worker_status["status"] == "not_found":
                        authorizer_service.create_worker(worker)
                except Exception as e:
                    _l.error(f"sync_celery_workers: worker {worker} error {e}")

        except Exception as e:
            _l.info(f"sync_celery_workers error {e}")

    @staticmethod
    def create_member_layouts():
        # TODO wtf is default member layout?
        from poms.configuration.utils import get_default_configuration_code
        from poms.ui.models import MemberLayout
        from poms.users.models import Member

        members = Member.objects.using(settings.DB_DEFAULT).all()

        configuration_code = get_default_configuration_code()

        for member in members:
            try:
                MemberLayout.objects.using(settings.DB_DEFAULT).get(
                    member=member,
                    configuration_code=configuration_code,
                    user_code=f"{configuration_code}:default_member_layout",
                )
            except Exception:
                try:
                    # configuration code will be added automatically
                    MemberLayout.objects.using(settings.DB_DEFAULT).create(
                        member=member,
                        owner=member,
                        is_default=True,
                        configuration_code=configuration_code,
                        name="default",
                        user_code="default_member_layout",
                    )
                    _l.info(f"Created member layout for {member.username}")

                except Exception:
                    _l.info(f"Could not create member layout {member.username}")

    def create_base_folders(self):
        from tempfile import NamedTemporaryFile

        from poms.common.storage import get_storage
        from poms.users.models import Member
        from poms_app import settings

        try:
            storage = get_storage()
            if not storage:
                return

            _l.info("create base folders if not exists")

            if not storage.exists(f"{settings.BASE_API_URL}/.system/.init"):
                path = f"{settings.BASE_API_URL}/.system/.init"

                with NamedTemporaryFile() as tmpf:
                    self._save_tmp_to_storage(tmpf, storage, path)
                    _l.info("create .system folder")

            if not storage.exists(f"{settings.BASE_API_URL}/.system/tmp/.init"):
                path = f"{settings.BASE_API_URL}/.system/tmp/.init"

                with NamedTemporaryFile() as tmpf:
                    self._save_tmp_to_storage(tmpf, storage, path)
                    _l.info("create .system/tmp folder")

            if not storage.exists(f"{settings.BASE_API_URL}/.system/log/.init"):
                path = f"{settings.BASE_API_URL}/.system/log/.init"

                with NamedTemporaryFile() as tmpf:
                    self._save_tmp_to_storage(tmpf, storage, path)
                    _l.info("create system log folder")

            if not storage.exists(
                f"{settings.BASE_API_URL}/.system/new-member-setup-configurations/.init"
            ):
                path = (
                    settings.BASE_API_URL
                    + "/.system/new-member-setup-configurations/.init"
                )

                with NamedTemporaryFile() as tmpf:
                    self._save_tmp_to_storage(tmpf, storage, path)
                    _l.info("create system new-member-setup-configurations folder")

            if not storage.exists(f"{settings.BASE_API_URL}/public/.init"):
                path = f"{settings.BASE_API_URL}/public/.init"

                with NamedTemporaryFile() as tmpf:
                    self._save_tmp_to_storage(tmpf, storage, path)
                    _l.info("create public folder")

            if not storage.exists(f"{settings.BASE_API_URL}/configurations/.init"):
                path = f"{settings.BASE_API_URL}/configurations/.init"

                with NamedTemporaryFile() as tmpf:
                    self._save_tmp_to_storage(tmpf, storage, path)
                    _l.info("create configurations folder")

            if not storage.exists(f"{settings.BASE_API_URL}/workflows/.init"):
                path = f"{settings.BASE_API_URL}/workflows/.init"

                with NamedTemporaryFile() as tmpf:
                    self._save_tmp_to_storage(tmpf, storage, path)
                    _l.info("create workflows folder")

            members = Member.objects.using(settings.DB_DEFAULT).all()

            for member in members:
                if not storage.exists(
                    f"{settings.BASE_API_URL}/{member.username}/.init"
                ):
                    path = f"{settings.BASE_API_URL}/{member.username}/.init"

                    with NamedTemporaryFile() as tmpf:
                        self._save_tmp_to_storage(tmpf, storage, path)

        except Exception as e:
            _l.info(f"create_base_folders error {e} traceback {traceback.format_exc()}")

    @staticmethod
    def create_local_configuration():
        from poms.configuration.models import Configuration

        configuration_code = f"local.poms.{settings.BASE_API_URL}"

        try:
            Configuration.objects.using(settings.DB_DEFAULT).get(
                configuration_code=configuration_code
            )
            _l.info("Local Configuration is already created")

        except Configuration.DoesNotExist:
            Configuration.objects.using(settings.DB_DEFAULT).create(
                configuration_code=configuration_code,
                name="Local Configuration",
                is_primary=True,
                version="1.0.0",
                description="Local Configuration",
            )

            _l.info("Local Configuration created")

    @staticmethod
    def _save_tmp_to_storage(tmpf, storage, path):
        tmpf.write(b"")
        tmpf.flush()
        storage.save(path, tmpf)
