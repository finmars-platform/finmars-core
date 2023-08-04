import logging
import traceback

from celery import shared_task

from poms.celery_tasks import finmars_task
from poms.celery_tasks.models import CeleryTask
from poms.transaction_import.handlers import TransactionImportProcess

_l = logging.getLogger('poms.transaction_import')


@finmars_task(name='transaction_import.transaction_import', bind=True)
def transaction_import(self, task_id, procedure_instance_id=None):

    try:

        try:

            instance = TransactionImportProcess(task_id=task_id, procedure_instance_id=procedure_instance_id)

            self.finmars_task.update_progress(
                {
                    'current': 0,
                    'total': len(instance.raw_items),
                    'percent': 0,
                    'description': 'Going to parse raw items'
                }
            )

            instance.fill_with_file_items()

            if instance.scheme.data_preprocess_expression:
                try:

                    _l.info("Going to execute %s" % instance.scheme.data_preprocess_expression)

                    new_file_items = instance.whole_file_preprocess()
                    instance.file_items = new_file_items

                except Exception as e:
                    _l.error('transaction_import.preprocess errors %s' % e)
                    raise Exception ("Could not preprocess raw items %s" % e)


            instance.fill_with_raw_items()

            self.finmars_task.update_progress(
                {
                    'current': 0,
                    'total': len(instance.raw_items),
                    'percent': 0,
                    'description': 'Parse raw items'
                }
            )
            instance.apply_conversion_to_raw_items()
            self.finmars_task.update_progress(
                {
                    'current': 0,
                    'total': len(instance.raw_items),
                    'percent': 0,
                    'description': 'Apply Conversion'
                }
            )
            instance.preprocess()
            self.finmars_task.update_progress(
                {
                    'current': 0,
                    'total': len(instance.raw_items),
                    'percent': 0,
                    'description': 'Preprocess items'
                }
            )
            instance.process()

            return {"message": "import finished"}
            # return instance

        except Exception as e:

            _l.error("transaction_import error %s" % e)
            _l.error("transaction_import traceback %s" % traceback.format_exc())

            self.finmars_task.error_message = "Error %s. \n Traceback: %s" % (e, traceback.format_exc())
            self.finmars_task.status = CeleryTask.STATUS_ERROR
            self.finmars_task.mark_task_as_finished()
            self.finmars_task.save()

    except Exception as e:

        _l.error('transaction_import.General Exception occurred %s' % e)
        _l.error(traceback.format_exc())
