from functools import partial

from poms.celery_tasks.base import BaseTask
from poms_app.celery import app

default_app_config = "poms.celery_tasks.apps.CeleryTasksConfig"

finmars_task = partial(app.task, base=BaseTask)
