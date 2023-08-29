import json
from logging import getLogger

import requests
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

from poms_app import settings

_l = getLogger('poms.authorizer')


class AuthorizerService():

    def kick_member(self, member):
        User = get_user_model()

        # Probably need to come up with something more smart
        bot = User.objects.get(username="finmars_bot")

        refresh = RefreshToken.for_user(bot)

        refresh["space_code"] = settings.BASE_API_URL

        headers = {'Content-type': 'application/json',
                   'Accept': 'application/json',
                   'Authorization': 'Bearer %s' % refresh.access_token
                   }

        data = {
            "base_api_url": settings.BASE_API_URL,
            "username": member.user.username,
        }

        url = settings.AUTHORIZER_URL + '/api/v1/internal/kick-member/'

        _l.info("load_master_user_data url %s" % url)

        response = requests.post(url=url, data=json.dumps(data), headers=headers, verify=settings.VERIFY_SSL)

        if response.status_code != 200:
            raise Exception("Error kicking member %s" % response.text)

    def invite_member(self, member, from_user):

        User = get_user_model()

        # Probably need to come up with something more smart
        bot = User.objects.get(username="finmars_bot")

        refresh = RefreshToken.for_user(bot)

        refresh["space_code"] = settings.BASE_API_URL

        headers = {'Content-type': 'application/json',
                   'Accept': 'application/json',
                   'Authorization': 'Bearer %s' % refresh.access_token
                   }

        data = {
            "base_api_url": settings.BASE_API_URL,
            "username": member.username,
            "is_admin": member.is_admin,
            "from_user_username": from_user.username
        }

        url = settings.AUTHORIZER_URL + '/api/v1/internal/invite-member/'

        _l.info("load_master_user_data url %s" % url)

        response = requests.post(url=url, data=json.dumps(data), headers=headers, verify=settings.VERIFY_SSL)

        if response.status_code != 200:
            raise Exception("Error inviting member %s" % response.text)