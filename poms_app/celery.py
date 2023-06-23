import os

from celery import Celery

# from django.conf import settings
# from poms.common.kombu_serializers import register_pickle_signed
# register_pickle_signed(salt='poms-pickle-signed', compress=True)
# register_pickle_signed(salt='poms-pickle-signed', compress=False)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "poms_app.settings")

app = Celery("poms_app")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()

app.conf.task_routes = {"*": {"queue": "backend-general-queue"}}
