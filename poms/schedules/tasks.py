import logging
import traceback

from django.conf import settings
from django.utils import timezone

from poms.celery_tasks import finmars_task
from poms.procedures.handlers import DataProcedureProcess, ExpressionProcedureProcess
from poms.procedures.models import (
    ExpressionProcedure,
    PricingProcedure,
    RequestDataFileProcedure,
)
from poms.schedules.models import Schedule, ScheduleInstance, ScheduleProcedure
from poms.system_messages.handlers import send_system_message
from poms.users.models import MasterUser, Member

_l = logging.getLogger("poms.schedules")


@finmars_task(name="schedules.process_procedure_async", bind=True)
def process_procedure_async(
    self, procedure_id, master_user_id, schedule_instance_id, *args, **kwargs
):
    try:
        _l.info(
            f"Schedule: Subprocess process. Master User: {master_user_id}."
            f" Procedure: {procedure_id}"
        )

        procedure = ScheduleProcedure.objects.get(id=procedure_id)

        _l.info(f"Schedule: Subprocess process.  Procedure type: {procedure.type}")
        master_user = MasterUser.objects.get(id=master_user_id)
        schedule_instance = ScheduleInstance.objects.get(id=schedule_instance_id)

        schedule = Schedule.objects.get(id=schedule_instance.schedule_id)

        owner = Member.objects.get(username=schedule.owner.username)

        context = {
            "execution_context": {
                "source": "schedule",
                "actor": schedule.user_code,
                "schedule_object": {"id": schedule.id, "user_code": schedule.user_code},
            }
        }

        if procedure.type == "pricing_procedure":
            try:
                item = PricingProcedure.objects.get(
                    master_user=master_user, user_code=procedure.user_code
                )

                date_from = None
                date_to = None

                if schedule.data:
                    if "pl_first_date" in schedule.data:
                        date_from = schedule.data["date_from"]
                        if "report_date" in schedule.data:
                            date_to = schedule.data["report_date"]
                    elif "report_date" in schedule_instance.data:
                        date_from = schedule.data["report_date"]
                        date_to = schedule.data["report_date"]
                    elif "begin_date" in schedule.data:
                        date_from = schedule.data["begin_date"]
                        if "end_date" in schedule.data:
                            date_to = schedule.data["end_date"]

                # TODO pricingv2 do something? probably all deprecated
                # TODO delete in 1.9.0?
                instance = None
                # instance = PricingProcedureProcess(
                #     procedure=item,
                #     master_user=master_user,
                #     member=finmars_bot,
                #     schedule_instance=schedule_instance,
                #     date_from=date_from,
                #     context=context,
                #     date_to=date_to,
                # )
                # instance.process()

            except Exception as e:
                send_system_message(
                    master_user=master_user,
                    action_status="required",
                    type="warning",
                    title=f"Schedule Pricing Procedure Failed. User Code: {procedure.user_code}",
                    description=str(e),
                )

                _l.info(
                    f"Can't find Pricing Procedure error {e}  user_code {procedure.user_code}"
                )

        if procedure.type == "data_procedure":
            try:
                item = RequestDataFileProcedure.objects.get(
                    master_user=master_user, user_code=procedure.user_code
                )

                instance = DataProcedureProcess(
                    procedure=item,
                    master_user=master_user,
                    member=owner,
                    context=context,
                    schedule_instance=schedule_instance,
                )
                instance.process()

            except Exception as e:
                send_system_message(
                    master_user=master_user,
                    action_status="required",
                    type="warning",
                    title=f"Schedule Data Procedure Failed. User Code: {procedure.user_code}",
                    description=str(e),
                )

                _l.info(f"Can't find Request Data File Procedure {procedure.user_code}")

        if procedure.type == "expression_procedure":
            try:
                item = ExpressionProcedure.objects.get(
                    master_user=master_user, user_code=procedure.user_code
                )
                instance = ExpressionProcedureProcess(
                    procedure=item,
                    master_user=master_user,
                    member=owner,
                    context=context,
                )
                instance.process()

            except Exception as e:
                send_system_message(
                    master_user=master_user,
                    action_status="required",
                    type="warning",
                    title=f"Schedule Expression Procedure Failed. User Code: {procedure.user_code}",
                    description=str(e),
                )

                _l.info(f"Can't find ExpressionProcedure {procedure.user_code}")

    except Exception as e:
        _l.error(f"process_procedure_async e {e} traceback {traceback.format_exc()}")


@finmars_task(name="schedules.process", bind=True)
def process(self, schedule_user_code, *args, **kwargs):
    _l.info(f"schedule_user_code {schedule_user_code}")

    s = Schedule.objects.select_related("master_user").get(user_code=schedule_user_code)

    procedures_count = 0

    master_user = s.master_user

    try:
        with timezone.override(master_user.timezone or settings.TIME_ZONE):
            s.schedule(save=True)

            _l.info(
                "Schedule: master_user=%s, next_run_at=%s. STARTED",
                master_user.id,
                s.next_run_at,
            )

            _l.info(f"Schedule: schedule procedures count {len(s.procedures.all())}")

            schedule_instance = ScheduleInstance(schedule=s, master_user=master_user)
            schedule_instance.save()

            total_procedures = len(s.procedures.all())

            for procedure in s.procedures.all():
                try:
                    _l.info(f"Schedule : schedule procedure order {procedure.order}")

                    if procedure.order == 0:
                        _l.info("Schedule : start processing first procedure")

                        schedule_instance.current_processing_procedure_number = 0
                        schedule_instance.status = ScheduleInstance.STATUS_PENDING
                        schedule_instance.save()

                        send_system_message(
                            master_user=master_user,
                            performed_by="System",
                            section="schedules",
                            description=f"Schedule {s.name}. Start processing step {schedule_instance.current_processing_procedure_number}/{total_procedures}",
                        )

                        process_procedure_async.apply_async(
                            kwargs={
                                "procedure_id": procedure.id,
                                "master_user_id": master_user.id,
                                "schedule_instance_id": schedule_instance.id,
                                "context": {
                                    "space_code": master_user.space_code,
                                    "realm_code": master_user.realm_code,
                                },
                            }
                        )

                        _l.info(
                            "Schedule: Process first procedure master_user=%s, next_run_at=%s",
                            master_user.id,
                            s.next_run_at,
                        )

                        procedures_count += 1

                except Exception as e:
                    send_system_message(
                        master_user=master_user,
                        action_status="required",
                        type="warning",
                        title=f"Schedule Instance Failed. User Code: {schedule_user_code}",
                        description=str(e),
                    )

                    schedule_instance.status = ScheduleInstance.STATUS_ERROR
                    schedule_instance.save()

                    send_system_message(
                        master_user=master_user,
                        performed_by="System",
                        type="error",
                        section="schedules",
                        description=f"Schedule {s.name}. Error occurred",
                    )

                    _l.info(
                        "Schedule: master_user=%s, next_run_at=%s. Error",
                        master_user.id,
                        s.next_run_at,
                    )

                    _l.info(f"Schedule: Error {e}")

        s.last_run_at = timezone.now()
        s.save(update_fields=["last_run_at"])

        _l.info(f"Schedule {s} executed successfully")

        if procedures_count:
            _l.info(f"Schedules Finished. Procedures initialized: {procedures_count}")

    except Exception as e:
        send_system_message(
            master_user=master_user,
            action_status="required",
            type="error",
            title=f"Schedule Failed. User Code: {schedule_user_code}",
            description=str(e),
        )

        _l.error(f"schedules.process. error {e} traceback {traceback.format_exc()}")
