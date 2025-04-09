from poms.accounts.models import Account, AccountType
from poms.common.fields import UserCodeOrPrimaryKeyRelatedField
from poms.users.filters import OwnerByMasterUserFilter


class AccountTypeField(UserCodeOrPrimaryKeyRelatedField):
    queryset = AccountType.objects
    filter_backends = [
        OwnerByMasterUserFilter,
    ]


class AccountDefault:
    requires_context = True

    def set_context(self, serializer_field):
        from poms.users.models import MasterUser

        request = serializer_field.context["request"]
        self._master_user = MasterUser.objects.filter(space_code=request.space_code).first()

    def __call__(self, serializer_field):
        self.set_context(serializer_field)
        return self._master_user.account if hasattr(self._master_user, "account") else None


class AccountField(UserCodeOrPrimaryKeyRelatedField):
    queryset = Account.objects
