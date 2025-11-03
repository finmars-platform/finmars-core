import logging
import random
import string
import time
from datetime import timedelta

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions
from rest_framework.authentication import TokenAuthentication, get_authorization_header

from poms.common.keycloak import KeycloakConnect

_l = logging.getLogger("poms.common")


def generate_random_string(N):
    return "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(N))


def get_access_token(request):
    auth = get_authorization_header(request).split()

    try:
        token = auth[1].decode()
    except UnicodeError as e:
        msg = _("Invalid token header. Token string should not contain invalid characters.")
        raise exceptions.AuthenticationFailed(msg) from e

    return token


class KeycloakAuthentication(TokenAuthentication):
    """

    Important piece of code, here we override default authentication handler in django
    Each user request that django processes, it make request to Keycloak server with users Bearer Token
    And Keycloak response decide if user has permission or not

    look at method authenticate_credentials

    """

    def get_auth_token_from_request(self, request):
        auth = get_authorization_header(request).split()

        if not auth:
            for key, value in request.COOKIES.items():
                if key == "access_token":
                    auth = [b"Token", value.encode()]

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
        except UnicodeError as e:
            msg = _("Invalid token header. Token string should not contain invalid characters.")
            raise exceptions.AuthenticationFailed(msg) from e

        return token

    def authenticate(self, request):
        # print('KeycloakAuthentication.authenticate')
        # print('KeycloakAuthentication.request.method %s' % request.method)

        user_model = get_user_model()  # noqa: F841

        if request.method == "OPTIONS":
            finmars_bot = User.objects.get(username="finmars_bot")

            return finmars_bot, None

        token = self.get_auth_token_from_request(request)
        if token is None:
            return None  # No token or not a Bearer token, continue to next authentication

        return self.authenticate_credentials(token, request)

    def authenticate_credentials(self, key, request=None):
        from poms.users.models import MasterUser, Member

        auth_start_time = time.perf_counter()  # noqa: F841
        """
        Validate user Berarer token in keycloak

        :param key:
        :param request:
        :return:
        """

        self.keycloak = KeycloakConnect(
            server_url=settings.KEYCLOAK_SERVER_URL,
            realm_name=settings.KEYCLOAK_REALM,
            client_id=settings.KEYCLOAK_CLIENT_ID,
            client_secret_key=settings.KEYCLOAK_CLIENT_SECRET_KEY,
        )

        # if not self.keycloak.is_token_active(key):
        #     msg = _('Invalid or expired token.')
        #     raise exceptions.AuthenticationFailed(msg)
        try:
            userinfo = self.keycloak.userinfo(key)
        except Exception as e:
            msg = _("Invalid or expired token.")
            raise exceptions.AuthenticationFailed(msg) from e  # noqa: F821

        logging.info(f"userinfo: {userinfo}")

        try:
            user = User.objects.get(username=userinfo["preferred_username"])
        except Exception as e:
            if settings.EDITION_TYPE != "community" or userinfo["preferred_username"] != settings.ADMIN_USERNAME:
                _l.error("User not found %s", e)
                raise exceptions.AuthenticationFailed(e) from e

            user = User.objects.create_superuser(
                username=userinfo["preferred_username"],
                password=settings.ADMIN_PASSWORD,
            )
            logging.info(f"user: {user}")

            master_user = MasterUser.objects.all().first()
            if not master_user:
                master_user = MasterUser.objects.create(
                    name="Finmars",
                    space_code="space00000",
                    realm_code=settings.REALM_CODE,
                )
            logging.info(f"master_user: {master_user}")

            member = Member.objects.get_or_create(
                user=user,
                master_user=master_user,
                defaults=dict(is_owner=True, is_admin=True, username=user.username),
            )
            logging.info(f"member: {member}")

            # Security hole, we should not create user on a fly
            # Was in use when we have poor invites implementation
            # Not is not need
            # try:
            #     user = User.objects.create_user(username=userinfo['preferred_username'],
            #                                     password=generate_random_string(12))
            #
            # except Exception as e:
            #
            #     try:
            #         # TODO
            #         # Do not remove this thing
            #         # Because we create user on a fly
            #         # It could be 2 request at same time trying to create new user
            #         # So, we trying to lookup again if first request already created it
            #         user = User.objects.get(username=userinfo['preferred_username'])
            #
            #     except Exception as e:
            #         # _l.error("Error create new user %s" % e)
            #         raise exceptions.AuthenticationFailed(e)

        return user, key


class JWTAuthentication(TokenAuthentication):
    keyword = "Bearer"

    """

    Important piece of code, here we override default authentication handler in django
    Each user request that django processes, it checks if JWT is valid ad signed by Space secret_key

    look at method authenticate_credentials

    """

    def get_auth_token_from_request(self, request):
        auth = get_authorization_header(request).split()

        if not auth:
            for key, value in request.COOKIES.items():
                if key == "bearer_token":
                    auth = [b"Bearer", value.encode()]

        if not auth or auth[0].lower() != self.keyword.lower().encode():
            return None  # Ensure that if there's no 'Bearer', None is returned.

        if len(auth) == 1:
            msg = _("Invalid token header. No credentials provided.")
            raise exceptions.AuthenticationFailed(msg)
        elif len(auth) > 2:
            msg = _("Invalid token header. Token string should not contain spaces.")
            raise exceptions.AuthenticationFailed(msg)

        try:
            token = auth[1].decode()
        except UnicodeError as e:
            msg = _("Invalid token header. Token string should not contain invalid characters.")
            raise exceptions.AuthenticationFailed(msg) from e

        return token

    def authenticate(self, request):
        user_model = get_user_model()  # noqa: F841

        if request.method == "OPTIONS":
            finmars_bot = User.objects.get(username="finmars_bot")

            return finmars_bot, None

        token = self.get_auth_token_from_request(request)
        if token is None:
            return None  # No token or not a Bearer token, continue to next authentication

        return self.authenticate_credentials(token, request)

    def authenticate_credentials(self, key, request=None):
        user_model = get_user_model()  # noqa: F841

        # user = user_model.objects.get(username=userinfo['preferred_username'])

        try:
            # Decode the JWT token
            payload = jwt.decode(
                key,
                settings.SECRET_KEY,
                algorithms=["HS256"],
                options={"leeway": timedelta(seconds=5)},
            )

        except jwt.ExpiredSignatureError as e:
            raise exceptions.AuthenticationFailed("Token has expired") from e
        except jwt.InvalidTokenError as e:
            raise exceptions.AuthenticationFailed(f"Invalid token: {str(e)}") from e
        except Exception as e:
            raise exceptions.AuthenticationFailed(str(e)) from e

        try:
            user = User.objects.get(username=payload["username"])
        except Exception as e:
            # _l.error("User not found %s" % e)

            raise exceptions.AuthenticationFailed(e) from e

        return user, key
