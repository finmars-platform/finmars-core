from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy

from poms.users.models import MasterUser


class CsvImportScheme(models.Model):
    name = models.CharField(max_length=255)
    content_type = models.ForeignKey(ContentType, verbose_name=ugettext_lazy('content type'))
    master_user = models.ForeignKey('users.MasterUser', verbose_name=ugettext_lazy('master user'))

    class Meta:
        unique_together = (
            ('content_type', 'name', 'master_user')
        )

    def __str__(self):
        return self.name


class CsvField(models.Model):
    column = models.IntegerField(default=0)
    name = models.CharField(max_length=255, blank=True, default='')

    scheme = models.ForeignKey(CsvImportScheme, related_name='csv_fields', on_delete=models.CASCADE)


class EntityField(models.Model):
    name = models.CharField(max_length=255)
    expression = models.CharField(max_length=255, blank=True, default='')

    system_property_key = models.CharField(max_length=255, null=True)
    dynamic_attribute_id = models.IntegerField(null=True)

    scheme = models.ForeignKey(CsvImportScheme, related_name='entity_fields', on_delete=models.CASCADE)


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


class CsvDataImport(models.Model):
    master_user = models.ForeignKey(MasterUser, blank=True, null=True)
    scheme = models.ForeignKey(CsvImportScheme)
    status = models.CharField(max_length=255)
    mode = models.CharField(max_length=255, choices=MODE_CHOICES, default='skip')
    delimiter = models.CharField(max_length=255, choices=DELIMITER_CHOICES, default=',')
    created_at = models.DateTimeField(auto_now_add=True)
    error_handler = models.CharField(max_length=255, choices=ERROR_HANDLER_CHOICES, default='break')
    filename = models.CharField(max_length=255)
    filesize = models.CharField(max_length=255)

    file = ''
