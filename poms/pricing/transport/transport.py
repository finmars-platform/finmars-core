from poms_app import settings
import requests
import json



class PricingTransport(object):

    mediator_url = settings.MEDIATOR_URL

    def __init__(self):

        print("Transport Status: Initialized")


    def send_request(self, data):

        headers = {'Content-type': 'application/json', 'Accept': 'application/json'}

        response = requests.post(url=self.mediator_url, data=json.dumps(data), headers=headers)

        return response
