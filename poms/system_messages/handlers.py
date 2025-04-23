import logging
import traceback

import requests

from django.conf import settings

from poms.system_messages.models import (
    SystemMessage,
    SystemMessageAttachment,
    SystemMessageMember,
)
from poms.users.models import Member

_l = logging.getLogger("poms.system_messages")
service_url = settings.NOTIFICATION_SERVICE_BASE_URL


def send_system_message(
    master_user,
    title=None,
    description=None,
    attachments=None,
    section="other",
    type="info",
    action_status="not_required",
    performed_by=None,
    target=None,
    linked_event=None,
):
    if attachments is None:
        attachments = []

    try:
        type_mapping = {
            "info": SystemMessage.TYPE_INFORMATION,
            "warning": SystemMessage.TYPE_WARNING,
            "error": SystemMessage.TYPE_ERROR,
            "success": SystemMessage.TYPE_SUCCESS,
        }

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

        section_mapping = {
            "general": SystemMessage.SECTION_GENERAL,
            "events": SystemMessage.SECTION_EVENTS,
            "transactions": SystemMessage.SECTION_TRANSACTIONS,
            "instruments": SystemMessage.SECTION_INSTRUMENTS,
            "data": SystemMessage.SECTION_DATA,
            "prices": SystemMessage.SECTION_PRICES,
            "report": SystemMessage.SECTION_REPORT,
            "import": SystemMessage.SECTION_IMPORT,
            "activity_log": SystemMessage.SECTION_ACTIVITY_LOG,
            "schedules": SystemMessage.SECTION_SCHEDULES,
            "other": SystemMessage.SECTION_OTHER,
        }

        action_status_mapping = {
            "not_required": SystemMessage.ACTION_STATUS_NOT_REQUIRED,
            "required": SystemMessage.ACTION_STATUS_REQUIRED,
            "solved": SystemMessage.ACTION_STATUS_SOLVED,
        }

        system_message = SystemMessage.objects.create(
            master_user=master_user,
            performed_by=performed_by,
            target=target,
            title=title,
            description=description,
            section=section_mapping[section],
            action_status=action_status_mapping[action_status],
            type=type_mapping[type],
            linked_event=linked_event,
        )

        _l.info(f"system_message {system_message}")

        system_message_attachments = [
            SystemMessageAttachment(
                system_message=system_message, file_report_id=file_report_id
            )
            for file_report_id in attachments
        ]
        if len(system_message_attachments):
            SystemMessageAttachment.objects.bulk_create(system_message_attachments)
            _l.info(f"Saved {len(system_message_attachments)} attachments ")

        members = Member.objects.all()

        system_message_members = [
            SystemMessageMember(member=member, system_message=system_message)
            for member in members
        ]
        if len(system_message_members):
            SystemMessageMember.objects.bulk_create(system_message_members)

            _l.debug(f"Send message to {len(system_message_members)} members ")

    except Exception as e:
        _l.info(
            f"Error send system message: exception {repr(e)} "
            f"trace {traceback.format_exc()}"
        )


"""
========================================================
# Methods to forward calls to the notification service
========================================================
"""


def prepare_headers_for_service(request) -> dict:
    headers = dict(request.headers)
    headers["Accept"] = "application/json"
    headers["Content-Type"] = "application/json"
    return headers


def forward_get_user_notifications(request):
    try:
        query_params = request.query_params.urlencode()

        base_url = f"{service_url.format(space_code=request.space_code)}notifications/"
        url = f"{base_url}?{query_params}" if query_params else base_url

        response = requests.get(url, headers=prepare_headers_for_service(request))
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        _l.error(f"Failed to get notifications: {e}")
        raise


def forward_create_notification_to_service(payload, request):
    try:
        response = requests.post(
            f"{service_url.format(space_code=request.space_code)}notifications/create/",
            json=payload,
            headers=prepare_headers_for_service(request),
        )
        response.raise_for_status()
        return response.json()  # Return the exact response from the microservice
    except requests.exceptions.RequestException as e:
        _l.error(f"Failed to create notification: {e}")  # Log the error and raise it
        raise


def forward_update_notification_to_service(user_code, payload, request):
    try:
        response = requests.put(
            f"{service_url.format(space_code=request.space_code)}notifications/{user_code}/",
            json=payload,
            headers=prepare_headers_for_service(request),
        )
        response.raise_for_status()
        return response.json()  # Return the exact response from the microservice
    except requests.exceptions.RequestException as e:
        _l.error(f"Failed to update notification: {e}")  # Log the error and raise it
        raise


