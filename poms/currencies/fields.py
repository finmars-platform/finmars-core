from __future__ import unicode_literals

from poms.common.fields import PrimaryKeyRelatedFilteredField
from poms.currencies.models import Currency
from poms.users.filters import OwnerByMasterUserFilter


class CurrencyDefault(object):
    requires_context = True

    def set_context(self, serializer_field):
        request = serializer_field.context['request']
        self._master_user = request.user.master_user

    def __call__(self, serializer_field):
        self.set_context(serializer_field)
        return self._master_user.currency



class CurrencyField(PrimaryKeyRelatedFilteredField):
    queryset = Currency.objects
    filter_backends = (
        OwnerByMasterUserFilter,
    )
