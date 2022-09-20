"""
Django settings for poms project.

Checklist: https://docs.djangoproject.com/en/1.9/howto/deployment/checklist/

"""

from __future__ import unicode_literals

import os
import datetime

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
from django.utils.translation import gettext_lazy


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DJANGO_LOG_LEVEL = os.environ.get('DJANGO_LOG_LEVEL', 'INFO')

print('DJANGO_LOG_LEVEL %s' % DJANGO_LOG_LEVEL)

SECRET_KEY = os.environ.get('SECRET_KEY', None)

SERVER_TYPE = os.environ.get('SERVER_TYPE', 'local')

print('SERVER_TYPE %s' % SERVER_TYPE)

BASE_API_URL = os.environ.get('BASE_API_URL', 'main')
HOST_LOCATION = os.environ.get('HOST_LOCATION', 'AWS') # azure, aws, or custom, only log purpose

print('BASE_API_URL %s' % BASE_API_URL)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False
if os.environ.get('DEBUG') == 'True':
    DEBUG = True

if not DEBUG:
    print('Debug disabled')

ADMIN = True

ALLOWED_HOSTS = ['*']

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

    # 'poms.cache_machine',

    'poms.users',
    'poms.audit',
    'poms.notifications',
    'poms.obj_attrs',
    'poms.obj_perms',
    'poms.chats',
    'poms.ui',
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
    'poms.transaction_import',
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
    'poms.procedures',
    'poms.credentials',
    'poms.system_messages',

    'poms.layout_recovery',

    'poms.auth_tokens',
    'poms.widgets',

    'django.contrib.admin',
    'django.contrib.admindocs',

    'crispy_forms',
    'rest_framework',
    'rest_framework_swagger',

    'corsheaders',

    # 'django_otp',
    # 'django_otp.plugins.otp_hotp',
    # 'django_otp.plugins.otp_totp',
    # 'django_otp.plugins.otp_email',
    # 'django_otp.plugins.otp_static',
    # 'two_factor',
    'django_celery_results',
    'django_celery_beat',
]

if SERVER_TYPE == 'local':
    INSTALLED_APPS.append('debug_toolbar')

# MIDDLEWARE_CLASSES = [
MIDDLEWARE = [

    'django.middleware.gzip.GZipMiddleware',
    'django.middleware.http.ConditionalGetMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # 'django.middleware.cache.UpdateCacheMiddleware',
    # 'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    # 'django_otp.middleware.OTPMiddleware',
    # 'django.middleware.cache.FetchFromCacheMiddleware',

    'corsheaders.middleware.CorsMiddleware',
    'corsheaders.middleware.CorsPostCsrfMiddleware',

    'poms.http_sessions.middleware.SessionMiddleware',
    'poms.common.middleware.CommonMiddleware',
    'poms.common.middleware.CustomExceptionMiddleware',
    # 'poms.users.middleware.AuthenticationMiddleware',
    # 'poms.users.middleware.TimezoneMiddleware',
    # 'poms.users.middleware.LocaleMiddleware',
    # 'poms.notifications.middleware.NotificationMiddleware',
    # 'poms.common.middleware.NoCacheMiddleware',

]

if SERVER_TYPE == 'local':
    MIDDLEWARE.append('debug_toolbar.middleware.DebugToolbarMiddleware')

PROFILER = False
if os.environ.get('PROFILER') == 'True':
    PROFILER = True

if PROFILER:
    print("Profiler enabled")

    MIDDLEWARE.append('django_cprofile_middleware.middleware.ProfilerMiddleware')
    DJANGO_CPROFILE_MIDDLEWARE_REQUIRE_STAFF = False

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
            'libraries' : {
                'staticfiles': 'django.templatetags.static',
            }

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
    ('en', gettext_lazy('English')),
    # ('es', gettext_lazy('Spanish')),
    # ('de', gettext_lazy('Deutsch')),
    # ('ru', gettext_lazy('Russian')),
]

TIME_ZONE = 'UTC'

USE_I18N = True
USE_L10N = True
USE_TZ = True
USE_ETAGS = True

