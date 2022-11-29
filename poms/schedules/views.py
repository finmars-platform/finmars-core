import traceback
from logging import getLogger

from django_filters import FilterSet
from rest_framework.decorators import action
from rest_framework.response import Response

from poms.common.filters import CharFilter
from poms.common.views import AbstractModelViewSet
from poms.schedules.models import Schedule
from poms.schedules.serializers import ScheduleSerializer
from poms.users.filters import OwnerByMasterUserFilter

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

            from poms.schedules.tasks import process
            process.apply_async(kwargs={'schedule_user_code': schedule.user_code})

            return Response({"status": "ok"})

        except Exception as e:

            _l.error("Exception e %s" % e)
            _l.error("Exception traceback %s" % traceback.format_exc())

            return Response(e)
