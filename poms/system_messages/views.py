from django_filters.rest_framework import FilterSet


from poms.common.filters import CharFilter

from poms.common.views import AbstractModelViewSet


from poms.users.filters import OwnerByMasterUserFilter

from poms.system_messages.models import SystemMessage
from poms.system_messages.serializers import SystemMessageSerializer

from logging import getLogger

_l = getLogger('poms.system_messages')


class SystemMessageFilterSet(FilterSet):
    text = CharFilter()

    class Meta:
        model = SystemMessage
        fields = []


class MessageViewSet(AbstractModelViewSet):
    queryset = SystemMessage.objects
    serializer_class = SystemMessageSerializer
    filter_class = SystemMessageFilterSet
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    permission_classes = AbstractModelViewSet.permission_classes + [

    ]
    ordering_fields = [
        'created', 'level', 'status', 'source',
    ]
