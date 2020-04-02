import copy

from django.contrib.contenttypes.models import ContentType
import time

from poms.configuration_import.data import currency_standard, account_type_standard, instrument_type_standard
from poms.configuration_import.models import ConfigurationEntityArchetype
from poms.users.models import MasterUser, EcosystemDefault

import logging

_l = logging.getLogger('poms.configuration_import')


class ConfigurationEntityArchetypeGenerateHandler(object):

    def __init__(self):

        self.master_users = MasterUser.objects.all()
        self.ecosystem_defaults = {}
        self.fetch_ecosystem_defaults_by_master_user()

    def fetch_ecosystem_defaults_by_master_user(self):

        defaults = EcosystemDefault.objects.all()

        for master_user in self.master_users:

            for default in defaults:

                if default.master_user == master_user:
                    self.ecosystem_defaults[master_user.id] = default

    def generate_currency_archetype(self):

        st = time.perf_counter()

        for master_user in self.master_users:

            name = "Currency Archetype"
            content_type = ContentType.objects.get(model="currency", app_label="currencies")

            try:
                archetype = ConfigurationEntityArchetype.objects.get(master_user=master_user, name=name,
                                                               content_type=content_type)
            except ConfigurationEntityArchetype.DoesNotExist:
                archetype = ConfigurationEntityArchetype(master_user=master_user, name=name,
                                                   content_type=content_type)

            archetype.data = currency_standard

            archetype.save()

        _l.info('Generating Currency Archetypes %s' % (time.perf_counter() - st))

    def generate_account_type_archetype(self):

        st = time.perf_counter()

        for master_user in self.master_users:

            name = "Account Type Archetype"
            content_type = ContentType.objects.get(model="accounttype", app_label="accounts")

            try:
                archetype = ConfigurationEntityArchetype.objects.get(master_user=master_user, name=name,
                                                                     content_type=content_type)
            except ConfigurationEntityArchetype.DoesNotExist:
                archetype = ConfigurationEntityArchetype(master_user=master_user, name=name,
                                                         content_type=content_type)

            archetype.data = account_type_standard

            archetype.save()

        _l.info('Generating Instrument Types Archetypes %s' % (time.perf_counter() - st))

    def generate_instrument_type_archetype(self):

        st = time.perf_counter()

        for master_user in self.master_users:

            ecosystem_defaults = self.ecosystem_defaults[master_user.id]

            name = "Instrument Type Archetype"
            content_type = ContentType.objects.get(model="instrumenttype", app_label="instruments")

            try:
                archetype = ConfigurationEntityArchetype.objects.get(master_user=master_user, name=name,
                                                                     content_type=content_type)
            except ConfigurationEntityArchetype.DoesNotExist:
                archetype = ConfigurationEntityArchetype(master_user=master_user, name=name,
                                                         content_type=content_type)

            data = copy.deepcopy(instrument_type_standard)

            data['instrument_class'] = ecosystem_defaults.instrument_class.id
            data['one_off_event'] = ecosystem_defaults.transaction_type.id
            data['regular_event'] = ecosystem_defaults.transaction_type.id
            data['factor_same'] = ecosystem_defaults.transaction_type.id
            data['factor_up'] = ecosystem_defaults.transaction_type.id
            data['factor_down'] = ecosystem_defaults.transaction_type.id

            archetype.data = data

            archetype.save()

        _l.info('Generating Instrument Type Archetypes %s' % (time.perf_counter() - st))



    def process(self):

        self.generate_currency_archetype()
        self.generate_account_type_archetype()
        self.generate_instrument_type_archetype()

