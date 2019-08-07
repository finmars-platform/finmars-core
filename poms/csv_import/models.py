from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy

from poms.users.models import MasterUser


class CsvImportScheme(models.Model):
    scheme_name = models.CharField(max_length=255)
    content_type = models.ForeignKey(ContentType, verbose_name=ugettext_lazy('content type'))
    master_user = models.ForeignKey('users.MasterUser', verbose_name=ugettext_lazy('master user'))

    filter_expr = models.CharField(max_length=1000, default='', blank=True, null=True, verbose_name=ugettext_lazy('filter expression'))

    class Meta:
        unique_together = (
            ('content_type', 'scheme_name', 'master_user', 'filter_expr')
        )

    def __str__(self):
        return self.scheme_name


class CsvField(models.Model):
    column = models.IntegerField(default=0)
    name = models.CharField(max_length=255, blank=True, default='')

    name_expr = models.CharField(max_length=1000, default='', verbose_name=ugettext_lazy('name expression'))

    scheme = models.ForeignKey(CsvImportScheme, related_name='csv_fields', on_delete=models.CASCADE)


class EntityField(models.Model):
    name = models.CharField(max_length=255)
    expression = models.CharField(max_length=255, blank=True, default='')

    order = models.IntegerField(default=0, verbose_name=ugettext_lazy('order'))

    system_property_key = models.CharField(max_length=255, null=True)
    dynamic_attribute_id = models.IntegerField(null=True)

    scheme = models.ForeignKey(CsvImportScheme, related_name='entity_fields', on_delete=models.CASCADE)

    class Meta:
        verbose_name = ugettext_lazy('entity field')
        verbose_name_plural = ugettext_lazy('entity fields')

        index_together = [
            ['scheme', 'order'],
        ]
        ordering = ['order']

ERROR_HANDLER_CHOICES = [
    ['break', 'Break'],
    ['continue', 'Continue'],
]

MODE_CHOICES = [
    ['skip', 'Skip if exists'],
    ['overwrite', 'Overwrite'],
]

DELIMITER_CHOICES = [
    [',', 'Comma'],
    [';', 'Semicolon'],
    ['\t', 'Tab'],
]

MISSING_DATA_CHOICES = [
    ['throw_error', 'Treat as Error'],
    ['set_defaults', 'Replace with Default Value'],
]

CLASSIFIER_HANDLER = [
    ['skip', 'Skip'],
    ['append', 'Append'],
]


class CsvDataImport(models.Model):
    master_user = models.ForeignKey(MasterUser, blank=True, null=True)
    scheme = models.ForeignKey(CsvImportScheme)
    task_id = models.CharField(max_length=255, blank=True, null=True)
    task_status = models.CharField(max_length=255, blank=True, null=True)

    mode = models.CharField(max_length=255, choices=MODE_CHOICES, default='skip')
    delimiter = models.CharField(max_length=255, choices=DELIMITER_CHOICES, default=',')
    created_at = models.DateTimeField(auto_now_add=True)
    error_handler = models.CharField(max_length=255, choices=ERROR_HANDLER_CHOICES, default='break')
    missing_data_handler = models.CharField(max_length=255, choices=MISSING_DATA_CHOICES, default='throw_error')
    classifier_handler = models.CharField(max_length=255, choices=CLASSIFIER_HANDLER, default='skip')

    file = ''
