from poms.system_messages.models import SystemMessage, SystemMessageAttachment

import logging
_l = logging.getLogger('poms.system_messages')

def send_system_message(master_user, source=None, text=None, file_report=None, level=SystemMessage.LEVEL_INFO, status=SystemMessage.STATUS_NEW):

    _l.info('send_system_message %s' % text)

    system_message = SystemMessage.objects.create(master_user=master_user,
                                 source=source,
                                 text=text,
                                 level=level,
                                 status=status)

    _l.info('system_message %s' % system_message)
    _l.info('file_report %s' % file_report)

    if file_report:

        attachment = SystemMessageAttachment.objects.create(system_message=system_message, file_report=file_report)
        attachment.save()

        _l.info('file_report saved %s' % attachment )