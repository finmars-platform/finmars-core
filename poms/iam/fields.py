from rest_framework.relations import PrimaryKeyRelatedField, SlugRelatedField, RelatedField

from poms.iam.filters import ObjectPermissionBackend
from poms.iam.utils import get_allowed_queryset
from poms.users.utils import get_member_from_context

import logging

_l = logging.getLogger('poms.iam')

class IamProtectedRelatedField(RelatedField):

    def get_queryset(self):
        queryset = super().get_queryset()

        member = get_member_from_context(self.context)

        if member.is_admin:
            return queryset

        _l.info('IamProtectedRelatedField %s' % member)

        queryset = get_allowed_queryset(member, queryset)

        return queryset
