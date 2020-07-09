"""
Django settings for poms project.

Checklist: https://docs.djangoproject.com/en/1.9/howto/deployment/checklist/

"""

from __future__ import unicode_literals

import json
import logging
import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
from celery.schedules import crontab
from django.utils.translation import ugettext_lazy

import boto3
import base64
from botocore.exceptions import ClientError


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class BackendRole:
    ALL = 'ALL'
    SIMPLE = 'SIMPLE'
    REPORTER = 'REPORTER'
    FILE_IMPORTER = 'FILE_IMPORTER'
    DATA_PROVIDER = 'DATA_PROVIDER'


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'jrixf-%65l5&#@hbmq()sa-pzy@e)=zpdr6g0cg8a!i_&w-c!)'

LOCAL = False
if os.environ.get('LOCAL') == 'True':
    LOCAL = True

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False
if os.environ.get('DEBUG') == 'True':
    DEBUG = True

if not DEBUG:
    print('Debug disabled')

ADMIN = True

ALLOWED_HOSTS = ['*']

BACKEND_ROLES = ['ALL']

if os.environ.get('BACKEND_ROLES'):
    BACKEND_ROLES = os.environ.get('BACKEND_ROLES').split(', ')

print('BACKEND_ROLES %s' % BACKEND_ROLES)

# Application definition

INSTALLED_APPS = [
    'modeltranslation',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',

    'django_filters',

    'mptt',

    'healthcheck',

    'poms.system',
    'poms.http_sessions',
    'poms.users',
    'poms.audit',
    'poms.notifications',
    'poms.obj_attrs',
    'poms.obj_perms',
    'poms.chats',
    'poms.ui',
    'poms.tags',
    'poms.accounts',
    'poms.counterparties',
    'poms.currencies',
    'poms.instruments',
    'poms.portfolios',
    'poms.strategies',
    'poms.transactions',
    'poms.integrations',
    'poms.reports',
    'poms.api',
    'poms.csv_import',
    'poms.complex_import',
    'poms.configuration_export',
    'poms.configuration_import',
    'poms.reference_tables',
    'poms.celery_tasks',

    'poms.reconciliation',
    'poms.file_reports',
    'poms.configuration_sharing',
    'poms.pricing',

    'poms.schedules',

    'poms.layout_recovery',

    'django.contrib.admin',
    'django.contrib.admindocs',

    'crispy_forms',
    'rest_framework',
    # 'rest_framework_swagger',

    'corsheaders',

    # 'django_otp',
    # 'django_otp.plugins.otp_hotp',
    # 'django_otp.plugins.otp_totp',
    # 'django_otp.plugins.otp_email',
    # 'django_otp.plugins.otp_static',
    # 'two_factor',
    'django_celery_results',
    'django_celery_beat',
    # 'debug_toolbar',
]

if LOCAL:
    INSTALLED_APPS.append('debug_toolbar')

# MIDDLEWARE_CLASSES = [
MIDDLEWARE = [
    'poms.common.middleware.CommonMiddleware',
    # 'django.middleware.cache.UpdateCacheMiddleware',
    'django.middleware.gzip.GZipMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.http.ConditionalGetMiddleware',
    'django.middleware.security.SecurityMiddleware',
    # 'poms.common.middleware.NoCacheMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'poms.http_sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'corsheaders.middleware.CorsPostCsrfMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    # 'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    # 'django_otp.middleware.OTPMiddleware',
    # 'poms.users.middleware.AuthenticationMiddleware',
    # 'poms.users.middleware.TimezoneMiddleware',
    # 'poms.users.middleware.LocaleMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # 'poms.notifications.middleware.NotificationMiddleware',
    # 'django.middleware.cache.FetchFromCacheMiddleware',
    # 'debug_toolbar.middleware.DebugToolbarMiddleware',
]

if LOCAL:
    MIDDLEWARE.append('debug_toolbar.middleware.DebugToolbarMiddleware')

ROOT_URLCONF = 'poms_app.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.request',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'poms_app.wsgi.application'

# Database
# https://docs.djangoproject.com/en/1.9/ref/settings/#databases

