
from celery import shared_task
from django.utils import timezone
from django.conf import settings

import logging

from poms.pricing.handlers import PricingProcedureProcess
from poms.pricing.models import PricingProcedure
from poms.procedures.models import RequestDataFileProcedure
from poms.schedules.handlers import RequestDataFileProcedureProcess
from poms.schedules.models import PricingSchedule, Schedule


_l = logging.getLogger('poms.schedules')


# DEPRECATED SINCE 26.08.2020 DELETE SOON START
@shared_task(name='schedules.process_pricing_procedure_async', bind=True, ignore_result=True)
def process_pricing_procedure_async(self, procedure, master_user):

    _l.info("PricingSchedule: Subprocess process_pricing_procedure_async. Master User: %s. Procedure: %s" % (master_user, procedure) )

    instance = PricingProcedureProcess(procedure=procedure, master_user=master_user)
    from time import sleep
    from random import randint

    # val = randint(5, 10)
    #
    # _l.info("PricingSchedule: Sleep for %s seconds" % val)

    # sleep(val)
    instance.process()


@shared_task(name='schedules.auto_process_pricing_procedures_schedules', bind=True, ignore_result=True)
def auto_process_pricing_procedures_schedules(self):

    schedule_qs = PricingSchedule.objects.select_related('master_user').filter(
        is_enabled=True, next_run_at__lte=timezone.now()
    )

    if schedule_qs.count():
        _l.info('PricingSchedule: Schedules initialized: %s', schedule_qs.count())

    # TODO tmp limit

    procedures_count = 0

    for s in schedule_qs:

        master_user = s.master_user

        with timezone.override(master_user.timezone or settings.TIME_ZONE):
            next_run_at = timezone.localtime(s.next_run_at)
            s.schedule(save=True)

            _l.info('PricingSchedule: master_user=%s, next_run_at=%s. STARTED',
                    master_user.id, s.next_run_at)

            _l.info('PricingSchedule: count %s' % len(s.pricing_procedures.all()))

            for procedure in s.pricing_procedures.all():

                try:

                    process_pricing_procedure_async.apply_async(kwargs={'procedure':procedure, 'master_user':master_user})

                    _l.info('PricingSchedule: master_user=%s, next_run_at=%s. PROCESSED',
                            master_user.id, s.next_run_at)

                    procedures_count = procedures_count + 1

                except Exception as e:

                    _l.info('PricingSchedule: master_user=%s, next_run_at=%s. Error',
                            master_user.id, s.next_run_at)

                    _l.info('PricingSchedule: Error %s' % e)

                    pass

        s.last_run_at = timezone.now()
        s.save(update_fields=['last_run_at'])

    if procedures_count:
        _l.info('PricingSchedule: Finished. Procedures initialized: %s' % procedures_count)


@shared_task(name='schedules.process_pricing_procedures_schedules', bind=True, ignore_result=True)
def process_pricing_procedures_schedules(self, schedules):

    if len(schedules):
        _l.info('PricingSchedule: Schedules initialized: %s', len(schedules))

    procedures_count = 0

    for s in schedules:

        master_user = s.master_user

        with timezone.override(master_user.timezone or settings.TIME_ZONE):
            next_run_at = timezone.localtime(s.next_run_at)
            s.schedule(save=True)

            _l.info('PricingSchedule: master_user=%s, next_run_at=%s. STARTED',
                    master_user.id, s.next_run_at)

            _l.info('PricingSchedule: count %s' % len(s.pricing_procedures.all()))

            for procedure in s.pricing_procedures.all():

                try:

                    process_pricing_procedure_async.apply_async(kwargs={'procedure':procedure, 'master_user':master_user})

                    _l.info('PricingSchedule: master_user=%s, next_run_at=%s. PROCESSED',
                            master_user.id, s.next_run_at)

                    procedures_count = procedures_count + 1

                except Exception as e:

                    _l.info('PricingSchedule: master_user=%s, next_run_at=%s. Error',
                            master_user.id, s.next_run_at)

                    _l.info('PricingSchedule: Error %s' % e)

                    pass

        s.last_run_at = timezone.now()
        s.save(update_fields=['last_run_at'])

    if procedures_count:
        _l.info('PricingSchedule: Finished. Procedures initialized: %s' % procedures_count)
# DEPRECATED SINCE 26.08.2020 DELETE SOON END


## New Schedules

@shared_task(name='schedules.process_procedure_async', bind=True, ignore_result=True)
def process_procedure_async(self, procedure, master_user):

    _l.info("Schedule: Subprocess process. Master User: %s. Procedure: %s" % (master_user, procedure))

    if procedure.type == 'pricing':

        try:

            item = PricingProcedure.objects.get(master_user=master_user, user_code=procedure.user_code)

            instance = PricingProcedureProcess(procedure=item, master_user=master_user)
            instance.process()

        except PricingProcedure.DoesNotExist:

            _l.info("Can't find Pricing Procedure %s" % procedure.user_code)

    if procedure.type == 'request_data_file':

        try:

            item = RequestDataFileProcedure.objects.get(master_user=master_user, user_code=procedure.user_code)

            instance = RequestDataFileProcedureProcess(procedure=item, master_user=master_user)
            instance.process()

        except RequestDataFileProcedure.DoesNotExist:

            _l.info("Can't find Request Data File Procedure %s" % procedure.user_code)




@shared_task(name='schedules.process', bind=True, ignore_result=True)
def process(self):

    schedule_qs = Schedule.objects.select_related('master_user').filter(
        is_enabled=True, next_run_at__lte=timezone.now()
    )

    if schedule_qs.count():
        _l.info('Schedules initialized: %s', schedule_qs.count())

    procedures_count = 0

    for s in schedule_qs:

        master_user = s.master_user

        with timezone.override(master_user.timezone or settings.TIME_ZONE):
            next_run_at = timezone.localtime(s.next_run_at)
            s.schedule(save=True)

            _l.info('Schedule: master_user=%s, next_run_at=%s. STARTED',
                    master_user.id, s.next_run_at)

            _l.info('Schedule: count %s' % len(s.pricing_procedures.all()))

            for procedure in s.procedures.all():

                try:

                    process_procedure_async.apply_async(kwargs={'procedure':procedure, 'master_user':master_user})

                    _l.info('Schedule: master_user=%s, next_run_at=%s. PROCESSED',
                            master_user.id, s.next_run_at)

                    procedures_count = procedures_count + 1

                except Exception as e:

                    _l.info('Schedule: master_user=%s, next_run_at=%s. Error',
                            master_user.id, s.next_run_at)

                    _l.info('Schedule: Error %s' % e)

                    pass

        s.last_run_at = timezone.now()
        s.save(update_fields=['last_run_at'])

    if procedures_count:
        _l.info('Schedules Finished. Procedures initialized: %s' % procedures_count)
