from django_filters.rest_framework import FilterSet
from rest_framework.response import Response
import django_filters
from poms.common.filters import CharFilter

from poms.common.views import AbstractModelViewSet
from poms.system_messages.filters import SystemMessageQueryFilter, SystemMessageOnlyNewFilter

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

    # section = django_filters.MultipleChoiceFilter(choices = SystemMessage.SECTION_CHOICES)
    # type = django_filters.MultipleChoiceFilter(choices = SystemMessage.TYPE_CHOICES)
    action_status = django_filters.MultipleChoiceFilter(choices = SystemMessage.ACTION_STATUS_CHOICES)

    class Meta:
        model = SystemMessage
        fields = []


class MessageViewSet(AbstractModelViewSet):
    queryset = SystemMessage.objects.prefetch_related("members")
    serializer_class = SystemMessageSerializer
    filter_class = SystemMessageFilterSet
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        SystemMessageOnlyNewFilter,
    ]
    permission_classes = AbstractModelViewSet.permission_classes + [

    ]
    ordering_fields = [
        'members__is_pinned', 'created', 'section', 'type', 'action_status', 'title'
    ]

    def list(self, request, *args, **kwargs):

        if not hasattr(request.user, 'master_user'):
            return Response([])

        queryset = self.filter_queryset(self.get_queryset())

        ordering = request.GET.get('ordering')
        type = request.GET.get('type', None)
        section = request.GET.get('section', None)

        if type:
            type = type.split(',')
            queryset = queryset.filter(type__in=type)


        if section:
            section = section.split(',')
            queryset = queryset.filter(section__in=section)

        if ordering:
            queryset = queryset.order_by(
                '-members__is_pinned', ordering)
        else:
            queryset = queryset.order_by(
                '-members__is_pinned')

        queryset = queryset.distinct()

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def get_stats_for_section(self, section, only_new, member):

        # SECTION_GENERAL = 0
        # SECTION_EVENTS = 1
        # SECTION_TRANSACTIONS = 2
        # SECTION_INSTRUMENTS = 3
        # SECTION_DATA = 4
        # SECTION_PRICES = 5
        # SECTION_REPORT = 6
        # SECTION_IMPORT = 7
        # SECTION_ACTIVITY_LOG = 8
        # SECTION_SCHEDULES = 9
        # OTHER = 10

        section_mapping = {
            0: 'General',
            1: 'Events',
            2: 'Transactions',
            3: 'Instruments',
            4: 'Data',
            5: 'Prices',
            6: 'Report',
            7: 'Import',
            8: 'Activity Log',
            9: 'Schedules',
            10: 'Other'
        }

        if only_new:

            stats = {
                'name':  section_mapping[section],
                'errors': SystemMessage.objects.filter(section=section, type=SystemMessage.TYPE_ERROR, members__member=member, members__is_read=False).count(),
                'warning': SystemMessage.objects.filter(section=section, type=SystemMessage.TYPE_WARNING, members__member=member, members__is_read=False).count(),
                'information': SystemMessage.objects.filter(section=section, type=SystemMessage.TYPE_INFORMATION, members__member=member, members__is_read=False).count(),
                'success': SystemMessage.objects.filter(section=section, type=SystemMessage.TYPE_SUCCESS, members__member=member, members__is_read=False).count(),
            }
        else:

            stats = {
                'name':  section_mapping[section],
                'errors': SystemMessage.objects.filter(section=section, type=SystemMessage.TYPE_ERROR, members__member=member).count(),
                'warning': SystemMessage.objects.filter(section=section, type=SystemMessage.TYPE_WARNING, members__member=member).count(),
                'information': SystemMessage.objects.filter(section=section, type=SystemMessage.TYPE_INFORMATION, members__member=member).count(),
                'success': SystemMessage.objects.filter(section=section, type=SystemMessage.TYPE_SUCCESS, members__member=member).count(),
            }


        return stats

    @action(detail=False, methods=['get'], url_path='stats')
    def stats(self, request, pk=None):

        only_new = request.query_params.get('only_new', False)

        if only_new == 'True':
            only_new = True

        result = []

        member = request.user.member

        # SECTION_GENERAL = 0
        # SECTION_EVENTS = 1
        # SECTION_TRANSACTIONS = 2
        # SECTION_INSTRUMENTS = 3
        # SECTION_DATA = 4
        # SECTION_PRICES = 5
        # SECTION_REPORT = 6
        # SECTION_IMPORT = 7
        # SECTION_ACTIVITY_LOG = 8
        # SECTION_SCHEDULES = 9

        result.append(self.get_stats_for_section(SystemMessage.SECTION_GENERAL, only_new, member))
        result.append(self.get_stats_for_section(SystemMessage.SECTION_EVENTS, only_new, member))
        result.append(self.get_stats_for_section(SystemMessage.SECTION_TRANSACTIONS, only_new, member))
        result.append(self.get_stats_for_section(SystemMessage.SECTION_INSTRUMENTS, only_new, member))
        result.append(self.get_stats_for_section(SystemMessage.SECTION_DATA, only_new, member))
        result.append(self.get_stats_for_section(SystemMessage.SECTION_PRICES, only_new, member))
        result.append(self.get_stats_for_section(SystemMessage.SECTION_REPORT, only_new, member))
        result.append(self.get_stats_for_section(SystemMessage.SECTION_IMPORT, only_new, member))
        result.append(self.get_stats_for_section(SystemMessage.SECTION_ACTIVITY_LOG, only_new, member))
        result.append(self.get_stats_for_section(SystemMessage.SECTION_SCHEDULES, only_new, member))
        result.append(self.get_stats_for_section(SystemMessage.SECTION_OTHER, only_new, member))

        # [
        #     {
        #         name: 'Events',
        #         errors: 123,
        #         warning: 123,
        #         information: 123,
        #         success: 123,
        #     }
        # ]




        return Response(result)

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

        print('mark_as_read ids %s' % ids)

        if not isinstance(ids, list):
            ids = [ids]

        messages = SystemMessage.objects.filter(id__in=ids)

        for message in messages:

            for member_message in message.members.all():
                member_message.is_read = True
                member_message.save()


        return Response({'status': 'ok'})

    @action(detail=False, methods=['post'], url_path='mark-as-solved', serializer_class=SystemMessageActionSerializer)
    def mark_as_solved(self, request, pk=None):

        ids = request.data['ids']

        if not isinstance(ids, list):
            ids = [ids]

        messages = SystemMessage.objects.filter(id__in=ids)

        for message in messages:

            message.action_status = SystemMessage.ACTION_STATUS_SOLVED
            message.save()


        return Response({'status': 'ok'})

    @action(detail=False, methods=['post'], url_path='pin', serializer_class=SystemMessageActionSerializer)
    def pin(self, request, pk=None):

        ids = request.data['ids']

        if not isinstance(ids, list):
            ids = [ids]

        messages = SystemMessage.objects.filter(id__in=ids)

        for message in messages:

            for member_message in message.members.all():
                member_message.is_pinned = True
                member_message.save()

        return Response({'status': 'ok'})

    @action(detail=False, methods=['post'], url_path='unpin', serializer_class=SystemMessageActionSerializer)
    def unpin(self, request, pk=None):

        ids = request.data['ids']

        if not isinstance(ids, list):
            ids = [ids]

        messages = SystemMessage.objects.filter(id__in=ids)

        for message in messages:

            for member_message in message.members.all():
                member_message.is_pinned = False
                member_message.save()

        return Response({'status': 'ok'})