ENV_CSRF_COOKIE_DOMAIN = os.environ.get('ENV_CSRF_COOKIE_DOMAIN', '.finmars.com')
ENV_CSRF_TRUSTED_ORIGINS = os.environ.get('ENV_CSRF_TRUSTED_ORIGINS', 'https://finmars.com')

if SERVER_TYPE == "production":
    CORS_URLS_REGEX = r'^/api/.*$'
    CORS_REPLACE_HTTPS_REFERER = True
    CORS_ALLOW_CREDENTIALS = True
    CORS_PREFLIGHT_MAX_AGE = 300
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_REDIRECT_EXEMPT = ['healthcheck']
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    CSRF_COOKIE_SAMESITE = 'Strict'
    CSRF_COOKIE_DOMAIN = ENV_CSRF_COOKIE_DOMAIN
    CSRF_TRUSTED_ORIGINS = ENV_CSRF_TRUSTED_ORIGINS.split(',')

if SERVER_TYPE == "development":
    CORS_ORIGIN_ALLOW_ALL = True
    CORS_ALLOW_CREDENTIALS = True

if SERVER_TYPE == "local":
    CORS_ORIGIN_ALLOW_ALL = True
    CORS_ALLOW_CREDENTIALS = True

STATIC_URL = '/' + BASE_API_URL + '/api/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static') # creates when collectstatic

STATICFILES_DIR = (
    os.path.join(BASE_DIR,  'poms', 'api', 'static')
)

USE_WEBSOCKETS = False

if os.environ.get('USE_WEBSOCKETS', None) == 'True':
    USE_WEBSOCKETS = True

WEBSOCKET_HOST = os.environ.get('WEBSOCKET_HOST', 'ws://0.0.0.0:6969')
WEBSOCKET_APP_TOKEN = os.environ.get('WEBSOCKET_APP_TOKEN', '943821230')

print('WEBSOCKET_HOST %s' % WEBSOCKET_HOST)

RABBITMQ_HOST = os.environ.get('RABBITMQ_HOST', 'localhost:5672')
print('RABBITMQ_HOST %s' % RABBITMQ_HOST)

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    },
    'throttling': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    },
    'http_session': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# SESSION_SERIALIZER = 'django.contrib.sessions.serializers.JSONSerializer'
SESSION_ENGINE = "poms.http_sessions.backends.cached_db"
SESSION_CACHE_ALIAS = 'http_session'

LOGGING = {
    'version': 1,
    'formatters': {
        'verbose': {
            '()': 'colorlog.ColoredFormatter',
            'format': '%(log_color)s [' + HOST_LOCATION + '] [' + BASE_API_URL + '] [%(levelname)s] [%(asctime)s] [%(processName)s] [%(name)s] [%(module)s:%(lineno)d] - %(message)s',
            'log_colors': {
                'DEBUG':    'cyan',
                'WARNING':  'yellow',
                'ERROR':    'red',
                'CRITICAL': 'bold_red',
            },
        },
    },
    'handlers': {
        'console': {
            'level': DJANGO_LOG_LEVEL,
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
        'file': {
              'level': DJANGO_LOG_LEVEL,
              'class': 'logging.FileHandler',
              'filename': '/var/log/finmars/django.log',
              'formatter': 'verbose'
        }
    },
    'loggers': {
        'django.request': {
            "level": "ERROR",
            "handlers": ["console", "file"]
        },
        "django": {
            "handlers": ["file"],
            "level": "ERROR",
            "propagate": True
        },
        "poms": {
            "level": DJANGO_LOG_LEVEL,
            "handlers": ["console", "file"],
            "propagate": True
        }
    }
}

REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'rest_framework.schemas.coreapi.AutoSchema',
    'DEFAULT_PAGINATION_CLASS': 'poms.common.pagination.PageNumberPaginationExt',
    'PAGE_SIZE': 40,
    'DEFAULT_AUTHENTICATION_CLASSES': (
        # 'rest_framework.authentication.SessionAuthentication',
        # 'rest_framework.authentication.BasicAuthentication',
        # 'rest_framework.authentication.TokenAuthentication',
        "poms.common.authentication.KeycloakAuthentication",
        # "poms.auth_tokens.authentication.ExpiringTokenAuthentication",
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
    }

    # 'DATETIME_FORMAT': '%Y-%m-%dT%H:%M:%S %Z',
    # 'DATETIME_INPUT_FORMATS': (ISO_8601, '%c', '%Y-%m-%d %H:%M:%S %Z'),
}

