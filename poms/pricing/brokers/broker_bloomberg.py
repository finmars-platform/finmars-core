from poms.pricing.brokers.base_broker import BaseBroker
from poms_app import settings


class BrokerBloomberg(BaseBroker):

    broker_url = settings.BROKER_BLOOMBERG_URL

    def __init__(self):

        print("Broker: Bloomberg. Status: Initialized")


    def send_request(self, data):

        self.request_post(data)
