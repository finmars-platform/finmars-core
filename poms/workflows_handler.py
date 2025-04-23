import logging

import requests
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

from poms_app import settings

_l = logging.getLogger("poms.api")


def get_workflows_list(date_from, date_to, realm_code, space_code):
    """
    Requesting list of workflows from Finmars Workflow microservice
    Serves in Finmars Calendar web intrerface page
    :return:
    """

    user_model = get_user_model()

    bot = user_model.objects.get(username="finmars_bot")

    refresh = RefreshToken.for_user(bot)

    headers = {
        "Content-type": "application/json",
        "Accept": "application/json",
        "Authorization": "Bearer %s" % refresh.access_token,
    }

    if realm_code:
        url = (
            "https://"
            + settings.DOMAIN_NAME
            + "/"
            + realm_code
            + "/"
            + space_code
            + "/workflow/api/workflow/?created_after="
            + str(date_from)
            + "&created_before="
            + str(date_to)
        )

    else:
        url = (
            "https://"
            + settings.DOMAIN_NAME
            + "/"
            + space_code
            + "/workflow/api/workflow/?created_after="
            + str(date_from)
            + "&created_before="
            + str(date_to)
        )

    response = requests.get(url, headers=headers, verify=settings.VERIFY_SSL)

    if response.status_code != 200:
        _l.info("get_workflows_list.response.status_code %s" % response.status_code)
        raise Exception(response.text)

    data = response.json()

    workflows = data["results"]

    return workflows
