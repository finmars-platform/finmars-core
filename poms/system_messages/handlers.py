from poms.system_messages.models import SystemMessage, SystemMessageAttachment

import logging
_l = logging.getLogger('poms.system_messages')

def send_system_message(master_user,  title=None, description=None, file_report_id=None, section=SystemMessage.SECTION_GENERAL, type=SystemMessage.TYPE_INFORMATION, performed_by=None, target=None):

    try:

        system_message = SystemMessage.objects.create(master_user=master_user,
                                     performed_by=performed_by,
                                     target=target,
                                     title=title,
                                     description=description,
                                     section=section,
                                     type=type)

        _l.info('system_message %s' % system_message)
        _l.info('file_report %s' % file_report_id)

        if file_report_id is not None:

            attachment = SystemMessageAttachment.objects.create(system_message=system_message, file_report_id=file_report_id)
            attachment.save()

            _l.info('file_report saved %s' % attachment )

    except Exception as e:
        _l.info("Error send system message: %s" % e)