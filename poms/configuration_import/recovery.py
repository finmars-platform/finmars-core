import time

from logging import getLogger

from poms.configuration_import.data import currency_standard
from poms.layout_recovery.utils import recursive_dict_fix

_l = getLogger('poms.configuration_import')


class ConfigurationRecoveryHandler(object):

    def __init__(self, configuration=None):

        if configuration:
            self.configuration = configuration

    def set_configuration(self, configuration):

        self.configuration = configuration

    def process_recovery(self):

        st = time.perf_counter()

        self.fix_currencies()

        _l.info('Configuration Recovery done %s' % (time.perf_counter() - st))

        return self.configuration

    def fix_currencies(self):

        st = time.perf_counter()

        for item in self.configuration['items']:

            if 'currencies.currency' in item['entity']:

                if 'content' in item:

                    for content_object in item['content']:

                        content_object = recursive_dict_fix(currency_standard, content_object)

        _l.info('Currency Recovery done %s' % (time.perf_counter() - st))
