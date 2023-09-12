import time

from django.core.management.base import BaseCommand

import logging

from django.core.management.base import BaseCommand

from poms.celery_tasks.models import CeleryWorker

_l = logging.getLogger('provision')


class Command(BaseCommand):
    help = 'Deploy Default Worker'

    def handle(self, *args, **options):

        _l.info("Downloading init configuration")

        try:
            _l.info("deploy_default_worker processing")


            _l.info('Waiting for Rabbitmq...')
            time.sleep(10)

            try:

                try:
                    default_worker = CeleryWorker.objects.get(worker_name='default_worker')
                except Exception as e:
                    default_worker = CeleryWorker.objects.create(worker_name='worker00',
                                                                 worker_type='worker',
                                                                 memory_limit='1Gi',
                                                                 queue='backend-general-queue,backend-reports-queue,backend-imports-queue,backend-background-queue')

                status_detail = default_worker.get_status()

                if status_detail['status']['deployed']:
                    _l.info("Default worker already deployed")
                    return
                elif status_detail['status']['not_found']:
                    default_worker.deploy()
                else:
                    default_worker.start()

            except Exception as e:
                _l.error("Could not deploy worker %s" % e)


        except Exception as e:
            _l.info("deploy_default_worker error %s" % e)
