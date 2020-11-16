from poms.system_messages.models import SystemMessage, SystemMessageAttachment

import logging
_l = logging.getLogger('poms.system_messages')

def send_system_message(master_user, source=None, text=None, file_report_id=None, level=SystemMessage.LEVEL_INFO, status=SystemMessage.STATUS_NEW):

    try:

        _l.debug('send_system_message %s' % text)

        system_message = SystemMessage.objects.create(master_user=master_user,
                                     source=source,
                                     text=text,
                                     level=level,
                                     status=status)

        _l.debug('system_message %s' % system_message)
        _l.debug('file_report %s' % file_report_id)

        if file_report_id is not None:

            attachment = SystemMessageAttachment.objects.create(system_message=system_message, file_report_id=file_report_id)
            attachment.save()

            _l.debug('file_report saved %s' % attachment )

    except Exception as e:
        _l.debug("Error send system message: %s" % e)