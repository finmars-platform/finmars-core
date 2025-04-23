from poms.common.fields import UserCodeOrPrimaryKeyRelatedField
from poms.currencies.models import Currency


class CurrencyDefault:
    requires_context = True

    def set_context(self, serializer_field):
        request = serializer_field.context["request"]
        self._master_user = (
            request.user.master_user if request.user.is_authenticated else None
        )

    def __call__(self, serializer_field):
        self.set_context(serializer_field)
        return self._master_user.currency if self._master_user else None


class SystemCurrencyDefault:
    requires_context = True

    def set_context(self, serializer_field):
        request = serializer_field.context["request"]
        self._master_user = (
            request.user.master_user if request.user.is_authenticated else None
        )

    def __call__(self, serializer_field):
        from poms.users.models import EcosystemDefault

        self.set_context(serializer_field)

        master_user_pk = self._master_user.pk if self._master_user else None
        if not master_user_pk:
            return None

        ecosystem_default = EcosystemDefault.cache.get_cache(
            master_user_pk=master_user_pk
        )
        return ecosystem_default.currency


class CurrencyField(UserCodeOrPrimaryKeyRelatedField):
    queryset = Currency.objects
