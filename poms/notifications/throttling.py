from django.core.cache import caches
from rest_framework import throttling

from poms.common.middleware import get_request


class NotificationRateThrottle(throttling.UserRateThrottle):
    cache = caches["throttling"]
    cache_format = "notification_throttle_%(scope)s_%(ident)s"
    rate = "1/day"


def allow_notification():
    request = get_request()
    if request is None:
        return True
    return NotificationRateThrottle().allow_request(request, None)
