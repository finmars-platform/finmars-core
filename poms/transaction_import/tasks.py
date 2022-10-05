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

        instance = TransactionImportProcess(task_id=task_id, procedure_instance_id=procedure_instance_id)

        instance.fill_with_raw_items()
        instance.apply_conversion_to_raw_items()
        instance.preprocess()
        instance.process()

    except Exception as e:

        _l.error('transaction_import.General Exception occurred %s' % e)
        _l.error(traceback.format_exc())
