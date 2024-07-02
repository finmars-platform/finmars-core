import logging

from poms.celery_tasks import finmars_task
from poms.celery_tasks.models import CeleryTask
from poms.currencies.models import Currency
from poms.instruments.models import Instrument
from poms.configuration.utils import run_workflow, wait_workflow_until_end

_l = logging.getLogger('poms.pricing')


@finmars_task(name="pricing.tasks.run_pricing", bind=True)
def run_pricing(self, *args, **kwargs):
    task = CeleryTask.objects.get(id=kwargs["task_id"])
    task.celery_task_id = self.request.id
    task.status = CeleryTask.STATUS_PENDING
    task.save()
    options = task.options_object

    last_exception = None
    if options.get("instruments"):
        objects = Instrument.objects.filter(user_code__in=options["instruments"])
    else:
        objects = Currency.objects.filter(user_code__in=options["currencies"])

    for obj in objects:
        for schema in obj.pricing_policies.all():
            payload = schema.options.copy()
            payload["date_from"] = options["date_from"]
            payload["date_to"] = options["date_to"]
            payload["reference"] = obj.id  # !!! or user_code? depends on the market module
            payload["pricing_policy"] = schema.pricing_policy.user_code
            # TODO, when instrument whill have reference_dict we can fetch different reference base on provider

            try:
                workflow = schema.target_pricing_schema_user_code
                _l.info(f"run_pricing.going to execute workflow {workflow}")

                response_data = run_workflow(workflow, payload, task)
                #response_data = wait_workflow_until_end(response_data["id"], task)

                _l.info(f"run_pricing.workflow finished {response_data}")
            except Exception as e:
                last_exception = e
                _l.exception(f"Could not execute run_pricing.workflow for instrument {payload['reference']}"
                             f" and pricing policy {payload['pricing_policy']}")

    if last_exception:
        task.status = CeleryTask.STATUS_ERROR
        task.save()
