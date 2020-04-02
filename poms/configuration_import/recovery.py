import time

from logging import getLogger

from poms.configuration_import.data import currency_standard, account_type_standard
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

        for item in self.configuration['items']:

            if 'currencies.currency' in item['entity']:
                self.fix_currencies(item)

            if 'accounts.accounttype' in item['entity']:
                self.fix_account_types(item)

        _l.info('Configuration Recovery done %s' % (time.perf_counter() - st))

        return self.configuration

    def fix_currencies(self, data):

        st = time.perf_counter()

        if 'content' in data:

            for content_object in data['content']:

                content_object = recursive_dict_fix(currency_standard, content_object)

        _l.info('Currency Recovery done %s' % (time.perf_counter() - st))

    def fix_account_types(self, data):

        st = time.perf_counter()

        if 'content' in data:

            for content_object in data['content']:

                content_object = recursive_dict_fix(account_type_standard, content_object)

        _l.info('Account Type Recovery done %s' % (time.perf_counter() - st))
