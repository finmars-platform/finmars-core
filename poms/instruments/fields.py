from poms.common.fields import (
    PrimaryKeyRelatedFilteredField,
    UserCodeOrPrimaryKeyRelatedField,
)
from poms.instruments.models import (
    AccrualCalculationModel,
    CostMethod,
    Country,
    DailyPricingModel,
    EventSchedule,
    Instrument,
    InstrumentType,
    PaymentSizeDetail,
    Periodicity,
    PricingCondition,
    PricingPolicy,
)
from poms.portfolios.models import PortfolioBundle
from poms.transactions.models import (
    EventClass,
    NotificationClass,
    TransactionTypeInput,
    TransactionTypeInputSettings,
)
from poms.users.filters import LinkedWithPortfolioFilter, OwnerByMasterUserFilter


class InstrumentTypeDefault(object):
    requires_context = True

    def set_context(self, serializer_field):
        request = serializer_field.context["request"]
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
        request = serializer_field.context["request"]
        self._master_user = request.user.master_user

    def __call__(self, serializer_field):
        self.set_context(serializer_field)
        return self._master_user.instrument


class InstrumentField(UserCodeOrPrimaryKeyRelatedField):
    queryset = Instrument.objects


class CountryField(UserCodeOrPrimaryKeyRelatedField):
    queryset = Country.objects


class PricingConditionField(UserCodeOrPrimaryKeyRelatedField):
    queryset = PricingCondition.objects


class PaymentSizeDetailField(UserCodeOrPrimaryKeyRelatedField):
    queryset = PaymentSizeDetail.objects


class DailyPricingModelField(UserCodeOrPrimaryKeyRelatedField):
    queryset = DailyPricingModel.objects


class RegisterField(UserCodeOrPrimaryKeyRelatedField):
    queryset = Instrument.objects
    filter_backends = [OwnerByMasterUserFilter, LinkedWithPortfolioFilter]


class BundleField(UserCodeOrPrimaryKeyRelatedField):
    queryset = PortfolioBundle.objects


class PricingPolicyField(UserCodeOrPrimaryKeyRelatedField):
    queryset = PricingPolicy.objects


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
