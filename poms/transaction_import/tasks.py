import json
import logging
import traceback

from poms.celery_tasks import finmars_task
from poms.transaction_import.handlers import TransactionImportProcess

_l = logging.getLogger("poms.transaction_import")


@finmars_task(name="transaction_import.transaction_import", bind=True)
def transaction_import(self, task_id, procedure_instance_id=None):
    try:
        instance = TransactionImportProcess(
            task_id=task_id, procedure_instance_id=procedure_instance_id
        )

        self.finmars_task.update_progress(
            {
                "current": 0,
                "total": len(instance.raw_items),
                "percent": 0,
                "description": "Going to parse raw items",
            }
        )

        instance.fill_with_file_items()

        if instance.scheme.data_preprocess_expression:
            try:
                _l.info(
                    f"Going to execute {instance.scheme.data_preprocess_expression}"
                )

                new_file_items = instance.whole_file_preprocess()
                instance.file_items = new_file_items

            except Exception as e:
                err_msg = f"transaction_import.preprocess errors {repr(e)}"
                _l.error(err_msg)
                raise RuntimeError(err_msg) from e

        instance.fill_with_raw_items()

        self.finmars_task.update_progress(
            {
                "current": 0,
                "total": len(instance.raw_items),
                "percent": 0,
                "description": "Parse raw items",
            }
        )
        instance.apply_conversion_to_raw_items()
        self.finmars_task.update_progress(
            {
                "current": 0,
                "total": len(instance.raw_items),
                "percent": 0,
                "description": "Apply Conversion",
            }
        )
        instance.preprocess()
        self.finmars_task.update_progress(
            {
                "current": 0,
                "total": len(instance.raw_items),
                "percent": 0,
                "description": "Preprocess items",
            }
        )
        instance.process()

        _l.info(f"instance.import_result {instance.import_result}")

        return json.dumps(instance.import_result, default=str)

    except Exception as e:
        _l.error(
            f"transaction_import error {repr(e)} traceback {traceback.format_exc()}"
        )
        raise e
