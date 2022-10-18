from __future__ import unicode_literals

from poms.counterparties.models import Counterparty, Responsible, CounterpartyGroup, ResponsibleGroup
from poms.obj_perms.fields import PrimaryKeyRelatedFilteredWithObjectPermissionField
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
        self._master_user = request.user.master_user

    def __call__(self, serializer_field):
        self.set_context(serializer_field)
        return self._master_user.counterparty_group


class CounterpartyGroupField(PrimaryKeyRelatedFilteredWithObjectPermissionField):
    queryset = CounterpartyGroup.objects
    filter_backends = [
        OwnerByMasterUserFilter,
    ]


class CounterpartyDefault(object):
    requires_context = True
    def set_context(self, serializer_field):
        request = serializer_field.context['request']
        self._master_user = request.user.master_user

    def __call__(self, serializer_field):
        self.set_context(serializer_field)
        return self._master_user.counterparty


class CounterpartyField(PrimaryKeyRelatedFilteredWithObjectPermissionField):
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
        self._master_user = request.user.master_user

    def __call__(self, serializer_field):
        self.set_context(serializer_field)
        return self._master_user.responsible_group


class ResponsibleGroupField(PrimaryKeyRelatedFilteredWithObjectPermissionField):
    queryset = ResponsibleGroup.objects
    filter_backends = [
        OwnerByMasterUserFilter,
    ]


class ResponsibleDefault(object):
    requires_context = True
    def set_context(self, serializer_field):
        request = serializer_field.context['request']
        self._master_user = request.user.master_user

    def __call__(self, serializer_field):
        self.set_context(serializer_field)
        return self._master_user.responsible


class ResponsibleField(PrimaryKeyRelatedFilteredWithObjectPermissionField):
    queryset = Responsible.objects
    filter_backends = [
        OwnerByMasterUserFilter,
    ]
