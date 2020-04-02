import time

from logging import getLogger

from poms.configuration_import.models import ConfigurationEntityArchetype
from poms.layout_recovery.utils import recursive_dict_fix

_l = getLogger('poms.configuration_import')


class ConfigurationRecoveryHandler(object):

    def __init__(self, master_user, configuration=None):

        self.master_user = master_user

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

            if 'instruments.instrumenttype' in item['entity']:
                self.fix_instrument_types(item)

        _l.info('Configuration Recovery done %s' % (time.perf_counter() - st))

        return self.configuration

    def fix_currencies(self, data):

        try:

            st = time.perf_counter()

            archetype = ConfigurationEntityArchetype.objects.get(master_user=self.master_user,
                                                                 content_type__model="currency",
                                                                 content_type__app_label="currencies")

            if 'content' in data:

                for content_object in data['content']:
                    content_object = recursive_dict_fix(archetype.data, content_object)

            _l.info('Currency Recovery done %s' % (time.perf_counter() - st))

        except (ConfigurationEntityArchetype.DoesNotExist, Exception) as e:

            _l.info('Currency Recovery error %s' % e)

    def fix_account_types(self, data):

        try:

            st = time.perf_counter()

            archetype = ConfigurationEntityArchetype.objects.get(master_user=self.master_user,
                                                                 content_type__model="accounttype",
                                                                 content_type__app_label="accounts")

            if 'content' in data:

                for content_object in data['content']:
                    content_object = recursive_dict_fix(archetype.data, content_object)

            _l.info('Account Type Recovery done %s' % (time.perf_counter() - st))

        except (ConfigurationEntityArchetype.DoesNotExist, Exception) as e:

            _l.info('Account Type Recovery error %s' % e)

    def fix_instrument_types(self, data):

        try:

            st = time.perf_counter()

            archetype = ConfigurationEntityArchetype.objects.get(master_user=self.master_user,
                                                                 content_type__model="instrumenttype",
                                                                 content_type__app_label="instruments")

            if 'content' in data:

                for content_object in data['content']:
                    content_object = recursive_dict_fix(archetype.data, content_object)

            _l.info('Instrument Type Recovery done %s' % (time.perf_counter() - st))

        except (ConfigurationEntityArchetype.DoesNotExist, Exception) as e:

            _l.info('Instrument Type Recovery error %s' % e)
