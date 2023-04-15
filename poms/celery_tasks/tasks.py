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

            items = list(queryset)

            for instance in items:
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


def import_item(item, context):
    meta = item.get('meta', None)

    from poms.common.utils import get_content_type_by_name
    from poms.common.utils import get_serializer

    if not meta:
        raise ValueError("Meta is not found. Could not process JSON")

    if meta['content_type'] == 'transactions.complextransaction':

        from poms.transactions.handlers import TransactionTypeProcess

        from poms.transactions.models import TransactionType
        transaction_type = TransactionType.objects.get(user_code=item['transaction_type'])

        values = {}

        for input in item['inputs']:

            if input['value_type'] == 10:
                values[input['transaction_type_input']] = input['value_string']

            if input['value_type'] == 20:
                values[input['transaction_type_input']] = input['value_float']

            if input['value_type'] == 40:
                values[input['transaction_type_input']] = input['value_date']

            if input['value_type'] == 110:
                values[input['transaction_type_input']] = input['value_string']

            if input['value_type'] == 100:
                content_type_key = input['content_type']

                content_type = get_content_type_by_name(content_type_key)
                try:
                    values[input['transaction_type_input']] = content_type.model_class().objects.get(
                        user_code=input['value_relation'])
                except Exception as e:
                    pass

        process_instance = TransactionTypeProcess(
            transaction_type=transaction_type,
            default_values=values,
            context=context,
            member=context['member'],
            source=item['source'],
            execution_context="manual"
        )

        process_instance.process()

    else:

        serializer_class = get_serializer(meta['content_type'])

        serializer = serializer_class(data=item, context=context)
        serializer.is_valid(raise_exception=True)
        serializer.save()


@shared_task(name='celery_tasks.universal_input', bind=True)
def universal_input(self, task_id):
    # is_fake = bool(request.query_params.get('is_fake'))

    _l.info('universal_input.task_id %s' % task_id)

    celery_task = CeleryTask.objects.get(id=task_id)
    celery_task.celery_task_id = self.request.id
    celery_task.status = CeleryTask.STATUS_PENDING
    celery_task.save()

    result = {}

    try:

        data = celery_task.options_object

        from poms.common.models import ProxyUser
        proxy_user = ProxyUser(celery_task.member, celery_task.master_user)
        from poms.common.models import ProxyRequest
        proxy_request = ProxyRequest(proxy_user)

        context = {
            'master_user': celery_task.master_user,
            'member': celery_task.member,
            'request': proxy_request
        }

        if isinstance(data, dict):
            data = [data]

        i = 1

        for item in data:
            try:
                import_item(item, context)

                result[str(i)] = {
                    'status': 'success'
                }

            except Exception as e:

                result[str(i)] = {
                    'status': 'error',
                    'error_message': str(e)
                }

            celery_task.update_progress(
                {
                    'current': i,
                    'total': len(data),
                    'percent': round(i / (len(data) / 100)),
                    'description': 'Going to import %s' % i
                }
            )

            i = i + 1

        celery_task.result_object = result
        celery_task.status = CeleryTask.STATUS_DONE
        celery_task.mark_task_as_finished()
        celery_task.save()

    except Exception as e:
        celery_task.result_object = result
        celery_task.status = CeleryTask.STATUS_ERROR
        celery_task.error_message = str(e)
        celery_task.save()
