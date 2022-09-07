import traceback

from django_filters import FilterSet
from rest_framework.decorators import action
from rest_framework.response import Response

from poms.common.filters import CharFilter
from poms.common.views import AbstractModelViewSet

from django.utils import timezone
from django.conf import settings


from poms.schedules.models import Schedule, ScheduleInstance
from poms.schedules.serializers import RunScheduleSerializer, ScheduleSerializer
from poms.schedules.tasks import process_procedure_async
from poms.system_messages.handlers import send_system_message

from poms.users.filters import OwnerByMasterUserFilter

from logging import getLogger

_l = getLogger('poms.schedules')


class ScheduleFilterSet(FilterSet):
    user_code = CharFilter()
    name = CharFilter()

    class Meta:
        model = Schedule
        fields = []


class ScheduleViewSet(AbstractModelViewSet):
    queryset = Schedule.objects
    serializer_class = ScheduleSerializer
    filter_class = ScheduleFilterSet
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    # permission_classes = AbstractModelViewSet.permission_classes + [
    #     PomsConfigurationPermission
    # ]
    permission_classes = []

    @action(detail=True, methods=['post'], url_path='run-schedule', serializer_class=ScheduleSerializer)
    def run_schedule(self, request, pk=None):

        try:

            _l.info("Run Procedure %s" % pk)

            _l.info("Run Procedure data %s" % request.data)

            schedule = Schedule.objects.get(pk=pk)

            master_user = request.user.master_user

            with timezone.override(master_user.timezone or settings.TIME_ZONE):
                next_run_at = timezone.localtime(schedule.next_run_at)
                schedule.schedule(save=True)

                _l.info('Schedule: master_user=%s, next_run_at=%s. STARTED',
                        master_user.id, schedule.next_run_at)

                _l.info('Schedule: procedures count %s' % len(schedule.procedures.all()))

                schedule_instance = ScheduleInstance(schedule=schedule, master_user=master_user)
                schedule_instance.save()

                total_procedures = len(schedule.procedures.all())

                for procedure in schedule.procedures.all():

                    try:

                        if procedure.order == 0:

                            schedule_instance.current_processing_procedure_number = 0
                            schedule_instance.status = ScheduleInstance.STATUS_PENDING
                            schedule_instance = schedule_instance.save()

                            send_system_message(master_user=master_user,
                                                performed_by="System",
                                                section='schedules',
                                                description="Schedule %s. Start processing step %s/%s" % (schedule.name, schedule_instance.current_processing_procedure_number, total_procedures))


                            process_procedure_async.apply_async(kwargs={'procedure_id':procedure.id, 'master_user_id':master_user.id, 'schedule_instance_id': schedule_instance.id})

                            _l.info('Schedule: Process first procedure master_user=%s, next_run_at=%s', master_user.id, schedule.next_run_at)

                    except Exception as e:

                        schedule_instance.status = ScheduleInstance.STATUS_ERROR
                        schedule_instance.save()

                        _l.info('Schedule: master_user=%s, next_run_at=%s. Error',
                                master_user.id, schedule.next_run_at)

                        _l.info('Schedule: Error %s' % e)

                        send_system_message(master_user=master_user,
                                            performed_by="System",
                                            type='error',
                                            section='schedules',
                                            description="Schedule %s. Error occurred" % schedule.name)

                        pass

            schedule.last_run_at = timezone.now()
            schedule.save(update_fields=['last_run_at'])

            return Response({"status": "ok"})

        except Exception as e:

            _l.error("Exception e %s" % e)
            _l.error("Exception traceback %s" % traceback.format_exc())

            return Response(e)
