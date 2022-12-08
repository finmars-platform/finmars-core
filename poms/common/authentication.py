import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions
from rest_framework.authentication import TokenAuthentication, get_authorization_header

from poms.common.keycloak import KeycloakConnect

_l = logging.getLogger('poms.common')


class KeycloakAuthentication(TokenAuthentication):

    def authenticate(self, request):

        # print('KeycloakAuthentication.authenticate')

        auth = get_authorization_header(request).split()

        if not auth:

            for key, value in request.COOKIES.items():

                if 'access_token' == key:
                    auth = ['Token'.encode(), value.encode()]

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

        self.keycloak = KeycloakConnect(server_url=settings.KEYCLOAK_SERVER_URL,
                                        realm_name=settings.KEYCLOAK_REALM,
                                        client_id=settings.KEYCLOAK_CLIENT_ID,
                                        client_secret_key=settings.KEYCLOAK_CLIENT_SECRET_KEY)

        # if not self.keycloak.is_token_active(key):
        #     msg = _('Invalid or expired token.')
        #     raise exceptions.AuthenticationFailed(msg)
        try:
            userinfo = self.keycloak.userinfo(key)
        except Exception as e:
            msg = _('Invalid or expired token.')
            raise exceptions.AuthenticationFailed(msg)

        user_model = get_user_model()

        user = user_model.objects.get(username=userinfo['preferred_username'])

        return user, key
