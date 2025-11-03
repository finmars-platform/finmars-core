import contextlib
import ipaddress
import logging
import re
import socket
import time
import uuid
from threading import local

from django.conf import settings
from django.contrib.gis.geoip2 import GeoIP2
from django.db import connection
from django.http.response import JsonResponse
from django.utils.cache import add_never_cache_headers, get_max_age, patch_cache_control
from django.utils.deprecation import MiddlewareMixin
from django.utils.functional import SimpleLazyObject
from django.utils.translation import gettext_lazy as _
from geoip2.errors import AddressNotFoundError
from memory_profiler import profile
from pympler.muppy import get_objects, summary
from rest_framework import exceptions
from rest_framework.exceptions import (
    AuthenticationFailed,
    NotAuthenticated,
    PermissionDenied,
)

from .keycloak import KeycloakConnect

_l = logging.getLogger("poms.common")


def get_ip(request):  # noqa: PLR0912
    user_ip = None

    ips = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if ips:
        for ip in [ip.strip() for ip in ips.split(",")]:
            try:
                ip = ipaddress.ip_address(ip)  # noqa: PLW2901
            except ValueError:
                pass
            else:
                if ip.is_private:
                    continue
                user_ip = str(ip)
                break

    if user_ip is None:
        ip = request.META.get("HTTP_X_REAL_IP", "")
        if ip:
            try:
                ip = ipaddress.ip_address(ip)
            except ValueError:
                pass
            else:
                if not ip.is_private:
                    user_ip = str(ip)

    if user_ip is None:
        ip = request.META.get("REMOTE_ADDR", "")
        if ip:
            try:
                ip = ipaddress.ip_address(ip)
            except ValueError:
                pass
            else:
                user_ip = str(ip)

    if not user_ip:
        user_ip = "127.0.0.1"

    if settings.DEBUG:
        ip = ipaddress.ip_address(user_ip)
        if ip.is_private or ip.is_reserved:
            user_ip = "95.165.168.246"  # москва
            # user_ip = '195.19.204.76' # питер
            # user_ip = '77.221.130.2' # норильск
            # user_ip = '93.88.13.132' # владивосток
            # user_ip = '8.8.8.8'
            # user_ip = '185.76.80.1'
            # user_ip = '91.219.220.8' # Ukraine
            # user_ip = '128.199.165.82'  # Singapore

    return user_ip


def get_user_agent(request):
    return request.META.get("HTTP_USER_AGENT", None)


_geoip = SimpleLazyObject(lambda: GeoIP2())


def get_city_by_ip(ip):
    try:
        return _geoip.city(ip)
    except AddressNotFoundError:
        with contextlib.suppress(AddressNotFoundError):
            return _geoip.country(ip)

    return None


_active = local()


def activate(request):
    _active.request = request


def deactivate():
    if hasattr(_active, "request"):
        del _active.request


def get_request():
    # _l.info('get_request._active %s' % _active)

    return getattr(_active, "request", None)


class CommonMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.user_ip = get_ip(request)
        request.user_agent = get_user_agent(request)
        request.user_city = get_city_by_ip(request.user_ip)
        activate(request)

    def process_response(self, request, response):
        deactivate()
        return response


class NoCacheMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        max_age = get_max_age(response)
        if max_age:
            patch_cache_control(response, private=True)
        else:
            add_never_cache_headers(response)
        return response


