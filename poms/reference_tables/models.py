from __future__ import unicode_literals

from django.db import models
from django.utils.translation import gettext_lazy

from poms.common.models import NamedModel, DataTimeStampedModel
from poms.configuration.models import ConfigurationModel


class ReferenceTable(NamedModel, DataTimeStampedModel, ConfigurationModel):
    '''

    When users configures Transaction Type he could pick ReferenceTable as value_type for input
    so instead of typing some words user just could pick them from dropdown list. How convenient!

    ==== Important ====
    Part of Finmars Configuration
    Part of Finmars Marketplace
    '''
    master_user = models.ForeignKey('users.MasterUser', related_name='reference_tables',
                                    verbose_name=gettext_lazy('master user'), on_delete=models.CASCADE)
    name = models.CharField(max_length=255, verbose_name=gettext_lazy('name'))

    class Meta:
        unique_together = (
            ('name', 'master_user')
        )
        verbose_name = gettext_lazy('Reference Table')
        verbose_name_plural = gettext_lazy('Reference Tables')


class ReferenceTableRow(models.Model):
    '''
        Its a row for ReferenceTable
        Users see a list of it when dropdown in Input editing in TransactionType editor appears
    '''
    reference_table = models.ForeignKey(ReferenceTable, on_delete=models.CASCADE, null=True, blank=True,
                                        related_name='rows',
                                        verbose_name=gettext_lazy('reference table'))

    key = models.CharField(max_length=255, verbose_name=gettext_lazy('key'))

    value = models.CharField(max_length=255, verbose_name=gettext_lazy('value'))

    order = models.IntegerField(default=0, verbose_name=gettext_lazy('order'))

    class Meta:
        unique_together = (
            ('reference_table', 'key')
        )
        verbose_name = gettext_lazy('Reference Table Row')
        verbose_name_plural = gettext_lazy('Reference Table Rows')
