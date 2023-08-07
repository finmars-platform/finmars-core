import sys

from celery import Task as _Task
from celery.utils.log import get_task_logger
from django.utils.timezone import now

logger = get_task_logger(__name__)
import cProfile
import pstats
import io


class BaseTask(_Task):

    def update_progress(self, progress):

        self.finmars_task.progress = progress

        self.finmars_task.save()

    def log(self, message):
        # Append the message to the task's log

        if hasattr(self, 'finmars_task') and hasattr(self, 'task'):
            if not self.task.log:
                self.finmars_task.log = ''

            self.finmars_task.log = self.task.log + message + '\n'
            self.finmars_task.save()

    # max_memory = settings.WORKER_MAX_MEMORY

    # def __init__(self):
    #     self.run = self.decorated_run(self.run)

    # def print_memory_usage(self, ):
    #     process = psutil.Process()
    #     mem_info = process.memory_info()
    #     logger.info(f"Current memory usage: {mem_info.rss / 1024 / 1024} MB")

    # def decorated_run(self, func):
    #
    #     if platform.system() == 'Linux':
    #
    #         if "test" in sys.argv or "makemigrations" in sys.argv or "migrate" in sys.argv:
    #             logger.info("Memory Limit is not set. Probably Test or Migration context")
    #         else:
    #
    #             self.print_memory_usage()
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

    # return func

    # def run(self, *args, **kwargs):
    #     # Set the soft memory limit
    #
    #     logger.info('run.settings memory limit')
    #
    #     # resource.setrlimit(resource.RLIMIT_AS, (self.max_memory, resource.RLIM_INFINITY))
    #     return super().run(*args, **kwargs)

    def generate_file(self, verbose_name, file_name, text):

        from poms.file_reports.models import FileReport
        file_report = FileReport()

        logger.info('TransactionImportProcess.generate_json_report uploading file')

        file_report.upload_file(file_name=file_name, text=text,
                                master_user=self.finmars_task.master_user)
        file_report.master_user = self.finmars_task.master_user
        file_report.name = verbose_name
        file_report.file_name = file_name
        file_report.type = 'task.metadata'
        file_report.notes = 'System File'
        file_report.content_type = 'plain/txt'

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
            ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
            ps.print_stats()

            # Here s.getvalue() contains the profiling info, you can log it,
            # save it to a file or do whatever you want with it.
            current_date_time = now().strftime("%Y-%m-%d-%H-%M")
            task_id = self.finmars_task.id if hasattr(self, 'finmars_task') else 'unknown'
            verbose_name = f'Execution Profile {current_date_time} (Task {task_id}).txt'
            file_name = f'execution_profile_{current_date_time}_{task_id}.txt'

            self.generate_file(verbose_name, file_name, s.getvalue())



        return result

    def before_start(self, task_id, args, kwargs):

        try:

            logger.info('before_start.task_id %s' % task_id)
            logger.info('before_start.args %s' % args)
            logger.info('before_start.kwargs %s' % kwargs)

            from poms.celery_tasks.models import CeleryTask

            task = CeleryTask.objects.get(id=kwargs['task_id'])
            task.status = CeleryTask.STATUS_PENDING

            task.celery_task_id = self.request.id

            task.worker_name = self.request.hostname

            task.save()

            self.finmars_task = task

            logger.info(f"Task {task_id} is now in progress")

        except Exception as e:
            logger.error("BaseTask.before_start %s" % e)

        super(BaseTask, self).before_start(task_id, args, kwargs)

    def on_failure(self, exc, task_id, args, kwargs, einfo):

        try:

            from poms.celery_tasks.models import CeleryTask

            self.finmars_task.status = CeleryTask.STATUS_ERROR
            self.finmars_task.result_object = {"exception": str(exc), "traceback": einfo.traceback}
            self.finmars_task.error_message = str(exc)
            self.finmars_task.mark_task_as_finished()
            self.finmars_task.save()

            logger.info(f"Task {task_id} is now in error")

        except Exception as e:
            logger.error("BaseTask.on_failure %s" % e)

        super(BaseTask, self).on_failure(exc, task_id, args, kwargs, einfo)

    def on_success(self, retval, task_id, args, kwargs):

        try:

            from poms.celery_tasks.models import CeleryTask

            self.finmars_task.status = CeleryTask.STATUS_DONE
            if not retval:
                result_object = {
                    "message": "Task finished successfully. No results returned"
                }
                self.finmars_task.result_object = result_object

            self.finmars_task.mark_task_as_finished()
            self.finmars_task.save()

            logger.info(f"Task {task_id} is now in success. Retval {retval}")

        except Exception as e:
            logger.error("BaseTask.on_success %s" % e)

        super(BaseTask, self).on_success(retval, task_id, args, kwargs)
