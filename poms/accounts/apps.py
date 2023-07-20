from django.apps import AppConfig
from django.utils.translation import gettext_lazy


class AccountsConfig(AppConfig):
    name = "poms.accounts"
    verbose_name = gettext_lazy("Accounts")
