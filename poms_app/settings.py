"""
Django settings for the main Backend project.
"""

import os

from django.utils.translation import gettext_lazy

from poms_app.log_formatter import GunicornWorkerIDLogFormatter
from poms_app.utils import ENV_BOOL, ENV_STR, ENV_INT

DEFAULT_CHARSET = "utf-8"
SERVICE_NAME = "finmars"  # needs for Finmars Access Policy

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = ENV_BOOL("DEBUG", True)

SECRET_KEY = ENV_STR("SECRET_KEY", "django_secret_key")
ENCRYPTION_KEY = ENV_STR("ENCRYPTION_KEY", None)  # Need to encrypt everything related to storage
SERVER_TYPE = ENV_STR("SERVER_TYPE", "local")
USE_DEBUGGER = ENV_STR("USE_DEBUGGER", False)
BASE_API_URL = ENV_STR("BASE_API_URL", "space00000")
HOST_LOCATION = ENV_STR(
    "HOST_LOCATION", "AWS"
)  # azure, aws, or custom, only log purpose
DOMAIN_NAME = ENV_STR(
    "DOMAIN_NAME", "finmars.com"
)  # looks like HOST_URL, maybe refactor required
HOST_URL = ENV_STR("HOST_URL", "https://finmars.com")  #
JWT_SECRET_KEY = ENV_STR("JWT_SECRET_KEY", None)
VERIFY_SSL = ENV_BOOL("VERIFY_SSL", True)
ENABLE_DEV_DOCUMENTATION = ENV_BOOL("ENABLE_DEV_DOCUMENTATION", False)
USE_FILESYSTEM_STORAGE = ENV_BOOL("USE_FILESYSTEM_STORAGE", False)
MEDIA_ROOT = os.path.join(BASE_DIR, "finmars_data")
DOCS_ROOT = os.path.join(BASE_DIR, "docs/build/html")
DROP_VIEWS = ENV_BOOL("DROP_VIEWS", True)
AUTHORIZER_URL = ENV_STR("AUTHORIZER_URL", None)
CBONDS_BROKER_URL = os.environ.get("CBONDS_BROKER_URL", None)
SUPERSET_URL = os.environ.get("SUPERSET_URL", None)
UNIFIED_DATA_PROVIDER_URL = os.environ.get("UNIFIED_DATA_PROVIDER_URL", None)
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10240
ROUND_NDIGITS = ENV_INT("ROUND_NDIGITS", 6)
FILE_UPLOAD_MAX_MEMORY_SIZE = (
    0  # Important, that all files write to temporary file no matter size
)
ALLOWED_HOSTS = ["*"]

# Application definition

INSTALLED_APPS = [
    "modeltranslation",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "drf_yasg",
    "django_filters",
    "mptt",
    "healthcheck",
    "poms.history",  # order is important because it registers models to listen to
    "poms.system",
    # 'poms.cache_machine',
    "poms.users",
    "poms.iam",
    "poms.notifications",
    "poms.obj_attrs",
    "poms.ui",
    "poms.accounts",
    "poms.counterparties",
    "poms.currencies",
    "poms.instruments",
    "poms.portfolios",
    "poms.strategies",
    "poms.transactions",
    "poms.integrations",
    "poms.reports",
    "poms.api",
    "poms.csv_import",
    "poms.transaction_import",
    "poms.complex_import",
    "poms.configuration_export",  # DEPRECATED
    "poms.configuration_import",  # DEPRECATED
    "poms.reference_tables",
    "poms.celery_tasks",
    "poms.reconciliation",
    "poms.file_reports",
    "poms.configuration_sharing",  # DEPRECATED
    "poms.pricing",
    "poms.schedules",
    "poms.procedures",
    "poms.credentials",
    "poms.vault",
    "poms.system_messages",
    "poms.configuration",
    "poms.auth_tokens",
    "poms.widgets",
    "django.contrib.admin",
    "django.contrib.admindocs",
    "crispy_forms",
    "rest_framework",
    "rest_framework_swagger",
    "corsheaders",
    # 'django_otp',
    # 'django_otp.plugins.otp_hotp',
    # 'django_otp.plugins.otp_totp',
    # 'django_otp.plugins.otp_email',
    # 'django_otp.plugins.otp_static',
    # 'two_factor',
    "django_celery_results",
    "django_celery_beat",
    "finmars_standardized_errors",
    # ==================================
    # = IMPORTANT LOGIC ON APP STARTUP =
    # ==================================
    "poms.bootstrap",
]

