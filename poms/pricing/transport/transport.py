from poms_app import settings
import requests
import json

import logging

_l = logging.getLogger('poms.pricing')


class PricingTransport(object):

    mediator_url = settings.MEDIATOR_URL

    def __init__(self):

        print("Transport Status: Initialized")


    def send_request(self, data):

        headers = {'Content-type': 'application/json', 'Accept': 'application/json'}

        response = None

        try:

            response = requests.post(url=self.mediator_url + 'process/pricing/', data=json.dumps(data), headers=headers)

        except Exception:
            _l.info("Can't send request to Mediator. Is Mediator offline?")

            raise Exception("Mediator is unavailable")

        return response
