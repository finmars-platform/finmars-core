from django_filters import FilterSet
from rest_framework.decorators import action

from poms.common.filters import CharFilter
from poms.common.views import AbstractModelViewSet


from poms.schedules.models import  Schedule
from poms.schedules.serializers import RunScheduleSerializer, ScheduleSerializer


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

    # TODO Disable after Tests
    # @action(detail=False, methods=['get', 'post'], url_path='manual-run-schedules', serializer_class=RunScheduleSerializer)
    # def manual_run_schedules(self, request, pk=None):
    #
    #     if request.method == 'POST':
    #
    #         schedules_ids = None
    #
    #         if request.data['schedules']:
    #
    #             schedules_ids = request.data['schedules'].split(',')
    #
    #             for i in range(0, len(schedules_ids)):
    #                 schedules_ids[i] = int(schedules_ids[i])
    #
    #         schedule_qs = PricingSchedule.objects.select_related('master_user').filter(
    #             id__in=schedules_ids
    #         )
    #
    #         _l.info("Manual Run Schedules: Schedules found: %s" % schedule_qs.count())
    #
    #         process_pricing_procedures_schedules.apply_async(kwargs={'schedules': schedule_qs})
    #
    #
    #     return Response({'status:' 'ok'})
    #
