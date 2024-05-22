import contextlib
import logging
import traceback
from datetime import datetime, timedelta, timezone

from django.contrib.contenttypes.models import ContentType
import django.db.utils
from django.utils.timezone import now

from celery.utils.log import get_task_logger

from poms.celery_tasks import finmars_task
from poms.celery_tasks.models import CeleryTask
from poms.system_messages.handlers import send_system_message
from poms.users.models import MasterUser
from poms_app.celery import app


@finmars_task(name="explorer.tasks.move_directory_in_storage", bind=True)
def move_directory_in_storage(self, task_id, *args, **kwargs):
    celery_task = CeleryTask.objects.get(id=task_id)
    celery_task.celery_task_id = self.request.id
    celery_task.status = CeleryTask.STATUS_PENDING
    celery_task.save()

    celery_task.update_progress(
        {
            "current": 0,
            "total": 0,
            "percent": 0,
            "description": "move_directory_in_storage initialized",
        }
    )
