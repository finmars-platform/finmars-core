import traceback
from celery import shared_task

from poms.transaction_import.handlers import TransactionImportProcess


from storages.backends.sftpstorage import SFTPStorage
SFS = SFTPStorage()

import logging
_l = logging.getLogger('poms.transaction_import')


@shared_task(name='transaction_import.transaction_import', bind=True)
def transaction_import(self, task_id, procedure_instance_id=None):

    try:

        instance = TransactionImportProcess(task_id=task_id, procedure_instance_id=procedure_instance_id)

        instance.fill_with_raw_items()
        instance.preprocess()
        instance.process()

    except Exception as e:

        _l.error('transaction_import.General Exception occurred %s' % e)
        _l.error(traceback.format_exc())
