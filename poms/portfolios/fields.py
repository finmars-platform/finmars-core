from enum import Enum

from poms.common.fields import UserCodeOrPrimaryKeyRelatedField
from poms.portfolios.models import Portfolio, PortfolioReconcileGroup


class PortfolioDefault:
    requires_context = True

    def set_context(self, serializer_field):
        request = serializer_field.context["request"]
        self._master_user = (
            request.user.master_user if request.user.is_authenticated else None
        )

    def __call__(self, serializer_field):
        self.set_context(serializer_field)
        return (
            self._master_user.portfolio
            if hasattr(self._master_user, "portfolio")
            else None
        )


class PortfolioField(UserCodeOrPrimaryKeyRelatedField):
    queryset = Portfolio.objects


class PortfolioReconcileGroupField(UserCodeOrPrimaryKeyRelatedField):
    queryset = PortfolioReconcileGroup.objects


class ReconcileStatus(Enum):
    NO_GROUP = "no_group"
    NOT_RUN_YET = "not_run_yet"
    ERROR = "error"
    OK = "ok"
