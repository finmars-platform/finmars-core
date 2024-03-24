import cProfile
import io
import json
import pstats
import sys

from celery import Task as _Task
from celery.utils.log import get_task_logger
from django.utils.timezone import now

logger = get_task_logger(__name__)


class BaseTask(_Task):

    finmars_task = None

    def _generate_file(self, verbose_name, file_name, text):
        from poms.file_reports.models import FileReport

        logger.info(f"generate_file uploading file {file_name} verbose {verbose_name}")

        file_report = FileReport()
        file_report.upload_file(
            file_name=file_name,
            text=text,
            master_user=self.finmars_task.master_user,
        )
        file_report.master_user = self.finmars_task.master_user
        file_report.name = verbose_name
        file_report.file_name = file_name
        file_report.type = "task.metadata"
        file_report.notes = "System File"
        file_report.content_type = "plain/txt"
        file_report.save()

        self.finmars_task.add_attachment(file_report.id)

    def _update_celery_task_with_run_info(self, kwargs: dict):
        from poms.celery_tasks.models import CeleryTask

        task_id = kwargs.get("task_id")
        if not task_id:
            return None

        task = CeleryTask.objects.filter(id=task_id).first()
        if not task:
            return None

        task.status = CeleryTask.STATUS_PENDING
        task.celery_task_id = self.request.id
        task.worker_name = self.request.hostname
        task.save()

        return task

    def before_start(self, task_id, args, kwargs):
        # logger.info(f"before_start task_id={task_id} args={args} kwargs={kwargs}")

        if kwargs:
            self.finmars_task = self._update_celery_task_with_run_info(kwargs)

        super().before_start(task_id, args, kwargs)

    def _update_celery_task_with_error(self, exc, einfo):
        from poms.celery_tasks.models import CeleryTask

        self.finmars_task.status = CeleryTask.STATUS_ERROR
        self.finmars_task.result_object = {
            "exception": str(exc),
            "traceback": einfo.traceback,
        }
        self.finmars_task.error_message = str(exc)
        self.finmars_task.mark_task_as_finished()
        self.finmars_task.save()

    def on_failure(self, exc, task_id, args, kwargs, einfo):

        if self.finmars_task:
            self._update_celery_task_with_error(exc, einfo)

        super().on_failure(exc, task_id, args, kwargs, einfo)

    def is_valid_json(self, retval):
        try:
            json.loads(retval)
            return True
        except json.JSONDecodeError:
            return False

    def _update_celery_task_with_success(self, retval, task_id):
        from poms.celery_tasks.models import CeleryTask

        self.finmars_task.status = CeleryTask.STATUS_DONE
        if not retval:
            result_object = {
                "message": f"Task {task_id} finished successfully. No results"
            }
            self.finmars_task.result_object = result_object
        else:
            try:
                if self.is_valid_json(retval):
                    self.finmars_task.result_object = json.loads(
                        retval)  ## TODO strange logic, probably refactor # but we can pass only string in celery
                else:
                    result_object = {
                        "message": f"Task {task_id} returned result is not JSON"
                    }
                    self.finmars_task.result_object = result_object
            except Exception as e:
                pass

        # self.finmars_task.result_object = result_object

        self.finmars_task.mark_task_as_finished()
        self.finmars_task.save()

    def on_success(self, retval, task_id, args, kwargs):
        # logger.info(
        #     f"on_success retval={retval} task_id={task_id} args={args} kwargs={kwargs}"
        # )

        if self.finmars_task:
            self._update_celery_task_with_success(retval, task_id)

        super().on_success(retval, task_id, args, kwargs)

    def update_progress(self, progress):
        if self.finmars_task:
            self.finmars_task.progress = progress
            self.finmars_task.save()