from django_filters.rest_framework import FilterSet
from rest_framework.response import Response
import django_filters
from poms.common.filters import CharFilter

from poms.common.views import AbstractModelViewSet
from poms.system_messages.filters import SystemMessageQueryFilter

from poms.users.filters import OwnerByMasterUserFilter

from poms.system_messages.models import SystemMessage
from poms.system_messages.serializers import SystemMessageSerializer, SystemMessageActionSerializer

from rest_framework.views import APIView


from logging import getLogger

_l = getLogger('poms.system_messages')
from rest_framework.decorators import action


class SystemMessageFilterSet(FilterSet):
    title = CharFilter()
    description = CharFilter()
    created = django_filters.DateFromToRangeFilter()
    query = SystemMessageQueryFilter(label='Query')

    section = django_filters.MultipleChoiceFilter(choices = SystemMessage.SECTION_CHOICES)
    type = django_filters.MultipleChoiceFilter(choices = SystemMessage.TYPE_CHOICES)
    action_status = django_filters.MultipleChoiceFilter(choices = SystemMessage.ACTION_STATUS_CHOICES)

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
        'created', 'section', 'type', 'action_status', 'title'
    ]

    @action(detail=False, methods=['get'], url_path='stats')
    def stats(self, request, pk=None):

        only_new = request.query_params.get('only_new', False)

        # [
        #     {
        #         name: 'Events',
        #         errors: 123,
        #         warning: 123,
        #         information: 123,
        #         success: 123,
        #     }
        # ]

        return Response({'status': 'ok'})

    @action(detail=False, methods=['get'], url_path='mark-all-as-read')
    def mark_all_as_read(self, request, pk=None):

        member = request.user.member

        messages = SystemMessage.objects.all()

        for message in messages:

            for member_message in message.members.all():
                if member_message.member_id == member.id:
                    member_message.is_read = True
                    member_message.save()

        return Response({'status': 'ok'})

    @action(detail=False, methods=['post'], url_path='mark-as-read', serializer_class=SystemMessageActionSerializer)
    def mark_as_read(self, request, pk=None):

        ids = request.data['ids']

        messages = SystemMessage.objects.filter(id__in=ids)

        for message in messages:

            for member_message in message.members.all():
                member_message.is_read = True
                member_message.save()


        return Response({'status': 'ok'})

    @action(detail=False, methods=['post'], url_path='mark-as-solved', serializer_class=SystemMessageActionSerializer)
    def mark_as_solved(self, request, pk=None):

        ids = request.data['ids']

        messages = SystemMessage.objects.filter(id__in=ids)

        for message in messages:

            message.action_status = SystemMessage.ACTION_STATUS_SOLVED
            message.save()


        return Response({'status': 'ok'})

    @action(detail=False, methods=['post'], url_path='pin', serializer_class=SystemMessageActionSerializer)
    def pin(self, request, pk=None):

        ids = request.data['ids']

        messages = SystemMessage.objects.filter(id__in=ids)

        for message in messages:

            for member_message in message.members.all():
                member_message.is_pinned = True
                member_message.save()

        return Response({'status': 'ok'})

    @action(detail=False, methods=['post'], url_path='unpin', serializer_class=SystemMessageActionSerializer)
    def pin(self, request, pk=None):

        ids = request.data['ids']

        messages = SystemMessage.objects.filter(id__in=ids)

        for message in messages:

            for member_message in message.members.all():
                member_message.is_pinned = False
                member_message.save()

        return Response({'status': 'ok'})
