from __future__ import unicode_literals

# noinspection PyUnresolvedReferences
import os
from .settings import *

# DEBUG = True

# DATABASES['default']['NAME'] = 'test_poms_dev2'

ROOT_URLCONF = 'poms_app.urls_standalone'

if 'crispy_forms' not in INSTALLED_APPS:
    INSTALLED_APPS += ['crispy_forms', ]
if 'redisboard' not in INSTALLED_APPS:
    INSTALLED_APPS += ['redisboard', ]

SECRET_KEY = 's#)m^ug%_jr0dtko#83_55rd_we&xu#f9p#!1gh@k&$=5&3e67'

AUTH_PASSWORD_VALIDATORS = []
# SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

CORS_ORIGIN_WHITELIST = ('localhost:8080', '127.0.0.1:8080',)

DEFAULT_FROM_EMAIL = '"Standalone: Finmars Notifications" <no-reply@finmars.com>'
SERVER_EMAIL = '"STANDALONE: FinMars" <no-reply@finmars.com>'
ADMINS = MANAGERS = [
]
EMAIL_BACKEND = 'django.core.mail.backends.dummy.EmailBackend'

MEDIA_URL = '/api/media/'
MEDIA_ROOT = '/var/app-data/media/'
MEDIA_SERVE = False


# CELERY ------------------------------------------------

CELERY_WORKER_CONCURRENCY = 2
# CELERY_BEAT_SCHEDULE = {
#     # 'integrations.download_pricing_auto_scheduler': {
#     #     'task': 'integrations.download_pricing_auto_scheduler',
#     #     'schedule': 10,
#     # },
#     # 'instruments.generate_events': {
#     #     'task': 'instruments.generate_events',
#     #     'schedule': 10,
#     # },
#     # 'instruments.process_events': {
#     #     'task': 'instruments.process_events',
#     #     'schedule': 10,
#     # },
# }


# INTEGRATIONS ------------------------------------------------


IMPORT_CONFIG_STORAGE = {
    'BACKEND': 'django.core.files.storage.FileSystemStorage',
    'KWARGS': {
        'location': '/var/app-data/import/configs',
        'base_url': '/api/hidden/import/config/'
    }
}

IMPORT_FILE_STORAGE = {
    'BACKEND': 'django.core.files.storage.FileSystemStorage',
    'KWARGS': {
        'location': '/var/app-data/import/files',
        'base_url': '/api/hidden/import/files/'
    }
}

PRICING_AUTO_DOWNLOAD_DISABLED = False
PRICING_AUTO_DOWNLOAD_MIN_TIMEDELTA = None

BLOOMBERG_SANDBOX = True
# BLOOMBERG_RETRY_DELAY = 0.1
BLOOMBERG_RETRY_DELAY = 5
BLOOMBERG_SANDBOX_SEND_EMPTY = False
BLOOMBERG_SANDBOX_SEND_FAIL = False
BLOOMBERG_SANDBOX_WAIT_FAIL = False
