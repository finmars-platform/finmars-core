from __future__ import unicode_literals

from django.db import models
from django.utils.translation import gettext_lazy


class ReferenceTable(models.Model):
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
