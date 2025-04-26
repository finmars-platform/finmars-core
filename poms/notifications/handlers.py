from django.db.models.signals import post_save
from django.dispatch import receiver
from django.template.loader import get_template

from poms.integrations.tasks import send_mail
from poms.notifications.models import Notification
from poms.users.models import Member


@receiver(post_save, dispatch_uid="notification_post_save", sender=Notification)
def notification_post_save(sender, instance=None, created=None, **kwargs):
    if (
        created
        and instance.recipient.email
        and instance.recipient_member
        and instance.recipient_member.notification_level
        in [Member.EMAIL_ONLY, Member.SHOW_AND_EMAIL]
    ):
        context = {
            "notification": instance,
        }
        subject = get_template("poms/notifications/mail/subject.txt").render(context)
        message = get_template("poms/notifications/mail/message.txt").render(context)
        html_message = get_template("poms/notifications/mail/message.html").render(
            context
        )
        recipient_list = [instance.recipient.email]

        send_mail(subject, message, None, recipient_list, html_message=html_message)
