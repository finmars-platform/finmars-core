import json
import traceback
from logging import getLogger

from django.db import transaction

from poms.celery_tasks import finmars_task
from poms.celery_tasks.models import CeleryTask
from poms.common.storage import get_storage
from poms.csv_import.handlers import SimpleImportProcess
from poms.csv_import.models import CsvImportScheme
from poms.system_messages.handlers import send_system_message

_l = getLogger("poms.csv_import")

storage = get_storage()


@finmars_task(name="csv_import.simple_import", bind=True)
def simple_import(self, task_id, procedure_instance_id=None):
    try:
        celery_task = CeleryTask.objects.get(pk=task_id)
        # Important (record history rely on that)
        celery_task.celery_task_id = self.request.id
        celery_task.status = CeleryTask.STATUS_PENDING
        celery_task.save()
    except Exception as e:
        err_msg = (
            f"simple_import celery_task {task_id} error {repr(e)} "
            f"traceback {traceback.format_exc()}"
        )
        _l.error(err_msg)
        raise RuntimeError(err_msg) from e

    try:
        instance = SimpleImportProcess(
            task_id=task_id,
            procedure_instance_id=procedure_instance_id,
        )

        celery_task.update_progress(
            {
                "current": 0,
                "total": len(instance.raw_items),
                "percent": 0,
                "description": "Going to parse raw items",
            }
        )

        instance.fill_with_file_items()

        if instance.scheme.data_preprocess_expression:
            _l.info(f"Going to execute {instance.scheme.data_preprocess_expression}")
            try:
                new_file_items = instance.whole_file_preprocess()
                instance.file_items = new_file_items

            except Exception as e:
                err_msg = f"transaction_import.preprocess errors {repr(e)}"
                _l.error(err_msg)
                celery_task.error_message = err_msg
                celery_task.status = CeleryTask.STATUS_ERROR
                celery_task.save()
                raise RuntimeError(err_msg) from e

        instance.fill_with_raw_items()

        celery_task.update_progress(
            {
                "current": 0,
                "total": len(instance.raw_items),
                "percent": 0,
                "description": "Parse raw items",
            }
        )

        instance.apply_conversion_to_raw_items()

        celery_task.update_progress(
            {
                "current": 0,
                "total": len(instance.raw_items),
                "percent": 0,
                "description": "Apply Conversion",
            }
        )

        instance.preprocess()

        celery_task.update_progress(
            {
                "current": 0,
                "total": len(instance.raw_items),
                "percent": 0,
                "description": "Preprocess items",
            }
        )
        instance.process()

        return json.dumps(instance.task.result_object, default=str)

    except Exception as e:
        err_msg = f"simple_import error {repr(e)} trace {traceback.format_exc()}"
        _l.error(err_msg)

        celery_task.error_message = err_msg
        celery_task.status = CeleryTask.STATUS_ERROR
        celery_task.save()


@finmars_task(name="csv_import.data_csv_file_import_by_procedure_json", bind=True)
def data_csv_file_import_by_procedure_json(self, procedure_instance_id, celery_task_id):
    from poms.procedures.models import RequestDataFileProcedureInstance

    _l.info(
        f"data_csv_file_import_by_procedure_json  procedure_instance_id "
        f"{procedure_instance_id} celery_task_id {celery_task_id}"
    )

    procedure_instance = RequestDataFileProcedureInstance.objects.get(
        id=procedure_instance_id
    )
    celery_task = CeleryTask.objects.get(id=celery_task_id)
    celery_task.status = CeleryTask.STATUS_PENDING
    celery_task.celery_task_id = self.request.id
    celery_task.save()

    _l.info(
        f"data_csv_file_import_by_procedure_json looking for "
        f"scheme {procedure_instance.procedure.scheme_user_code} "
    )

    try:
        scheme = CsvImportScheme.objects.get(
            master_user=procedure_instance.master_user,
            user_code=procedure_instance.procedure.scheme_user_code,
        )

        options_object = celery_task.options_object

        options_object["file_path"] = ""
        options_object["filename"] = ""
        options_object["scheme_id"] = scheme.id
        options_object["execution_context"] = {"started_by": "procedure"}

        celery_task.options_object = options_object
        celery_task.save()

        text = (
            f"Data File Procedure {procedure_instance.id}. "
            f"Procedure Instance {procedure_instance.procedure.user_code}. "
            f"File is received. Importing JSON"
        )

        send_system_message(
            master_user=procedure_instance.master_user,
            performed_by="System",
            description=text,
        )

        transaction.on_commit(
            lambda: simple_import.apply_async(
                kwargs={
                    "task_id": celery_task.id,
                    "procedure_instance_id": procedure_instance_id,
                },
                queue="backend-background-queue",
            )
        )

    except Exception as e:
        _l.info(
            f"data_csv_file_import_by_procedure_json "
            f"scheme {procedure_instance.procedure.scheme_name} not found "
            f"error {repr(e)}"
        )

        text = (
            f"Data File Procedure {procedure_instance.procedure.user_code}. "
            f"Can't import json, Error {repr(e)}"
        )
        send_system_message(
            master_user=procedure_instance.master_user,
            performed_by="System",
            description=text,
        )

        procedure_instance.status = RequestDataFileProcedureInstance.STATUS_ERROR
        procedure_instance.save()
