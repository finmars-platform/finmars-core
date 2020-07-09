
from celery import shared_task

import logging

from poms.file_reports.models import FileReport

from django.utils.timezone import now

from poms.pricing.models import PricingProcedureInstance, PricingParentProcedureInstance

_l = logging.getLogger('poms.pricing')

@shared_task(name='pricing.clear_old_pricing_procedure_instances', bind=True, ignore_result=True)
def clear_old_pricing_procedure_instances(self,):

    _l.info("Pricing: clear_old_pricing_procedure_instances")

    today = now()

    ids_to_delete = []

    items = PricingProcedureInstance.objects.all()

    for item in items:

        diff = today - item.created

        if diff.days > 3:
            ids_to_delete.append(item.id)

    if len(ids_to_delete):
        PricingProcedureInstance.objects.filter(id__in=ids_to_delete).delete()

    _l.info("PricingProcedureInstance items deleted %s" % len(ids_to_delete))

    ids_to_delete = []

    items = PricingParentProcedureInstance.objects.all()

    for item in items:

        diff = today - item.created

        if diff.days > 3:
            ids_to_delete.append(item.id)

    if len(ids_to_delete):
        PricingParentProcedureInstance.objects.filter(id__in=ids_to_delete).delete()

    _l.info("PricingParentProcedureInstance items deleted %s" % len(ids_to_delete))


@shared_task(name='pricing.set_old_processing_procedure_instances_to_error', bind=True, ignore_result=True)
def set_old_processing_procedure_instances_to_error(self,):

    _l.info("Pricing: set_old_processing_procedure_instances_to_error")

    today = now()

    items = PricingProcedureInstance.objects.all()

    count = 0

    for item in items:

        diff = today - item.created

        if diff.days > 1:

           if item.status == PricingProcedureInstance.STATUS_PENDING:

               item.status = PricingProcedureInstance.STATUS_ERROR
               item.save()

               count = count + 1

    _l.info("PricingParentProcedureInstance items set to error status %s" % len(count))

