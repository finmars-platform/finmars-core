import json
import logging

import requests

from poms_app import settings

_l = logging.getLogger('poms.pricing')


class PricingTransport(object):
    mediator_url = settings.MEDIATOR_URL

    def __init__(self):

        print("Transport Status: Initialized")

    def send_request(self, data):

        headers = {'Content-type': 'application/json', 'Accept': 'application/json'}

        response = None

        try:

            _l.debug("Sending request to %s" % (str(self.mediator_url) + 'process/pricing/'))

            response = requests.post(url=str(self.mediator_url) + 'process/pricing/', data=json.dumps(data),
                                     headers=headers)

            _l.debug("Response received %s" % response)

        except Exception:
            _l.debug("Can't send request to Mediator. Is Mediator offline?")

            raise Exception("Mediator is unavailable")

        return response
