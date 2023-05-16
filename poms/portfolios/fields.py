from __future__ import unicode_literals

from poms.common.fields import PrimaryKeyRelatedFilteredField, UserCodeOrPrimaryKeyRelatedField
from poms.portfolios.models import Portfolio
from poms.users.filters import OwnerByMasterUserFilter


# class PortfolioClassifierField(AttributeClassifierBaseField):
#     queryset = PortfolioClassifier.objects
#
#
# class PortfolioAttributeTypeField(PrimaryKeyRelatedFilteredField):
#     queryset = PortfolioAttributeType.objects
#     filter_backends = [
#         OwnerByMasterUserFilter,
#         ObjectPermissionBackend,
#     ]


class PortfolioDefault(object):
    requires_context = True

    def set_context(self, serializer_field):
        request = serializer_field.context['request']
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
