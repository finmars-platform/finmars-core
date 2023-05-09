from __future__ import unicode_literals

from poms.common.fields import PrimaryKeyRelatedFilteredField, UserCodeOrPrimaryKeyRelatedField
from poms.instruments.models import Instrument, InstrumentType, PricingPolicy, AccrualCalculationModel, Periodicity, \
    EventSchedule, CostMethod, Country, PricingCondition, PaymentSizeDetail, DailyPricingModel
from poms.portfolios.models import PortfolioBundle
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
    requires_context = True

    def set_context(self, serializer_field):
        request = serializer_field.context['request']
        self._master_user = request.user.master_user

    def __call__(self, serializer_field):
        self.set_context(serializer_field)
        return self._master_user.instrument_type


class InstrumentTypeField(UserCodeOrPrimaryKeyRelatedField):
    queryset = InstrumentType.objects
    filter_backends = [
        OwnerByMasterUserFilter,
    ]


class InstrumentDefault(object):
    requires_context = True

    def set_context(self, serializer_field):
        request = serializer_field.context['request']
        self._master_user = request.user.master_user

    def __call__(self, serializer_field):
        self.set_context(serializer_field)
        return self._master_user.instrument


class InstrumentField(UserCodeOrPrimaryKeyRelatedField):
    queryset = Instrument.objects
    filter_backends = [
        OwnerByMasterUserFilter,
    ]


class CountryField(UserCodeOrPrimaryKeyRelatedField):
    queryset = Country.objects
    filter_backends = [
    ]


class PricingConditionField(UserCodeOrPrimaryKeyRelatedField):
    queryset = PricingCondition.objects
    filter_backends = [
    ]


class PaymentSizeDetailField(UserCodeOrPrimaryKeyRelatedField):
    queryset = PaymentSizeDetail.objects
    filter_backends = [
    ]


class DailyPricingModelField(UserCodeOrPrimaryKeyRelatedField):
    queryset = DailyPricingModel.objects
    filter_backends = [
    ]


class RegisterField(PrimaryKeyRelatedFilteredField):
    queryset = Instrument.objects
    filter_backends = [
        OwnerByMasterUserFilter,
        LinkedWithPortfolioFilter
    ]


class BundleField(PrimaryKeyRelatedFilteredField):
    queryset = PortfolioBundle.objects
    filter_backends = [
        OwnerByMasterUserFilter
    ]


class PricingPolicyField(UserCodeOrPrimaryKeyRelatedField):
    queryset = PricingPolicy.objects
    filter_backends = [
        OwnerByMasterUserFilter,
    ]


class CostMethodField(PrimaryKeyRelatedFilteredField):
    queryset = CostMethod.objects


class TransactionTypeInputField(PrimaryKeyRelatedFilteredField):
    queryset = TransactionTypeInput.objects


class AccrualCalculationModelField(UserCodeOrPrimaryKeyRelatedField):
    queryset = AccrualCalculationModel.objects


class PeriodicityField(UserCodeOrPrimaryKeyRelatedField):
    queryset = Periodicity.objects


class TransactionTypeInputSettingsField(PrimaryKeyRelatedFilteredField):
    queryset = TransactionTypeInputSettings.objects


class NotificationClassField(PrimaryKeyRelatedFilteredField):
    queryset = NotificationClass.objects


class EventClassField(PrimaryKeyRelatedFilteredField):
    queryset = EventClass.objects


class EventScheduleField(PrimaryKeyRelatedFilteredField):
    queryset = EventSchedule.objects
