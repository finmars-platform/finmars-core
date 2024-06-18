import logging

from celery import shared_task
from django.utils.timezone import now

from poms.celery_tasks import finmars_task
from poms.pricing.models import PricingProcedureInstance
from poms.procedures.models import PricingParentProcedureInstance

_l = logging.getLogger('poms.pricing')

