from poms.common.fields import PrimaryKeyRelatedFilteredField
from poms.currencies.fields import CurrencyField
from poms.instruments.fields import BundleField, PricingPolicyField
from poms.reports.models import (
    BalanceReportCustomField,
    PLReportCustomField,
    TransactionReportCustomField,
)
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


class ReportBundleField(BundleField):
    """Resolve a bundle in the current master user's report context."""

    def get_queryset(self):
        request = self.context.get("request")
        if request is not None:
            user = getattr(request, "user", None)
            member = getattr(user, "member", None)
            master_user = getattr(user, "master_user", None)
        else:
            member = self.context.get("member")
            master_user = self.context.get("master_user")
        if member is None or master_user is None:
            return self.queryset.none()
        return super().get_queryset().filter(master_user_id=master_user.id)

    def to_internal_value(self, value):
        if isinstance(value, bool):
            self.fail("invalid", value=value)
        if isinstance(value, str) and value.isdigit():
            try:
                bundle_id = int(value)
            except ValueError:
                self.fail("invalid", value=value)
            code_id = self.get_queryset().filter(user_code=value).values_list("id", flat=True).first()
            if code_id is not None and code_id != bundle_id:
                self.fail("invalid", value=value)
        return super().to_internal_value(value)


class ReportCurrencyField(CurrencyField):
    def to_representation(self, obj):
        return obj.user_code


class ReportPricingPolicyField(PricingPolicyField):
    def to_representation(self, obj):
        return obj.user_code
