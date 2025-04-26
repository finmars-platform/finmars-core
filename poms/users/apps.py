from __future__ import unicode_literals

from django.apps import AppConfig
from django.utils.translation import gettext_lazy


class UsersConfig(AppConfig):
    name = "poms.users"
    verbose_name = gettext_lazy("Poms users")

    # def ready(self):
    #     # noinspection PyUnresolvedReferences
    #     import poms.users.signals