# if DEBUG:
REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] += (
    'rest_framework.renderers.BrowsableAPIRenderer',
    'rest_framework.renderers.AdminRenderer',
)

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    # 'poms.obj_perms.backends.PomsPermissionBackend',
)

DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5mb

DOMAIN_NAME = os.environ.get('DOMAIN_NAME', 'finmars.com')

print('DOMAIN_NAME %s' % DOMAIN_NAME)

# email config

DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', '"Finmars Notifications" <no-reply@finmars.com>')
SERVER_EMAIL = os.environ.get('SERVER_EMAIL', '"ADMIN: FinMars" <no-reply@finmars.com>')
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

# DEPRECATED
# DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
# AWS_S3_ACCESS_KEY_ID = os.environ.get('AWS_S3_ACCESS_KEY_ID', None)
# AWS_S3_SECRET_ACCESS_KEY = os.environ.get('AWS_S3_SECRET_ACCESS_KEY', None)
# AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME', None)
# AWS_DEFAULT_ACL = 'private'
# AWS_BUCKET_ACL = 'private'
# AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME', None)

# CELERY ------------------------------------------------

# CELERYD_LOG_LEVEL = "DEBUG"
# CELERYD_HIJACK_ROOT_LOGGER = False
CELERY_EAGER_PROPAGATES = True
CELERY_ALWAYS_EAGER = True
CELERY_ACKS_LATE = True

CELERY_BROKER_URL = 'amqp://%s' % RABBITMQ_HOST
CELERY_RESULT_BACKEND = 'django-db'
CELERY_ENABLE_UTC = True
CELERY_TIMEZONE = 'UTC'

CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'

CELERY_SEND_TASK_SENT_EVENT = True

if CELERY_RESULT_BACKEND in ['django-db', ]:
    CELERY_RESULT_EXPIRES = 2 * 24 * 60 * 60
    CELERY_TASK_STORE_ERRORS_EVEN_IF_IGNORED = CELERY_RESULT_BACKEND in ['django-db', ]
else:
    CELERY_RESULT_EXPIRES = 60
    CELERY_TASK_STORE_ERRORS_EVEN_IF_IGNORED = True

CELERY_WORKER_LOG_COLOR = True
CELERY_WORKER_LOG_FORMAT = '[%(levelname)1.1s %(asctime)s %(process)d:%(thread)d %(name)s %(module)s:%(lineno)d] %(message)s'
try:
    CELERY_WORKER_CONCURRENCY = int(os.environ.get('CELERY_WORKER_CONCURRENCY', '1'))
except (ValueError, TypeError):
    CELERY_WORKER_CONCURRENCY = 1

# FILE STORAGE ----------------------------------------------

DEFAULT_FILE_STORAGE = 'storages.backends.sftpstorage.SFTPStorage'

if SERVER_TYPE == 'local':
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'

print('DEFAULT_FILE_STORAGE %s' % DEFAULT_FILE_STORAGE)

SFTP_HOST = os.environ.get('SFTP_HOST', None)
if SFTP_HOST:
    SFTP_HOST = SFTP_HOST.strip()

print("SFTP HOST %s" % SFTP_HOST)

# SFTP_STORAGE_HOST = os.environ.get('SFTP_HOST', None)
SFTP_STORAGE_HOST = SFTP_HOST
SFTP_STORAGE_ROOT = os.environ.get('SFTP_ROOT', '/finmars/')

SFTP_PKEY_PATH = os.environ.get('SFTP_PKEY_PATH', None)

print('SFTP_PKEY_PATH %s' % SFTP_PKEY_PATH)

