from django.apps import AppConfig
from django.utils.translation import gettext_lazy


class NotificationsConfig(AppConfig):
    name = "poms.notifications"
    verbose_name = gettext_lazy("Notification")

    def ready(self):
        # noinspection PyUnresolvedReferences
        import poms.notifications.handlers
