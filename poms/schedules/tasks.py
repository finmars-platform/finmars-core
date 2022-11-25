import traceback

from celery import shared_task
from django.utils import timezone
from django.conf import settings

import logging

from poms.pricing.handlers import PricingProcedureProcess
from poms.procedures.handlers import DataProcedureProcess, ExpressionProcedureProcess
from poms.procedures.models import RequestDataFileProcedure, PricingProcedure, ExpressionProcedure
from poms.schedules.models import Schedule, ScheduleInstance, ScheduleProcedure
from poms.system_messages.handlers import send_system_message
from poms.users.models import Member, MasterUser

_l = logging.getLogger('poms.schedules')


@shared_task(name='schedules.process_procedure_async', bind=True)
def process_procedure_async(self, procedure_id, master_user_id, schedule_instance_id):

    try:
        _l.info("Schedule: Subprocess process. Master User: %s. Procedure: %s" % (master_user_id, procedure_id))

        procedure = ScheduleProcedure.objects.get(id=procedure_id)

        _l.info("Schedule: Subprocess process.  Procedure type: %s" % (procedure.type))
        master_user = MasterUser.objects.get(id=master_user_id)
        schedule_instance = ScheduleInstance.objects.get(id=schedule_instance_id)

        schedule = Schedule.objects.get(id=schedule_instance.schedule_id)

        owner_member = Member.objects.filter(master_user=master_user, is_owner=True)[0]

        if procedure.type == 'pricing_procedure':

            try:

                item = PricingProcedure.objects.get(master_user=master_user, user_code=procedure.user_code)

                date_from = None
                date_to = None

                if schedule.data:
                    if 'pl_first_date' in schedule.data:
                        date_from = schedule.data['date_from']
                        if 'report_date' in schedule.data:
                            date_to = schedule.data['report_date']
                    elif 'report_date' in schedule_instance.data:
                        date_from = schedule.data['report_date']
                        date_to = schedule.data['report_date']
                    elif 'begin_date' in schedule.data:
                        date_from = schedule.data['begin_date']
                        if 'end_date' in schedule.data:
                            date_to = schedule.data['end_date']

                instance = PricingProcedureProcess(procedure=item, master_user=master_user, member=owner_member,
                                                   schedule_instance=schedule_instance, date_from=date_from, date_to=date_to)
                instance.process()

            except Exception as e:

                _l.info("Can't find Pricing Procedure error %s" % e)
                _l.info("Can't find Pricing Procedure  user_code %s" % procedure.user_code)

        if procedure.type == 'data_procedure':

            try:

                item = RequestDataFileProcedure.objects.get(master_user=master_user, user_code=procedure.user_code)

                instance = DataProcedureProcess(procedure=item, master_user=master_user,
                                                           member=owner_member,
                                                           schedule_instance=schedule_instance)
                instance.process()

            except RequestDataFileProcedure.DoesNotExist:

                _l.info("Can't find Request Data File Procedure %s" % procedure.user_code)

        if procedure.type == 'expression_procedure':

            try:

                item = ExpressionProcedure.objects.get(master_user=master_user, user_code=procedure.user_code)

                instance = ExpressionProcedureProcess(procedure=item, master_user=master_user, member=owner_member)
                instance.process()

            except ExpressionProcedure.DoesNotExist:

                _l.info("Can't find ExpressionProcedure %s" % procedure.user_code)

    except Exception as e:
        _l.error('process_procedure_async e %s' % e)
        _l.error('process_procedure_async traceback %s' % traceback.format_exc())

@shared_task(name='schedules.process', bind=True)
def process(self, schedule_user_code):

    try:

        _l.info('schedule_user_code %s' % schedule_user_code)

        s = Schedule.objects.select_related('master_user').get(
            user_code=schedule_user_code
        )

        procedures_count = 0

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
                                            performed_by='System',
                                            section='schedules',
                                            description="Schedule %s. Start processing step %s/%s" % (
                                                s.name, schedule_instance.current_processing_procedure_number,
                                                total_procedures))

                        process_procedure_async.apply_async(kwargs={'procedure_id': procedure.id, 'master_user_id': master_user.id,
                                                                    'schedule_instance_id': schedule_instance.id})

                        _l.info('Schedule: Process first procedure master_user=%s, next_run_at=%s', master_user.id,
                                s.next_run_at)

                        procedures_count = procedures_count + 1

                except Exception as e:

                    schedule_instance.status = ScheduleInstance.STATUS_ERROR
                    schedule_instance.save()

                    send_system_message(master_user=master_user,
                                        performed_by='System',
                                        type='error',
                                        section='schedules',
                                        description="Schedule %s. Error occurred" % s.name)

                    _l.info('Schedule: master_user=%s, next_run_at=%s. Error',
                            master_user.id, s.next_run_at)

                    _l.info('Schedule: Error %s' % e)

                    pass

        s.last_run_at = timezone.now()
        s.save(update_fields=['last_run_at'])

        _l.info("Schedule %s executed successfuly" % s)

        if procedures_count:
            _l.info('Schedules Finished. Procedures initialized: %s' % procedures_count)

    except Exception as e:
        _l.error('schedules.process. error %s' % e)
        _l.error('schedules.process. traceback %s' % traceback.format_exc())
