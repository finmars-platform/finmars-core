import os
import time
import traceback

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from poms.common.storage import get_storage
import logging
_l = logging.getLogger('provision')

class Command(BaseCommand):
    help = 'Install Initial Configuration'

    def handle(self, *args, **options):

        _l.info("Downloading init configuration")

        from poms_app.celery import app as celery_app

        # Need to wait to ensure celery workers are available
        i = celery_app.control.inspect()

        while not i.stats():
            _l.info('Waiting for Celery worker(s)...')
            time.sleep(5)

        _l.info('Celery worker(s) are now available.')

        from poms.users.models import Member, MasterUser
        from poms.celery_tasks.models import CeleryTask
        from poms.configuration.tasks import install_package_from_marketplace

        if not settings.AUTHORIZER_URL:
            _l.error("Authorizer url is not set!")
            return

        try:
            _l.info("load_init_configuration processing")

            try:


                master_user = MasterUser.objects.filter()[0]
                # member = Member.objects.get(master_user=master_user, is_owner=True)
                member = Member.objects.get(username='finmars_bot')

                celery_task = CeleryTask.objects.create(master_user=master_user,
                                                        member=member,
                                                        verbose_name="Install Configuration From Marketplace",
                                                        type='install_configuration_from_marketplace')

                options_object = {
                    'configuration_code': "com.finmars.initial",
                    'version': "1.0.1",
                    'is_package': True,
                    # "access_token": get_access_token(request) TODO Implement when keycloak refactored
                    # TODO check this later, important security thins, need to be destroyed inside task
                }
                celery_task.options_object = options_object
                celery_task.save()

                install_package_from_marketplace.apply_async(kwargs={'task_id': celery_task.id})

            except Exception as e:
                _l.error("Could not init configuration %s" % e)


        except Exception as e:
            _l.info("load_init_configuration error %s" % e)