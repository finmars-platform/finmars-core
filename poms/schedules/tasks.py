from celery import shared_task
from django.utils import timezone
from django.conf import settings

import logging

from poms.pricing.handlers import PricingProcedureProcess
from poms.procedures.handlers import RequestDataFileProcedureProcess
from poms.procedures.models import RequestDataFileProcedure, PricingProcedure
from poms.schedules.models import Schedule, ScheduleInstance
from poms.system_messages.handlers import send_system_message

_l = logging.getLogger('poms.schedules')


@shared_task(name='schedules.process_procedure_async', bind=True, ignore_result=True)
def process_procedure_async(self, procedure, master_user, schedule_instance):
    _l.info("Schedule: Subprocess process. Master User: %s. Procedure: %s" % (master_user, procedure.type))

    if procedure.type == 'pricing':

        try:

            item = PricingProcedure.objects.get(master_user=master_user, user_code=procedure.user_code)

            date_from = None
            date_to = None

            if schedule_instance.data:
                if 'pl_first_date' in schedule_instance.data:
                    date_from = schedule_instance.data['date_from']
                    if 'report_date' in schedule_instance.data:
                        date_to = schedule_instance.data['report_date']
                elif 'report_date' in schedule_instance.data:
                    date_from = schedule_instance.data['report_date']
                    date_to = schedule_instance.data['report_date']
                elif 'begin_date' in schedule_instance.data:
                    date_from = schedule_instance.data['begin_date']
                    if 'end_date' in schedule_instance.data:
                        date_to = schedule_instance.data['end_date']

            instance = PricingProcedureProcess(procedure=item, master_user=master_user,
                                               schedule_instance=schedule_instance, date_from=date_from, date_to=date_to)
            instance.process()

        except PricingProcedure.DoesNotExist:

            _l.info("Can't find Pricing Procedure %s" % procedure.user_code)

    if procedure.type == 'data_provider':

        try:

            item = RequestDataFileProcedure.objects.get(master_user=master_user, user_code=procedure.user_code)

            instance = RequestDataFileProcedureProcess(procedure=item, master_user=master_user,
                                                       schedule_instance=schedule_instance)
            instance.process()

        except RequestDataFileProcedure.DoesNotExist:

            _l.info("Can't find Request Data File Procedure %s" % procedure.user_code)


@shared_task(name='schedules.process', bind=True, ignore_result=True)
def process(self):
    schedule_qs = Schedule.objects.select_related('master_user').filter(
        is_enabled=True, next_run_at__lte=timezone.now()
    )

    _l.info('schedule_qs test %s' % schedule_qs.count())

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

            _l.info('Schedule: schedule procedures count %s' % len(s.procedures.all()))

            schedule_instance = ScheduleInstance(schedule=s, master_user=master_user)
            schedule_instance.save()

            total_procedures = len(s.procedures.all())

            for procedure in s.procedures.all():

                try:

                    _l.info('Schedule : schedule procedure order %s' % procedure.order)

                    if procedure.order == 0:
                        _l.info('Schedule : start processing first procedure')

                        schedule_instance.current_processing_procedure_number = 0
                        schedule_instance.status = ScheduleInstance.STATUS_PENDING
                        schedule_instance.save()

                        send_system_message(master_user=master_user,
                                            source="Schedule Service",
                                            text="Schedule %s. Start processing step %s/%s" % (
                                                s.name, schedule_instance.current_processing_procedure_number,
                                                total_procedures))

                        process_procedure_async.apply_async(kwargs={'procedure': procedure, 'master_user': master_user,
                                                                    'schedule_instance': schedule_instance})

                        _l.info('Schedule: Process first procedure master_user=%s, next_run_at=%s', master_user.id,
                                s.next_run_at)

                        procedures_count = procedures_count + 1

                except Exception as e:

                    schedule_instance.status = ScheduleInstance.STATUS_ERROR
                    schedule_instance.save()

                    send_system_message(master_user=master_user,
                                        source="Schedule Service",
                                        text="Schedule %s. Error occurred" % s.name)

                    _l.info('Schedule: master_user=%s, next_run_at=%s. Error',
                            master_user.id, s.next_run_at)

                    _l.info('Schedule: Error %s' % e)

                    pass

        s.last_run_at = timezone.now()
        s.save(update_fields=['last_run_at'])

    if procedures_count:
        _l.info('Schedules Finished. Procedures initialized: %s' % procedures_count)
