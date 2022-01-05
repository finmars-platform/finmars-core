# coding=utf-8
from __future__ import unicode_literals

import ipaddress
import json
import re
import traceback
from threading import local

from django.conf import settings
from django.contrib.gis.geoip2 import GeoIP2
from django.http import HttpResponse
from django.utils.cache import get_max_age, patch_cache_control, add_never_cache_headers
from django.utils.functional import SimpleLazyObject
from geoip2.errors import AddressNotFoundError

try:
    from django.utils.deprecation import MiddlewareMixin
except ImportError:
    MiddlewareMixin = object


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



class CustomExceptionMiddleware(MiddlewareMixin):

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):


        # print('exception %s' % exception)

        print(traceback.format_exc())

        lines = traceback.format_exc().splitlines()[-6:]
        traceback_lines = []

        for line in lines:
            traceback_lines.append(re.sub(r'File ".*[\\/]([^\\/]+.py)"', r'File "\1"', line))

        # print(traceback_lines)

        data = {
            'url': request.build_absolute_uri(),
            'message': repr(exception),
            'trace': '\n'.join(traceback_lines)
        }

        response_json = json.dumps(data, indent=2, sort_keys=True)

        return HttpResponse(response_json, status=500)
