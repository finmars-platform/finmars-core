
import requests
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

from poms_app import settings

import logging

_l = logging.getLogger('poms.api')


def get_workflows_list():
    '''
    Requesting list of workflows from Finmars Workflow microservice
    Serves in Finmars Calendar web intrerface page
    :return:
    '''

    user_model = get_user_model()

    bot = user_model.objects.get(username="finmars_bot")

    refresh = RefreshToken.for_user(bot)

    headers = {'Content-type': 'application/json', 'Accept': 'application/json',
               'Authorization': 'Bearer %s' % refresh.access_token}

    url = settings.HOST_URL + '/' + settings.BASE_API_URL + '/workflow/api/workflow/'

    response = requests.get(url, headers)

    if response.status_code != 200:
        _l.info('get_workflows_list.response.status_code %s' % response.status_code)
        raise Exception(response.text)

    data = response.json()

    workflows = data['results']

    return workflows