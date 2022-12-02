import json

import requests


class BaseBroker(object):
    broker_url = None

    def request_post(self, data):
        headers = {'Content-type': 'application/json', 'Accept': 'application/json'}

        response = requests.post(url=self.broker_url + 'process/pricing/', data=json.dumps(data), headers=headers, verify=settings.VERIFY_SSL)

        return response
