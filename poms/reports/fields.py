from poms.common.fields import PrimaryKeyRelatedFilteredField
from poms.currencies.fields import CurrencyField
from poms.instruments.fields import PricingPolicyField
from poms.reports.models import BalanceReportCustomField, PLReportCustomField, TransactionReportCustomField
from poms.users.filters import OwnerByMasterUserFilter


class BalanceReportCustomFieldField(PrimaryKeyRelatedFilteredField):
    queryset = BalanceReportCustomField.objects
    filter_backends = [
        OwnerByMasterUserFilter,
    ]


class PLReportCustomFieldField(PrimaryKeyRelatedFilteredField):
    queryset = PLReportCustomField.objects
    filter_backends = [
        OwnerByMasterUserFilter,
    ]


class TransactionReportCustomFieldField(PrimaryKeyRelatedFilteredField):
    queryset = TransactionReportCustomField.objects
    filter_backends = [
        OwnerByMasterUserFilter,
    ]


class ReportCurrencyField(CurrencyField):

    def to_representation(self, obj):
        return getattr(obj, 'user_code')

class ReportPricingPolicyField(PricingPolicyField):

    def to_representation(self, obj):
        return getattr(obj, 'user_code')