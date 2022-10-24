import traceback
from celery import shared_task

from poms.celery_tasks.models import CeleryTask
from poms.transaction_import.handlers import TransactionImportProcess

import logging

_l = logging.getLogger('poms.transaction_import')


@shared_task(name='transaction_import.transaction_import', bind=True)
def transaction_import(self, task_id, procedure_instance_id=None):
    try:

        celery_task = CeleryTask.objects.get(pk=task_id)
        celery_task.celery_task_id = self.request.id
        celery_task.save()

        try:

            instance = TransactionImportProcess(task_id=task_id, procedure_instance_id=procedure_instance_id)

            celery_task.update_progress(
                {
                    'current': 0,
                    'total': len(instance.raw_items),
                    'percent': 0,
                    'description': 'Going to parse raw items'
                }
            )
            instance.fill_with_raw_items()

            celery_task.update_progress(
                {
                    'current': 0,
                    'total': len(instance.raw_items),
                    'percent': 0,
                    'description': 'Parse raw items'
                }
            )
            instance.apply_conversion_to_raw_items()
            celery_task.update_progress(
                {
                    'current': 0,
                    'total': len(instance.raw_items),
                    'percent': 0,
                    'description': 'Apply Conversion'
                }
            )
            instance.preprocess()
            celery_task.update_progress(
                {
                    'current': 0,
                    'total': len(instance.raw_items),
                    'percent': 0,
                    'description': 'Preprocess items'
                }
            )
            instance.process()

        except Exception as e:

            celery_task.error_message = "Error %s. \n Traceback: %s" % (e, traceback.format_exc())
            celery_task.status = CeleryTask.STATUS_ERROR
            celery_task.save()

    except Exception as e:

        _l.error('transaction_import.General Exception occurred %s' % e)
        _l.error(traceback.format_exc())
