from __future__ import absolute_import, unicode_literals

from celery import Celery
import os
from django.conf import settings

from director import create_app
from poms.common.kombu_serializers import register_pickle_signed

# register_pickle_signed(salt='poms-pickle-signed', compress=True)
# register_pickle_signed(salt='poms-pickle-signed', compress=False)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'poms_app.settings')


app = Celery('poms_app')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()

# IMPORTANT
# =========================================================
# = HERE ARE DIRECTOR APP INITING FLASK/SQLALCHEMY        =
# = THATS ALLOWS DIRECTOR TASKS WORKS WITH CELERY BROKER  =
# = DO NOT REMOVE THIS LINE BELOW                         =
# =========================================================
director_app = create_app()