from celery import Task as _Task
from celery.signals import task_prerun
from celery.utils.log import get_task_logger



logger = get_task_logger(__name__)

class BaseTask(_Task):

    def update_progress(self, progress):

        self.finmars_task.progress = progress

        self.finmars_task.save()

    def log(self, message):
        # Append the message to the task's log

        if not self.task.log:
            self.finmars_task.log = ''

        self.finmars_task.log = self.task.log + message + '\n'
        self.finmars_task.save()

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
            self.finmars_task.result = {"exception": str(exc), "traceback": einfo.traceback}
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
            if retval:
                pass # TODO fix it later
                # self.finmars_task.result_object = retval
            else:
                self.finmars_task.result_object = {"message": "Task finished successfully. No results returned"}
            self.finmars_task.mark_task_as_finished()
            self.finmars_task.save()

            logger.info(f"Task {task_id} is now in success. Retval {retval}")

        except Exception as e:
            logger.error("BaseTask.on_success %s" % e)

        super(BaseTask, self).on_success(retval, task_id, args, kwargs)
