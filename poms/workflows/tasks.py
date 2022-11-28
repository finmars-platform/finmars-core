import logging

from celery import shared_task

from poms.common import formula
from poms.workflows.models import Workflow, WorkflowStep

_l = logging.getLogger('poms.workflows')


@shared_task(name='workflows.run_workflow_step', bind=True)
def run_workflow_step(self, workflow_id):
    _l.info("run_workflow_step init workflow %s" % workflow_id)

    workflow = Workflow.objects.get(id=workflow_id)

    workflow_step = WorkflowStep.objects.get(workflow_id=workflow_id, order=workflow.current_step)

    try:

        names = {}
        context = {'master_user': workflow.master_user, 'member': workflow.member}

        workflow_step.code = workflow_step.code + '\nrun_step_' + str(workflow_step.order) + '()'

        _l.info('workflow_step.code %s' % workflow_step.code)

        result, log = formula.safe_eval_with_logs(workflow_step.code, names=names, context=context)

        _l.debug('ExpressionProcedureProcess.result %s' % result)

        if result:
            workflow_step.result = result

        if log:
            workflow_step.log = log

        workflow_step.status = WorkflowStep.STATUS_DONE
        workflow_step.save()

        _l.info("run_workflow_step.step %s done success" % workflow_step.order)

    except Exception as e:

        _l.error("run_workflow_step.safe_eval error %s" % e)

        workflow_step.error_message = str(e)
        workflow_step.status = WorkflowStep.STATUS_ERROR
        workflow_step.save()

    workflow.current_step = workflow.current_step + 1
    workflow.save()

    run_workflow_step.apply_async(kwargs={"workflow_id": workflow.id})
