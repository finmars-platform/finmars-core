import logging

import pytz

from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions
from rest_framework.authentication import TokenAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed

from poms.auth_tokens.models import AuthToken

_l = logging.getLogger("poms.auth_tokens")


class ExpiringTokenAuthentication(TokenAuthentication):
    """
    Expiring token for mobile and desktop clients.
    It expires every {n} hrs requiring client to supply valid username
    and password for new one to be created.
    """

    model = AuthToken

    def try_token(self, tokens, index):
        if index < len(tokens):
            try:
                self.result_token_user, self.result_token = (
                    self.authenticate_credentials(tokens[index])
                )
            except Exception as e:
                index = index + 1

                self.try_token(tokens, index)

                _l.info("wrong token")
        else:
            msg = _("Invalid token header. All Tokens invalid.")
            raise exceptions.AuthenticationFailed(msg)

    def authenticate(self, request):
        auth = get_authorization_header(request).split()

        if len(auth) == 0:
            tokens = []

            for key, value in request.COOKIES.items():
                if "authtoken" == key:
                    tokens.append(value)

            if len(tokens):
                _l.info(f"Multiple tokens detected {len(tokens)} ")

                index = 0
                self.try_token(tokens, index)
                return self.result_token_user, self.result_token

        if not auth or auth[0].lower() != self.keyword.lower().encode():
            return None

        if len(auth) == 1:
            msg = _("Invalid token header. No credentials provided.")
            raise exceptions.AuthenticationFailed(msg)
        elif len(auth) > 2:
            msg = _("Invalid token header. Token string should not contain spaces.")
            raise exceptions.AuthenticationFailed(msg)

        try:
            token = auth[1].decode()
        except UnicodeError:
            msg = _(
                "Invalid token header. Token string should not contain invalid characters."
            )
            raise exceptions.AuthenticationFailed(msg)

        return self.authenticate_credentials(token)

    def authenticate_credentials(self, key, request=None):
        models = self.get_model()

        try:
            token = models.objects.select_related("user").get(key=key)
        except models.DoesNotExist:
            raise AuthenticationFailed(
                {"error": "Invalid or Inactive Token", "is_authenticated": False}
            )

        if not token.user.is_active:
            raise AuthenticationFailed(
                {"error": "Invalid user", "is_authenticated": False}
            )

        utc_now = timezone.now()
        utc_now = utc_now.replace(tzinfo=pytz.utc)
        return token.user, token
