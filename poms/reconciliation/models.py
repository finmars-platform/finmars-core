from django.db import models


from django.utils.translation import ugettext_lazy

from poms.common.models import EXPRESSION_FIELD_LENGTH
from poms.transactions.models import ComplexTransaction, TransactionType
from poms.users.models import MasterUser


class TransactionTypeReconField(models.Model):

    transaction_type = models.ForeignKey(TransactionType, related_name='recon_fields',
                                         verbose_name=ugettext_lazy('transaction type'), on_delete=models.CASCADE)

    reference_name = models.CharField(max_length=255, verbose_name=ugettext_lazy('reference name '))
    description = models.TextField(null=True, blank=True, verbose_name=ugettext_lazy('description'))

    value_string = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, verbose_name=ugettext_lazy('value string'),  blank=True, default='',)
    value_float = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, verbose_name=ugettext_lazy('value float'),  blank=True, default='',)
    value_date = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, verbose_name=ugettext_lazy('value date'),  blank=True, default='',)


class ReconciliationComplexTransactionField(models.Model):

    MATCHED = 1
    UNMATCHED = 2
    AUTO_MATCHED = 3
    IGNORE = 4

    STATUS_CHOICES = (
        (MATCHED, ugettext_lazy('Matched')),
        (UNMATCHED, ugettext_lazy('Unmatched')),
        (AUTO_MATCHED, ugettext_lazy('Auto Matched')),
        (IGNORE, ugettext_lazy('Ignore')),
    )

    master_user = models.ForeignKey(MasterUser, verbose_name=ugettext_lazy('master user'),
                                    on_delete=models.CASCADE)

    complex_transaction = models.ForeignKey(ComplexTransaction, related_name='recon_fields', on_delete=models.CASCADE, verbose_name=ugettext_lazy('complex transaction'))

    reference_name = models.CharField(max_length=255, verbose_name=ugettext_lazy('reference name '))

    description = models.TextField(null=True, blank=True, verbose_name=ugettext_lazy('description'))

    value_string = models.TextField(null=True, blank=True, verbose_name=ugettext_lazy('value string'))
    value_float = models.IntegerField(default=0, verbose_name=ugettext_lazy('value float'))
    value_date = models.DateField(blank=True, db_index=True, null=True, verbose_name=ugettext_lazy("value date"))

    status = models.PositiveSmallIntegerField(default=UNMATCHED, choices=STATUS_CHOICES, db_index=True,
                                              verbose_name=ugettext_lazy('status'))

    match_date = models.DateField(blank=True, db_index=True, null=True, verbose_name=ugettext_lazy("value date"))

    notes = models.TextField(null=True, blank=True, verbose_name=ugettext_lazy('notes'))

    class Meta:
        verbose_name = ugettext_lazy('reconciliation complex transaction field')
        verbose_name_plural = ugettext_lazy('reconciliation complex transaction fields')


class ReconciliationBankFileField(models.Model):

    MATCHED = 1
    CONFLICT = 2
    RESOLVED = 3
    IGNORE = 4
    AUTO_MATCHED = 5
    STATUS_CHOICES = (
        (MATCHED, ugettext_lazy('Matched')),
        (CONFLICT, ugettext_lazy('Conflict')),
        (RESOLVED, ugettext_lazy('Resolved')),
        (IGNORE, ugettext_lazy('Ignore')),
        (AUTO_MATCHED, ugettext_lazy('Auto Matched')),
    )

    master_user = models.ForeignKey(MasterUser, verbose_name=ugettext_lazy('master user'),
                                    on_delete=models.CASCADE)

    source_id = models.CharField(max_length=30, null=True, blank=True, verbose_name=ugettext_lazy('source id'))

    reference_name = models.CharField(max_length=255, verbose_name=ugettext_lazy('reference name '))

    description = models.TextField(null=True, blank=True, verbose_name=ugettext_lazy('description'))

    value_string = models.TextField(null=True, blank=True, verbose_name=ugettext_lazy('value string'))
    value_float = models.IntegerField(default=0, verbose_name=ugettext_lazy('value float'))
    value_date = models.DateField(blank=True, db_index=True, null=True, verbose_name=ugettext_lazy("value date"))

    is_canceled = models.BooleanField(default=False, db_index=True, verbose_name=ugettext_lazy('is canceled'))

    status = models.PositiveSmallIntegerField(default=CONFLICT, choices=STATUS_CHOICES, db_index=True,
                                              verbose_name=ugettext_lazy('status'))

    file_name = models.TextField(null=True, blank=True, verbose_name=ugettext_lazy('file name'))
    import_scheme_name = models.TextField(null=True, blank=True, verbose_name=ugettext_lazy('import scheme name'))

    reference_date = models.DateField(blank=True, db_index=True, null=True, verbose_name=ugettext_lazy("value date"))

    notes = models.TextField(null=True, blank=True, verbose_name=ugettext_lazy('notes'))

    linked_complex_transaction_field = models.ForeignKey(ReconciliationComplexTransactionField, null=True, blank=True, on_delete=models.SET_NULL,
                                             related_name='bank_file_fields', verbose_name=ugettext_lazy('linked complex transaction field'))

    class Meta:
        verbose_name = ugettext_lazy('reconciliation bank file field')
        verbose_name_plural = ugettext_lazy('reconciliation bank file fields')

        unique_together = [
            ['master_user', 'source_id', 'reference_name', 'import_scheme_name'],
        ]


class ReconciliationNewBankFileField(models.Model):

    master_user = models.ForeignKey(MasterUser,  verbose_name=ugettext_lazy('master user'),
                                    on_delete=models.CASCADE)

    source_id = models.CharField(max_length=30, null=True, blank=True, verbose_name=ugettext_lazy('source id'))

    reference_name = models.CharField(max_length=255, verbose_name=ugettext_lazy('reference name '))

    description = models.TextField(null=True, blank=True, verbose_name=ugettext_lazy('description'))

    value_string = models.TextField(null=True, blank=True, verbose_name=ugettext_lazy('value string'))
    value_float = models.FloatField(blank=True, null=True, verbose_name=ugettext_lazy('value float'))
    value_date = models.DateField(blank=True, db_index=True, null=True, verbose_name=ugettext_lazy("value date"))

    is_canceled = models.BooleanField(default=False, db_index=True, verbose_name=ugettext_lazy('is canceled'))

    file_name = models.TextField(null=True, blank=True, verbose_name=ugettext_lazy('file name'))
    import_scheme_name = models.TextField(null=True, blank=True, verbose_name=ugettext_lazy('import scheme name'))

    reference_date = models.DateField(blank=True, db_index=True, null=True, verbose_name=ugettext_lazy("value date"))

    class Meta:
        verbose_name = ugettext_lazy('reconciliation new bank file field')
        verbose_name_plural = ugettext_lazy('reconciliation new bank file fields')
