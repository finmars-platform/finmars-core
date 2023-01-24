import os
from pathlib import Path

from environs import Env
import warnings

def ENV_BOOL(env_name, default):

    val = os.environ.get(env_name, default)

    if not val:
        return default

    if val == 'True' or val == True:
        return True

    if val == 'False' or val == False:
        return False

    warnings.warn('Variable %s is not boolean. It is %s' % (env_name, val))

def ENV_STR(env_name, default):

    val = os.environ.get(env_name, default)

    if not val:
        return default

    return val

def ENV_INT(env_name, default):

    val = os.environ.get(env_name, default)

    if not val:
        return default

    return int(val)


HIDDEN_CONFIG = [
    "DIRECTOR_ENABLE_HISTORY_MODE",
    "DIRECTOR_REFRESH_INTERVAL",
    "DIRECTOR_API_URL",
    "DIRECTOR_FLOWER_URL",
    "DIRECTOR_DATABASE_URI",
    "DIRECTOR_DATABASE_POOL_RECYCLE",
    "DIRECTOR_BROKER_URI",
    "DIRECTOR_RESULT_BACKEND_URI",
    "DIRECTOR_SENTRY_DSN",
]


print("==== Director init Config ====")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DIRECTOR_HOME = BASE_DIR + '/poms_director'

print('DIRECTOR_HOME %s' % DIRECTOR_HOME)

ENABLE_HISTORY_MODE = ENV_BOOL("DIRECTOR_ENABLE_HISTORY_MODE", False)
ENABLE_CDN = ENV_BOOL("DIRECTOR_ENABLE_CDN", True)
STATIC_FOLDER = ENV_STR(
    "DIRECTOR_STATIC_FOLDER", str(Path(DIRECTOR_HOME).resolve() / "static")
)
API_URL = ENV_STR("DIRECTOR_API_URL", "http://0.0.0.0:8001/api")
print('API_URL %s' % API_URL)
FLOWER_URL = ENV_STR("DIRECTOR_FLOWER_URL", "http://127.0.0.1:5555")
WORKFLOWS_PER_PAGE = ENV_INT("DIRECTOR_WORKFLOWS_PER_PAGE", 1000)
REFRESH_INTERVAL = ENV_INT("DIRECTOR_REFRESH_INTERVAL", 30000)
REPO_LINK = ENV_STR(
    "DIRECTOR_REPO_LINK", "https://github.com/ovh/celery-director"
)
DOCUMENTATION_LINK = ENV_STR(
    "DIRECTOR_DOCUMENTATION_LINK", "https://ovh.github.io/celery-director"
)

# Authentication
AUTH_ENABLED = ENV_BOOL("DIRECTOR_AUTH_ENABLED", False)

# SQLAlchemy configuration
SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_DATABASE_URI = ENV_STR("DIRECTOR_DATABASE_URI", "")
print('SQLALCHEMY_DATABASE_URI %s' % SQLALCHEMY_DATABASE_URI)
SQLALCHEMY_ENGINE_OPTIONS = {
    "pool_recycle": ENV_INT("DIRECTOR_DATABASE_POOL_RECYCLE", -1),
}

RABBITMQ_HOST = ENV_STR('RABBITMQ_HOST', 'localhost')
RABBITMQ_PORT = ENV_INT('RABBITMQ_PORT', 5672)
RABBITMQ_USER = ENV_STR('RABBITMQ_USER', 'guest')
RABBITMQ_PASSWORD = ENV_STR('RABBITMQ_PASSWORD', 'guest')
RABBITMQ_VHOST = ENV_STR('RABBITMQ_VHOST', '')

# Celery configuration
CELERY_CONF = {
    "task_always_eager": False,
    "broker_url": 'amqp://%s:%s@%s:%s/%s' % (RABBITMQ_USER, RABBITMQ_PASSWORD, RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_VHOST),
    "result_backend": 'db+' + ENV_STR("DIRECTOR_DATABASE_URI", ""),
    "broker_transport_options": {"master_name": "director"},
}

# Sentry configuration
SENTRY_DSN = ENV_STR("DIRECTOR_SENTRY_DSN", "")

# Default retention value (number of workflows to keep in the database)
DEFAULT_RETENTION_OFFSET = ENV_INT("DIRECTOR_DEFAULT_RETENTION_OFFSET", -1)

# Enable Vue debug loading vue.js instead of vue.min.js
VUE_DEBUG = ENV_BOOL("DIRECTOR_VUE_DEBUG", False)
