from __future__ import unicode_literals

from poms.common.fields import PrimaryKeyRelatedFilteredField, UserCodeOrPrimaryKeyRelatedField
from poms.strategies.models import Strategy1Group, Strategy1Subgroup, Strategy1, Strategy2Group, Strategy2Subgroup, \
    Strategy2, Strategy3Group, Strategy3Subgroup, Strategy3
from poms.users.filters import OwnerByMasterUserFilter


class Strategy1GroupField(PrimaryKeyRelatedFilteredField):
    queryset = Strategy1Group.objects
    filter_backends = [
        OwnerByMasterUserFilter,
    ]


class Strategy1SubgroupField(PrimaryKeyRelatedFilteredField):
    queryset = Strategy1Subgroup.objects
    filter_backends = [
        OwnerByMasterUserFilter,
    ]


class Strategy1Field(UserCodeOrPrimaryKeyRelatedField):
    queryset = Strategy1.objects
    # Possibly Deprecated
    # filter_backends = UserCodeOrPrimaryKeyRelatedField.filter_backends + [
    #     OwnerByMasterUserFilter,
    # ]


class Strategy1GroupDefault(object):
    requires_context = True

    def set_context(self, serializer_field):
        request = serializer_field.context['request']
        from poms.users.models import MasterUser
        from poms_app import settings
        self._master_user = MasterUser.objects.all().first()

    def __call__(self, serializer_field):
        self.set_context(serializer_field)
        from poms.users.models import EcosystemDefault
        self.ecosystem_defaults = EcosystemDefault.objects.get(master_user=self._master_user)

        return self.ecosystem_defaults.strategy1_group


class Strategy1SubgroupDefault(object):
    requires_context = True

    def set_context(self, serializer_field):
        request = serializer_field.context['request']

        from poms.users.models import MasterUser
        from poms_app import settings
        self._master_user = MasterUser.objects.all().first()

    def __call__(self, serializer_field):
        self.set_context(serializer_field)

        from poms.users.models import EcosystemDefault
        self.ecosystem_defaults = EcosystemDefault.objects.get(master_user=self._master_user)

        return self.ecosystem_defaults.strategy1_subgroup


class Strategy1Default(object):

    requires_context = True
    def set_context(self, serializer_field):
        request = serializer_field.context['request']
        from poms.users.models import MasterUser
        from poms_app import settings
        self._master_user = MasterUser.objects.all().first()

    def __call__(self, serializer_field):
        self.set_context(serializer_field)
        from poms.users.models import EcosystemDefault
        self.ecosystem_defaults = EcosystemDefault.objects.get(master_user=self._master_user)

        return self.ecosystem_defaults.strategy1


# 2

class Strategy2GroupField(Strategy1GroupField):
    queryset = Strategy2Group.objects


class Strategy2SubgroupField(Strategy1SubgroupField):
    queryset = Strategy2Subgroup.objects


class Strategy2Field(Strategy1Field):
    queryset = Strategy2.objects


class Strategy2GroupDefault(Strategy1GroupDefault):
    def __call__(self, serializer_field):
        self.set_context(serializer_field)

        from poms.users.models import EcosystemDefault
        self.ecosystem_defaults = EcosystemDefault.objects.get(master_user=self._master_user)

        return self.ecosystem_defaults.strategy2_group


class Strategy2SubgroupDefault(Strategy1SubgroupDefault):
    def __call__(self, serializer_field):
        self.set_context(serializer_field)

        from poms.users.models import EcosystemDefault
        self.ecosystem_defaults = EcosystemDefault.objects.get(master_user=self._master_user)

        return self.ecosystem_defaults.strategy2_subgroup


class Strategy2Default(Strategy1Default):
    def __call__(self, serializer_field):
        self.set_context(serializer_field)

        from poms.users.models import EcosystemDefault
        self.ecosystem_defaults = EcosystemDefault.objects.get(master_user=self._master_user)

        return self.ecosystem_defaults.strategy2


# 3


class Strategy3GroupField(Strategy1GroupField):
    queryset = Strategy3Group.objects


class Strategy3SubgroupField(Strategy1SubgroupField):
    queryset = Strategy3Subgroup.objects


class Strategy3Field(Strategy1Field):
    queryset = Strategy3.objects


class Strategy3GroupDefault(Strategy1GroupDefault):
    def __call__(self, serializer_field):
        self.set_context(serializer_field)

        from poms.users.models import EcosystemDefault
        self.ecosystem_defaults = EcosystemDefault.objects.get(master_user=self._master_user)

        return self.ecosystem_defaults.strategy3_group


class Strategy3SubgroupDefault(Strategy1SubgroupDefault):
    def __call__(self, serializer_field):
        self.set_context(serializer_field)

        from poms.users.models import EcosystemDefault
        self.ecosystem_defaults = EcosystemDefault.objects.get(master_user=self._master_user)

        return self.ecosystem_defaults.strategy3_subgroup


class Strategy3Default(Strategy1Default):
    def __call__(self, serializer_field):
        self.set_context(serializer_field)

        from poms.users.models import EcosystemDefault
        self.ecosystem_defaults = EcosystemDefault.objects.get(master_user=self._master_user)

        return self.ecosystem_defaults.strategy3
