import os

from celery import Celery
from celery.signals import task_failure
# from django.conf import settings
# from poms.common.kombu_serializers import register_pickle_signed
# register_pickle_signed(salt='poms-pickle-signed', compress=True)
# register_pickle_signed(salt='poms-pickle-signed', compress=False)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "poms_app.settings")

app = Celery("poms_app")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()

app.conf.task_routes = {"*": {"queue": "backend-general-queue"}}


@task_failure.connect
def handle_task_failure(**kwargs):

    import logging
    from poms.celery_tasks.models import CeleryTask
    _l = logging.getLogger('celery')

    try:
        exception = kwargs['exception']
        task_id = kwargs['task_id']
        args = kwargs['args']
        kwargs = kwargs['kwargs']
        traceback = kwargs['traceback']
        einfo = kwargs['einfo']

        # Handle the exception in any way you want. For example, you could log it:
        _l.error(f'Task {task_id} raised exception: {einfo.exception} \n {einfo.traceback}')

        try:

            task = CeleryTask.objects.get(celery_task_id=task_id)
            task.error_message = einfo.exception
            task.status = CeleryTask.STATUS_ERROR
            task.save()

        except Exception as e:
            _l.error("Task is not registered in CeleryTask %s" % e)

    except Exception as e:
        _l.error("Could not handle task failure %s" % e)