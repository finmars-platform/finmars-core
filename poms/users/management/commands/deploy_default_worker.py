import json
import time

from django.core.management.base import BaseCommand

import logging

from django.core.management.base import BaseCommand

from poms.celery_tasks.models import CeleryWorker
from poms_app import settings

_l = logging.getLogger("provision")


class Command(BaseCommand):
    help = "Deploy Default Worker"

    def handle(self, *args, **options):
        _l.info("Downloading init configuration")

        try:
            _l.info("deploy_default_worker processing")

            _l.info("Waiting for Rabbitmq...")
            time.sleep(10)

            realm_code = settings.REALM_CODE

            try:
                try:
                    default_worker = CeleryWorker.objects.get(worker_name="worker00")
                except Exception as e:
                    default_worker = CeleryWorker.objects.create(
                        worker_name="worker00",
                        worker_type="worker",
                        memory_limit="1Gi",
                        queue="backend-general-queue,backend-reports-queue,backend-imports-queue,backend-background-queue",
                    )

                    default_worker.create_worker(realm_code)

                default_worker.get_status(realm_code)

                status_detail = json.loads(default_worker.status)

                _l.info("deploy_default_worker: status_detail %s" % status_detail)

                if status_detail:
                    if status_detail["status"] == "deployed":
                        _l.info(
                            "deploy_default_worker: Default worker already deployed"
                        )
                        return
                    elif status_detail["status"] == "not_found":
                        default_worker.deploy(realm_code)
                    else:
                        default_worker.start(realm_code)

            except Exception as e:
                _l.error("deploy_default_worker: Could not deploy worker %s" % e)

        except Exception as e:
            _l.info("deploy_default_worker: error %s" % e)
