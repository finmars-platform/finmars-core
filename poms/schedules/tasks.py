
from celery import shared_task
from django.utils import timezone
from django.conf import settings

import logging

from poms.pricing.handlers import PricingProcedureProcess
from poms.schedules.models import PricingSchedule

_l = logging.getLogger('poms.schedules')


@shared_task(name='schedules.process_pricing_procedures_schedules', bind=True, ignore_result=True)
def process_pricing_procedures_schedules(self):

    schedule_qs = PricingSchedule.objects.select_related('master_user').filter(
        is_enabled=True, next_run_at__lte=timezone.now()
    )

    _l.info('Schedules initialized: %s', schedule_qs.count())

    # TODO tmp limit

    procedures_count = 0

    for s in schedule_qs:

        master_user = s.master_user

        with timezone.override(master_user.timezone or settings.TIME_ZONE):
            next_run_at = timezone.localtime(s.next_run_at)
            s.schedule(save=True)
            _l.info('PricingSchedule: master_user=%s, next_run_at=%s',
                    master_user.id, s.next_run_at)

            for procedure in s.pricing_procedures.all():

                instance = PricingProcedureProcess(procedure=procedure, master_user=master_user)
                instance.process()

                procedures_count = procedures_count + 1

        s.last_run_at = timezone.now()
        s.save(update_fields=['last_run_at'])

    _l.info('Finished. Procedures initialized: %s' % procedures_count)
