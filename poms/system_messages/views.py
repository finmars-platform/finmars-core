from logging import getLogger

import django_filters
from django.db.models import Q
from django_filters.rest_framework import FilterSet
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from poms.common.filters import CharFilter

from poms.common.views import AbstractModelViewSet
from poms.system_messages.filters import (
    OwnerBySystemMessageMember,
    SystemMessageOnlyNewFilter,
)
from poms.system_messages.handlers import (
    forward_create_channel_to_service,
    forward_create_notification_to_service,
    forward_get_all_channels_to_service,
    forward_get_all_subscription_types_to_service,
    forward_get_categories_to_service,
    forward_get_statuses_to_service,
    forward_get_user_notifications,
    forward_get_user_subscriptions_to_service,
    forward_join_channel_to_service,
    forward_leave_channel_to_service,
    forward_partial_update_notification_to_service,
    forward_update_notification_to_service,
    forward_update_user_subscriptions_to_service,
    forward_user_subscribed_channels_to_service,
)
from poms.system_messages.models import SystemMessage, SystemMessageComment
from poms.system_messages.serializers import (
    SystemMessageActionSerializer,
    SystemMessageSerializer,
)
from poms.users.filters import OwnerByMasterUserFilter

_l = getLogger("poms.system_messages")


class SystemMessageFilterSet(FilterSet):
    title = CharFilter()
    description = CharFilter()
    created_at = django_filters.DateFromToRangeFilter()

    class Meta:
        model = SystemMessage
        fields = []


