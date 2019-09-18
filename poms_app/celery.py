from __future__ import absolute_import, unicode_literals

from celery import Celery
from django.conf import settings
from poms.common.kombu_serializers import register_pickle_signed

# register_pickle_signed(salt='poms-pickle-signed', compress=True)
# register_pickle_signed(salt='poms-pickle-signed', compress=False)

app = Celery('poms.backend')

app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
