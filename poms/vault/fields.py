from poms.common.fields import PrimaryKeyRelatedFilteredField
from poms.vault.models import VaultRecord


class VaultRecordField(PrimaryKeyRelatedFilteredField):
    queryset = VaultRecord.objects
