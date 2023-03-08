from celery.signals import before_task_publish, task_prerun, task_postrun
from threading import local

celery_state = local()

import logging

_l = logging.getLogger('poms.common')

def get_active_celery_task():

    task = getattr(celery_state, "task", None)

    return task

def get_active_celery_task_id():

    celery_task_id = getattr(celery_state, "celery_task_id", None)

    return celery_task_id


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