import datetime

import pytz
from django.conf import settings
from django.utils import timezone
from rest_framework.authentication import TokenAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed
from django.utils.translation import gettext_lazy as _
from rest_framework import HTTP_HEADER_ENCODING, exceptions

from poms.auth_tokens.models import AuthToken

import logging
_l = logging.getLogger('poms.auth_tokens')


class ExpiringTokenAuthentication(TokenAuthentication):
    """
    Expiring token for mobile and desktop clients.
    It expires every {n} hrs requiring client to supply valid username
    and password for new one to be created.
    """

    model = AuthToken

    def authenticate(self, request):
        auth = get_authorization_header(request).split()

        # print('auth %s' % auth)

        if len(auth) == 0:

            # print(request.COOKIES['authtoken'])

            token = None

            if 'authtoken' in request.COOKIES:
                token = request.COOKIES['authtoken']

            if token:
                return self.authenticate_credentials(token)

        if not auth or auth[0].lower() != self.keyword.lower().encode():
            return None



        if len(auth) == 1:
            msg = _('Invalid token header. No credentials provided.')
            raise exceptions.AuthenticationFailed(msg)
        elif len(auth) > 2:
            msg = _('Invalid token header. Token string should not contain spaces.')
            raise exceptions.AuthenticationFailed(msg)

        try:
            token = auth[1].decode()
        except UnicodeError:
            msg = _('Invalid token header. Token string should not contain invalid characters.')
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

        # if token.created < utc_now - settings.TOKEN_TTL:
        #     raise AuthenticationFailed(
        #         {"error": "Token has expired", "is_authenticated": False}
        #     )
        return token.user, token


