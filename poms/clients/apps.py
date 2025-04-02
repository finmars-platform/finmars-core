from django.apps import AppConfig
from django.utils.translation import gettext_lazy


class ClientsConfig(AppConfig):
    name = "poms.clients"
    verbose_name = gettext_lazy("Clients")
