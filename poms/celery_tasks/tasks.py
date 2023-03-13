from __future__ import unicode_literals, print_function

import logging
from datetime import timedelta

from celery import shared_task
from django.contrib.contenttypes.models import ContentType
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


@shared_task(name='celery_tasks.bulk_delete', bind=True)
def bulk_delete(self, task_id):
    # is_fake = bool(request.query_params.get('is_fake'))

    _l.info('bulk_delete.task_id %s' % task_id)

    celery_task = CeleryTask.objects.get(id=task_id)
    celery_task.celery_task_id = self.request.id
    celery_task.status = CeleryTask.STATUS_PENDING
    celery_task.save()

    options_object = celery_task.options_object

    _l.info('bulk_delete.options_object %s' % options_object)

    content_type_pieces = options_object['content_type'].split('.')

    content_type = ContentType.objects.get(app_label=content_type_pieces[0], model=content_type_pieces[1])

    queryset = content_type.model_class().objects.all()

    _l.info('bulk_delete %s' % options_object['ids'])

    celery_task.update_progress(
        {
            'current': 0,
            'total': len(options_object['ids']),
            'percent': 0,
            'description': 'Bulk delete initialized'
        }
    )

    try:
        if content_type.model_class()._meta.get_field('is_deleted'):

            # _l.info('bulk delete %s'  % queryset.model._meta.get_field('is_deleted'))

            queryset = queryset.filter(id__in=options_object['ids'])

            count = 0

            for instance in queryset:
                # try:
                #     self.check_object_permissions(request, instance)
                # except PermissionDenied:
                #     raise
                instance.fake_delete()

                count = count + 1

                celery_task.update_progress(
                    {
                        'current': count,
                        'total': len(options_object['ids']),
                        'percent': round(count / (len(options_object['ids']) / 100)),
                        'description': 'Instance %s was deleted' % instance.id
                    }
                )

    except Exception as e:
        _l.error('bulk_delete exception %s' % e)
        _l.error('bulk_delete traceback %s' % traceback.format_exc())

        if options_object['content_type'] == 'instruments.pricehistory' or options_object[
            'content_type'] == 'currencies.currencyhistory':
            _l.info("Going to permanent delete.")
            queryset.filter(id__in=options_object['ids']).delete()

    celery_task.status = CeleryTask.STATUS_DONE
    celery_task.mark_task_as_finished()
    celery_task.save()
