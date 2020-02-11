from poms.pricing.brokers.base_broker import BaseBroker
from poms_app import settings


class BrokerBloomberg(BaseBroker):

    broker_url = settings.BROKER_BLOOMBERG_URL

    def __init__(self):

        print("Broker: Bloomberg. Status: Initialized")


    def send_request(self, procedure, data):

        request_data = {}

        request_data['procedure'] = procedure.id
        request_data['data'] = data

        # print('request_data %s' % request_data)

        self.request_post(request_data)
