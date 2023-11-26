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
        In idea it should be the first methods that should be executed on backend server startup

        :param app_config:
        :param verbosity:
        :param using:
        :param kwargs:
        :return:
        """

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

        user = User.objects.get_or_create(username="finmars_bot")

        try:
            _ = Member.objects.get(user__username="finmars_bot")
            _l.info("finmars_bot already exists")

        except Member.DoesNotExist:
            _l.info("Member not found, going to create it")
            try:
                master_user = MasterUser.objects.get(base_api_url=settings.BASE_API_URL)

                _ = Member.objects.create(
                    user=user,
                    username="finmars_bot",
                    master_user=master_user,
                    is_admin=True,
                )

            except MasterUser.DoesNotExist as e:
                err_msg = (
                    f"Could not create finmars_bot {repr(e)} no master_user for "
                    f"base_api_url={settings.BASE_API_URL}"
                )
                _l.error(err_msg)
                raise RuntimeError(err_msg) from e

        _l.info("finmars_bot created")

    def create_iam_access_policies_templates(self):
        from poms.iam.policy_generator import create_base_iam_access_policies_templates

        if "test" not in sys.argv:
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
            print("Attention! AUTHORIZER_URL is not defined!")
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
                f"load_master_user_data  response.status_code "
                f"{response.status_code} response.text {response.text}"
            )

            response_data = response.json()

            name = response_data["name"]

            try:
                user = User.objects.get(username=response_data["owner"]["username"])

                _l.info("Owner exists")

            except User.DoesNotExist:
                password = generate_random_string(10)
                try:
                    user = User.objects.create(
                        email=response_data["owner"]["email"],
                        username=response_data["owner"]["username"],
                        password=password,
                    )
                    user.save()

                except Exception as e:
                    err_msg = f"Create user error {repr(e)}"
                    _l.info(err_msg)
                    raise RuntimeError(err_msg) from e

            _l.info(f'Create owner {response_data["owner"]["username"]}')

            user_profile, created = UserProfile.objects.get_or_create(user_id=user.pk)

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
                        f"Master User From Backup Renamed to new Name "
                        f"{master_user.name} and "
                        f"Base API URL {master_user.base_api_url}"
                    )
                    # Member.objects.filter(is_owner=False).delete()

            except MasterUser.DoesNotExist as e:
                _l.error(
                    f"Old backup name {response_data['old_backup_name']} "
                    f"error {repr(e)}"
                )

            if not MasterUser.objects.all():
                _l.info("Empty database, create new master user")

                master_user = MasterUser.objects.create_master_user(
                    user=user, language="en", name=name
                )

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

                # admin_group = Group.objects.get(master_user=master_user, role=Group.ADMIN)
                # admin_group.members.add(member.id)
                # admin_group.save()

                _l.info("Admin Group Created")

            master_user = MasterUser.objects.all().first()
            try:
                # TODO, carefull if someday return to multi master user inside one db

                master_user.base_api_url = settings.BASE_API_URL
                master_user.save()

                _l.info("Master User base_api_url synced")

            except Exception as e:
                _l.error(f"Could not sync base_api_url {e}")
                raise e

            try:
                current_owner_member = Member.objects.get(
                    username=response_data["owner"]["username"], master_user=master_user
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

        try:
            _l.info("register_at_authorizer_service processing")

            headers = {"Content-type": "application/json", "Accept": "application/json"}

            data = {
                "base_api_url": settings.BASE_API_URL,
            }

            url = settings.AUTHORIZER_URL + "/backend-is-ready/"

            _l.info("register_at_authorizer_service url %s" % url)

            response = requests.post(
                url=url,
                data=json.dumps(data),
                headers=headers,
                verify=settings.VERIFY_SSL,
            )

            _l.info(
                "register_at_authorizer_service backend-is-ready response.status_code %s"
                % response.status_code
            )
            _l.info(
                "register_at_authorizer_service backend-is-ready response.text %s"
                % response.text
            )

        except Exception as e:
            _l.info(f"register_at_authorizer_service error {e}")

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
        from poms.ui.models import MemberLayout
        from poms.users.models import Member

        members = Member.objects.all()

        from poms.configuration.utils import get_default_configuration_code

        configuration_code = get_default_configuration_code()

        for member in members:
            try:
                layout = MemberLayout.objects.get(
                    member=member,
                    configuration_code=configuration_code,
                    user_code=f"{configuration_code}:default_member_layout",
                )
            except Exception as e:
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

                except Exception as e:
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
                    self._extracted_from_create_base_folders_19(tmpf, storage, path)
                    _l.info("create .system folder")

            if not storage.exists(f"{settings.BASE_API_URL}/.system/tmp/.init"):
                path = f"{settings.BASE_API_URL}/.system/tmp/.init"

                with NamedTemporaryFile() as tmpf:
                    self._extracted_from_create_base_folders_19(tmpf, storage, path)
                    _l.info("create .system/tmp folder")

            if not storage.exists(f"{settings.BASE_API_URL}/.system/log/.init"):
                path = f"{settings.BASE_API_URL}/.system/log/.init"

                with NamedTemporaryFile() as tmpf:
                    self._extracted_from_create_base_folders_19(tmpf, storage, path)
                    _l.info("create system log folder")

            if not storage.exists(
                f"{settings.BASE_API_URL}/.system/new-member-setup-configurations/.init"
            ):
                path = (
                    settings.BASE_API_URL
                    + "/.system/new-member-setup-configurations/.init"
                )

                with NamedTemporaryFile() as tmpf:
                    self._extracted_from_create_base_folders_19(tmpf, storage, path)
                    _l.info("create system new-member-setup-configurations folder")

            if not storage.exists(f"{settings.BASE_API_URL}/public/.init"):
                path = f"{settings.BASE_API_URL}/public/.init"

                with NamedTemporaryFile() as tmpf:
                    self._extracted_from_create_base_folders_19(tmpf, storage, path)
                    _l.info("create public folder")

            if not storage.exists(f"{settings.BASE_API_URL}/configurations/.init"):
                path = f"{settings.BASE_API_URL}/configurations/.init"

                with NamedTemporaryFile() as tmpf:
                    self._extracted_from_create_base_folders_19(tmpf, storage, path)
                    _l.info("create configurations folder")

            if not storage.exists(f"{settings.BASE_API_URL}/workflows/.init"):
                path = f"{settings.BASE_API_URL}/workflows/.init"

                with NamedTemporaryFile() as tmpf:
                    self._extracted_from_create_base_folders_19(tmpf, storage, path)
                    _l.info("create workflows folder")

            members = Member.objects.all()

            for member in members:
                if not storage.exists(
                    f"{settings.BASE_API_URL}/{member.username}/.init"
                ):
                    path = f"{settings.BASE_API_URL}/{member.username}/.init"

                    with NamedTemporaryFile() as tmpf:
                        self._extracted_from_create_base_folders_19(tmpf, storage, path)
        except Exception as e:
            _l.info(f"create_base_folders error {e} traceback {traceback.format_exc()}")

    # TODO Rename this here and in `create_base_folders`
    def _extracted_from_create_base_folders_19(self, tmpf, storage, path):
        tmpf.write(b"")
        tmpf.flush()
        storage.save(path, tmpf)

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
