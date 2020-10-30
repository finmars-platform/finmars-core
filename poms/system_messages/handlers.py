from poms.system_messages.models import SystemMessage


def send_system_message(master_user, source=None, text=None, level=SystemMessage.LEVEL_INFO, status=SystemMessage.STATUS_NEW):

    SystemMessage.objects.create(master_user=master_user,
                                 source=source,
                                 text=text,
                                 level=level,
                                 status=status)
