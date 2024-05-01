import logging
import time

from django.conf import settings
from django.core.management.base import BaseCommand

_l = logging.getLogger("provision")


class Command(BaseCommand):
    help = "Install Initial Configuration"

    def handle(self, *args, **options):
        from poms.celery_tasks.models import CeleryTask
        from poms.configuration.tasks import install_package_from_marketplace
        from poms.users.models import MasterUser, Member
        from poms_app.celery import app as celery_app

        _l.info("Downloading init configuration")

        # Need to wait to ensure celery workers are available
        i = celery_app.control.inspect()

        max_retries = 20
        retry_count = 1

        while not i.stats() and retry_count < max_retries:
            _l.info(
                "Waiting for Celery worker(s) try %s/%s..." % (retry_count, max_retries)
            )
            time.sleep(5)
            retry_count = retry_count + 1

        if retry_count > max_retries:
            _l.info("Workers are unavailable, skip init install...")
            return

        _l.info("Celery worker(s) are now available.")

        if not settings.AUTHORIZER_URL:
            _l.error("Authorizer url is not set!")
            return

        _l.info("load_init_configuration processing")

        try:
            master_user = MasterUser.objects.filter()[0]
            member = Member.objects.get(username="finmars_bot")

            celery_task = CeleryTask.objects.create(
                master_user=master_user,
                member=member,
                verbose_name="Install Configuration From Marketplace",
                type="install_configuration_from_marketplace",
            )

            options_object = {
                "configuration_code": "com.finmars.initial",
                "version": "1.0.1",
                "channel": "stable",
                "is_package": True,
                # "access_token": get_access_token(request) TODO Implement when keycloak refactored
                # TODO check this later, important security thins, need to be destroyed inside task
            }
            celery_task.options_object = options_object
            celery_task.save()

            install_package_from_marketplace.apply_async(
                kwargs={
                    "task_id": celery_task.id,
                    "context": {
                        "space_code": celery_task.master_user.space_code,
                        "realm_code": celery_task.master_user.realm_code,
                    },
                }
            )

        except Exception as e:
            _l.error(f"load_init_configuration failed due to error {repr(e)}")