AWS_SECRETS_ACCESS_KEY_ID = os.environ.get('AWS_SECRETS_ACCESS_KEY_ID', None)
AWS_SECRETS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRETS_SECRET_ACCESS_KEY', None)
AWS_SECRET_NAME = os.environ.get('AWS_SECRET_NAME', None)


DATABASES = {
    'default': {
        # 'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', None),
        'USER': os.environ.get('DB_USER', None),
        'PASSWORD': os.environ.get('DB_PASSWORD', None),
        'HOST': os.environ.get('DB_HOST', None),
        'PORT': os.environ.get('DB_PORT', None),
        # 'ATOMIC_REQUESTS': True,
    }
}


REGISTER_ACCESS_KEY = os.environ.get('REGISTER_ACCESS_KEY', None)

# Password validation
# https://docs.djangoproject.com/en/1.9/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/1.9/topics/i18n/

LANGUAGE_CODE = 'en'
LANGUAGES = [
    ('en', ugettext_lazy('English')),
    # ('es', ugettext_lazy('Spanish')),
    # ('de', ugettext_lazy('Deutsch')),
    # ('ru', ugettext_lazy('Russian')),
]

TIME_ZONE = 'UTC'

USE_I18N = True
USE_L10N = True
USE_TZ = True
USE_ETAGS = True

if not LOCAL:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    CSRF_COOKIE_DOMAIN = 'finmars.com'
    CSRF_TRUSTED_ORIGINS = ['finmars.com', 'dev.finmars.com', 'localhost:8080', 'localhost:8081', '0.0.0.0:8080', 'www.finmars.com']

CORS_ORIGIN_WHITELIST = ('dev.finmars.com', 'finmars.com', 'localhost:8080', 'localhost:8081', '0.0.0.0:8080', 'www.finmars.com')

CORS_URLS_REGEX = r'^/api/.*$'
CORS_REPLACE_HTTPS_REFERER = True
CORS_ALLOW_CREDENTIALS = True
CORS_PREFLIGHT_MAX_AGE = 300

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.9/howto/static-files/

STATIC_URL = '/api/static/'
STATIC_ROOT = os.path.join(BASE_DIR, "static")

REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost:6379')

print('REDIS_HOST %s' % REDIS_HOST)


CACHE_VERSION = 1
CACHE_SERIALIZER = "django_redis.serializers.json.JSONSerializer"
# CACHE_SERIALIZER = "django_redis.serializers.pickle.PickleSerializer"
CACHE_COMPRESSOR = 'django_redis.compressors.identity.IdentityCompressor'
# CACHE_COMPRESSOR = 'django_redis.compressors.zlib.ZlibCompressor'
CACHE_SOCKET_CONNECT_TIMEOUT = 1
CACHE_SOCKET_TIMEOUT = 1

