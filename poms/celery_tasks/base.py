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
    # max_memory = settings.WORKER_MAX_MEMORY

    # def __init__(self):
    #     self.run = self.decorated_run(self.run)

    # def print_memory_usage(self, ):
    #     process = psutil.Process()
    #     mem_info = process.memory_info()
    #     logger.info(f"Current memory usage: {mem_info.rss / 1024 / 1024} MB")

    # def decorated_run(self, func):
    #     if platform.system() == 'Linux':
    #
    #         if "test" in sys.argv or "makemigrations" in sys.argv or "migrate" in sys.argv:
    #             logger.info("Memory Limit is not set. Probably Test or Migration context")
    #         else:
    #             self.print_memory_usage()
    #             logger.info('decorated_run limit %s MB' % (settings.WORKER_MAX_MEMORY  / 1024 / 1024))
    #
    #             soft_limit, hard_limit = resource.getrlimit(resource.RLIMIT_AS)
    #             logger.info(f"Soft limit: {soft_limit / 1024 / 1024} MB")
    #             logger.info(f"Hard limit: {hard_limit / 1024 / 1024} MB")
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
    # return func

    # def run(self, *args, **kwargs):
    #     # Set the soft memory limit
    #
    #     logger.info('run.settings memory limit')
    #
    #     # resource.setrlimit(resource.RLIMIT_AS, (self.max_memory, resource.RLIM_INFINITY))
    #     return super().run(*args, **kwargs)

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

    def __call__(self, *args, **kwargs):
        if "test" in sys.argv or "makemigrations" in sys.argv or "migrate" in sys.argv:
            logger.info("Memory Limit is not set. Probably Test or Migration context")

            # call the actual task
            result = super().__call__(*args, **kwargs)

        else:
            pr = cProfile.Profile()
            pr.enable()

            # call the actual task
            result = super().__call__(*args, **kwargs)

            pr.disable()
            s = io.StringIO()
            ps = pstats.Stats(pr, stream=s).sort_stats("cumulative")
            ps.print_stats()

            # Here s.getvalue() contains the profiling info, you can log it,
            # save it to a file or do whatever you want with it.
            text = s.getvalue()
            if self.finmars_task and text:
                current_date_time = now().strftime("%Y-%m-%d-%H-%M")
                task_id = self.finmars_task.id
                verbose_name = (
                    f"Execution Profile {current_date_time} (Task {task_id}).txt"
                )
                file_name = f"execution_profile_{current_date_time}_{task_id}.txt"

                self._generate_file(verbose_name, file_name, text)

        return result

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
        logger.info(f"before_start task_id={task_id} args={args} kwargs={kwargs}")

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
        logger.info(
            f"on_failure exc={exc} task_id={task_id} args={args} "
            f"kwargs={kwargs} einfo={einfo}"
        )

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
        logger.info(
            f"on_success retval={retval} task_id={task_id} args={args} kwargs={kwargs}"
        )

        if self.finmars_task:
            self._update_celery_task_with_success(retval, task_id)

        super().on_success(retval, task_id, args, kwargs)

    def update_progress(self, progress):
        if self.finmars_task:
            self.finmars_task.progress = progress
            self.finmars_task.save()

    # CeleryTask has no log attribute!
    # def log(self, message):
    #     # Append the message to the task's log
    #     if self.finmars_task:
    #         self.finmars_task.log += f"{message} \n"
    #         self.finmars_task.save()
