from rest_framework.relations import PrimaryKeyRelatedField

from poms.common.fields import PrimaryKeyRelatedFilteredField
from poms.integrations.models import (
    ComplexTransactionImportScheme,
    InstrumentDownloadScheme,
    PriceDownloadScheme,
    ProviderClass,
)
from poms.users.filters import OwnerByMasterUserFilter


class ProviderClassField(PrimaryKeyRelatedField):
    queryset = ProviderClass.objects


class PriceDownloadSchemeField(PrimaryKeyRelatedFilteredField):
    queryset = PriceDownloadScheme.objects
    filter_backends = [OwnerByMasterUserFilter]


class InstrumentDownloadSchemeField(PrimaryKeyRelatedFilteredField):
    queryset = InstrumentDownloadScheme.objects
    filter_backends = [OwnerByMasterUserFilter]


class ComplexTransactionImportSchemeRestField(PrimaryKeyRelatedFilteredField):
    queryset = ComplexTransactionImportScheme.objects
    filter_backends = [OwnerByMasterUserFilter]
