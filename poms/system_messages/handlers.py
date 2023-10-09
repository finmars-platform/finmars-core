import logging
import traceback

from poms.system_messages.models import (
    SystemMessage,
    SystemMessageAttachment,
    SystemMessageMember,
)
from poms.users.models import Member

_l = logging.getLogger("poms.system_messages")


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
