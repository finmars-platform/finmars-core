from __future__ import unicode_literals

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.template.loader import get_template

from poms.integrations.tasks import send_mail
from poms.notifications.models import Notification


@receiver(post_save, dispatch_uid='notification_post_save', sender=Notification)
def notification_post_save(sender, instance=None, created=None, **kwargs):
    if created and instance.recipient.email:
        context = {
            'notification': instance,
        }
        subject = get_template('poms/notifications/mail/subject.txt').render(context)
        message = get_template('poms/notifications/mail/message.txt').render(context)
        html_message = get_template('poms/notifications/mail/message.html').render(context)
        recipient_list = [
            instance.recipient.email
        ]
        # TODO activate it later
        # send_mail(subject, message, None, recipient_list, html_message=html_message)
