from django.core.cache import caches
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class AnonRateThrottleExt(AnonRateThrottle):
    cache = caches["throttling"]


class UserRateThrottleExt(UserRateThrottle):
    cache = caches["throttling"]