if USE_DEBUGGER:
    INSTALLED_APPS.append("debug_toolbar")
    INSTALLED_APPS.append("pympler")

# MIDDLEWARE_CLASSES = [
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",

    "corsheaders.middleware.CorsMiddleware",
    "corsheaders.middleware.CorsPostCsrfMiddleware",

    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # for static files
    # Possibly Deprecated
    # 'django.middleware.gzip.GZipMiddleware',
    # 'django.middleware.http.ConditionalGetMiddleware',
    # 'django.middleware.security.SecurityMiddleware',
    # 'django.contrib.sessions.middleware.SessionMiddleware',
    # 'django.middleware.locale.LocaleMiddleware',
    # 'django.middleware.common.CommonMiddleware',
    # 'django.middleware.csrf.CsrfViewMiddleware',
    # 'django.contrib.auth.middleware.AuthenticationMiddleware',
    # 'django.contrib.messages.middleware.MessageMiddleware',
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',

    "poms.common.middleware.CommonMiddleware",  # required for getting request object anywhere

    # 'poms.common.middleware.LogRequestsMiddleware',
    "finmars_standardized_errors.middleware.ExceptionMiddleware",
]

if USE_DEBUGGER:
    MIDDLEWARE.append("debug_toolbar.middleware.DebugToolbarMiddleware")
    # MIDDLEWARE.append("poms.common.middleware.MemoryMiddleware")  # memory tracking


PROFILER = ENV_BOOL("PROFILER", False)

if PROFILER:
    MIDDLEWARE.append("django_cprofile_middleware.middleware.ProfilerMiddleware")
    DJANGO_CPROFILE_MIDDLEWARE_REQUIRE_STAFF = False

ROOT_URLCONF = "poms_app.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.request",
                "django.template.context_processors.debug",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages",
            ],
            "libraries": {
                "staticfiles": "django.templatetags.static",
            },
        },
    },
]

WSGI_APPLICATION = "poms_app.wsgi.application"

# ============
# = Database =
# ============
# https://docs.djangoproject.com/en/4.0/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": ENV_STR("DB_NAME", "postgres"),
        "USER": ENV_STR("DB_USER", "postgres"),
        "PASSWORD": ENV_STR("DB_PASSWORD", "postgres"),
        "HOST": ENV_STR("DB_HOST", "localhost"),
        "PORT": ENV_INT("DB_PORT", 5432),
        "CONN_MAX_AGE": ENV_INT("CONN_MAX_AGE", 60),
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

# Password validation
# https://docs.djangoproject.com/en/1.9/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
# https://docs.djangoproject.com/en/1.9/topics/i18n/

LANGUAGE_CODE = "en"
LANGUAGES = [
    ("en", gettext_lazy("English")),
    # ('es', gettext_lazy('Spanish')),
    # ('de', gettext_lazy('Deutsch')),
    # ('ru', gettext_lazy('Russian')),
]

TIME_ZONE = "UTC"

USE_I18N = True
USE_L10N = True
USE_TZ = True
USE_ETAGS = True

# TODO Refactor csrf protection later

ENV_CSRF_COOKIE_DOMAIN = os.environ.get("ENV_CSRF_COOKIE_DOMAIN", ".finmars.com")
ENV_CSRF_TRUSTED_ORIGINS = os.environ.get("ENV_CSRF_TRUSTED_ORIGINS", None)

if SERVER_TYPE == "production":
    CORS_URLS_REGEX = r"^/api/.*$"
    # CORS_REPLACE_HTTPS_REFERER = True
    CORS_ALLOW_CREDENTIALS = True
    CORS_PREFLIGHT_MAX_AGE = 300
    USE_X_FORWARDED_HOST = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_REDIRECT_EXEMPT = ['healthcheck']
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    CSRF_COOKIE_SAMESITE = 'Strict'

if SERVER_TYPE == "development":
    CORS_ORIGIN_ALLOW_ALL = True
    CORS_ALLOW_CREDENTIALS = True
    CSRF_COOKIE_SECURE = True
    CSRF_COOKIE_SAMESITE = "Strict"
    CSRF_COOKIE_DOMAIN = ENV_CSRF_COOKIE_DOMAIN
    CSRF_TRUSTED_ORIGINS = ENV_CSRF_TRUSTED_ORIGINS.split(",")

