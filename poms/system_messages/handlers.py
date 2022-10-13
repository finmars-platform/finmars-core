import traceback

from django.db import transaction

from poms.common.websockets import send_websocket_message
from poms.system_messages.models import SystemMessage, SystemMessageAttachment, SystemMessageMember

import logging

from poms.users.models import Member

_l = logging.getLogger('poms.system_messages')


def send_system_message(master_user, title=None, description=None, attachments=[], section='other', type='info',
                        performed_by=None, target=None, linked_event=None):
    try:

        type_mapping = {
            'info': SystemMessage.TYPE_INFORMATION,
            'warning': SystemMessage.TYPE_WARNING,
            'error': SystemMessage.TYPE_ERROR,
            'success': SystemMessage.TYPE_SUCCESS
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
            'general': SystemMessage.SECTION_GENERAL,
            'events': SystemMessage.SECTION_EVENTS,
            'transactions': SystemMessage.SECTION_TRANSACTIONS,
            'instruments': SystemMessage.SECTION_INSTRUMENTS,
            'data': SystemMessage.SECTION_DATA,
            'prices': SystemMessage.SECTION_PRICES,
            'report': SystemMessage.SECTION_REPORT,
            'import': SystemMessage.SECTION_IMPORT,
            'activity_log': SystemMessage.SECTION_ACTIVITY_LOG,
            'schedules': SystemMessage.SECTION_SCHEDULES,
            'other': SystemMessage.SECTION_OTHER,
        }

        system_message = SystemMessage.objects.create(master_user=master_user,
                                                      performed_by=performed_by,
                                                      target=target,
                                                      title=title,
                                                      description=description,
                                                      section=section_mapping[section],
                                                      type=type_mapping[type],
                                                      linked_event=linked_event
                                                      )

        _l.info('system_message %s' % system_message)

        for file_report_id in attachments:
            attachment = SystemMessageAttachment.objects.create(system_message=system_message,
                                                                file_report_id=file_report_id)
            attachment.save()

            _l.info('file_report saved %s' % attachment)

        members = Member.objects.all()

        for member in members:
            SystemMessageMember.objects.create(member=member, system_message=system_message)

            send_websocket_message(data={
                'type': 'new_system_message',
                'payload': {
                    'id': system_message.id,
                    'type': system_message.type,
                    'section': system_message.section,
                    'title': system_message.title,
                    'description': system_message.description,
                    'created': str(system_message.created)
                }
            }, level="member",
                context={"master_user": master_user, "member": member})

    except Exception as e:
        _l.info("Error send system message: exception %s" % e)
        _l.info("Error send system message: trace %s" % traceback.format_exc())
