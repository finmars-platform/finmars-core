import logging

from poms.celery_tasks import finmars_task
from poms.celery_tasks.models import CeleryTask
from poms.currencies.models import Currency
from poms.instruments.models import Instrument
from poms.configuration.utils import run_workflow, wait_workflow_until_end

_l = logging.getLogger('poms.pricing')


def _run_pricing(task, reference_type, objects):
    last_exception = None
    options = task.options_object
    for count, obj in enumerate(objects):
        pricing_policies = obj.pricing_policies.all()
        if options.get("pricing_policies"):
            pricing_policies = pricing_policies.filter(pricing_policy__user_code__in=options["pricing_policies"])
        for schema in pricing_policies:
            payload = schema.options.copy()
            payload["date_from"] = options["date_from"]
            payload["date_to"] = options["date_to"]
            payload["reference_type"] = reference_type
            payload["reference"] = obj.user_code
            payload["pricing_policy"] = schema.pricing_policy.user_code
            # TODO, when instrument whill have reference_dict we can fetch different reference base on provider

            try:
                workflow = schema.target_pricing_schema_user_code + ':run_pricing'
                _l.info(f"run_pricing.going to execute workflow {workflow}")

                response_data = run_workflow(workflow, payload, task)
                #response_data = wait_workflow_until_end(response_data["id"], task)

                _l.info(f"run_pricing.workflow finished {response_data}")
            except Exception as e:
                last_exception = e
                _l.exception(f"Could not execute run_pricing.workflow for instrument {obj.user_code}"
                             f" and pricing policy {schema.pricing_policy.user_code}")

            task.status = CeleryTask.STATUS_REQUEST_SENT
            task.update_progress(
                {
                    "current": count,
                    "total": len(objects),
                    "percent": round(count / (len(objects) / 100)),
                    "description": f"Instance {obj.id} pricing scheduled",
                }
            )
    return last_exception


@finmars_task(name="pricing.tasks.run_pricing", bind=True)
def run_pricing(self, *args, **kwargs):
    task = CeleryTask.objects.get(id=kwargs["task_id"])
    task.celery_task_id = self.request.id
    task.status = CeleryTask.STATUS_PENDING
    task.save()
    options = task.options_object

    objects = instruments_exception = currencies_exception = None

    if options.get("instrument_types"):
        objects = Instrument.objects.filter(instrument_type__user_code__in=options["instrument_types"])
    elif options.get("instruments"):
        objects = Instrument.objects.filter(user_code__in=options["instruments"])
    if objects:
        instruments_exception = _run_pricing(task, "instruments", objects)

    if options.get("currencies"):
        objects = Currency.objects.filter(user_code__in=options["currencies"])
        currencies_exception = _run_pricing(task, "currencies", objects)

    exc = instruments_exception or currencies_exception
    if exc:
        raise exc
    task.save()