# 1 -> celery
# 2 -> default
# 3 -> http_cache, http_session
# 4 -> all "poms"
CACHES = {
    'default': {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://%s/2" % REDIS_HOST,
        'KEY_PREFIX': 'default',
        'TIMEOUT': 300,
        'VERSION': CACHE_VERSION,
        'OPTIONS': {
            'SERIALIZER': CACHE_SERIALIZER,
            'COMPRESSOR': CACHE_COMPRESSOR,
            "SOCKET_CONNECT_TIMEOUT": CACHE_SOCKET_CONNECT_TIMEOUT,
            "SOCKET_TIMEOUT": CACHE_SOCKET_TIMEOUT,
        }
    },
    # 'http_cache': {
    #     "BACKEND": "django_redis.cache.RedisCache",
    #     "LOCATION": "redis://%s/3" % REDIS_HOST,
    #     'KEY_PREFIX': 'http_cache',
    #     'TIMEOUT': 3600,
    #     'OPTIONS': {
    #         'SERIALIZER': CACHE_SERIALIZER,
    #         'COMPRESSOR': CACHE_COMPRESSOR,
    #         "SOCKET_CONNECT_TIMEOUT": CACHE_SOCKET_CONNECT_TIMEOUT,
    #         "SOCKET_TIMEOUT": CACHE_SOCKET_TIMEOUT,
    #     }
    # },
    'http_session': {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://%s/3" % REDIS_HOST,
        'KEY_PREFIX': 'http_session',
        'TIMEOUT': 3600,
        'VERSION': CACHE_VERSION,
        'OPTIONS': {
            'SERIALIZER': CACHE_SERIALIZER,
            'COMPRESSOR': CACHE_COMPRESSOR,
            "SOCKET_CONNECT_TIMEOUT": CACHE_SOCKET_CONNECT_TIMEOUT,
            "SOCKET_TIMEOUT": CACHE_SOCKET_TIMEOUT,
        }
    },
    'throttling': {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://%s/4" % REDIS_HOST,
        'KEY_PREFIX': 'throttling',
        'TIMEOUT': 300,
        'VERSION': CACHE_VERSION,
        'OPTIONS': {
            'SERIALIZER': CACHE_SERIALIZER,
            'COMPRESSOR': CACHE_COMPRESSOR,
            "SOCKET_CONNECT_TIMEOUT": CACHE_SOCKET_CONNECT_TIMEOUT,
            "SOCKET_TIMEOUT": CACHE_SOCKET_TIMEOUT,
        }
    },
    # 'bloomberg': {
    #     "BACKEND": "django_redis.cache.RedisCache",
    #     "LOCATION": "redis://%s/4" % REDIS_HOST,
    #     'KEY_PREFIX': 'bloomberg',
    #     'TIMEOUT': 3600,
    #     'OPTIONS': {
    #         'SERIALIZER': CACHE_SERIALIZER,
    #         'COMPRESSOR': CACHE_COMPRESSOR,
    #         "SOCKET_CONNECT_TIMEOUT": CACHE_SOCKET_CONNECT_TIMEOUT,
    #         "SOCKET_TIMEOUT": CACHE_SOCKET_TIMEOUT,
    #     }
    # },
}

# SESSION_SERIALIZER = 'django.contrib.sessions.serializers.JSONSerializer'
SESSION_ENGINE = "poms.http_sessions.backends.cached_db"
SESSION_CACHE_ALIAS = 'http_session'

LOGGING = {
    'version': 1,
    'formatters': {
        'verbose': {
            # 'format': '%(asctime)s %(levelname)s %(process)d/%(thread)d %(module)s - %(message)s'
            # 'format': '[%(levelname)1.1s %(asctime)s %(process)d:%(thread)d %(name)s %(module)s:%(lineno)d] %(message)s',
            'format': '[%(levelname)s] [%(asctime)s] [%(name)s] [%(module)s:%(lineno)d] - %(message)s',
        },
    },
    'filters': {
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
        'filebeat-info': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/finmars/django-info.log',
            'maxBytes': 1024*1024*15,  # 15MB
            'backupCount': 10,
            'formatter': 'verbose'
        },
        'filebeat-error': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/finmars/django-error.log',
            'maxBytes': 1024*1024*15,  # 15MB
            'backupCount': 10,
            'formatter': 'verbose'
        }
    },
    'loggers': {
        'py.warnings': {
            'handlers': ['console'],
            'propagate': False,
        },
        'django': {
            'level': 'INFO',
            'handlers': ['console'],
            'propagate': False,
        },
        'django.request': {
            'level': 'ERROR',
            'handlers': ['console',  'filebeat-error'],
        },
        'django_test': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
        'poms': {
            'level': 'DEBUG',
            'handlers': ['console', 'filebeat-info'],
            'propagate': False,
        },
        'celery': {
            'level': 'INFO',
            'handlers': ['console', 'filebeat-info'],
        },
        'suds': {
            'level': 'INFO',
            'handlers': ['console'],
            'propagate': False,
        },
        'kombu': {
            'level': 'INFO',
            'handlers': ['console'],
            'propagate': False,
        },
        'werkzeug': {
            'level': 'INFO',
            'handlers': ['console'],
            'propagate': False,
        },
    }
}

REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'poms.common.pagination.PageNumberPaginationExt',
    'POST_PAGINATION_CLASS': 'poms.common.pagination.PostPageNumberPagination',
    'PAGE_SIZE': 40,
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
        # 'rest_framework.authentication.BasicAuthentication',
        # 'rest_framework.authentication.TokenAuthentication',
    ),
    'DEFAULT_FILTER_BACKENDS': ('django_filters.rest_framework.DjangoFilterBackend',),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_RENDERER_CLASSES': (
        # 'rest_framework.renderers.JSONRenderer',
        'poms.common.renderers.CustomJSONRenderer',
    ),
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.NamespaceVersioning',
    # 'DEFAULT_PARSER_CLASSES': (
    #     'rest_framework.parsers.JSONParser',
    #     'rest_framework.parsers.FormParser',
    #     'rest_framework.parsers.MultiPartParser',
    # ),
    'DEFAULT_THROTTLE_CLASSES': (
        'poms.api.throttling.AnonRateThrottleExt',
        'poms.api.throttling.UserRateThrottleExt'
    ),
    'DEFAULT_THROTTLE_RATES': {
        # 'anon': '5/second',
        # 'user': '50/second',
        'anon': '20/min',
        'user': '500/min',
    },

    # 'DATETIME_FORMAT': '%Y-%m-%dT%H:%M:%S %Z',
    # 'DATETIME_INPUT_FORMATS': (ISO_8601, '%c', '%Y-%m-%d %H:%M:%S %Z'),
}

if DEBUG:
    REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] += (
        'rest_framework.renderers.BrowsableAPIRenderer',
        'rest_framework.renderers.AdminRenderer',
    )

# CURRENCY_CODE = 'USD'

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    # 'poms.obj_perms.backends.PomsPermissionBackend',
)

DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5mb

# email config

DEFAULT_FROM_EMAIL = '"Finmars Notifications" <no-reply@finmars.com>'
SERVER_EMAIL = '"ADMIN: FinMars" <no-reply@finmars.com>'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'email-smtp.eu-west-1.amazonaws.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', "587"))
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', None)
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', None)
EMAIL_USE_TLS = True
EMAIL_TIMEOUT = 10

if DEBUG:
    DEFAULT_FROM_EMAIL = '"DEV: Finmars Notifications" <no-reply@finmars.com>'
    SERVER_EMAIL = '"DEV-ADMIN: FinMars" <no-reply@finmars.com>'

ADMINS = [
    ['Site Admins', 'site-admins@finmars.com'],
]
MANAGERS = [
    ['Site Managers', 'site-managers@finmars.com'],
]
if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# EMAIL_BACKEND = 'backends.smtp.SSLEmailBackend'

# MESSAGE_STORAGE = 'poms.notifications.message_storage.FallbackStorage'

GEOIP_PATH = os.path.join(BASE_DIR, 'data')
GEOIP_COUNTRY = "GeoLite2-Country.mmdb"
GEOIP_CITY = "GeoLite2-City.mmdb"

# MEDIA_URL = '/api/media/'
# MEDIA_ROOT = '/opt/finmars-media'
# MEDIA_SERVE = True

DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
AWS_S3_ACCESS_KEY_ID = os.environ.get('AWS_S3_ACCESS_KEY_ID', None)
AWS_S3_SECRET_ACCESS_KEY = os.environ.get('AWS_S3_SECRET_ACCESS_KEY', None)
AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME', None)
AWS_DEFAULT_ACL = 'private'
AWS_BUCKET_ACL = 'private'
AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME', None)

# CELERY ------------------------------------------------

CELERYD_LOG_LEVEL = "DEBUG"
CELERYD_HIJACK_ROOT_LOGGER = False

CELERY_BROKER_URL = 'redis://%s/1' % REDIS_HOST
# CELERY_RESULT_BACKEND = 'redis://%s/1' % REDIS_HOST
CELERY_RESULT_BACKEND = 'django-db'
CELERY_ENABLE_UTC = True
CELERY_TIMEZONE = 'UTC'

