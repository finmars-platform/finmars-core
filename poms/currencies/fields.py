from poms.common.fields import UserCodeOrPrimaryKeyRelatedField
from poms.currencies.models import Currency


class CurrencyDefault:
    requires_context = True

    def set_context(self, serializer_field):
        request = serializer_field.context["request"]
        self._master_user = request.user.master_user

    def __call__(self, serializer_field):
        self.set_context(serializer_field)
        return self._master_user.currency


class SystemCurrencyDefault:
    requires_context = True

    def set_context(self, serializer_field):
        request = serializer_field.context["request"]
        self._master_user = request.user.master_user

    def __call__(self, serializer_field):
        from poms.users.models import EcosystemDefault

        self.set_context(serializer_field)

        ecosystem_default = EcosystemDefault.objects.get(master_user=self._master_user)

        return ecosystem_default.currency


class CurrencyField(UserCodeOrPrimaryKeyRelatedField):
    queryset = Currency.objects
