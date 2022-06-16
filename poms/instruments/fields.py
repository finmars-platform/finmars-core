from __future__ import unicode_literals

from poms.common.fields import PrimaryKeyRelatedFilteredField
from poms.instruments.models import Instrument, InstrumentType, PricingPolicy, AccrualCalculationModel, Periodicity, \
    EventSchedule
from poms.obj_perms.fields import PrimaryKeyRelatedFilteredWithObjectPermissionField
from poms.transactions.models import NotificationClass, EventClass, TransactionTypeInputSettings, TransactionTypeInput
from poms.users.filters import OwnerByMasterUserFilter, LinkedWithPortfolioFilter


# class InstrumentClassifierField(AttributeClassifierBaseField):
#     queryset = InstrumentClassifier.objects
#
#
# class InstrumentAttributeTypeField(PrimaryKeyRelatedFilteredField):
#     queryset = InstrumentAttributeType.objects
#     filter_backends = [
#         OwnerByMasterUserFilter,
#         ObjectPermissionBackend,
#     ]


class InstrumentTypeDefault(object):
    def set_context(self, serializer_field):
        request = serializer_field.context['request']
        self._master_user = request.user.master_user

    def __call__(self):
        return self._master_user.instrument_type


class InstrumentTypeField(PrimaryKeyRelatedFilteredWithObjectPermissionField):
    queryset = InstrumentType.objects
    filter_backends = [
        OwnerByMasterUserFilter,
    ]


class InstrumentDefault(object):
    def set_context(self, serializer_field):
        request = serializer_field.context['request']
        self._master_user = request.user.master_user

    def __call__(self):
        return self._master_user.instrument


class InstrumentField(PrimaryKeyRelatedFilteredWithObjectPermissionField):
    queryset = Instrument.objects
    filter_backends = [
        OwnerByMasterUserFilter,
    ]

class RegisterField(PrimaryKeyRelatedFilteredWithObjectPermissionField):
    queryset = Instrument.objects
    filter_backends = [
        OwnerByMasterUserFilter,
        LinkedWithPortfolioFilter
    ]


class PricingPolicyField(PrimaryKeyRelatedFilteredField):
    queryset = PricingPolicy.objects
    filter_backends = [
        OwnerByMasterUserFilter,
    ]


class TransactionTypeInputField(PrimaryKeyRelatedFilteredField):
    queryset = TransactionTypeInput.objects

class AccrualCalculationModelField(PrimaryKeyRelatedFilteredField):
    queryset = AccrualCalculationModel.objects


class PeriodicityField(PrimaryKeyRelatedFilteredField):
    queryset = Periodicity.objects

class TransactionTypeInputSettingsField(PrimaryKeyRelatedFilteredField):
    queryset = TransactionTypeInputSettings.objects

class NotificationClassField(PrimaryKeyRelatedFilteredField):
    queryset = NotificationClass.objects

class EventClassField(PrimaryKeyRelatedFilteredField):
    queryset = EventClass.objects


class EventScheduleField(PrimaryKeyRelatedFilteredField):
    queryset = EventSchedule.objects