# CELERY_ACCEPT_CONTENT = ['json', 'json']
# CELERY_TASK_SERIALIZER = 'json'
# CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json', 'pickle']
CELERY_TASK_SERIALIZER = 'pickle'
CELERY_RESULT_SERIALIZER = 'pickle'
# CELERY_ACCEPT_CONTENT = ['json', 'pickle-signed']
# CELERY_TASK_SERIALIZER = 'pickle-signed'
# CELERY_RESULT_SERIALIZER = 'pickle-signed'

CELERYD_CONCURRENCY = 4  # Defaults to the number of available CPUs, but I prefer doubling it.
CELERYD_TASK_SOFT_TIME_LIMIT = 60 * 20
CELERYD_TASK_TIME_LIMIT = 60 * 30  # The worker processing the task will be killed and replaced with a new one when this is exceeded.
CELERY_SEND_TASK_SENT_EVENT = True

if CELERY_RESULT_BACKEND in ['django-db', ]:
    CELERY_RESULT_EXPIRES = 2 * 24 * 60 * 60
    CELERY_TASK_STORE_ERRORS_EVEN_IF_IGNORED = CELERY_RESULT_BACKEND in ['django-db', ]
else:
    CELERY_RESULT_EXPIRES = 60
    CELERY_TASK_STORE_ERRORS_EVEN_IF_IGNORED = True
# CELERY_TASK_STORE_ERRORS_EVEN_IF_IGNORED = True
# CELERY_WORKER_REDIRECT_STDOUTS = False
# CELERY_WORKER_LOG_COLOR = False
# CELERY_WORKER_LOG_FORMAT = '[%(levelname)1.1s %(asctime)s %(process)d:%(thread)d %(name)s %(module)s:%(lineno)d] %(message)s'
try:
    CELERY_WORKER_CONCURRENCY = int(os.environ.get('CELERY_WORKER_CONCURRENCY', '1'))
except (ValueError, TypeError):
    CELERY_WORKER_CONCURRENCY = 1
# CELERY_TASK_TRACK_STARTED = True
# CELERY_SEND_EVENTS = True
# CELERY_TASK_SEND_SENT_EVENT = True

PRICING_AUTO_DOWNLOAD_MIN_TIMEDELTA = 6 * 60  # min delta is 12 hour

if BackendRole.ALL in BACKEND_ROLES or BackendRole.DATA_PROVIDER in BACKEND_ROLES:

    print("Role: DATA_PROVIDER. CELERY BEAT SCHEDULE INITIALIZED")

    CELERY_BEAT_SCHEDULE = {
        'schedules.auto_process_pricing_procedures_schedules': {
            'task': 'schedules.auto_process_pricing_procedures_schedules',
            'schedule': crontab(minute='0,10,20,30,40,50'),
        },
        'instruments.generate_events_do_not_inform_apply_default': {
            'task': 'instruments.generate_events_do_not_inform_apply_default',
            'schedule': crontab(minute=0, hour=0),
        },
        'file_reports.clear_old_file_reports': {
            'task': 'file_reports.clear_old_file_reports',
            'schedule': crontab(minute=0, hour=0)
        },
        'pricing.set_old_processing_procedure_instances_to_error': {
            'task': 'pricing.set_old_processing_procedure_instances_to_error',
            'schedule': crontab(minute=0, hour=0)
        },
        'pricing.clear_old_pricing_procedure_instances': {
            'task': 'pricing.clear_old_pricing_procedure_instances',
            'schedule': crontab(minute='0,10,20,30,40,50')
        }
        # 'instruments.process_events': {
        #     'task': 'instruments.process_events',
        #     'schedule': crontab(minute='2,32'),
        # },
    }

# FILE STORAGE ----------------------------------------------

DEFAULT_FILE_STORAGE = 'storages.backends.sftpstorage.SFTPStorage'

SFTP_HOST = os.environ.get('SFTP_HOST', None)
if SFTP_HOST:
    SFTP_HOST = SFTP_HOST.strip()

print("SFTP HOST %s" % SFTP_HOST)

