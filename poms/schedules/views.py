from logging import getLogger

from django_filters import FilterSet
from rest_framework.decorators import action
from rest_framework.response import Response

from poms.common.filters import CharFilter
from poms.common.views import AbstractModelViewSet
from poms.schedules.models import Schedule
from poms.schedules.serializers import ScheduleSerializer
from poms.schedules.tasks import process
from poms.users.filters import OwnerByMasterUserFilter

_l = getLogger("poms.schedules")


class ScheduleFilterSet(FilterSet):
    user_code = CharFilter()
    name = CharFilter()

    class Meta:
        model = Schedule
        fields = []


class ScheduleViewSet(AbstractModelViewSet):
    queryset = Schedule.objects
    serializer_class = ScheduleSerializer
    permission_classes = []
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    filter_class = ScheduleFilterSet

    @action(detail=True, methods=["post"], url_path="run-schedule")
    def run_schedule(self, request, *args, **kwargs):
        schedule = self.get_object()
        process.apply_async(
            kwargs={
                "schedule_user_code": schedule.user_code,
                "context": {"space_code": request.space_code, "realm_code": request.realm_code},
            }
        )
        return Response({"status": "ok"})
