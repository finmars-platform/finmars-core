import json
import logging
import os
import sys
import time
import traceback
import psutil

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
        _l.info(f"Total Memory Usage by Gunicorn Workers: {total_memory / 1024**2:.2f} MB")

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
        # Do not disable bootstrap code, it's important to be executed on every startup
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

        user, _ = User.objects.using(settings.DB_DEFAULT).get_or_create(
            username=FINMARS_BOT,
        )

        try:
            Member.objects.using(settings.DB_DEFAULT).get(username=FINMARS_BOT)
            _l.info(f"{FINMARS_BOT} member already exists")

        except Member.DoesNotExist:
            _l.info(f"Member {FINMARS_BOT} not found, going to create it")

            try:
                master_user = MasterUser.objects.using(settings.DB_DEFAULT).filter(
                    base_api_url=settings.BASE_API_URL
                ).first()
                if not master_user:
                    MasterUser.objects.using(settings.DB_DEFAULT).create_master_user(
                        user=user
                    )
                Member.objects.using(settings.DB_DEFAULT).create(
                    user=user,
                    username=FINMARS_BOT,
                    master_user=master_user,
                    is_admin=True,
                )

            except Exception as e:
                err_msg = f"Could not create {FINMARS_BOT} due to {repr(e)}"
                _l.error(f"{err_msg}", exc_info=True)
                raise RuntimeError(err_msg) from e

        _l.info(f"Member {FINMARS_BOT} created")

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

        try:
            old_members = Member.objects.filter(is_owner=False)
            old_members.update(is_deleted=True)
            marked_count = old_members.count()

        except Exception as e:
            _l.error(f"remove_old_members resulted in {repr(e)}")

        else:
            _l.info(f"remove_old_members {marked_count} members marked as deleted")

    @staticmethod
    def load_master_user_data():
        from django.contrib.auth.models import User

        from poms.auth_tokens.utils import generate_random_string
        from poms.users.models import MasterUser, Member, UserProfile

        log = "load_master_user_data"

        if not settings.AUTHORIZER_URL:
            _l.info(f"{log} exited, AUTHORIZER_URL is not defined")
            return

        data = {"base_api_url": settings.BASE_API_URL}
        url = f"{settings.AUTHORIZER_URL}/backend-master-user-data/"

        _l.info(
            f"{log} started, calling api 'backend-master-user-data' "
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
                f"{log} api 'backend-master-user-data' responded with "
                f"status_code={response.status_code} text={response.text}"
            )

            response.raise_for_status()
            response_data = response.json()

            username = response_data["owner"]["username"]
            owner_email = response_data["owner"]["email"]
            name = response_data["name"]
            backend_status = response_data["status"]
            old_backup_name = response_data.get("old_backup_name")

            base_api_url = response_data["base_api_url"]
            if base_api_url != settings.BASE_API_URL:
                raise ValueError(
                    f"received {base_api_url} != expected {settings.BASE_API_URL}"
                )

        except Exception as e:
            _l.error(f"{log} call to 'backend-master-user-data' resulted in {repr(e)}")
            raise RuntimeError(e) from e

        try:
            user, created = User.objects.using(settings.DB_DEFAULT).get_or_create(
                username=username,
                defaults=dict(
                    email=owner_email,
                    password=generate_random_string(10),
                )
            )
            _l.info(f"{log} owner {username} {'created' if created else 'exists'}")

            user_profile, created = UserProfile.objects.using(
                settings.DB_DEFAULT
            ).get_or_create(user_id=user.pk)
            _l.info(f"{log} owner's user_profile {'created' if created else 'exists'}")

            # if the status is initial (0), remove old members from workspace
            if backend_status == 0:
                BootstrapConfig.remove_old_members()

            master_user = None

            if old_backup_name:  # check if restored from backup
                master_user = MasterUser.objects.using(
                    settings.DB_DEFAULT,
                ).filter(
                    name=old_backup_name,
                ).first()

                if master_user:
                    master_user.name = name
                    master_user.base_api_url = base_api_url
                    master_user.save()

                    BootstrapConfig.remove_old_members()

                    _l.info(
                        f"{log} master_user from backup {old_backup_name} renamed to "
                        f"{master_user.name} & base_api_url {master_user.base_api_url}"
                    )

            if not master_user:
                _l.info(f"{log} create new master_user")

                master_user = MasterUser.objects.create_master_user(
                    name=name,
                    base_api_url=base_api_url,
                )

                _l.info(
                    f"{log} master_user with name {master_user.name} and "
                    f"base_api_url {master_user.base_api_url} created"
                )

            current_owner_member, created = Member.objects.using(
                settings.DB_DEFAULT,
            ).get_or_create(
                username=username,
                master_user=master_user,
            )
            current_owner_member.is_owner = True
            current_owner_member.is_admin = True
            current_owner_member.language = settings.LANGUAGE_CODE
            current_owner_member.save()

            _l.info(
                f"{log} current_owner_member with username {username} and master_user"
                f".name {master_user.name} {'created' if created else 'exists'}"
            )
        except Exception as e:
            err_msg = f"{log} resulted in {repr(e)}"
            _l.error(f"{err_msg} trace {traceback.format_exc()}")
            raise RuntimeError(err_msg) from e

        else:
            _l.info(f"{log} successfully finished")

    @staticmethod
    def register_at_authorizer_service():
        if not settings.AUTHORIZER_URL:
            return

        data = {"base_api_url": settings.BASE_API_URL}
        url = f"{settings.AUTHORIZER_URL}/backend-is-ready/"

        _l.info(f"register_at_authorizer_service with url={url} data={data}")

        try:
            response = requests.post(
                url=url,
                data=json.dumps(data),
                headers=HEADERS,
                verify=settings.VERIFY_SSL,
            )
            _l.info(
                f"register_at_authorizer_service backend-is-ready api response: "
                f"status_code={response.status_code} text={response.text}"
            )

            response.raise_for_status()

        except Exception as e:
            _l.info(f"register_at_authorizer_service resulted in {repr(e)}")
            raise e

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

        for worker in workers:
            try:
                worker_status = authorizer_service.get_worker_status(worker)

                if worker_status["status"] == "not_found":
                    authorizer_service.create_worker(worker)
            except Exception as e:
                _l.error(f"sync_celery_workers: worker {worker} error {repr(e)}")
                raise e

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
            except MemberLayout.DoesNotExist:
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
                    _l.info(f"Could not create member layout {member.username}")
                    raise e

            _l.info(f"Created member layout for {member.username}")

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
            _l.error(
                f"create_base_folders error {repr(e)} trace {traceback.format_exc()}"
            )

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
