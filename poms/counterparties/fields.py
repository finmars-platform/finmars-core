from __future__ import unicode_literals

from poms.common.fields import PrimaryKeyRelatedFilteredField, UserCodeOrPrimaryKeyRelatedField
from poms.counterparties.models import Counterparty, Responsible, CounterpartyGroup, ResponsibleGroup
from poms.users.filters import OwnerByMasterUserFilter


# class CounterpartyAttributeTypeField(PrimaryKeyRelatedFilteredField):
#     queryset = CounterpartyAttributeType.objects
#     filter_backends = [
#         OwnerByMasterUserFilter,
#         ObjectPermissionBackend,
#     ]
#
#
# class CounterpartyClassifierField(AttributeClassifierBaseField):
#     queryset = CounterpartyClassifier.objects


class CounterpartyGroupDefault(object):
    requires_context = True

    def set_context(self, serializer_field):
        request = serializer_field.context['request']
        from poms.users.models import MasterUser
        from poms_app import settings
        self._master_user = MasterUser.objects.get(base_api_url=settings.BASE_API_URL)

    def __call__(self, serializer_field):
        self.set_context(serializer_field)
        from poms.users.models import EcosystemDefault
        self.ecosystem_defaults = EcosystemDefault.objects.get(master_user=self._master_user)

        return self.ecosystem_defaults.counterparty_group


class CounterpartyGroupField(UserCodeOrPrimaryKeyRelatedField):
    queryset = CounterpartyGroup.objects
    filter_backends = [
        OwnerByMasterUserFilter,
    ]


class CounterpartyDefault(object):
    requires_context = True

    def set_context(self, serializer_field):
        request = serializer_field.context['request']
        from poms.users.models import MasterUser
        from poms_app import settings
        self._master_user = MasterUser.objects.get(base_api_url=settings.BASE_API_URL)

    def __call__(self, serializer_field):
        self.set_context(serializer_field)
        from poms.users.models import EcosystemDefault
        self.ecosystem_defaults = EcosystemDefault.objects.get(master_user=self._master_user)

        return self.ecosystem_defaults.counterparty


class CounterpartyField(UserCodeOrPrimaryKeyRelatedField):
    queryset = Counterparty.objects
    filter_backends = [
        OwnerByMasterUserFilter,
    ]


# class ResponsibleAttributeTypeField(PrimaryKeyRelatedFilteredField):
#     queryset = ResponsibleAttributeType.objects
#     filter_backends = [
#         OwnerByMasterUserFilter,
#         ObjectPermissionBackend,
#     ]
#
#
# class ResponsibleClassifierField(AttributeClassifierBaseField):
#     queryset = ResponsibleClassifier.objects


class ResponsibleGroupDefault(object):
    requires_context = True

    def set_context(self, serializer_field):
        request = serializer_field.context['request']
        from poms.users.models import MasterUser
        from poms_app import settings
        self._master_user = MasterUser.objects.get(base_api_url=settings.BASE_API_URL)

    def __call__(self, serializer_field):
        self.set_context(serializer_field)
        from poms.users.models import EcosystemDefault
        self.ecosystem_defaults = EcosystemDefault.objects.get(master_user=self._master_user)

        return self.ecosystem_defaults.responsible_group


class ResponsibleGroupField(UserCodeOrPrimaryKeyRelatedField):
    queryset = ResponsibleGroup.objects
    filter_backends = [
        OwnerByMasterUserFilter,
    ]


class ResponsibleDefault(object):
    requires_context = True

    def set_context(self, serializer_field):
        request = serializer_field.context['request']
        from poms.users.models import MasterUser
        from poms_app import settings
        self._master_user = MasterUser.objects.get(base_api_url=settings.BASE_API_URL)

    def __call__(self, serializer_field):
        self.set_context(serializer_field)
        from poms.users.models import EcosystemDefault
        self.ecosystem_defaults = EcosystemDefault.objects.get(master_user=self._master_user)

        return self.ecosystem_defaults.responsible


class ResponsibleField(UserCodeOrPrimaryKeyRelatedField):
    queryset = Responsible.objects
    filter_backends = [
        OwnerByMasterUserFilter,
    ]
