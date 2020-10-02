
from celery import shared_task
from django.utils import timezone
from django.conf import settings

import logging

from poms.pricing.handlers import PricingProcedureProcess
from poms.procedures.handlers import RequestDataFileProcedureProcess
from poms.procedures.models import RequestDataFileProcedure, PricingProcedure
from poms.schedules.models import Schedule, ScheduleInstance

_l = logging.getLogger('poms.schedules')


@shared_task(name='schedules.process_procedure_async', bind=True, ignore_result=True)
def process_procedure_async(self, procedure, master_user, schedule_instance):

    _l.info("Schedule: Subprocess process. Master User: %s. Procedure: %s" % (master_user, procedure))

    if procedure.type == 'pricing':

        try:

            item = PricingProcedure.objects.get(master_user=master_user, user_code=procedure.user_code)

            instance = PricingProcedureProcess(procedure=item, master_user=master_user, schedule_instance=schedule_instance)
            instance.process()

        except PricingProcedure.DoesNotExist:

            _l.info("Can't find Pricing Procedure %s" % procedure.user_code)

    if procedure.type == 'request_data_file':

        try:

            item = RequestDataFileProcedure.objects.get(master_user=master_user, user_code=procedure.user_code)

            instance = RequestDataFileProcedureProcess(procedure=item, master_user=master_user, schedule_instance=schedule_instance)
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

            _l.info('Schedule: count %s' % len(s.procedures.all()))

            schedule_instance = ScheduleInstance(schedule=s, master_user=master_user)
            schedule_instance.save()

            for procedure in s.procedures.all():

                try:

                    if procedure.order == 1:

                        schedule_instance.current_processing_procedure_number = 1
                        schedule_instance.status = ScheduleInstance.STATUS_PENDING
                        schedule_instance.save()

                        process_procedure_async.apply_async(kwargs={'procedure':procedure, 'master_user':master_user, 'schedule_instance': schedule_instance})

                        _l.info('Schedule: Process first procedure master_user=%s, next_run_at=%s', master_user.id, s.next_run_at)

                        procedures_count = procedures_count + 1

                except Exception as e:

                    schedule_instance.status = ScheduleInstance.STATUS_ERROR
                    schedule_instance.save()

                    _l.info('Schedule: master_user=%s, next_run_at=%s. Error',
                            master_user.id, s.next_run_at)

                    _l.info('Schedule: Error %s' % e)

                    pass

        s.last_run_at = timezone.now()
        s.save(update_fields=['last_run_at'])

    if procedures_count:
        _l.info('Schedules Finished. Procedures initialized: %s' % procedures_count)
