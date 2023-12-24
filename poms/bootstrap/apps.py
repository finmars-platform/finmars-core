import json
import logging
import sys
import traceback

from django.apps import AppConfig
from django.db import DEFAULT_DB_ALIAS
from django.db.models.signals import post_migrate
from django.utils.translation import gettext_lazy

import requests

from poms_app import settings

_l = logging.getLogger("provision")


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
        if (
            "test" not in sys.argv
            and "makemigrations" not in sys.argv
            and "migrate" not in sys.argv
        ):
            self.create_local_configuration()
            self.add_view_and_manage_permissions()
            self.load_master_user_data()
            self.create_finmars_bot()
            self.create_member_layouts()
            self.create_base_folders()
            self.register_at_authorizer_service()
            self.sync_celery_workers()
            self.create_iam_access_policies_templates()

    def create_finmars_bot(self):
        from django.contrib.auth.models import User

        from poms.users.models import MasterUser, Member

        try:
            user = User.objects.get(username="finmars_bot")

        except Exception:
            user = User.objects.create(username="finmars_bot")

        try:
            member = Member.objects.get(user__username="finmars_bot")
            _l.info("finmars_bot already exists")

        except Exception:
            try:
                _l.info("Member not found, going to create it")

                master_user = MasterUser.objects.get(base_api_url=settings.BASE_API_URL)

                member = Member.objects.create(
                    user=user,
                    username="finmars_bot",
                    master_user=master_user,
                    is_admin=True,
                )

                _l.info("finmars_bot created")

            except Exception as e:
                _l.error(f"Warning. Could not create finmars_bot {e}")

    def create_iam_access_policies_templates(self):
        from poms.iam.policy_generator import create_base_iam_access_policies_templates

        _l.info("create_iam_access_policies_templates")

        create_base_iam_access_policies_templates()

        _l.info("create_iam_access_policies_templates done")

    # Probably deprecated
    def add_view_and_manage_permissions(self):
        from poms.common.utils import add_view_and_manage_permissions

        add_view_and_manage_permissions()

    def load_master_user_data(self):
        from django.contrib.auth.models import User

        from poms.auth_tokens.utils import generate_random_string
        from poms.users.models import MasterUser, Member, UserProfile

        if not settings.AUTHORIZER_URL:
            return

        try:
            _l.info("load_master_user_data processing")

            headers = {"Content-type": "application/json", "Accept": "application/json"}

            data = {
                "base_api_url": settings.BASE_API_URL,
            }

            url = f"{settings.AUTHORIZER_URL}/backend-master-user-data/"

            _l.info(f"load_master_user_data url {url}")

            response = requests.post(
                url=url,
                data=json.dumps(data),
                headers=headers,
                verify=settings.VERIFY_SSL,
            )

            _l.info(
                f"load_master_user_data  response.status_code {response.status_code} "
                f"response.text {response.text}"
            )

            response_data = response.json()

            name = response_data["name"]

            user = None

            try:
                user = User.objects.get(username=response_data["owner"]["username"])

                _l.info("Owner exists")

            except User.DoesNotExist:
                try:
                    password = generate_random_string(10)

                    user = User.objects.create(
                        email=response_data["owner"]["email"],
                        username=response_data["owner"]["username"],
                        password=password,
                    )
                    user.save()

                    _l.info(f'Create owner {response_data["owner"]["username"]}')

                except Exception as e:
                    _l.info(f"Create user error {e} traceback {traceback.format_exc()}")

            if user:
                user_profile, created = UserProfile.objects.using(
                    settings.DB_DEFAULT
                ).get_or_create(user_id=user.pk)

                _l.info("Owner User Profile Updated")

                user_profile.save()

            try:
                if (
                    "old_backup_name" in response_data
                    and response_data["old_backup_name"]
                ):
                    # If From backup
                    master_user = MasterUser.objects.get(
                        name=response_data["old_backup_name"]
                    )

                    master_user.name = name
                    master_user.base_api_url = response_data["base_api_url"]
                    master_user.save()

                    _l.info(
                        f"Master User From Backup Renamed to Name {master_user.name} "
                        f"and Base API URL {master_user.base_api_url}"
                    )

            except Exception as e:
                _l.error(f"Old backup name error {e}")

            if MasterUser.objects.all().count() == 0:
                _l.info("Empty database, create new master user")

                master_user = MasterUser.objects.using(
                    settings.DB_DEFAULT
                ).create_master_user(user=user, language="en", name=name)

                master_user.base_api_url = response_data["base_api_url"]

                master_user.save()

                _l.info(
                    f"Master user with name {master_user.name} and "
                    f"base_api_url {master_user.base_api_url} created"
                )

                member = Member.objects.create(
                    user=user,
                    username=user.username,
                    master_user=master_user,
                    is_owner=True,
                    is_admin=True,
                )
                member.save()

                _l.info("Owner Member created")

                _l.info("Admin Group Created")

            try:
                # TODO, carefull if someday return to multi master user inside one db
                master_user = MasterUser.objects.all().first()

                master_user.base_api_url = settings.BASE_API_URL
                master_user.save()

                _l.info("Master User base_api_url synced")

            except Exception as e:
                _l.error(f"Could not sync base_api_url {e}")
                raise e

            try:
                current_owner_member = Member.objects.get(
                    username=response_data["owner"]["username"],
                    master_user=master_user,
                )

                current_owner_member.is_owner = True
                current_owner_member.is_admin = True
                current_owner_member.save()

            except Exception as e:
                _l.error(f"Could not find current owner member {e} ")

                user = User.objects.get(username=response_data["owner"]["username"])

                current_owner_member = Member.objects.create(
                    username=response_data["owner"]["username"],
                    user=user,
                    master_user=master_user,
                    is_owner=True,
                    is_admin=True,
                )

        except Exception as e:
            _l.error(
                f"load_master_user_data error {e} traceback {traceback.format_exc()}"
            )

    def register_at_authorizer_service(self):
        if not settings.AUTHORIZER_URL:
            return

        _l.info("register_at_authorizer_service processing")

        headers = {"Content-type": "application/json", "Accept": "application/json"}
        data = {"base_api_url": settings.BASE_API_URL}
        url = f"{settings.AUTHORIZER_URL}/backend-is-ready/"

        _l.info(f"register_at_authorizer_service url {url} data {data}")

        try:
            response = requests.post(
                url=url,
                data=json.dumps(data),
                headers=headers,
                verify=settings.VERIFY_SSL,
            )

            _l.info(
                f"register_at_authorizer_service backend-is-ready response.status_code"
                f" {response.status_code} response.text {response.text}"
            )

            response.raise_for_status()

        except Exception as e:
            _l.info(
                f"register_at_authorizer_service error {repr(e)} "
                f"traceback {traceback.format_exc()}"
            )

    # Creating worker in case if deployment is missing (e.g. from backup?)
    def sync_celery_workers(self):
        from poms.celery_tasks.models import CeleryWorker
        from poms.common.finmars_authorizer import AuthorizerService

        if not settings.AUTHORIZER_URL:
            return

        try:
            _l.info("sync_celery_workers processing")

            authorizer_service = AuthorizerService()

            workers = CeleryWorker.objects.all()

            for worker in workers:
                try:
                    worker_status = authorizer_service.get_worker_status(worker)

                    if worker_status["status"] == "not_found":
                        authorizer_service.create_worker(worker)
                except Exception as e:
                    _l.error(f"sync_celery_workers: worker {worker} error {e}")

        except Exception as e:
            _l.info(f"sync_celery_workers error {e}")

    def create_member_layouts(self):
        # TODO wtf is default member layout?
        from poms.configuration.utils import get_default_configuration_code
        from poms.ui.models import MemberLayout
        from poms.users.models import Member

        members = Member.objects.all()

        configuration_code = get_default_configuration_code()

        for member in members:
            try:
                layout = MemberLayout.objects.get(
                    member=member,
                    configuration_code=configuration_code,
                    user_code=f"{configuration_code}:default_member_layout",
                )
            except Exception:
                try:
                    layout = MemberLayout.objects.create(
                        member=member,
                        owner=member,
                        is_default=True,
                        configuration_code=configuration_code,
                        name="default",
                        user_code="default_member_layout",
                    )  # configuration code will be added automatically
                    _l.info(f"Created member layout for {member.username}")
                except Exception:
                    _l.info("Could not create member layout" % member.username)

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

            members = Member.objects.all()

            for member in members:
                if not storage.exists(
                    f"{settings.BASE_API_URL}/{member.username}/.init"
                ):
                    path = f"{settings.BASE_API_URL}/{member.username}/.init"

                    with NamedTemporaryFile() as tmpf:
                        self._save_tmp_to_storage(tmpf, storage, path)

        except Exception as e:
            _l.info(f"create_base_folders error {e} traceback {traceback.format_exc()}")

    def create_local_configuration(self):
        from poms.configuration.models import Configuration

        configuration_code = f"local.poms.{settings.BASE_API_URL}"

        try:
            configuration = Configuration.objects.get(
                configuration_code=configuration_code
            )
            _l.info("Local Configuration is already created")
        except Configuration.DoesNotExist:
            Configuration.objects.create(
                configuration_code=configuration_code,
                name="Local Configuration",
                is_primary=True,
                version="1.0.0",
                description="Local Configuration",
            )

            _l.info("Local Configuration created")

    def _save_tmp_to_storage(self, tmpf, storage, path):
        tmpf.write(b"")
        tmpf.flush()
        storage.save(path, tmpf)
