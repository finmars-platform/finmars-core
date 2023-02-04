from django_filters import FilterSet

from poms.common.filters import NoOpFilter
from poms.common.views import AbstractModelViewSet
from poms.history.models import HistoricalRecord
from poms.history.serializers import HistoricalRecordSerializer
from poms.users.filters import OwnerByMasterUserFilter


class HistoricalRecordFilterSet(FilterSet):
    id = NoOpFilter()

    class Meta:
        model = HistoricalRecord
        fields = []


class HistoricalRecordViewSet(AbstractModelViewSet):
    queryset = HistoricalRecord.objects.select_related(
        'master_user',
    )
    serializer_class = HistoricalRecordSerializer
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    filter_class = HistoricalRecordFilterSet
