from poms.system_messages.models import SystemMessage, SystemMessageAttachment


def send_system_message(master_user, source=None, text=None, file_report=None, level=SystemMessage.LEVEL_INFO, status=SystemMessage.STATUS_NEW):

    system_message = SystemMessage.objects.create(master_user=master_user,
                                 source=source,
                                 text=text,
                                 level=level,
                                 status=status)

    if file_report:

        SystemMessageAttachment.objects.create(system_message=system_message, file_report=file_report)
