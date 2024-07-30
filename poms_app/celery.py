import os
import platform
import sys

from celery import Celery
from celery.signals import task_failure
import resource
from celery.signals import worker_ready
# from django.conf import settings
# from poms.common.kombu_serializers import register_pickle_signed
# register_pickle_signed(salt='poms-pickle-signed', compress=True)
# register_pickle_signed(salt='poms-pickle-signed', compress=False)
from celery.signals import worker_process_init

from poms_app import settings

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
        einfo = kwargs.get('einfo')

        if not exception and einfo:
            exception = einfo.exception

        # Handle the exception in any way you want. For example, you could log it:
        # _l.error(f'Task {task_id} raised exception: {einfo.exception} \n {einfo.traceback}')

        try:

            task = CeleryTask.objects.get(celery_task_id=task_id)
            task.error_message = exception
            task.status = CeleryTask.STATUS_ERROR
            task.save()

        except Exception as e:
            _l.error("Task is not registered in CeleryTask %s" % e)

    except Exception as e:
        _l.error("Could not handle task failure %s" % e)

# Probably not needed, it also killing a workier, not a task
# @worker_ready.connect
# def configure_worker(sender=None, **kwargs):
#
#     from celery.utils.log import get_task_logger
#     logger = get_task_logger('poms.celery_tasks')
#
#     logger.info("worker_process_init")
#
#     if platform.system() == 'Linux':
#
#         if "test" in sys.argv or "makemigrations" in sys.argv or "migrate" in sys.argv:
#             logger.info("Memory Limit is not set. Probably Test or Migration context")
#         else:
#
#             logger.info('decorated_run limit %s MB' % (settings.WORKER_MAX_MEMORY  / 1024 / 1024))
#
#             soft_limit, hard_limit = resource.getrlimit(resource.RLIMIT_AS)
#             logger.info(f"Soft limit: {soft_limit / 1024 / 1024} MB")
#             logger.info(f"Hard limit: {hard_limit / 1024 / 1024} MB")
#
#             new_limit = settings.WORKER_MAX_MEMORY
#             new_limit_mb = new_limit / 1024 / 1024
#
#             # Make sure we're not trying to set the limit beyond the current hard limit
#             resource.setrlimit(resource.RLIMIT_AS, (new_limit, resource.RLIM_INFINITY))
#             logger.info(f"New limit set to {new_limit_mb} MB")
#
#             # Get the current memory limit
#             soft_limit, hard_limit = resource.getrlimit(resource.RLIMIT_AS)
#             logger.info(f"Updated Soft limit: {soft_limit / 1024 / 1024} MB")
#             logger.info(f"Updated Hard limit: {hard_limit / 1024 / 1024} MB")
#     else:
#         logger.info("Running not on Linux. Memory limit not changed.")
