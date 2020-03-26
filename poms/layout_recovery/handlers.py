import time

from django.contrib.contenttypes.models import ContentType

from poms.layout_recovery.data import entity_viewer_layout, balance_report_viewer_layout, \
    transaction_report_viewer_layout, pl_report_viewer_layout
from poms.layout_recovery.models import LayoutArchetype
from poms.layout_recovery.utils import recursive_dict_fix
from poms.ui.models import ListLayout
from poms.users.models import MasterUser, EcosystemDefault

import logging
import copy

_l = logging.getLogger('poms.layout_recovery')


class LayoutArchetypeGenerateHandler():

    def __init__(self):

        self.master_users = MasterUser.objects.all()
        self.entity_viewer_content_types = ContentType.objects.filter(
            model__in=['portfolio', 'account', 'instrument', 'counterparty', 'responsible', 'currency', 'strategy1',
                       'strategy2', 'strategy3', 'pricehistory', 'currencyhistory', 'type', 'instruenttype',
                       'transactiontype'])

        _l.info('entity_viewer_content_types %s' % self.entity_viewer_content_types)

        self.ecosystem_defaults = {}

        self.fetch_ecosystem_defaults_by_master_user()

    def fetch_ecosystem_defaults_by_master_user(self):

        defaults = EcosystemDefault.objects.all()

        for master_user in self.master_users:

            for default in defaults:

                if default.master_user == master_user:
                    self.ecosystem_defaults[master_user.id] = default

    def generate_entity_viewer_layout_archetype(self):

        st = time.perf_counter()

        for master_user in self.master_users:

            for content_type in self.entity_viewer_content_types:

                name = "Entity Viewer Layout (%s)" % content_type.model

                try:
                    layout_archetype = LayoutArchetype.objects.get(master_user=master_user, name=name,
                                                                   content_type=content_type)
                except LayoutArchetype.DoesNotExist:
                    layout_archetype = LayoutArchetype(master_user=master_user, name=name,
                                                       content_type=content_type)

                layout_archetype.data = entity_viewer_layout['data']

                layout_archetype.save()

        _l.info('Generating Entity Viewer Layouts Archetypes %s' % (time.perf_counter() - st))

    def generate_balance_report_viewer_archetype(self):

        st = time.perf_counter()

        content_type = ContentType.objects.get(model="balancereport")

        for master_user in self.master_users:

            try:

                name = "Balance Report Viewer Layout"

                ecosystem_defaults = self.ecosystem_defaults[master_user.id]

                try:
                    layout_archetype = LayoutArchetype.objects.get(master_user=master_user, name=name,
                                                                   content_type=content_type)
                except LayoutArchetype.DoesNotExist:
                    layout_archetype = LayoutArchetype(master_user=master_user, name=name,
                                                       content_type=content_type)

                data = copy.deepcopy(balance_report_viewer_layout['data'])

                data['reportOptions']['pricing_policy'] = ecosystem_defaults.pricing_policy.id
                data['reportOptions']['report_currency'] = ecosystem_defaults.currency.id

                layout_archetype.data = data

                layout_archetype.save()

            except Exception as e:
                _l.info('Balance Report Layout Error Master user %s' % master_user)
                _l.info('Balance Report Layout Error Message %s' % e)
                continue

        _l.info('Generating Balance Report Viewer Layouts Archetypes %s' % (time.perf_counter() - st))

    def generate_pl_report_viewer_archetype(self):

        st = time.perf_counter()

        content_type = ContentType.objects.get(model="plreport")

        for master_user in self.master_users:

            try:

                name = "PL Report Viewer Layout"

                ecosystem_defaults = self.ecosystem_defaults[master_user.id]

                try:
                    layout_archetype = LayoutArchetype.objects.get(master_user=master_user, name=name,
                                                                   content_type=content_type)
                except LayoutArchetype.DoesNotExist:
                    layout_archetype = LayoutArchetype(master_user=master_user, name=name,
                                                       content_type=content_type)

                data = copy.deepcopy(pl_report_viewer_layout['data'])

                data['reportOptions']['pricing_policy'] = ecosystem_defaults.pricing_policy.id
                data['reportOptions']['report_currency'] = ecosystem_defaults.currency.id

                layout_archetype.data = data

                layout_archetype.save()

            except Exception as e:
                _l.info('PL Report Layout Error Master user %s' % master_user)
                _l.info('PL Report Layout Error Message %s' % e)
                continue

        _l.info('Generating PL Report Viewer Layouts Archetypes %s' % (time.perf_counter() - st))

    def generate_transaction_report_viewer_archetype(self):

        st = time.perf_counter()

        content_type = ContentType.objects.get(model="transactionreport")

        for master_user in self.master_users:

            try:

                name = "Transaction Report Viewer Layout"

                ecosystem_defaults = self.ecosystem_defaults[master_user.id]

                try:
                    layout_archetype = LayoutArchetype.objects.get(master_user=master_user, name=name,
                                                                   content_type=content_type)
                except LayoutArchetype.DoesNotExist:
                    layout_archetype = LayoutArchetype(master_user=master_user, name=name,
                                                       content_type=content_type)

                data = copy.deepcopy(transaction_report_viewer_layout['data'])

                data['reportOptions']['pricing_policy'] = ecosystem_defaults.pricing_policy.id
                data['reportOptions']['report_currency'] = ecosystem_defaults.currency.id

                layout_archetype.data = data

                layout_archetype.save()

            except Exception as e:
                _l.info('Balance Report Layout Error Master user %s' % master_user)
                _l.info('Balance Report Layout Error Message %s' % e)
                continue

        _l.info('Generating Transaction Report Viewer Layouts Archetypes %s' % (time.perf_counter() - st))

    def process(self):

        self.generate_entity_viewer_layout_archetype()
        self.generate_balance_report_viewer_archetype()
        self.generate_pl_report_viewer_archetype()
        self.generate_transaction_report_viewer_archetype()


class LayoutFixHandler():

    def __init__(self):
        self.master_users = MasterUser.objects.all()
        self.layouts = ListLayout.objects.select_related('member').all()
        self.layout_archetypes = {}

        self.fetch_layout_archetypes_by_master_user()

    def fetch_layout_archetypes_by_master_user(self):

        layout_archetypes = LayoutArchetype.objects.all()

        for master_user in self.master_users:

            self.layout_archetypes[master_user.id] = []

            for layout_archetype in layout_archetypes:

                if layout_archetype.master_user == master_user:
                    self.layout_archetypes[master_user.id].append(layout_archetype)

    def process(self):

        st = time.perf_counter()

        index = 0

        for layout in self.layouts:

            layout_archetypes = self.layout_archetypes[layout.member.master_user_id]

            for layout_archetype in layout_archetypes:

                if layout_archetype.content_type == layout.content_type:

                    layout.data = recursive_dict_fix(layout_archetype.data, layout.data)

                    layout.save()

                    index = index + 1

        _l.info('Layout Fix Process %s' % (time.perf_counter() - st))
        _l.info("Layout Fix: Fixed layouts %s" % index)
