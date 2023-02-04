# coding=utf-8
from __future__ import unicode_literals

import datetime
import ipaddress
import json
import os
import re
import time
import traceback
from http import HTTPStatus
from threading import local
from django.utils.timezone import now

from django.conf import settings
from django.contrib.gis.geoip2 import GeoIP2
from django.http import HttpResponse
from django.http.response import JsonResponse
from django.utils.cache import get_max_age, patch_cache_control, add_never_cache_headers
from django.utils.functional import SimpleLazyObject
from django.utils.translation import gettext_lazy as _
from geoip2.errors import AddressNotFoundError
from rest_framework import exceptions
from rest_framework.exceptions import PermissionDenied, AuthenticationFailed, NotAuthenticated

from .keycloak import KeycloakConnect

try:
    from django.utils.deprecation import MiddlewareMixin
except ImportError:
    MiddlewareMixin = object

import logging
_l = logging.getLogger('poms.common')

def get_ip(request):
    user_ip = None

    ips = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if ips:
        if ',' in ips:
            ips = [ip.strip() for ip in ips.split(',')]
        else:
            ips = [ips.strip()]
        for ip in ips:
            try:
                ip = ipaddress.ip_address(ip)
            except ValueError:
                pass
            else:
                if ip.is_private:
                    continue
                else:
                    user_ip = str(ip)
                    break

    if user_ip is None:
        ip = request.META.get('HTTP_X_REAL_IP', '')
        if ip:
            try:
                ip = ipaddress.ip_address(ip)
            except ValueError:
                pass
            else:
                if ip.is_private:
                    pass
                else:
                    user_ip = str(ip)

    if user_ip is None:
        ip = request.META.get('REMOTE_ADDR', '')
        if ip:
            try:
                ip = ipaddress.ip_address(ip)
            except ValueError:
                pass
            else:
                if ip.is_private:
                    user_ip = str(ip)
                else:
                    user_ip = str(ip)

    if not user_ip:
        user_ip = '127.0.0.1'

    if settings.DEBUG:
        ip = ipaddress.ip_address(user_ip)
        if ip.is_private or ip.is_reserved:
            user_ip = '95.165.168.246'  # москва
            # user_ip = '195.19.204.76' # питер
            # user_ip = '77.221.130.2' # норильск
            # user_ip = '93.88.13.132' # владивосток
            # user_ip = '8.8.8.8'
            # user_ip = '185.76.80.1'
            # user_ip = '91.219.220.8' # Ukraine
            # user_ip = '128.199.165.82'  # Singapore

    return user_ip


def get_user_agent(request):
    return request.META.get('HTTP_USER_AGENT', None)


_geoip = SimpleLazyObject(lambda: GeoIP2())


def get_city_by_ip(ip):
    try:
        return _geoip.city(ip)
    except AddressNotFoundError:
        try:
            return _geoip.country(ip)
        except AddressNotFoundError:
            pass
    return None


_active = local()


def activate(request):
    _active.request = request


def deactivate():
    if hasattr(_active, "request"):
        del _active.request


def get_request():

    _l.info('get_request._active %s' % _active)

    request = getattr(_active, "request", None)
    # assert request is not None, "CommonMiddleware is not installed"
    return request
    # if hasattr(_active, "request"):
    #     return _active.request
    # raise RuntimeError('request not found')


class CommonMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.user_ip = get_ip(request)
        request.user_agent = get_user_agent(request)
        request.user_city = get_city_by_ip(request.user_ip)

        # request.user_ip = SimpleLazyObject(lambda: get_ip(request))
        # request.user_agent = SimpleLazyObject(lambda: get_user_agent(request))
        # request.user_city = SimpleLazyObject(lambda: get_city_by_ip(request))

        activate(request)

    def process_response(self, request, response):
        deactivate()
        # timezone.deactivate()
        # translation.deactivate()
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
            self.server_url = self.config['KEYCLOAK_SERVER_URL']
            self.realm = self.config['KEYCLOAK_REALM']
            self.client_id = self.config['KEYCLOAK_CLIENT_ID']
            self.client_secret_key = self.config['KEYCLOAK_CLIENT_SECRET_KEY']
        except KeyError as e:
            raise Exception("The mandatory KEYCLOAK configuration variables has not defined.")

        if self.config['KEYCLOAK_SERVER_URL'] is None:
            raise Exception("The mandatory KEYCLOAK_SERVER_URL configuration variables has not defined.")

        if self.config['KEYCLOAK_REALM'] is None:
            raise Exception("The mandatory KEYCLOAK_REALM configuration variables has not defined.")

        if self.config['KEYCLOAK_CLIENT_ID'] is None:
            raise Exception("The mandatory KEYCLOAK_CLIENT_ID configuration variables has not defined.")

        if self.config['KEYCLOAK_CLIENT_SECRET_KEY'] is None:
            raise Exception("The mandatory KEYCLOAK_CLIENT_SECRET_KEY configuration variables has not defined.")

        # Create Keycloak instance
        self.keycloak = KeycloakConnect(server_url=self.server_url,
                                        realm_name=self.realm,
                                        client_id=self.client_id,
                                        client_secret_key=self.client_secret_key)

        print('self.keycloak %s' % self.keycloak)

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):

        # for now there is no role assigned yet
        request.roles = []

        # Checks the URIs (paths) that doesn't needs authentication
        if hasattr(settings, 'KEYCLOAK_EXEMPT_URIS'):
            path = request.path_info.lstrip('/')
            if any(re.match(m, path) for m in settings.KEYCLOAK_EXEMPT_URIS):
                return None

        # Read if View has attribute 'keycloak_roles'
        # Whether View hasn't this attribute, it means all request method routes will be permitted.
        try:
            view_roles = view_func.cls.keycloak_roles
        except AttributeError as e:
            return None

        # Select actual role from 'keycloak_roles' according http request method (GET, POST, PUT or DELETE)
        require_view_role = view_roles.get(request.method, [None])

        # Checks if exists an authentication in the http request header
        if 'HTTP_AUTHORIZATION' not in request.META:
            return JsonResponse({"detail": NotAuthenticated.default_detail}, status=NotAuthenticated.status_code)

        # Get access token in the http request header
        auth_header = request.META.get('HTTP_AUTHORIZATION').split()
        token = auth_header[1] if len(auth_header) == 2 else auth_header[0]

        # Checks token is active
        if not self.keycloak.is_token_active(token):
            msg = _('Invalid or expired token. Verify your Keycloak configuration.')
            raise exceptions.AuthenticationFailed(msg)

            # Get roles from access token
        token_roles = self.keycloak.roles_from_token(token)
        if token_roles is None:
            return JsonResponse(
                {'detail': 'This token has no client_id roles and no realm roles or client_id is not configured '
                           'correctly.'},
                status=AuthenticationFailed.status_code
            )

        # Check exists any Token Role contains in View Role
        if len(set(token_roles) & set(require_view_role)) == 0:
            return JsonResponse({'detail': PermissionDenied.default_detail}, status=PermissionDenied.status_code)

        # Add to View request param list of roles from authenticated token
        request.roles = token_roles

        # Add to userinfo to the view
        request.userinfo = self.keycloak.userinfo(token)


class LogRequestsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        _l.info("Going to handle %s " % request.build_absolute_uri())

        self.log_middleware_start = time.perf_counter()

        start = time.perf_counter()
        response = self.get_response(request)
        end = time.perf_counter()

        elapsed = float("{:3.3f}".format(end - start))

        # for line in traceback.format_stack():
        #     print(line.strip())

        # _l.info("Worker pid %s" % os.getpid())
        _l.info("Finish to handle %s " % request.build_absolute_uri())
        _l.info('LogRequestsMiddleware. response time %s' % elapsed)

        return response