def forward_partial_update_notification_to_service(user_code, payload, request):
    try:
        response = requests.patch(
            f"{service_url.format(space_code=request.space_code)}notifications/{user_code}/",
            json=payload,
            headers=prepare_headers_for_service(request),
        )
        response.raise_for_status()
        return response.json()  # Return the exact response from the microservice
    except requests.exceptions.RequestException as e:
        _l.error(f"Failed to update notification: {e}")  # Log the error and raise it
        raise


def forward_get_user_subscriptions_to_service(request):
    try:
        query_params = request.query_params.urlencode()
        base_url = f"{service_url.format(space_code=request.space_code)}subscriptions/"
        url = f"{base_url}?{query_params}" if query_params else base_url

        response = requests.get(url, headers=prepare_headers_for_service(request))

        response.raise_for_status()
        return response.json()  # Return the exact response from the microservice
    except requests.exceptions.RequestException as e:
        _l.error(
            f"Failed to fetch user's subscriptions: {e}"
        )  # Log the error and raise it
        raise


def forward_update_user_subscriptions_to_service(request, payload):
    try:
        response = requests.post(
            f"{service_url.format(space_code=request.space_code)}subscriptions/update/",
            json=payload,
            headers=prepare_headers_for_service(request),
        )
        response.raise_for_status()
        return response.json()  # Return the exact response from the microservice
    except requests.exceptions.RequestException as e:
        _l.error(
            f"Failed to fetch subscription types: {e}"
        )  # Log the error and raise it
        raise


def forward_get_all_subscription_types_to_service(request):
    try:
        response = requests.get(
            f"{service_url.format(space_code=request.space_code)}subscriptions/types/",
            headers=prepare_headers_for_service(request),
        )
        response.raise_for_status()
        return response.json()  # Return the exact response from the microservice
    except requests.exceptions.RequestException as e:
        _l.error(
            f"Failed to fetch subscription types: {e}"
        )  # Log the error and raise it
        raise


def forward_create_channel_to_service(request, payload):
    try:
        response = requests.post(
            f"{service_url.format(space_code=request.space_code)}channels/",
            json=payload,
            headers=prepare_headers_for_service(request),
        )
        response.raise_for_status()
        return response.json()  # Return the exact response from the microservice
    except requests.exceptions.RequestException as e:
        _l.error(f"Failed to create new channel: {e}")  # Log the error and raise it
        raise


def forward_join_channel_to_service(request, payload, user_code):
    try:
        response = requests.post(
            f"{service_url.format(space_code=request.space_code)}channels/{user_code}/join/",
            json=payload,
            headers=prepare_headers_for_service(request),
        )
        response.raise_for_status()
        return response.json()  # Return the exact response from the microservice
    except requests.exceptions.RequestException as e:
        _l.error(f"Failed to join channel: {e}")  # Log the error and raise it
        raise


def forward_leave_channel_to_service(request, payload, user_code):
    try:
        response = requests.post(
            f"{service_url.format(space_code=request.space_code)}channels/{user_code}/leave/",
            json=payload,
            headers=prepare_headers_for_service(request),
        )
        response.raise_for_status()
        return response.json()  # Return the exact response from the microservice
    except requests.exceptions.RequestException as e:
        _l.error(f"Failed to leave channel: {e}")  # Log the error and raise it
        raise


def forward_user_subscribed_channels_to_service(request):
    try:
        query_params = request.query_params.urlencode()
        base_url = (
            f"{service_url.format(space_code=request.space_code)}channels/subscribed/"
        )
        url = f"{base_url}?{query_params}" if query_params else base_url

        response = requests.get(url, headers=prepare_headers_for_service(request))
        response.raise_for_status()
        return response.json()  # Return the exact response from the microservice
    except requests.exceptions.RequestException as e:
        _l.error(
            f"Failed to channels user subscribed: {e}"
        )  # Log the error and raise it
        raise


def forward_get_categories_to_service(request):
    """Forward request to get all notification categories from notification service"""
    try:
        response = requests.get(
            f"{service_url.format(space_code=request.space_code)}categories/",
            headers=prepare_headers_for_service(request),
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        _l.error(f"Failed to get categories: {e}")
        raise


def forward_get_statuses_to_service(request):
    """Forward request to get all notification statuses from notification service"""
    try:
        response = requests.get(
            f"{service_url.format(space_code=request.space_code)}statuses/",
            headers=prepare_headers_for_service(request),
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        _l.error(f"Failed to get statuses: {e}")
        raise


def forward_get_all_channels_to_service(request):
    """Forward request to get all channels from notification service"""
    try:
        query_params = request.query_params.urlencode()
        base_url = (
            f"{service_url.format(space_code=request.space_code)}channels/all_channels/"
        )
        url = f"{base_url}?{query_params}" if query_params else base_url

        response = requests.get(url, headers=prepare_headers_for_service(request))
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        _l.error(f"Failed to get all channels: {e}")
        raise
