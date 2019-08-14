from __future__ import unicode_literals

from poms.common.fields import SlugRelatedFilteredField, PrimaryKeyRelatedFilteredField

from poms.reference_tables.models import ReferenceTableRow


class ReferenceTableRowField(PrimaryKeyRelatedFilteredField):
    queryset = ReferenceTableRow.objects
    filter_backends = (
    )
