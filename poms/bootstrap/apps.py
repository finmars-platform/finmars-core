import json
import logging
import os
import sys
import time
import traceback

import psutil
import requests
from django.apps import AppConfig
from django.conf import settings
from django.db import DEFAULT_DB_ALIAS
from django.db import connection
from django.db.models import Q
from django.db.models.signals import post_migrate
from django.utils.translation import gettext_lazy

from poms.common.exceptions import FinmarsBaseException

_l = logging.getLogger("provision")

HEADERS = {
    "Content-type": "application/json",
    "Accept": "application/json",
}
FINMARS_BOT = "finmars_bot"


class BootstrapError(FinmarsBaseException):
    ...


def get_current_search_path():
    with connection.cursor() as cursor:
        cursor.execute("SHOW search_path;")
        search_path = cursor.fetchone()
        return search_path[0] if search_path else None


class BootstrapConfig(AppConfig):
    name = "poms.bootstrap"
    verbose_name = gettext_lazy("Bootstrap")

    def get_gunicorn_memory_usage(self):
        total_memory = 0
        for proc in psutil.process_iter(['cmdline', 'memory_info']):
            try:
                # Check if this is a Gunicorn worker process
                name = ' '.join(proc.cmdline())
                # if 'gunicorn' in name or 'runserver' in name:
                if 'gunicorn' in name:
                    total_memory += proc.info['memory_info'].rss
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass  # Process terminated or access denied
        _l.info(f"Total Memory Usage by Gunicorn Workers: {total_memory / 1024 ** 2:.2f} MB")

    def ready(self):

        _l.info("bootstrap: Bootstrapping Finmars Application")

        if settings.PROFILER:
            _l.info("bootstrap:Profiler enabled")

        if settings.SERVER_TYPE == "local":
            _l.info("bootstrap: LOCAL development. CORS disabled")

        if settings.SEND_LOGS_TO_FINMARS:
            _l.info("bootstrap: Logs will be sending to Finmars")

        post_migrate.connect(self.bootstrap, sender=self)

        _l.info("bootstrap: Finmars Application is running 💚")

        self.get_gunicorn_memory_usage()

        gunicorn_start_time = os.environ.get('GUNICORN_START_TIME')
        if gunicorn_start_time:
            gunicorn_start_time = float(gunicorn_start_time)
            ready_time = time.time()
            startup_duration = ready_time - gunicorn_start_time
            _l.info(
                "Finmars bootstrap time: %s"
                % "{:3.3f}".format(startup_duration)
            )

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

        current_space_code = get_current_search_path()

        _l.info("bootstrap: Current search path: %s" % current_space_code)

        # Do not disable bootstrap code, it's important to be executed on every startup
        if "test" not in sys.argv and 'public' not in current_space_code:

            try:
                self.sync_space_data()
                self.create_finmars_bot()
                self.create_local_configuration()
                self.add_view_and_manage_permissions()
                self.create_member_layouts()
                self.create_base_folders()
                # self.register_at_authorizer_service()
                # self.sync_celery_workers() # TODO temporary not needed, think in 1.7.0?
                self.create_iam_access_policies_templates()
            except Exception as e:
                _l.error(f"bootstrap: failed for {current_space_code} due to {repr(e)}")

    @staticmethod
    def create_finmars_bot():
        from django.contrib.auth.models import User
        from poms.users.models import MasterUser, Member

        log = "create_finmars_bot"

        finmars_user, created_user = User.objects.using(
            settings.DB_DEFAULT,
        ).get_or_create(
            username=FINMARS_BOT,
        )

        master_user = MasterUser.objects.using(settings.DB_DEFAULT).all().first()
        if not master_user:
            err_msg = f"{log} no master_user exists"
            _l.error(err_msg)
            raise BootstrapError("fatal", message=err_msg)

        finmars_bot, created_bot = Member.objects.using(
            settings.DB_DEFAULT,
        ).get_or_create(
            username=FINMARS_BOT,
            defaults={
                "user": finmars_user,
                "master_user": master_user,
                "is_admin": True,
            }
        )
        if not created_bot:
            finmars_bot.user = finmars_user
            finmars_bot.master_user = master_user
            finmars_bot.is_admin = True
            finmars_bot.save()

        _l.info(
            f"{log} for master_user {master_user.space_code} finmars_user "
            f"'{FINMARS_BOT}' {'created' if created_user else 'exists'} "
            f"and '{FINMARS_BOT}' member {'created' if created_bot else 'updated'}"
        )

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
    def deactivate_old_members():
        from poms.users.models import Member

        log = "deactivate_old_members"

        try:
            old_members = list(
                Member.objects.exclude(
                    Q(is_owner=True) |
                    Q(status=Member.STATUS_DELETED) |
                    Q(username="finmars_bot")
                )
            )
            total_count = len(old_members)

            _l.info(f"{log} found {total_count} old members")

            count = 0
            for member in old_members:
                member.status = Member.STATUS_DELETED
                member.save()
                count += 1

            _l.info(f"{log} {count}/{total_count} members deactivated")

        except Exception as e:
            _l.error(f"{log} failed due to {repr(e)}")

    @staticmethod
    def sync_space_data():
        from django.contrib.auth.models import User

        from poms.auth_tokens.utils import generate_random_string
        from poms.users.models import MasterUser, Member, UserProfile

        log = "sync_space_data"

        if not settings.AUTHORIZER_URL:
            _l.info(f"{log} exited, AUTHORIZER_URL is not defined")
            return

        current_space_code = get_current_search_path()

        # Probably its a Legacy space
        # Remove that in 1.9.0
        if 'public' in current_space_code:
            current_space_code = settings.BASE_API_URL

        data = {
                "base_api_url": current_space_code,
                "space_code": current_space_code,
                "realm_code": settings.REALM_CODE
                }
        # url = f"{settings.AUTHORIZER_URL}/backend-master-user-data/"
        url = f"{settings.AUTHORIZER_URL}/api/v2/space/sync/"

        _l.info(
            f"{log} started, calling api '/space/sync/' "
            f"with url={url} data={data}"
        )

        try:
            response = requests.post(
                url=url,
                data=json.dumps(data),
                headers=HEADERS,
                verify=settings.VERIFY_SSL,
            )

            _l.info(
                f"{log} api '/space/sync/' responded with "
                f"status_code={response.status_code} text={response.text}"
            )

            response.raise_for_status()
            response_data = response.json()

            owner_username = response_data["owner"]["username"]
            owner_email = response_data["owner"]["email"]
            master_user_name = response_data["name"]
            backend_status = response_data["status"]
            old_backup_name = response_data.get("old_backup_name")

            base_api_url = response_data["base_api_url"]

            # Probably its a Legacy space
            # Remove that in 1.9.0
            if 'public' in current_space_code:
                current_space_code = settings.BASE_API_URL

            if base_api_url != current_space_code:
                raise ValueError(
                    f"received {base_api_url} != expected {current_space_code}"
                )

        except Exception as e:
            err_msg = f"{log} call to 'backend-master-user-data' resulted in {repr(e)}"
            _l.error(err_msg)
            raise BootstrapError("fatal", message=err_msg) from e

        try:
            user, created = User.objects.using(settings.DB_DEFAULT).get_or_create(
                username=owner_username,
                defaults=dict(
                    email=owner_email,
                    password=generate_random_string(10),
                )
            )
            _l.info(f"{log} owner {owner_username} {'created' if created else 'exists'}")

            user_profile, created = UserProfile.objects.using(
                settings.DB_DEFAULT
            ).get_or_create(user_id=user.pk)
            _l.info(f"{log} owner's user_profile {'created' if created else 'exists'}")

            if backend_status == 0:
                # status is initial (0), remove old members from workspace
                BootstrapConfig.deactivate_old_members()
            else:
                _l.info(
                    f"{log} backend_status={backend_status} "
                    f"no need to deactivate old members"
                )

            master_user = MasterUser.objects.using(settings.DB_DEFAULT).first()

            if master_user:
                _l.info(
                    f"{log} master_user with name {master_user.name} and "
                    f"base_api_url {master_user.space_code} exists"
                )

                master_user.name = master_user_name
                master_user.space_code = base_api_url
                master_user.realm_code = settings.REALM_CODE
                master_user.save()

                if master_user.name == old_backup_name:
                    # check if restored from backup
                    BootstrapConfig.deactivate_old_members()

                    _l.info(
                        f"{log} master_user from backup {old_backup_name} renamed to "
                        f"{master_user.name} & base_api_url {master_user.space_code}"
                    )

            else:
                master_user = MasterUser.objects.create_master_user(
                    name=master_user_name,
                    space_code=base_api_url,
                    realm_code=settings.REALM_CODE
                )

                _l.info(
                    f"{log} created master_user with name {master_user.name} & "
                    f"base_api_url {master_user.space_code}"
                )

            current_owner_member, created = Member.objects.using(
                settings.DB_DEFAULT,
            ).get_or_create(
                username=owner_username,
                master_user=master_user,
                defaults=dict(
                    user=user,
                    is_owner=True,
                    is_admin=True,
                ),
            )
            if not created:
                current_owner_member.user = user
                current_owner_member.is_owner = True
                current_owner_member.is_admin = True
                current_owner_member.is_deleted = False
                current_owner_member.status = Member.STATUS_ACTIVE
                current_owner_member.save()
            Member.objects.exclude(user=user).update(is_owner=False)

            _l.info(
                f"{log} current_owner_member with username {owner_username} and master"
                f"_user.name {master_user.name} {'created' if created else 'exists'}"
            )
        except Exception as e:
            err_msg = f"{log} resulted in {repr(e)}"
            _l.error(f"{err_msg} trace {traceback.format_exc()}")
            raise BootstrapError("fatal", message=err_msg) from e

        else:
            _l.info(f"{log} successfully finished")

    # Deprecated
    # @staticmethod
    # def register_at_authorizer_service():
    #     if not settings.AUTHORIZER_URL:
    #         return
    #
    #     current_space_code = get_current_search_path()
    #
    #     # Probably its a Legacy space
    #     # Remove that in 1.9.0
    #     if 'public' in current_space_code:
    #         current_space_code = settings.BASE_API_URL
    #
    #     data = {"base_api_url": current_space_code,
    #             "space_code": current_space_code,
    #             "realm_code": settings.REALM_CODE
    #             }
    #     url = f"{settings.AUTHORIZER_URL}/backend-is-ready/"
    #
    #     _l.info(f"register_at_authorizer_service with url={url} data={data}")
    #
    #     try:
    #         response = requests.post(
    #             url=url,
    #             data=json.dumps(data),
    #             headers=HEADERS,
    #             verify=settings.VERIFY_SSL,
    #         )
    #         _l.info(
    #             f"register_at_authorizer_service backend-is-ready api response: "
    #             f"status_code={response.status_code} text={response.text}"
    #         )
    #
    #         response.raise_for_status()
    #
    #     except Exception as e:
    #         err_msg = f"register_at_authorizer_service resulted in {repr(e)}"
    #         _l.error(err_msg)
    #         raise BootstrapError("fatal", message=err_msg) from e

    # Creating worker in case if deployment is missing (e.g. from backup?)
    @staticmethod
    def sync_celery_workers():
        from poms.celery_tasks.models import CeleryWorker
        from poms.common.finmars_authorizer import AuthorizerService

        if not settings.AUTHORIZER_URL:
            return

        _l.info("sync_celery_workers processing")

        authorizer_service = AuthorizerService()

        workers = CeleryWorker.objects.using(settings.DB_DEFAULT).all()

        from poms.users.models import MasterUser
        master_user = MasterUser.objects.using(settings.DB_DEFAULT).all().first()

        for worker in workers:
            try:
                worker_status = authorizer_service.get_worker_status(worker,
                                                                     realm_code=master_user.realm_code,
                                                                     space_code=master_user.space_code)

                if worker_status["status"] == "not_found":
                    authorizer_service.create_worker(worker, realm_code=master_user.realm_code)
            except Exception as e:
                err_msg = f"sync_celery_workers: worker {worker} error {repr(e)}"
                _l.error(err_msg)
                # Starting worker is not fatal error
                # TODO refactor later?
                # szhitenev 2024-03-24
                # raise BootstrapError("fatal", message=err_msg) from e

    @staticmethod
    def create_member_layouts():
        # TODO wtf is default member layout?
        from poms.configuration.utils import get_default_configuration_code
        from poms.ui.models import MemberLayout
        from poms.users.models import Member

        members = Member.objects.using(settings.DB_DEFAULT).all()

        configuration_code = get_default_configuration_code()

        _l.info('create_member_layouts.configuration_code %s' % configuration_code)

        for member in members:

            layouts = MemberLayout.objects.using(settings.DB_DEFAULT).filter(
                member=member,
                configuration_code=configuration_code,
                user_code=f"{configuration_code}:default_member_layout",
            )

            if not len(layouts):
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

                except Exception as e:
                    err_msg = f"Could not create member layout {member.username}"
                    _l.error(err_msg)
                    raise BootstrapError("fatal", message=err_msg) from e

                _l.info(f"create_member_layouts.created_member_layout_for: {member.username}")

    def create_base_folders(self):
        from tempfile import NamedTemporaryFile

        from poms.common.storage import get_storage
        from poms.users.models import Member
        from poms_app import settings

        from poms.users.models import MasterUser
        master_user = MasterUser.objects.using(settings.DB_DEFAULT).all().first()

        try:
            storage = get_storage()
            if not storage:
                return

            _l.info("create base folders if not exists")

            if not storage.exists(f"{master_user.space_code}/.system/.init"):
                path = f"{master_user.space_code}/.system/.init"

                with NamedTemporaryFile() as tmpf:
                    self._save_tmp_to_storage(tmpf, storage, path)
                    _l.info("create .system folder")

            if not storage.exists(f"{master_user.space_code}/.system/tmp/.init"):
                path = f"{master_user.space_code}/.system/tmp/.init"

                with NamedTemporaryFile() as tmpf:
                    self._save_tmp_to_storage(tmpf, storage, path)
                    _l.info("create .system/tmp folder")

            if not storage.exists(f"{master_user.space_code}/.system/log/.init"):
                path = f"{master_user.space_code}/.system/log/.init"

                with NamedTemporaryFile() as tmpf:
                    self._save_tmp_to_storage(tmpf, storage, path)
                    _l.info("create system log folder")

            if not storage.exists(
                    f"{master_user.space_code}/.system/new-member-setup-configurations/.init"
            ):
                path = (
                        master_user.space_code
                        + "/.system/new-member-setup-configurations/.init"
                )

                with NamedTemporaryFile() as tmpf:
                    self._save_tmp_to_storage(tmpf, storage, path)
                    _l.info("create system new-member-setup-configurations folder")

            if not storage.exists(f"{master_user.space_code}/public/.init"):
                path = f"{master_user.space_code}/public/.init"

                with NamedTemporaryFile() as tmpf:
                    self._save_tmp_to_storage(tmpf, storage, path)
                    _l.info("create public folder")

            if not storage.exists(f"{master_user.space_code}/configurations/.init"):
                path = f"{master_user.space_code}/configurations/.init"

                with NamedTemporaryFile() as tmpf:
                    self._save_tmp_to_storage(tmpf, storage, path)
                    _l.info("create configurations folder")

            if not storage.exists(f"{master_user.space_code}/workflows/.init"):
                path = f"{master_user.space_code}/workflows/.init"

                with NamedTemporaryFile() as tmpf:
                    self._save_tmp_to_storage(tmpf, storage, path)
                    _l.info("create workflows folder")

            members = Member.objects.using(settings.DB_DEFAULT).all()

            for member in members:
                if not storage.exists(
                        f"{master_user.space_code}/{member.username}/.init"
                ):
                    path = f"{master_user.space_code}/{member.username}/.init"

                    with NamedTemporaryFile() as tmpf:
                        self._save_tmp_to_storage(tmpf, storage, path)

        except Exception as e:
            err_msg = f"create_base_folders error {repr(e)}"
            _l.error(f"{err_msg} trace {traceback.format_exc()}")
            raise BootstrapError("fatal", message=err_msg) from e

    @staticmethod
    def create_local_configuration():
        from poms.configuration.models import Configuration

        from poms.users.models import MasterUser
        master_user = MasterUser.objects.using(settings.DB_DEFAULT).all().first()

        configuration_code = f"local.poms.{master_user.space_code}"

        _, created = Configuration.objects.using(settings.DB_DEFAULT).get_or_create(
            configuration_code=configuration_code,
            defaults=dict(
                name="Local Configuration",
                is_primary=True,
                version="1.0.0",
                description="Local Configuration",
            )
        )
        _l.info(f"Local Configuration is already {'created' if created else 'exists'}")

    @staticmethod
    def _save_tmp_to_storage(tmpf, storage, path):
        tmpf.write(b"")
        tmpf.flush()
        storage.save(path, tmpf)
