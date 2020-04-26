from django.conf import settings

HEALTHCHECK = getattr(settings, 'HEALTHCHECK', {})
HEALTHCHECK.setdefault('DISK_USAGE_MAX', 90)
HEALTHCHECK.setdefault('MEMORY_MIN', 100)
HEALTHCHECK.setdefault('WARNINGS_AS_ERRORS', True)
