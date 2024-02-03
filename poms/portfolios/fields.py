from poms.common.fields import UserCodeOrPrimaryKeyRelatedField
from poms.portfolios.models import Portfolio, PortfolioReconcileGroup


class PortfolioDefault:
    requires_context = True

    def set_context(self, serializer_field):
        request = serializer_field.context["request"]
        self._master_user = request.user.master_user

    def __call__(self, serializer_field):
        self.set_context(serializer_field)
        return self._master_user.portfolio


class PortfolioField(UserCodeOrPrimaryKeyRelatedField):
    queryset = Portfolio.objects

    # Possibly Deprecated
    # filter_backends = UserCodeOrPrimaryKeyRelatedField.filter_backends + [
    #     OwnerByMasterUserFilter,
    # ]

class PortfolioReconcileGroupField(UserCodeOrPrimaryKeyRelatedField):
    queryset = PortfolioReconcileGroup.objects