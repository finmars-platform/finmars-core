from __future__ import unicode_literals

from django.apps import AppConfig
from django.utils.translation import ugettext_lazy


class AuthTokensConfig(AppConfig):
    name = 'poms.auth_tokens'
    # label = 'poms_sessions'
    verbose_name = ugettext_lazy('Auth Tokens')
