import logging
import time

from django.core.management.base import BaseCommand

_l = logging.getLogger('provision')


class Command(BaseCommand):
    help = 'Clear celery tasks and procedures'

    def handle(self, *args, **options):
        from poms_app.celery import app as celery_app

        _l.info("Clearing celery tasks and procedures")

        # Need to wait to ensure celery workers are available
        i = celery_app.control.inspect()

        while not i.stats():
            _l.info('Waiting for Celery worker(s)...')
            time.sleep(5)

        _l.info('Celery worker(s) are now available.')

        # WARNING Do not delete
        # important, its inits celery listeners for global state
        # it uses for record history in post_save post_delete signals for proper context
        from poms_app import celery_app

        from poms.common.celery import cancel_existing_tasks
        cancel_existing_tasks(celery_app)
        from poms.common.celery import cancel_existing_procedures
        cancel_existing_procedures(celery_app)