class KeycloakMiddleware:
    def __init__(self, get_response):
        # Set configurations from the settings file
        self.config = settings.KEYCLOAK_CONFIG

        # Django response
        self.get_response = get_response

        # Read keycloak configurations and set each attribute
        try:
            self.server_url = self.config["KEYCLOAK_SERVER_URL"]
            self.realm = self.config["KEYCLOAK_REALM"]
            self.client_id = self.config["KEYCLOAK_CLIENT_ID"]
            self.client_secret_key = self.config["KEYCLOAK_CLIENT_SECRET_KEY"]
        except KeyError as e:
            raise Exception("The mandatory KEYCLOAK configuration variables has not defined.") from e

        if self.config["KEYCLOAK_SERVER_URL"] is None:
            raise Exception("The mandatory KEYCLOAK_SERVER_URL configuration variables has not defined.")

        if self.config["KEYCLOAK_REALM"] is None:
            raise Exception("The mandatory KEYCLOAK_REALM configuration variables has not defined.")

        if self.config["KEYCLOAK_CLIENT_ID"] is None:
            raise Exception("The mandatory KEYCLOAK_CLIENT_ID configuration variables has not defined.")

        if self.config["KEYCLOAK_CLIENT_SECRET_KEY"] is None:
            raise Exception("The mandatory KEYCLOAK_CLIENT_SECRET_KEY configuration variables has not defined.")

        # Create Keycloak instance
        self.keycloak = KeycloakConnect(
            server_url=self.server_url,
            realm_name=self.realm,
            client_id=self.client_id,
            client_secret_key=self.client_secret_key,
        )

        print(f"self.keycloak {self.keycloak}")

    def __call__(self, request):
        response = self.get_response(request)

        # If authentication timing is available, add it to the response headers
        if hasattr(request, "keycloak_auth_time"):
            response["X-Keycloak-Auth-Time"] = request.keycloak_auth_time

        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        # for now there is no role assigned yet
        request.roles = []
        # Measure the time taken to authenticate with Keycloak
        auth_start_time = time.perf_counter()

        # Checks the URIs (paths) that doesn't needs authentication
        if hasattr(settings, "KEYCLOAK_EXEMPT_URIS"):
            path = request.path_info.lstrip("/")
            if any(re.match(m, path) for m in settings.KEYCLOAK_EXEMPT_URIS):
                return None

        # Read if View has attribute 'keycloak_roles'
        # Whether View hasn't this attribute, it means all request method routes will be permitted.
        try:
            view_roles = view_func.cls.keycloak_roles
        except AttributeError:
            return None

        # Select actual role from 'keycloak_roles' according http request method (GET, POST, PUT or DELETE)
        require_view_role = view_roles.get(request.method, [None])

        # Checks if exists an authentication in the http request header
        if "HTTP_AUTHORIZATION" not in request.META:
            return JsonResponse(
                {"detail": NotAuthenticated.default_detail},
                status=NotAuthenticated.status_code,
            )

        # Get access token in the http request header
        auth_header = request.META.get("HTTP_AUTHORIZATION").split()
        token = auth_header[1] if len(auth_header) == 2 else auth_header[0]

        # Checks token is active
        if not self.keycloak.is_token_active(token):
            msg = _("Invalid or expired token. Verify your Keycloak configuration.")
            raise exceptions.AuthenticationFailed(msg)

            # Get roles from access token
        token_roles = self.keycloak.roles_from_token(token)
        if token_roles is None:
            return JsonResponse(
                {
                    "detail": "This token has no client_id roles and no realm roles or client_id is not configured "
                    "correctly."
                },
                status=AuthenticationFailed.status_code,
            )

        # Check exists any Token Role contains in View Role
        if len(set(token_roles) & set(require_view_role)) == 0:
            return JsonResponse(
                {"detail": PermissionDenied.default_detail},
                status=PermissionDenied.status_code,
            )

        # Add to View request param list of roles from authenticated token
        request.roles = token_roles

        # Add to userinfo to the view
        request.userinfo = self.keycloak.userinfo(token)

        # Record authentication time
        request.keycloak_auth_time = int((time.perf_counter() - auth_start_time) * 1000)

        print(f"keycloak_auth_time {request.keycloak_auth_time}")


class LogRequestsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _l.info(f"Going to handle {request.build_absolute_uri()} ")

        self.log_middleware_start = time.perf_counter()

        start = time.perf_counter()
        response = self.get_response(request)
        end = time.perf_counter()

        elapsed = float(f"{end - start:3.3f}")

        # for line in traceback.format_stack():
        #     print(line.strip())

        # _l.info("Worker pid %s" % os.getpid())
        _l.info(f"Finish to handle {request.build_absolute_uri()} LogRequestsMiddleware. response time {elapsed}")

        return response


class MemoryMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    @profile
    def __call__(self, request):
        # Code to be executed for each request before the view (and later middleware) are called.
        all_objects = get_objects()

        before = summary.summarize(all_objects)
        # before = sum([x[2] for x in summary.summarize(all_objects)])
        # before.sort(key=lambda x: x[2], reverse=True)  # Sort by size
        # print('Memory consumption before request:')
        for item in before[:5]:
            print(item)

        response = self.get_response(request)

        # Code to be executed for each request/response after the view is called.
        # all_objects = get_objects()
        # after = summary.summarize(all_objects)
        # after = sum([x[2] for x in summary.summarize(all_objects)])

        # print(f'Memory consumption: {after - before} bytes')
        # after.sort(key=lambda x: x[2], reverse=True)  # Sort by size
        # print('Memory consumption after request:')
        # for item in after[:10]:
        #     print(item)

        return response


class ResponseTimeMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.start_time = time.time()
        request.request_id = str(uuid.uuid4())

    def process_response(self, request, response):
        # Check if we have the start_time attribute to calculate the time
        if hasattr(request, "start_time"):
            execution_time = int((time.time() - request.start_time) * 1000)  # in ms
            response["X-Execution-Time"] = execution_time
            response["X-Request-Id"] = request.request_id
            response["X-Worker"] = socket.gethostname()

        return response


def schema_exists(schema_name):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT schema_name
            FROM information_schema.schemata
            WHERE schema_name = %s;
            """,
            [schema_name],
        )
        return cursor.fetchone() is not None


# Very Important Middleware
# It sets the PostgreSQL search path to the tenant's schema
# Do not modify this code
# 2024-03-24 szhitenev
class RealmAndSpaceMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from django.contrib.contenttypes.models import ContentType

        # Example URL pattern: /realm0abcd/space0xyzv/

        request.realm_code = None
        request.space_code = None

        path_parts = request.path_info.split("/")

        if "realm" in path_parts[1]:
            request.realm_code = path_parts[1]
            request.space_code = path_parts[2]

            if not schema_exists(request.space_code):
                # Uncomment in 1.9.0 when there is no more legacy Spaces
                # Handle the error (e.g., log it, return a 400 Bad Request, etc.)
                # For demonstration, returning a simple HttpResponseBadRequest
                # return HttpResponseBadRequest("Invalid space code.")

                with connection.cursor() as cursor:
                    cursor.execute("SET search_path TO public;")

            else:  # REMOVE IN 1.9.0, PROBABLY SECURITY ISSUE
                # Setting the PostgreSQL search path to the tenant's schema
                with connection.cursor() as cursor:
                    cursor.execute(f"SET search_path TO {request.space_code};")

            # fix PLAT-1001: cache might return data from another schema, clear it
            ContentType.objects.clear_cache()

        else:
            # If we do not have realm_code, we suppose its legacy Space which do not need scheme changing
            request.space_code = path_parts[1]

            # Remain in public scheme
            with connection.cursor() as cursor:
                cursor.execute("SET search_path TO public;")

        response = self.get_response(request)

        if not response.streaming and "/admin/" in request.path_info:
            response.content = response.content.replace(b"spacexxxxx", request.space_code.encode())
            if "location" in response:
                response["location"] = response["location"].replace("spacexxxxx", request.space_code)

        # Optionally, reset the search path to default after the request is processed
        # This can be important in preventing "leakage" of the schema setting across requests
        with connection.cursor() as cursor:
            cursor.execute("SET search_path TO public;")

        return response


class TimerMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.start_time = time.perf_counter()

    def process_response(self, request, response):
        if hasattr(request, "start_time"):
            duration = time.perf_counter() - request.start_time
            print(f"==== Request to {request.path} took {duration:.3f}s")
        return response


class SentryContextMiddleware:
    """
    Middleware that adds realm_code, space_code and domain to Sentry scope.
    Must be placed after RealmAndSpaceMiddleware in MIDDLEWARE list.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Set Sentry context from request attributes
        # These attributes are set by RealmAndSpaceMiddleware
        try:
            import sentry_sdk

            with sentry_sdk.configure_scope() as scope:
                # Add realm_code
                realm_code = getattr(request, "realm_code", None)
                if realm_code:
                    scope.set_tag("realm_code", realm_code)
                    scope.set_context("realm", {"code": realm_code})

                # Add space_code
                space_code = getattr(request, "space_code", None)
                if space_code:
                    scope.set_tag("space_code", space_code)
                    scope.set_context("space", {"code": space_code})

                # Add domain
                domain = settings.DOMAIN_NAME
                if domain:
                    scope.set_tag("domain", domain)
                    scope.set_context("domain", {"name": domain})

        except Exception as e:
            _l.debug(f"Failed to set Sentry context: {e}")

        response = self.get_response(request)
        return response
