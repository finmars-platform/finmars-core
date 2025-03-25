from functools import partial

from poms.celery_tasks.base import BaseTask
from poms_app.celery import app

default_app_config = "poms.celery_tasks.apps.CeleryTasksConfig"

finmars_task = partial(app.task, base=BaseTask)


def get_celery_task_names():
    """
    Retrieves a list of all registered Celery task names.

    Returns:
        list: A list of strings, where each string is the name of a registered Celery task.
    """
    inspect = app.control.inspect()
    registered_tasks = inspect.registered()
    if registered_tasks:
        all_tasks = set()
        for worker_tasks in registered_tasks.values():
            all_tasks.update(worker_tasks)
        return list(all_tasks)
    return []
