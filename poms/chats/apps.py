from django.apps import AppConfig

from django.utils.translation import gettext_lazy


class ChatsConfig(AppConfig):
    name = 'poms.chats'
    # label = 'poms'
    verbose_name = gettext_lazy('Chats')

    def ready(self):
        # noinspection PyUnresolvedReferences
        import poms.chats.handlers
