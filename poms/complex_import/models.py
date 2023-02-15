from django.db import models
from django.utils.translation import gettext_lazy

from poms.common.models import DataTimeStampedModel, NamedModel
from poms.users.models import MasterUser


class ComplexImportScheme(NamedModel, DataTimeStampedModel):
    '''
    Probably Deprecated
    Synthetic Entity which idea was is to mix SimpleImport and TransactionImport into one process
    Deprecated since we got DataProcedures and ExpressionProcedures
    Will be more deprecated when it would be moved to Workflow
    '''
    user_code = models.CharField(max_length=255, null=True, blank=True, verbose_name=gettext_lazy('user code'))
    master_user = models.ForeignKey('users.MasterUser', verbose_name=gettext_lazy('master user'),
                                    on_delete=models.CASCADE)

    class Meta:
        unique_together = (
            ('user_code', 'master_user')
        )


MISSING_DATA_CHOICES = [
    ['throw_error', 'Treat as Error'],
    ['set_defaults', 'Replace with Default Value'],
]

ERROR_HANDLER_CHOICES = [
    ['break', 'Break'],
    ['continue', 'Continue'],
]

MODE_CHOICES = [
    ['skip', 'Skip if exists'],
    ['overwrite', 'Overwrite'],
]

CLASSIFIER_HANDLER = [
    ['skip', 'Skip'],
    ['append', 'Append'],
]


class ComplexImportSchemeAction(models.Model):
    action_notes = models.TextField(default='', verbose_name=gettext_lazy('action notes'))
    order = models.IntegerField(default=0, verbose_name=gettext_lazy('order'))

    skip = models.BooleanField(default=False,
                               verbose_name=gettext_lazy('Skip Action'))

    complex_import_scheme = models.ForeignKey(ComplexImportScheme, related_name='actions', on_delete=models.CASCADE)

    class Meta:
        verbose_name = gettext_lazy('action')
        verbose_name_plural = gettext_lazy('actions')
        index_together = [
            ['complex_import_scheme', 'order'],
        ]
        ordering = ['order']

    def __str__(self):
        return 'Action #%s' % self.order


class ComplexImportSchemeActionCsvImport(ComplexImportSchemeAction):
    csv_import_scheme = models.ForeignKey('csv_import.CsvImportScheme', null=True, blank=True,
                                          on_delete=models.SET_NULL,
                                          related_name='+', verbose_name=gettext_lazy('csv import scheme'))

    mode = models.CharField(max_length=255, choices=MODE_CHOICES, default='')
    missing_data_handler = models.CharField(max_length=255, choices=MISSING_DATA_CHOICES, default='throw_error')
    classifier_handler = models.CharField(max_length=255, choices=CLASSIFIER_HANDLER, default='skip')
    error_handler = models.CharField(max_length=255, choices=ERROR_HANDLER_CHOICES, default='break')

    notes = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('notes'))


class ComplexImportSchemeActionTransactionImport(ComplexImportSchemeAction):
    complex_transaction_import_scheme = models.ForeignKey('integrations.ComplexTransactionImportScheme', null=True,
                                                          blank=True, on_delete=models.SET_NULL,
                                                          related_name='+', verbose_name=gettext_lazy(
            'complex transaction import scheme'))

    missing_data_handler = models.CharField(max_length=255, choices=MISSING_DATA_CHOICES, default='throw_error')
    error_handler = models.CharField(max_length=255, choices=ERROR_HANDLER_CHOICES, default='break')

    notes = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('notes'))


class ComplexImport(models.Model):
    master_user = models.ForeignKey(MasterUser, blank=True, null=True, on_delete=models.CASCADE)
    complex_import_scheme = models.ForeignKey(ComplexImportScheme, on_delete=models.CASCADE)
    status = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    filename = models.CharField(max_length=255)
    filesize = models.CharField(max_length=255)
    file = ''