class SystemMessageViewSet(AbstractModelViewSet):
    queryset = SystemMessage.objects.select_related("master_user", "linked_event").prefetch_related(
        "comments", "attachments", "members"
    )
    serializer_class = SystemMessageSerializer

    filter_class = SystemMessageFilterSet
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
        OwnerBySystemMessageMember,
        SystemMessageOnlyNewFilter,
    ]
    permission_classes = AbstractModelViewSet.permission_classes + []
    ordering_fields = [
        "members__is_pinned",
        "created_at",
        "section",
        "type",
        "action_status",
        "title",
    ]

    def list(self, request, *args, **kwargs):
        if not hasattr(request.user, "master_user"):
            return Response([])

        queryset = self.filter_queryset(self.get_queryset())

        ordering = request.GET.get("ordering", None)
        msg_type = request.GET.get("type", None)
        section = request.GET.get("section", None)
        action_status = request.GET.get("action_status", None)
        query = request.GET.get("query", None)
        page = request.GET.get("page", None)
        only_new = request.GET.get("only_new", "")
        include_workflow = request.GET.get("include_workflow", "")

        if include_workflow != "true":
            queryset = queryset.exclude(title__icontains="Workflow")

        if only_new == "true":
            queryset = queryset.filter(members__is_read=False, members__member=request.user.member)

        queryset = queryset.filter(members__is_pinned=False, members__member=request.user.member)

        if msg_type:
            msg_type = msg_type.split(",")
            queryset = queryset.filter(type__in=msg_type)

        if section:
            section = section.split(",")
            queryset = queryset.filter(section__in=section)

        if action_status:
            action_status = action_status.split(",")
            queryset = queryset.filter(action_status__in=action_status)

        if query:
            queryset = queryset.filter(Q(title__icontains=query) | Q(description__icontains=query))

        if ordering:
            queryset = queryset.order_by(ordering)
        else:
            queryset = queryset.order_by("-created_at")

        if page is None or page == "1":
            pinned_queryset = self.get_queryset().filter(
                members__is_pinned=True,
                members__is_read=True,
                members__member=request.user.member,
            )

            if msg_type:
                pinned_queryset = pinned_queryset.filter(type__in=msg_type)

            if section:
                pinned_queryset = pinned_queryset.filter(section__in=section)

            if query:
                pinned_queryset = pinned_queryset.filter(
                    Q(title__icontains=query) | Q(description__icontains=query)
                )

            if len(pinned_queryset):
                _l.info(f"Inject {len(pinned_queryset)} pinned messages ")
                queryset = pinned_queryset.union(queryset, all=True)
            else:
                queryset = queryset.distinct()

        else:
            queryset = queryset.distinct()

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def get_stats_for_section(
        self,
        section,
        only_new,
        query,
        created_before,
        created_after,
        action_status,
        member,
    ):
        section_mapping = {
            0: "General",
            1: "Events",
            2: "Transactions",
            3: "Instruments",
            4: "Data",
            5: "Prices",
            6: "Report",
            7: "Import",
            8: "Activity Log",
            9: "Schedules",
            10: "Other",
        }

        def get_count(type, is_pinned=False):
            queryset = SystemMessage.objects.filter(section=section, type=type)

            if only_new and not is_pinned:
                queryset = queryset.filter(
                    members__is_read=False,
                    members__is_pinned=False,
                    members__member=member,
                )

            if is_pinned:
                queryset = queryset.filter(members__is_pinned=True, members__member=member)

            if query:
                queryset = queryset.filter(Q(title__icontains=query) | Q(description__icontains=query))

            if created_before:
                queryset = queryset.filter(created_at__lte=created_before)

            if created_after:
                queryset = queryset.filter(created_at__gte=created_after)

            if action_status:
                queryset = queryset.filter(action_status__in=[action_status])

            return queryset.count()

        stats = {
            "id": section,
            "name": section_mapping[section],
            "errors": get_count(SystemMessage.TYPE_ERROR)
            + get_count(SystemMessage.TYPE_ERROR, is_pinned=True),
            "warning": get_count(SystemMessage.TYPE_WARNING)
            + get_count(SystemMessage.TYPE_WARNING, is_pinned=True),
            "information": get_count(SystemMessage.TYPE_INFORMATION)
            + get_count(SystemMessage.TYPE_INFORMATION, is_pinned=True),
            "success": get_count(SystemMessage.TYPE_SUCCESS)
            + get_count(SystemMessage.TYPE_SUCCESS, is_pinned=True),
        }

        return stats

    @action(detail=False, methods=["get"], url_path="stats")
    def stats(self, request, pk=None, realm_code=None, space_code=None):
        only_new = request.query_params.get("only_new", False)
        query = request.query_params.get("query", None)

        created_before = request.query_params.get("created_before", None)
        created_after = request.query_params.get("created_after", None)

        action_status = request.query_params.get("action_status", None)

        if action_status and ("," in action_status):
            action_status = action_status.split(",")

        only_new = only_new == "true"
        member = request.user.member

        result = [
            self.get_stats_for_section(
                SystemMessage.SECTION_EVENTS,
                only_new,
                query,
                created_before,
                created_after,
                action_status,
                member,
            ),
            self.get_stats_for_section(
                SystemMessage.SECTION_TRANSACTIONS,
                only_new,
                query,
                created_before,
                created_after,
                action_status,
                member,
            ),
            self.get_stats_for_section(
                SystemMessage.SECTION_INSTRUMENTS,
                only_new,
                query,
                created_before,
                created_after,
                action_status,
                member,
            ),
            self.get_stats_for_section(
                SystemMessage.SECTION_DATA,
                only_new,
                query,
                created_before,
                created_after,
                action_status,
                member,
            ),
            self.get_stats_for_section(
                SystemMessage.SECTION_PRICES,
                only_new,
                query,
                created_before,
                created_after,
                action_status,
                member,
            ),
            self.get_stats_for_section(
                SystemMessage.SECTION_REPORT,
                only_new,
                query,
                created_before,
                created_after,
                action_status,
                member,
            ),
            self.get_stats_for_section(
                SystemMessage.SECTION_IMPORT,
                only_new,
                query,
                created_before,
                created_after,
                action_status,
                member,
            ),
            self.get_stats_for_section(
                SystemMessage.SECTION_ACTIVITY_LOG,
                only_new,
                query,
                created_before,
                created_after,
                action_status,
                member,
            ),
            self.get_stats_for_section(
                SystemMessage.SECTION_SCHEDULES,
                only_new,
                query,
                created_before,
                created_after,
                action_status,
                member,
            ),
            self.get_stats_for_section(
                SystemMessage.SECTION_OTHER,
                only_new,
                query,
                created_before,
                created_after,
                action_status,
                member,
            ),
        ]
        return Response(result)

    @action(detail=False, methods=["get"], url_path="mark-all-as-read")
    def mark_all_as_read(self, request, pk=None, realm_code=None, space_code=None):
        member = request.user.member

        messages = SystemMessage.objects.all()

        for message in messages:
            for member_message in message.members.all():
                if member_message.member_id == member.id:
                    member_message.is_read = True
                    member_message.save()

        return Response({"status": "ok"})

    @action(
        detail=False,
        methods=["post"],
        url_path="mark-as-read",
        serializer_class=SystemMessageActionSerializer,
    )
    def mark_as_read(self, request, pk=None, realm_code=None, space_code=None):
        ids = request.data.get("ids")
        sections = request.data.get("sections")

        queryset = SystemMessage.objects.all()

        print(f"mark_as_read ids {ids}")
        if ids:
            if not isinstance(ids, list):
                ids = [ids]

            queryset = queryset.filter(id__in=ids)

        print(f"mark_as_read sections {sections}")
        if sections:
            if not isinstance(sections, list):
                sections = [sections]

            queryset = queryset.filter(section__in=sections)

        index = 0
        for message in queryset:
            for member_message in message.members.all():
                if request.user.member.id == member_message.member_id:
                    member_message.is_read = True
                    member_message.save()

                    index += 1

        print(f"marked as read {index}")

        return Response({"status": "ok"})

    @action(
        detail=False,
        methods=["post"],
        url_path="mark-as-solved",
        serializer_class=SystemMessageActionSerializer,
    )
    def mark_as_solved(self, request, pk=None, realm_code=None, space_code=None):
        ids = request.data["ids"]

        if not isinstance(ids, list):
            ids = [ids]

        messages = SystemMessage.objects.filter(id__in=ids)

        for message in messages:
            message.action_status = SystemMessage.ACTION_STATUS_SOLVED
            message.save()

        return Response({"status": "ok"})

    @action(
        detail=False,
        methods=["post"],
        url_path="pin",
        serializer_class=SystemMessageActionSerializer,
    )
    def pin(self, request, pk=None, realm_code=None, space_code=None):
        ids = request.data["ids"]

        if not isinstance(ids, list):
            ids = [ids]

        messages = SystemMessage.objects.filter(id__in=ids)

        for message in messages:
            for member_message in message.members.all():
                member_message.is_pinned = True
                member_message.save()

        return Response({"status": "ok"})

    @action(
        detail=False,
        methods=["post"],
        url_path="unpin",
        serializer_class=SystemMessageActionSerializer,
    )
    def unpin(self, request, pk=None, realm_code=None, space_code=None):
        ids = request.data["ids"]

        if not isinstance(ids, list):
            ids = [ids]

        messages = SystemMessage.objects.filter(id__in=ids)

        for message in messages:
            for member_message in message.members.all():
                member_message.is_pinned = False
                member_message.save()

        return Response({"status": "ok"})

    @action(detail=True, methods=["put"], url_path="solve")
    def solve(self, request, pk=None, realm_code=None, space_code=None):
        system_message = SystemMessage.objects.get(id=pk)
        context = {"request": request, "master_user": request.user.master_user}
        system_message.action_status = SystemMessage.ACTION_STATUS_SOLVED
        system_message.save()

        comment = request.data.get("comment", None)

        if comment:
            SystemMessageComment.objects.create(
                comment=comment,
                system_message=system_message,
                member=request.user.member,
            )

        serializer = SystemMessageSerializer(instance=system_message, context=context)

        return Response(serializer.data)

    @action(detail=True, methods=["put"], url_path="comment")
    def comment(self, request, pk=None, realm_code=None, space_code=None):
        system_message = SystemMessage.objects.get(id=pk)
        context = {"request": request, "master_user": request.user.master_user}

        _l.info(f"request.data {request.data}")

        comment = request.data.get("comment", None)

        if comment:
            SystemMessageComment.objects.create(
                comment=comment,
                system_message=system_message,
                member=request.user.member,
            )

        serializer = SystemMessageSerializer(instance=system_message, context=context)

        return Response(serializer.data)


