from rest_framework.filters import BaseFilterBackend

from poms.accounts.models import Account, AccountType
from poms.counterparties.models import Counterparty, Responsible
from poms.instruments.models import InstrumentType, Instrument
from poms.obj_attrs.models import GenericAttributeType
from poms.portfolios.models import Portfolio
from poms.strategies.models import Strategy1, Strategy2, Strategy3


class TaskFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        # master_user = get_master_user(request)
        master_user = request.user.master_user
        member = request.user.member
        if member.is_superuser:
            return queryset.filter(master_user=master_user)
        else:
            return queryset.filter(master_user=master_user, member=member)


class AbstractMappingObjectPermissionFilter(BaseFilterBackend):
    content_object_model = None
    master_user_path = 'master_user'

    def filter_queryset(self, request, queryset, view):
        return queryset


class InstrumentTypeMappingObjectPermissionFilter(AbstractMappingObjectPermissionFilter):
    content_object_model = InstrumentType


class AccountTypeMappingObjectPermissionFilter(AbstractMappingObjectPermissionFilter):
    content_object_model = AccountType


class InstrumentAttributeValueMappingObjectPermissionFilter(AbstractMappingObjectPermissionFilter):
    content_object_model = GenericAttributeType


class AccountMappingObjectPermissionFilter(AbstractMappingObjectPermissionFilter):
    content_object_model = Account


class InstrumentMappingObjectPermissionFilter(AbstractMappingObjectPermissionFilter):
    content_object_model = Instrument


class CounterpartyMappingObjectPermissionFilter(AbstractMappingObjectPermissionFilter):
    content_object_model = Counterparty


class ResponsibleMappingObjectPermissionFilter(AbstractMappingObjectPermissionFilter):
    content_object_model = Responsible


class PortfolioMappingObjectPermissionFilter(AbstractMappingObjectPermissionFilter):
    content_object_model = Portfolio


class Strategy1MappingObjectPermissionFilter(AbstractMappingObjectPermissionFilter):
    content_object_model = Strategy1


class Strategy2MappingObjectPermissionFilter(AbstractMappingObjectPermissionFilter):
    content_object_model = Strategy2


class Strategy3MappingObjectPermissionFilter(AbstractMappingObjectPermissionFilter):
    content_object_model = Strategy3
