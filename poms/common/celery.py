import logging
from threading import local

from celery.signals import task_postrun, task_prerun
from django.db import connection

celery_state = local()

_l = logging.getLogger("poms.common")


def get_active_celery_task():
    return getattr(celery_state, "task", None)


def get_active_celery_task_id():
    return getattr(celery_state, "celery_task_id", None)


def cancel_existing_tasks(celery_app):
    from poms.celery_tasks.models import CeleryTask

    tasks = CeleryTask.objects.filter(
        status__in=[CeleryTask.STATUS_PENDING, CeleryTask.STATUS_INIT]
    )

    _l_new = logging.getLogger("provision")

    for task in tasks:
        task.status = CeleryTask.STATUS_CANCELED

        try:  # just in case if rabbitmq still holds a task
            if task.celery_task_id:
                celery_app.control.revoke(task.celery_task_id, terminate=True)

        except Exception as e:
            _l_new.error(f"Something went wrong {e}")

        task.save()

    _l_new.info(f"Canceled {len(tasks)} tasks ")


def cancel_existing_procedures(celery_app):
    from poms.procedures.models import RequestDataFileProcedureInstance

    procedures = RequestDataFileProcedureInstance.objects.filter(
        status__in=[
            RequestDataFileProcedureInstance.STATUS_PENDING,
            RequestDataFileProcedureInstance.STATUS_INIT,
        ]
    )

    _l = logging.getLogger("provision")

    for procedure in procedures:
        procedure.status = RequestDataFileProcedureInstance.STATUS_CANCELED

        # try:  # just in case if rabbitmq still holds a task
        #     if task.celery_task_id:
        #         celery_app.control.revoke(task.celery_task_id, terminate=True)
        #
        # except Exception as e:
        #     _l.error("Something went wrong %s" % e)

        procedure.save()

    _l.info(f"Canceled {len(procedures)} procedures ")

def schema_exists(schema_name):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT schema_name
            FROM information_schema.schemata
            WHERE schema_name = %s;
        """, [schema_name])
        return cursor.fetchone() is not None


# EXTREMELY IMPORTANT CODE
# DO NOT MODIFY IT
# IT SETS CONTEXT FOR SHARED WORKERS TO WORK WITH DIFFERENT SCHEMAS
# 2024-03-24 szhitenev
# ALL TASKS MUST BE PROVIDED WITH CONTEXT WITH space_code
@task_prerun.connect
def set_task_context(task_id, task, kwargs=None, **unused):

    _l.info(f"task_prerun.task {task} context: {kwargs['context']}" )

    context = kwargs.get('context')
    if context:
        if context.get('space_code'):
            space_code = context.get('space_code')

            if schema_exists(space_code):
                with connection.cursor() as cursor:
                    cursor.execute(f"SET search_path TO {space_code};")
                    _l.info(f"task_prerun.context {space_code}")
            else:
                raise Exception('No scheme in database')
        else:
            raise Exception('No space_code in context')
    else:
        raise Exception('No context in kwargs')

    celery_state.celery_task_id = task_id
    celery_state.task = task
    # _l.info('celery_task_id set to {t}'.format(t=task_id))


@task_postrun.connect
def cleanup(task_id, **kwargs):
    celery_state.celery_task_id = None
    celery_state.task = None
    # _l.info('cleaned current_tenant.id')
    with connection.cursor() as cursor:
        cursor.execute("SET search_path TO public;")
