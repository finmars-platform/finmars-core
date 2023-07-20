from poms.accounts.models import Account, AccountType
from poms.common.fields import (
    UserCodeOrPrimaryKeyRelatedField,
)
from poms.users.filters import OwnerByMasterUserFilter


class AccountTypeField(UserCodeOrPrimaryKeyRelatedField):
    queryset = AccountType.objects
    filter_backends = [
        OwnerByMasterUserFilter,
    ]


class AccountDefault:
    requires_context = True

    def set_context(self, serializer_field):
        request = serializer_field.context["request"]
        self._master_user = request.user.master_user

    def __call__(self, serializer_field):
        self.set_context(serializer_field)
        return self._master_user.account


class AccountField(UserCodeOrPrimaryKeyRelatedField):
    queryset = Account.objects
