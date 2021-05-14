"""
WSGI config for poms2 project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/howto/deployment/wsgi/
"""

from __future__ import unicode_literals

import os
import sys
from django.core.wsgi import get_wsgi_application

# import djcelery
# djcelery.setup_loader()
del sys.path[0]

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "poms_app.settings")

application = get_wsgi_application()

# application = StaticFilesHandler(application)


def register_at_authorizer_service():

    import requests
    import json

    try:
        print("register_at_authorizer_service processing")

        headers = {'Content-type': 'application/json', 'Accept': 'application/json'}

        data = {
            "base_api_url": settings.BASE_API_URL,
        }

        url = settings.AUTHORIZER_URL + '/backend-is-ready/'

        response = requests.post(url=url, data=json.dumps(data), headers=headers)

        print("register_at_authorizer_service processing response.status_code %s" % response.status_code)
        print("register_at_authorizer_service processing response.text %s" % response.text)

    except Exception as e:
        print("register_at_authorizer_service error %s" % e)

def one_time_startup():

    print("On startup methods")

    from django.conf import settings
    if 'SIMPLE' in settings.BACKEND_ROLES:
        register_at_authorizer_service()

one_time_startup()