import django_filters
from django_filters import FilterSet
from django_filters.fields import Lookup

from poms.common.filters import NoOpFilter, CharFilter, CharExactFilter
from poms.common.views import AbstractModelViewSet
from poms.history.models import HistoricalRecord
from poms.history.serializers import HistoricalRecordSerializer
from poms.users.filters import OwnerByMasterUserFilter


class ContentTypeFilter(django_filters.CharFilter):
    def filter(self, qs, value):

        if isinstance(value, Lookup):
            lookup = str(value.lookup_type)
            value = value.value
        else:
            lookup = self.lookup_expr
        if value in ([], (), {}, None, ''):
            return qs
        if self.distinct:
            qs = qs.distinct()
        try:
            app_label, model = value.split('.', maxsplit=1)
        except ValueError:
            # skip on invalid value
            app_label, model = '', ''
        qs = self.get_method(qs)(**{
            'content_type__app_label': app_label,
            'content_type__model__%s' % lookup: model,
        })
        return qs


class HistoricalRecordFilterSet(FilterSet):
    id = NoOpFilter()
    user_code = CharExactFilter()

    class Meta:
        model = HistoricalRecord
        fields = []


# TODO probably exclude data from list view

class HistoricalRecordViewSet(AbstractModelViewSet):
    queryset = HistoricalRecord.objects.select_related(
        'master_user',
    )
    serializer_class = HistoricalRecordSerializer
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    filter_class = HistoricalRecordFilterSet

    ordering_fields = [
        'created', 'user_code', 'member'
    ]
