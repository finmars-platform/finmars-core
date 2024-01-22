import logging
from threading import local

from celery.signals import task_postrun, task_prerun

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


@task_prerun.connect
def set_task_context(task_id, task, kwargs=None, **unused):
    _l.info(f"task {task}")

    celery_state.celery_task_id = task_id
    celery_state.task = task
    # _l.info('celery_task_id set to {t}'.format(t=task_id))


@task_postrun.connect
def cleanup(task_id, **kwargs):
    celery_state.celery_task_id = None
    celery_state.task = None
    # _l.info('cleaned current_tenant.id')
