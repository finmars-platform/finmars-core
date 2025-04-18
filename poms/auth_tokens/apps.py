from django.apps import AppConfig
from django.utils.translation import gettext_lazy


class AuthTokensConfig(AppConfig):
    name = "poms.auth_tokens"
    verbose_name = gettext_lazy("Auth Tokens")
