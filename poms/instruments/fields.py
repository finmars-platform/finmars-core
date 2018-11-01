from __future__ import unicode_literals

from poms.common.fields import PrimaryKeyRelatedFilteredField
from poms.instruments.models import Instrument, InstrumentType, PricingPolicy, AccrualCalculationModel, Periodicity
from poms.obj_perms.fields import PrimaryKeyRelatedFilteredWithObjectPermissionField
from poms.users.filters import OwnerByMasterUserFilter


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


class PricingPolicyField(PrimaryKeyRelatedFilteredField):
    queryset = PricingPolicy.objects
    filter_backends = [
        OwnerByMasterUserFilter,
    ]


class AccrualCalculationModelField(PrimaryKeyRelatedFilteredField):
    queryset = AccrualCalculationModel.objects


class PeriodicityField(PrimaryKeyRelatedFilteredField):
    queryset = Periodicity.objects