print('SFTP_STORAGE_ROOT %s' % SFTP_STORAGE_ROOT)

SFTP_STORAGE_PARAMS = {
    'username': os.environ.get('SFTP_USERNAME', None),
    'password': os.environ.get('SFTP_PASSWORD', None),
    'port': os.environ.get('SFTP_PORT', 22),
    'allow_agent': False,
    'look_for_keys': False,
}
if SFTP_PKEY_PATH:
    SFTP_STORAGE_PARAMS['key_filename'] = SFTP_PKEY_PATH

SFTP_STORAGE_INTERACTIVE = False

SFTP_KNOWN_HOST_FILE = os.path.join(BASE_DIR, '.ssh/known_hosts')

# INTEGRATIONS ------------------------------------------------

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

ROUND_NDIGITS = 6

# LOGIN_URL = 'two_factor:login'
# LOGIN_REDIRECT_URL = 'two_factor:profile'


# PRICING SECTION

MEDIATOR_URL = os.environ.get('MEDIATOR_URL', None)
DATA_FILE_SERVICE_URL = os.environ.get('DATA_FILE_SERVICE_URL', None)
FINMARS_DATABASE_URL = os.environ.get('FINMARS_DATABASE_URL', 'https://database.finmars.com/')
FINMARS_DATABASE_USER = os.environ.get('FINMARS_DATABASE_USER', None)
FINMARS_DATABASE_PASSWORD = os.environ.get('FINMARS_DATABASE_PASSWORD', None)

INSTRUMENT_EVENTS_REGULAR_MAX_INTERVALS = 1000

try:
    from poms_app.settings_local import *
except ImportError:
    pass


INTERNAL_IPS = [
    # ...
    '127.0.0.1',
    '0.0.0.0'
    'localhost'
    # ...
]

if SERVER_TYPE == 'local':
    DEBUG_TOOLBAR_PANELS = [
        'debug_toolbar.panels.versions.VersionsPanel',
        'debug_toolbar.panels.timer.TimerPanel',
        'debug_toolbar.panels.settings.SettingsPanel',
        'debug_toolbar.panels.headers.HeadersPanel',
        'debug_toolbar.panels.request.RequestPanel',
        'debug_toolbar.panels.sql.SQLPanel',
        'debug_toolbar.panels.templates.TemplatesPanel',
        'debug_toolbar.panels.staticfiles.StaticFilesPanel',
        'debug_toolbar.panels.cache.CachePanel',
        'debug_toolbar.panels.signals.SignalsPanel',
        'debug_toolbar.panels.logging.LoggingPanel',
        'debug_toolbar.panels.redirects.RedirectsPanel',
        'debug_toolbar.panels.profiling.ProfilingPanel',
    ]

    DEBUG_TOOLBAR_CONFIG = {
        'RESULTS_STORE_SIZE': 100,
    }

TOKEN_TTL = datetime.timedelta(days=15)

AUTHORIZER_URL = os.environ.get('AUTHORIZER_URL', None)
CBONDS_BROKER_URL = os.environ.get('CBONDS_BROKER_URL', None)
SUPERSET_URL = os.environ.get('SUPERSET_URL', None)
UNIFIED_DATA_PROVIDER_URL = os.environ.get('UNIFIED_DATA_PROVIDER_URL', None)
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10240

DROP_VIEWS = os.environ.get('DROP_VIEWS', 'True')

if DROP_VIEWS == 'False':
    DROP_VIEWS = False
else:
    DROP_VIEWS = True

JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', None)


DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'


KEYCLOAK_SERVER_URL = os.environ.get('KEYCLOAK_SERVER_URL', 'https://auth.finmars.com')
KEYCLOAK_REALM = os.environ.get('KEYCLOAK_REALM', 'finmars')
KEYCLOAK_CLIENT_ID = os.environ.get('KEYCLOAK_CLIENT_ID', 'finmars-backend')
KEYCLOAK_CLIENT_SECRET_KEY = os.environ.get('KEYCLOAK_CLIENT_SECRET_KEY', 'R8BlgeDuXZSzFINMLv8Pf84S8OQ4iONy')

