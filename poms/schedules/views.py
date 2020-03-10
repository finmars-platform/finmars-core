from django_filters import FilterSet

from poms.common.filters import CharFilter
from poms.common.views import AbstractModelViewSet


from poms.schedules.models import PricingSchedule
from poms.schedules.serializers import PricingScheduleSerializer

from poms.users.filters import OwnerByMasterUserFilter


class PricingScheduleFilterSet(FilterSet):
    user_code = CharFilter()
    name = CharFilter()

    class Meta:
        model = PricingSchedule
        fields = []

class PricingScheduleViewSet(AbstractModelViewSet):
    queryset = PricingSchedule.objects
    serializer_class = PricingScheduleSerializer
    filter_class = PricingScheduleFilterSet
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    # permission_classes = AbstractModelViewSet.permission_classes + [
    #     PomsConfigurationPermission
    # ]
    permission_classes = []