"""
=========================================================
# Methods to forward requests to the notification service
=========================================================
"""


class NotificationViewSet(ViewSet):


    def list(self, request, *args, **kwargs):
        _l.debug(f"Original request auth: {request.headers.get('Authorization')}")
        response = forward_get_user_notifications(request)
        return Response(response, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        payload = request.data
        response = forward_create_notification_to_service(payload, request)
        return Response(response, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        user_code = kwargs.get("pk")
        if not user_code:
            return Response(
                {"error": "Notification user_code is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payload = request.data
        response = forward_update_notification_to_service(user_code, payload, request)
        return Response(response, status=status.HTTP_200_OK)

    def partial_update(self, request, *args, **kwargs):
        user_code = kwargs.get("pk")
        if not user_code:
            return Response(
                {"error": "Notification user_code is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payload = request.data
        response = forward_partial_update_notification_to_service(user_code, payload, request)
        return Response(response, status=status.HTTP_200_OK)


class SubscriptionViewSet(ViewSet):
    def list(self, request, *args, **kwargs):
        return self.subscriptions_of_user(request)

    def create(self, request, *args, **kwargs):
        return self.subscriptions_update_for_user(request)

    @action(detail=False, methods=["get"])
    def subscriptions_of_user(self, request, *args, **kwargs):
        response = forward_get_user_subscriptions_to_service(request)
        return Response(response, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"])
    def subscriptions_update_for_user(self, request, *args, **kwargs):
        payload = request.data
        response = forward_update_user_subscriptions_to_service(request, payload)
        return Response(response, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def all_types(self, request, *args, **kwargs):
        response = forward_get_all_subscription_types_to_service(request)
        return Response(response, status=status.HTTP_200_OK)


class ChannelViewSet(ViewSet):
    lookup_field = "user_code"
    lookup_url_kwarg = "user_code"

    def list(self, request, *args, **kwargs):
        return self.user_subscribed_channels(request)

    def create(self, request, *args, **kwargs):
        return self.create_channel(request)

    # Channel 1: Create a channel (POST)
    @action(detail=False, methods=["post"])
    def create_channel(self, request, *args, **kwargs):
        payload = request.data
        response = forward_create_channel_to_service(request, payload)
        return Response(response, status=status.HTTP_201_CREATED)

    # Channel 2: Join a channel (POST)
    @action(detail=True, methods=["post"], url_path="join")
    def join_channel(self, request, user_code=None, *args, **kwargs):
        payload = request.data
        user_code = self.kwargs.get("user_code") or kwargs.get("user_code")

        if not user_code:
            return Response(
                {"error": "Channel user_code is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        response = forward_join_channel_to_service(request, payload, user_code)
        return Response(response, status=status.HTTP_200_OK)

    # Channel 3: Leave a channel (POST)
    @action(detail=True, methods=["post"], url_path="leave")
    def leave_channel(self, request, user_code=None, *args, **kwargs):
        payload = request.data
        user_code = self.kwargs.get("user_code") or kwargs.get("user_code")

        if not user_code:
            return Response(
                {"error": "Channel user_code is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        response = forward_leave_channel_to_service(request, payload, user_code)
        return Response(response, status=status.HTTP_200_OK)

    # Channel 4: List all channels the user is subscribed to (GET)
    @action(detail=False, methods=["get"])
    def user_subscribed_channels(self, request, *args, **kwargs):
        response = forward_user_subscribed_channels_to_service(request)
        return Response(response, status=status.HTTP_200_OK)

    # Channel 5: List all channels (GET)
    @action(detail=False, methods=["get"], url_path="all_channels")
    def all_channels(self, request, *args, **kwargs):
        response = forward_get_all_channels_to_service(request)
        return Response(response, status=status.HTTP_200_OK)


class CategoryViewSet(ViewSet):
    def list(self, request, *args, **kwargs):
        response = forward_get_categories_to_service(request)
        return Response(response, status=status.HTTP_200_OK)


class CurrentStatusViewSet(ViewSet):
    def list(self, request, *args, **kwargs):
        response = forward_get_statuses_to_service(request)
        return Response(response, status=status.HTTP_200_OK)
