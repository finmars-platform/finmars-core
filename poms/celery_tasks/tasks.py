from __future__ import unicode_literals, print_function

import logging
from datetime import timedelta

from celery import shared_task
from django.utils.timezone import now

from poms.system_messages.handlers import send_system_message
from poms.users.models import MasterUser
from poms_app import settings

_l = logging.getLogger('poms.celery_tasks')

from celery.utils.log import get_task_logger
import traceback
from poms.celery_tasks.models import CeleryTask

celery_logger = get_task_logger(__name__)


# TODO Refactor to task_id
@shared_task(name='celery_tasks.remove_old_tasks')
def remove_old_tasks():
    try:

        tasks = CeleryTask.objects.filter(created__lte=now() - timedelta(days=30))

        count = tasks.count()

        _l.info("Delete %s tasks" % count)
        master_user = MasterUser.objects.get(base_api_url=settings.BASE_API_URL)
        tasks.delete()

        send_system_message(master_user=master_user, type="info",
                            title='Old Task Clearance',
                            description='Finmars removed %s tasks' % count)

    except Exception as e:

        master_user = MasterUser.objects.get(base_api_url=settings.BASE_API_URL)

        send_system_message(master_user=master_user, action_status="required", type="warning",
                            title='Could not delete old Tasks',
                            description=str(e))

        _l.error("remove_old_tasks.exception %s" % e)
        _l.error("remove_old_tasks.exception %s" % traceback.format_exc())
