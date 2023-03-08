from threading import local

from celery.signals import task_prerun, task_postrun

celery_state = local()

import logging

_l = logging.getLogger('poms.common')



def get_active_celery_task():
    task = getattr(celery_state, "task", None)

    return task


def get_active_celery_task_id():
    celery_task_id = getattr(celery_state, "celery_task_id", None)

    return celery_task_id


def cancel_existing_tasks(celery_app):
    from poms.celery_tasks.models import CeleryTask
    tasks = CeleryTask.objects.filter(status__in=[CeleryTask.STATUS_PENDING, CeleryTask.STATUS_INIT])

    for task in tasks:
        task.status = CeleryTask.STATUS_CANCELED

        try:  # just in case if rabbitmq still holds a task
            if task.celery_task_id:
                celery_app.control.revoke(task.celery_task_id, terminate=True)

        except Exception as e:
            _l.error("Something went wrong %s" % e)

        task.save()

    _l.info("Canceled %s tasks " % len(tasks))

@task_prerun.connect
def set_task_context(task_id, task, kwargs=None, **unused):
    _l.info('task %s' % task)

    celery_state.celery_task_id = task_id
    celery_state.task = task
    _l.info('celery_task_id set to {t}'.format(t=task_id))

@task_postrun.connect
def cleanup(task_id, **kwargs):
    celery_state.celery_task_id = None
    celery_state.task = None
    _l.info('cleaned current_tenant.id')

