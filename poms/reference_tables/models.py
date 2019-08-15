from __future__ import unicode_literals

from django.db import models
from django.utils.translation import ugettext_lazy


class ReferenceTable(models.Model):
    master_user = models.ForeignKey('users.MasterUser', related_name='reference_tables',
                                    verbose_name=ugettext_lazy('master user'))
    name = models.CharField(max_length=255, verbose_name=ugettext_lazy('name'))

    class Meta:
        unique_together = (
            ('name', 'master_user')
        )
        verbose_name = ugettext_lazy('Reference Table')
        verbose_name_plural = ugettext_lazy('Reference Tables')


class ReferenceTableRow(models.Model):
    reference_table = models.ForeignKey(ReferenceTable, on_delete=models.CASCADE, null=True, blank=True,
                                        related_name='rows',
                                        verbose_name=ugettext_lazy('reference table'))

    key = models.CharField(max_length=255, verbose_name=ugettext_lazy('key'))

    value = models.CharField(max_length=255, verbose_name=ugettext_lazy('value'))

    class Meta:
        unique_together = (
            ('reference_table', 'key')
        )
        verbose_name = ugettext_lazy('Reference Table Row')
        verbose_name_plural = ugettext_lazy('Reference Table Rows')
