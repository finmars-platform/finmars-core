import logging
import os

from celery import Celery
from celery.signals import task_failure

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "poms_app.settings")

app = Celery("poms_app")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
app.conf.task_routes = {"*": {"queue": "backend-general-queue"}}


def get_celery_task_names() -> list:
    """Get all registered task names from the Celery app."""
    try:
        return list(sorted(app.tasks.keys()))
    except Exception as e:
        import traceback

        return ["error", repr(e), traceback.format_exc()]


def get_worker_task_names():
    """Get task names currently known to connected workers."""
    try:
        inspect = app.control.inspect(timeout=1)  # Add timeout
        registered_tasks = inspect.registered() or {}
        return list(set().union(*registered_tasks.values()))

    except Exception as e:
        print(f"get_worker_task_names: failed due to {repr(e)}")
        return []


@task_failure.connect
def handle_task_failure(**kwargs):
    from poms.celery_tasks.models import CeleryTask

    _l = logging.getLogger("celery")

    exception = kwargs.get("exception")
    task_id = kwargs.get("task_id")
    task_kwargs = kwargs.get("kwargs", {})
    einfo = task_kwargs.get("einfo")

    try:
        if not exception and einfo:
            exception = einfo.exception

        # Handle the exception in any way you want.
        _l.warning(f"CeleryTask {task_id} raised exception: {einfo.exception} trace: {einfo.traceback}")

        task = CeleryTask.objects.get(celery_task_id=task_id)
        task.error_message = exception
        task.status = CeleryTask.STATUS_ERROR
        task.save()

    except Exception as e:
        _l.error(f"Can't handle CeleryTask {task_id} exception {exception} due to {repr(e)}")


# Probably not needed, it's also killing a worker, not a task
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
