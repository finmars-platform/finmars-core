from __future__ import unicode_literals

from rest_framework.relations import PrimaryKeyRelatedField

from poms.common.fields import PrimaryKeyRelatedFilteredField
from poms.integrations.models import PriceDownloadScheme, ProviderClass, InstrumentDownloadScheme, \
    ComplexTransactionImportScheme
from poms.users.filters import OwnerByMasterUserFilter


class ProviderClassField(PrimaryKeyRelatedField):
    queryset = ProviderClass.objects


#
#
# class FactorScheduleDownloadMethodField(PrimaryKeyRelatedField):
#     queryset = FactorScheduleDownloadMethod.objects
#
#
# class AccrualScheduleDownloadMethodField(PrimaryKeyRelatedField):
#     queryset = AccrualScheduleDownloadMethod.objects


class PriceDownloadSchemeField(PrimaryKeyRelatedFilteredField):
    queryset = PriceDownloadScheme.objects
    filter_backends = [OwnerByMasterUserFilter]


class InstrumentDownloadSchemeField(PrimaryKeyRelatedFilteredField):
    queryset = InstrumentDownloadScheme.objects
    filter_backends = [OwnerByMasterUserFilter]


class ComplexTransactionImportSchemeRestField(PrimaryKeyRelatedFilteredField):
    queryset = ComplexTransactionImportScheme.objects
    filter_backends = [OwnerByMasterUserFilter]