# SFTP_STORAGE_HOST = os.environ.get('SFTP_HOST', None)
SFTP_STORAGE_HOST = SFTP_HOST
SFTP_STORAGE_ROOT = '/finmars/'
SFTP_STORAGE_PARAMS = {
    'username': os.environ.get('SFTP_USERNAME', None),
    'password': os.environ.get('SFTP_PASSWORD', None),
    'allow_agent': False,
    'look_for_keys': False,
}

SFTP_STORAGE_INTERACTIVE = False

SFTP_KNOWN_HOST_FILE = os.path.join(BASE_DIR, '.ssh/known_hosts')


# INTEGRATIONS ------------------------------------------------


if LOCAL:

    IMPORT_CONFIG_STORAGE = {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
        'KWARGS': {
            # 'location': '/opt/finmars-import/config',
            'location': '/home/szhitenev/projects/finmars/config',
            'base_url': '/api/hidden/'
        }
    }

    IMPORT_FILE_STORAGE = {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
        'KWARGS': {
            'location': '/home/szhitenev/projects/finmars/files',
            'base_url': '/api/import/'
        }
    }

    FILE_REPORTS_STORAGE = {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
        'KWARGS': {
            'location': '/home/szhitenev/projects/finmars/file_reports',
            'base_url': '/api/file-reports/'
        }
    }

else:

    IMPORT_CONFIG_STORAGE = {
        'BACKEND': 'storages.backends.s3boto3.S3Boto3Storage',
        'KWARGS': {
            'acl': 'private',
            'bucket': os.environ.get('AWS_STORAGE_CONFIG_BUCKET_NAME', None),
            'querystring_expire': 10,
            'custom_domain': None
        }
    }

    IMPORT_FILE_STORAGE = {
        'BACKEND': 'storages.backends.s3boto3.S3Boto3Storage',
        'KWARGS': {
            'acl': 'private',
            'bucket': os.environ.get('AWS_STORAGE_IMPORT_FILE_BUCKET_NAME', None),
            'querystring_expire': 10,
            'custom_domain': None
        }
    }

    FILE_REPORTS_STORAGE = {
        'BACKEND': 'storages.backends.s3boto3.S3Boto3Storage',
        'KWARGS': {
            'acl': 'private',
            'bucket': os.environ.get('AWS_STORAGE_FILE_REPORTS_BUCKET_NAME', None),
            'querystring_expire': 10,
            'custom_domain': None
        }
    }


BLOOMBERG_WSDL = 'https://service.bloomberg.com/assets/dl/dlws.wsdl'
BLOOMBERG_RETRY_DELAY = 5
BLOOMBERG_MAX_RETRIES = 60
BLOOMBERG_DATE_INPUT_FORMAT = '%m/%d/%Y'
BLOOMBERG_EMPTY_VALUE = [None, '', 'N.S.']

BLOOMBERG_SANDBOX = True
if os.environ.get('POMS_BLOOMBERG_SANDBOX') == 'False':
    BLOOMBERG_SANDBOX = False

print('BLOOMBERG_SANDBOX %s ' % BLOOMBERG_SANDBOX)

if BLOOMBERG_SANDBOX:
    BLOOMBERG_RETRY_DELAY = 0.1
BLOOMBERG_SANDBOX_SEND_EMPTY = False
BLOOMBERG_SANDBOX_SEND_FAIL = False
BLOOMBERG_SANDBOX_WAIT_FAIL = False

# LOGIN_URL = 'two_factor:login'
# LOGIN_REDIRECT_URL = 'two_factor:profile'


# PRICING SECTION

MEDIATOR_URL = os.environ.get('MEDIATOR_URL', None)


INSTRUMENT_EVENTS_REGULAR_MAX_INTERVALS = 1000

try:
    from poms_app.settings_local import *
except ImportError:
    pass


def show_toolbar(request):
    return True


INTERNAL_IPS = [
    # ...
    '127.0.0.1',
    '0.0.0.0'
    'localhost'
    # ...
]

if DEBUG:

    DEBUG_TOOLBAR_CONFIG = {
        "SHOW_TOOLBAR_CALLBACK": show_toolbar,
    }
