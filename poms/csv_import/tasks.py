import json
import traceback
from logging import getLogger

from django.db import transaction
from rest_framework.renderers import JSONRenderer

from poms.celery_tasks import finmars_task
from poms.celery_tasks.models import CeleryTask
from poms.csv_import.handlers import SimpleImportProcess
from poms.csv_import.models import CsvImportScheme
from poms.system_messages.handlers import send_system_message

_l = getLogger('poms.csv_import')

from poms.common.storage import get_storage

storage = get_storage()


@finmars_task(name='csv_import.simple_import', bind=True)
def simple_import(self, task_id, procedure_instance_id=None):
    try:
        celery_task = CeleryTask.objects.get(pk=task_id)
        celery_task.celery_task_id = self.request.id  # Important (record history rely on that)
        celery_task.status = CeleryTask.STATUS_PENDING
        celery_task.save()

        try:

            instance = SimpleImportProcess(task_id=task_id, procedure_instance_id=procedure_instance_id)

            celery_task.update_progress(
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
                    raise Exception("Could not preprocess raw items %s" % e)

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

            return json.dumps(instance.import_result)

        except Exception as e:
            _l.error('simple_import error %s' % e)
            _l.error('simple_import traceback %s' % traceback.format_exc())

            raise Exception(e)

            # celery_task.error_message = str(e)
            # celery_task.status = CeleryTask.STATUS_ERROR
            # celery_task.save()
            #


    except Exception as e:

        _l.error('simple_import general error %s' % e)
        _l.error('simple_import general traceback %s' % traceback.format_exc())
        raise Exception(e)


@finmars_task(name='csv_import.data_csv_file_import_by_procedure_json', bind=True)
def data_csv_file_import_by_procedure_json(self, procedure_instance_id, celery_task_id):
    _l.info('data_csv_file_import_by_procedure_json  procedure_instance_id %s celery_task_id %s' % (
        procedure_instance_id, celery_task_id))

    from poms.procedures.models import RequestDataFileProcedureInstance

    procedure_instance = RequestDataFileProcedureInstance.objects.get(id=procedure_instance_id)
    celery_task = CeleryTask.objects.get(id=celery_task_id)
    celery_task.status = CeleryTask.STATUS_PENDING
    celery_task.celery_task_id = self.request.id
    celery_task.save()

    try:

        _l.info(
            'data_csv_file_import_by_procedure_json looking for scheme %s ' % procedure_instance.procedure.scheme_user_code)

        scheme = CsvImportScheme.objects.get(master_user=procedure_instance.master_user,
                                             user_code=procedure_instance.procedure.scheme_user_code)

        options_object = celery_task.options_object

        options_object['file_path'] = ''
        options_object['filename'] = ''
        options_object['scheme_id'] = scheme.id
        options_object['execution_context'] = {'started_by': 'procedure'}

        celery_task.options_object = options_object
        celery_task.save()

        text = "Data File Procedure %s. Procedure Instance %s. File is received. Importing JSON" % (
            procedure_instance.id,
            procedure_instance.procedure.user_code)

        send_system_message(master_user=procedure_instance.master_user,
                            performed_by='System',
                            description=text)

        transaction.on_commit(lambda: simple_import.apply_async(
            kwargs={"task_id": celery_task.id, "procedure_instance_id": procedure_instance_id},
            queue='backend-background-queue'))


    except Exception as e:

        _l.info('data_csv_file_import_by_procedure_json e %s' % e)

        text = "Data File Procedure %s. Can't import json, Error %s" % (
            procedure_instance.procedure.user_code, e)

        send_system_message(master_user=procedure_instance.master_user,
                            performed_by='System',
                            description=text)

        _l.debug(
            'data_csv_file_import_by_procedure_json scheme %s not found' % procedure_instance.procedure.scheme_name)

        procedure_instance.status = RequestDataFileProcedureInstance.STATUS_ERROR
        procedure_instance.save()
