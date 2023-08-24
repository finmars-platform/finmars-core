import json

import django_filters
from django_filters.rest_framework import FilterSet
from django_filters.fields import Lookup

from poms.common.filters import NoOpFilter, CharFilter, CharExactFilter, ModelExtMultipleChoiceFilter
from poms.common.views import AbstractModelViewSet
from poms.history.filters import HistoryQueryFilter, HistoryActionFilter, HistoryMemberFilter, HistoryContentTypeFilter, \
    HistoryDateRangeFilter
from poms.history.models import HistoricalRecord
from poms.history.serializers import HistoricalRecordSerializer
from poms.users.filters import OwnerByMasterUserFilter
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied

from poms.users.models import Member

import logging
_l = logging.getLogger('poms.history')

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
    created = django_filters.DateFromToRangeFilter()

    class Meta:
        model = HistoricalRecord
        fields = []


# TODO probably exclude data from list view

class HistoricalRecordViewSet(AbstractModelViewSet):
    queryset = HistoricalRecord.objects.select_related(
        'master_user',
        'member',
        'content_type'
    )
    serializer_class = HistoricalRecordSerializer
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        HistoryDateRangeFilter,
        HistoryQueryFilter,
        HistoryActionFilter,
        HistoryMemberFilter,
        HistoryContentTypeFilter,
    ]
    filter_class = HistoricalRecordFilterSet

    ordering_fields = [
        'created', 'user_code', 'member'
    ]

    @action(detail=True, methods=['get'], url_path='data')
    def get_data(self, request, pk):
        instance = self.get_object()
        return Response(json.loads(instance.data))

    @action(detail=False, methods=['get'], url_path='content-types')
    def get_content_types(self, request):

        result = {
            'results': []
        }

        items = HistoricalRecord.objects.select_related('content_type').order_by().values('content_type__app_label', 'content_type__model').distinct()

        # _l.info('items %s' % items)

        for item in items:

            result['results'].append({
                'key': item['content_type__app_label'] + '.' + item['content_type__model']
            })

        return Response(result)

    def create(self, request, *args, **kwargs):

        raise PermissionDenied("History could not be created")

    def update(self, request, *args, **kwargs):

        raise PermissionDenied("History could not be updated")

    def perform_destroy(self, request, *args, **kwargs):

        raise PermissionDenied("History could not be deleted")


