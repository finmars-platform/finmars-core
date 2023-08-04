from __future__ import unicode_literals

default_app_config = 'poms.celery_tasks.apps.CeleryTasksConfig'

from poms.celery_tasks.base import BaseTask
from functools import partial

from poms_app.celery import app

finmars_task = partial(app.task, base=BaseTask)