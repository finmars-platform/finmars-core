import logging

from rest_framework.relations import RelatedField

from poms.iam.utils import get_allowed_queryset
from poms.users.utils import get_member_from_context

_l = logging.getLogger("poms.iam")


class IamProtectedRelatedField(RelatedField):
    def get_queryset(self):
        queryset = super().get_queryset()

        member = get_member_from_context(self.context)

        if member.is_admin:
            return queryset

        _l.debug(f"IamProtectedRelatedField {member}")

        queryset = get_allowed_queryset(member, queryset)

        return queryset