if SERVER_TYPE == "local":
    CORS_ALLOW_ALL_ORIGINS = True
    CORS_ORIGIN_ALLOW_ALL = True
    CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_ALL_ORIGINS = ENV_BOOL('CORS_ALLOW_ALL_ORIGINS', False)

CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]

CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]

STATIC_URL = f"/{BASE_API_URL}/api/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "static")  # creates when collectstatic

STATICFILES_DIR = os.path.join(BASE_DIR, "poms", "api", "static")

# ==============
# = WEBSOCKETS =
# ==============

USE_WEBSOCKETS = ENV_BOOL("USE_WEBSOCKETS", False)
WEBSOCKET_HOST = ENV_STR("WEBSOCKET_HOST", "ws://0.0.0.0:6969")
WEBSOCKET_APP_TOKEN = ENV_STR("WEBSOCKET_APP_TOKEN", "943821230")

# CACHES = {
#     "default": {
#         "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
#     },
#     "throttling": {
#         "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
#     },
#     "http_session": {
#         "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
#     },
# }

# Maybe in future, we will return to Redis
# CACHES = {
#     'default': {
#         'BACKEND': 'django.core.cache.backends.redis.RedisCache',
#         'LOCATION': 'redis://127.0.0.1:6379',
#     },
# }

# SESSION_SERIALIZER = 'django.contrib.sessions.serializers.JSONSerializer'
# SESSION_ENGINE = "poms.http_sessions.backends.cached_db"
# SESSION_CACHE_ALIAS = 'http_session'

SEND_LOGS_TO_FINMARS = ENV_BOOL("SEND_LOGS_TO_FINMARS", False)
FINMARS_LOGSTASH_HOST = ENV_STR("FINMARS_LOGSTASH_HOST", "3.123.159.169")
FINMARS_LOGSTASH_PORT = ENV_INT("FINMARS_LOGSTASH_PORT", 5044)

DJANGO_LOG_LEVEL = ENV_STR("DJANGO_LOG_LEVEL", "INFO")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "()": "colorlog.ColoredFormatter",
            "format": "%(log_color)s [%(levelname)s] [%(asctime)s] [%(processName)s] [%(name)s] [%(module)s:%(lineno)d] - %(message)s",
            "log_colors": {
                "DEBUG": "cyan",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "bold_red",
            },
        },
        "provision-verbose": {
            "()": GunicornWorkerIDLogFormatter,
            "format": "[%(asctime)s] [worker-%(pid)s] [%(module)s:%(lineno)d] - %(message)s",
        },
    },
    "handlers": {
        "console": {
            "level": DJANGO_LOG_LEVEL,
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "provision-console": {
            "level": DJANGO_LOG_LEVEL,
            "class": "logging.StreamHandler",
            "formatter": "provision-verbose",
        },
        "file": {
            "level": DJANGO_LOG_LEVEL,
            "class": "logging.FileHandler",  # TODO refactor to more sophisticated handler
            # 'class': 'logging.handlers.TimedRotatingFileHandler',
            # 'interval': 1,
            # 'when': 'D',
            "filename": "/var/log/finmars/backend/django.log",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django.request": {"level": "ERROR", "handlers": ["file"]},
        "provision": {
            "handlers": ["provision-console", "file"],
            "level": "INFO",
            "propagate": True,
        },
        "django": {
            "handlers": ["file"],
            "level": "ERROR",
            "propagate": True,
        },
        "poms": {
            "level": DJANGO_LOG_LEVEL,
            "handlers": ["file"],
            "propagate": True,
        },
        "finmars": {
            "level": DJANGO_LOG_LEVEL,
            "handlers": ["file"],
            "propagate": True,
        },
    },
}

if SEND_LOGS_TO_FINMARS:
    LOGGING["handlers"]["logstash"] = {
        "level": DJANGO_LOG_LEVEL,
        "class": "logstash.TCPLogstashHandler",
        "host": FINMARS_LOGSTASH_HOST,
        "port": FINMARS_LOGSTASH_PORT,  # Default value: 5959
        "message_type": "finmars-backend",  # 'type' field in logstash message. Default value: 'logstash'.
        "fqdn": False,  # Fully qualified domain name. Default value: false.
        "ssl_verify": False,  # Fully qualified domain name. Default value: false.
        # 'tags': ['tag1', 'tag2'],  # list of tags. Default: None.
    }

    LOGGING["loggers"]["django.request"]["handlers"].append("logstash")
    LOGGING["loggers"]["django"]["handlers"].append("logstash")
    LOGGING["loggers"]["poms"]["handlers"].append("logstash")

if SERVER_TYPE == "local":
    LOGGING["loggers"]["django.request"]["handlers"].append("console")
    LOGGING["loggers"]["django"]["handlers"].append("console")
    LOGGING["loggers"]["poms"]["handlers"].append("console")
    LOGGING["loggers"]["finmars"]["handlers"].append("console")

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "rest_framework.schemas.coreapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "poms.common.pagination.PageNumberPaginationExt",
    "PAGE_SIZE": 40,
    # 'EXCEPTION_HANDLER': 'poms.common.utils.finmars_exception_handler',
    "EXCEPTION_HANDLER": "finmars_standardized_errors.handler.exception_handler",
    "DEFAULT_AUTHENTICATION_CLASSES": (
        # 'rest_framework.authentication.SessionAuthentication',
        # 'rest_framework.authentication.BasicAuthentication',
        # 'rest_framework.authentication.TokenAuthentication',
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "poms.common.authentication.KeycloakAuthentication",
        # "poms.auth_tokens.authentication.ExpiringTokenAuthentication",
    ),
    "DEFAULT_FILTER_BACKENDS": ("django_filters.rest_framework.DjangoFilterBackend",),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_RENDERER_CLASSES": (
        # 'rest_framework.renderers.JSONRenderer',
        "poms.common.renderers.CustomJSONRenderer",
    ),
    "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.NamespaceVersioning",
    # 'DEFAULT_PARSER_CLASSES': (
    #     'rest_framework.parsers.JSONParser',
    #     'rest_framework.parsers.FormParser',
    #     'rest_framework.parsers.MultiPartParser',
    # ),
    # "DEFAULT_THROTTLE_CLASSES": (
    #     "poms.api.throttling.AnonRateThrottleExt",
    #     "poms.api.throttling.UserRateThrottleExt",
    # ),
    "DEFAULT_THROTTLE_RATES": {
        # 'anon': '5/second',
        # 'user': '50/second',
        "anon": "20/min",
        "user": "500/min",
    }
    # 'DATETIME_FORMAT': '%Y-%m-%dT%H:%M:%S %Z',
    # 'DATETIME_INPUT_FORMATS': (ISO_8601, '%c', '%Y-%m-%d %H:%M:%S %Z'),
}

REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] += (
    "rest_framework.renderers.BrowsableAPIRenderer",
    "rest_framework.renderers.AdminRenderer",
)

AUTHENTICATION_BACKENDS = ("django.contrib.auth.backends.ModelBackend",)

DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5mb

# =================
# = SMTP Settings =
# =================

DEFAULT_FROM_EMAIL = ENV_STR(
    "DEFAULT_FROM_EMAIL", '"Finmars Notifications" <no-reply@finmars.com>'
)
SERVER_EMAIL = ENV_STR("SERVER_EMAIL", '"ADMIN: FinMars" <no-reply@finmars.com>')
EMAIL_HOST = ENV_STR("EMAIL_HOST", "email-smtp.eu-west-1.amazonaws.com")
EMAIL_PORT = ENV_INT("EMAIL_PORT", 587)
EMAIL_HOST_USER = ENV_STR("EMAIL_HOST_USER", None)
EMAIL_HOST_PASSWORD = ENV_STR("EMAIL_HOST_PASSWORD", None)

GEOIP_PATH = os.path.join(BASE_DIR, "data")
GEOIP_COUNTRY = "GeoLite2-Country.mmdb"
GEOIP_CITY = "GeoLite2-City.mmdb"

# ==========
# = CELERY =
# ==========

RABBITMQ_HOST = ENV_STR("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = ENV_INT("RABBITMQ_PORT", 5672)
RABBITMQ_USER = ENV_STR("RABBITMQ_USER", "guest")
RABBITMQ_PASSWORD = ENV_STR("RABBITMQ_PASSWORD", "guest")
RABBITMQ_VHOST = ENV_STR("RABBITMQ_VHOST", "")

# CELERY_EAGER_PROPAGATES = True
# CELERY_TASK_ALWAYS_EAGER = True
# CELERY_TASK_ACKS_LATE = True

CELERY_BROKER_URL = (
    f"amqp://{RABBITMQ_USER}:{RABBITMQ_PASSWORD}@{RABBITMQ_HOST}:"
    f"{RABBITMQ_PORT}/{RABBITMQ_VHOST}"
)
CELERY_RESULT_BACKEND = "django-db"
CELERY_ENABLE_UTC = True
CELERY_TIMEZONE = "UTC"

CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"

CELERY_TASK_SEND_SENT_EVENT = True

if CELERY_RESULT_BACKEND in {"django-db"}:
    CELERY_RESULT_EXPIRES = 2 * 24 * 60 * 60
    CELERY_TASK_STORE_ERRORS_EVEN_IF_IGNORED = CELERY_RESULT_BACKEND in {"django-db"}
else:
    CELERY_RESULT_EXPIRES = 60
    CELERY_TASK_STORE_ERRORS_EVEN_IF_IGNORED = True

CELERY_MAX_MEMORY_PER_CHILD = ENV_INT("CELERY_MAX_MEMORY_PER_CHILD", 512 * 1024) # Maximum amount of resident memory, in KiB
CELERY_MAX_TASKS_PER_CHILD = ENV_INT("CELERY_MAX_TASKS_PER_CHILD", 1) # Maximum number of tasks a pool worker can execute before it’s terminated and replaced by a new worker.

CELERY_WORKER_LOG_COLOR = True
CELERY_WORKER_LOG_FORMAT = "[%(levelname)1.1s %(asctime)s %(process)d:%(thread)d %(name)s %(module)s:%(lineno)d] %(message)s"

CELERY_WORKER_CONCURRENCY = ENV_INT("CELERY_WORKER_CONCURRENCY", 2) # Number of child processes processing the queue. The default is the number of CPUs available on your system.


# CELERY_ACKS_LATE: If this is True, the task messages will be acknowledged after the task has been executed, not just before, which is the default behavior.
# This means the tasks can be recovered when a worker crashes, as the tasks won't be removed from the queue until they are completed.
# However, keep in mind that this could lead to tasks being executed multiple times if the worker crashes during execution, so ensure that your tasks are idempotent.
CELERY_ACKS_LATE = True

# CELERY_TASK_REJECT_ON_WORKER_LOST: If this is True, when the worker of a task is lost (e.g., crashes), the task will be returned back to the queue,
# so it can be picked up by another worker.
# This increases the resiliency of the system as the tasks are not lost, they are retried.
# But, it can also increase the load on the system as tasks could potentially be executed multiple times in the event of frequent worker failures.
# Make sure your tasks are safe to be retried in such cases (idempotent).
CELERY_TASK_REJECT_ON_WORKER_LOST = False  # Make tasks rejected

# ===================
# = Django Storages =
# ===================

SFTP_STORAGE_HOST = ENV_STR("SFTP_STORAGE_HOST", None)
SFTP_STORAGE_ROOT = os.environ.get("SFTP_ROOT", "/finmars/")
SFTP_PKEY_PATH = os.environ.get("SFTP_PKEY_PATH", None)

SFTP_STORAGE_PARAMS = {
    "username": os.environ.get("SFTP_USERNAME", None),
    "password": os.environ.get("SFTP_PASSWORD", None),
    "port": ENV_INT("SFTP_PORT", 22),
    "allow_agent": False,
    "look_for_keys": False,
}
if SFTP_PKEY_PATH:
    SFTP_STORAGE_PARAMS["key_filename"] = SFTP_PKEY_PATH

SFTP_STORAGE_INTERACTIVE = False
SFTP_KNOWN_HOST_FILE = os.path.join(BASE_DIR, ".ssh/known_hosts")

AWS_S3_ACCESS_KEY_ID = os.environ.get("AWS_S3_ACCESS_KEY_ID", None)
AWS_S3_SECRET_ACCESS_KEY = os.environ.get("AWS_S3_SECRET_ACCESS_KEY", None)
AWS_STORAGE_BUCKET_NAME = os.environ.get("AWS_STORAGE_BUCKET_NAME", None)
AWS_S3_ENDPOINT_URL = os.environ.get("AWS_S3_ENDPOINT_URL", None)
AWS_S3_VERIFY = os.environ.get("AWS_S3_VERIFY", None)
if os.environ.get("AWS_S3_VERIFY") == "False":
    AWS_S3_VERIFY = False

AZURE_ACCOUNT_KEY = os.environ.get("AZURE_ACCOUNT_KEY", None)
AZURE_ACCOUNT_NAME = os.environ.get("AZURE_ACCOUNT_NAME", None)
AZURE_CONTAINER = os.environ.get("AZURE_CONTAINER", None)

# INTEGRATIONS ------------------------------------------------
# DEPRECATED
BLOOMBERG_WSDL = "https://service.bloomberg.com/assets/dl/dlws.wsdl"
BLOOMBERG_MAX_RETRIES = 60
BLOOMBERG_DATE_INPUT_FORMAT = "%m/%d/%Y"
BLOOMBERG_EMPTY_VALUE = [None, "", "N.S."]

BLOOMBERG_SANDBOX = os.environ.get("POMS_BLOOMBERG_SANDBOX") != "False"
BLOOMBERG_RETRY_DELAY = 0.1 if BLOOMBERG_SANDBOX else 5
BLOOMBERG_SANDBOX_SEND_EMPTY = False
BLOOMBERG_SANDBOX_SEND_FAIL = False
BLOOMBERG_SANDBOX_WAIT_FAIL = False

# PRICING SECTION

MEDIATOR_URL = ENV_STR("MEDIATOR_URL", "")
DATA_FILE_SERVICE_URL = ENV_STR("DATA_FILE_SERVICE_URL", "")
FINMARS_DATABASE_URL = ENV_STR("FINMARS_DATABASE_URL", "https://database.finmars.com/")
FINMARS_DATABASE_RETRIES = ENV_INT("FINMARS_DATABASE_RETRIES", 2)
FINMARS_DATABASE_TIMEOUT = ENV_INT("FINMARS_DATABASE_TIMEOUT", 30)
FINMARS_DATABASE_SLEEP = ENV_INT("FINMARS_DATABASE_SLEEP", 1)

INSTRUMENT_EVENTS_REGULAR_MAX_INTERVALS = 1000

try:
    from poms_app.settings_local import *
except ImportError:
    pass

INTERNAL_IPS = [
    "0.0.0.0",
    "127.0.0.1",
    "localhost",
]

if USE_DEBUGGER:
    DEBUG_TOOLBAR_PANELS = [
        "debug_toolbar.panels.versions.VersionsPanel",
        "debug_toolbar.panels.timer.TimerPanel",
        "debug_toolbar.panels.settings.SettingsPanel",
        "debug_toolbar.panels.headers.HeadersPanel",
        "debug_toolbar.panels.request.RequestPanel",
        "debug_toolbar.panels.sql.SQLPanel",
        "debug_toolbar.panels.templates.TemplatesPanel",
        "debug_toolbar.panels.staticfiles.StaticFilesPanel",
        "debug_toolbar.panels.cache.CachePanel",
        "debug_toolbar.panels.signals.SignalsPanel",
        "debug_toolbar.panels.logging.LoggingPanel",
        "debug_toolbar.panels.redirects.RedirectsPanel",
        "debug_toolbar.panels.profiling.ProfilingPanel",
        "pympler.panels.MemoryPanel",
    ]

    DEBUG_TOOLBAR_CONFIG = {
        "RESULTS_STORE_SIZE": 100,
    }

# ========================
# = KEYCLOAK INTEGRATION =
# ========================

KEYCLOAK_SERVER_URL = os.environ.get(
    "KEYCLOAK_SERVER_URL", "https://eu-central.finmars.com"
)
KEYCLOAK_REALM = os.environ.get("KEYCLOAK_REALM", "finmars")
KEYCLOAK_CLIENT_ID = os.environ.get("KEYCLOAK_CLIENT_ID", "finmars")

# not required anymore, api works in Bearer-only mod
KEYCLOAK_CLIENT_SECRET_KEY = os.environ.get("KEYCLOAK_CLIENT_SECRET_KEY", None)

SIMPLE_JWT = {
    "SIGNING_KEY": os.getenv("SIGNING_KEY", SECRET_KEY),
    "USER_ID_FIELD": "username",
}

REDOC_SETTINGS = {
    "LAZY_RENDERING": True,
    "NATIVE_SCROLLBARS": True,
}

VAULT_TOKEN = ENV_STR("VAULT_TOKEN", None)

# SENTRY

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

sentry_sdk.init(
    dsn="https://af79f220a0594fa6a2b3d69a65c4c27a@sentry.finmars.com/2",
    integrations=[DjangoIntegration()],

    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    # We recommend adjusting this value in production.
    traces_sample_rate=1.0,

    # If you wish to associate users to errors (assuming you are using
    # django.contrib.auth) you may enable sending PII data.
    send_default_pii=True
)
