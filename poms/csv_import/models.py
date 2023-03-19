from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy

from poms.common.models import DataTimeStampedModel, NamedModel, EXPRESSION_FIELD_LENGTH
from poms.users.models import MasterUser

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

COLUMN_MATCHER_CHOICES = [
    ['index', 'Index'],
    ['name', 'Name']
]


class CsvImportScheme(NamedModel, DataTimeStampedModel):
    content_type = models.ForeignKey(ContentType, verbose_name=gettext_lazy('content type'), on_delete=models.CASCADE)
    master_user = models.ForeignKey('users.MasterUser', verbose_name=gettext_lazy('master user'),
                                    on_delete=models.CASCADE)
    user_code = models.CharField(max_length=255, null=True, blank=True, verbose_name=gettext_lazy('user code'))

    filter_expr = models.CharField(max_length=1000, default='', blank=True, null=True,
                                   verbose_name=gettext_lazy('filter expression'))

    mode = models.CharField(max_length=255, choices=MODE_CHOICES, default='skip')
    delimiter = models.CharField(max_length=255, choices=DELIMITER_CHOICES, default=',')
    error_handler = models.CharField(max_length=255, choices=ERROR_HANDLER_CHOICES, default='break')
    missing_data_handler = models.CharField(max_length=255, choices=MISSING_DATA_CHOICES, default='throw_error')
    classifier_handler = models.CharField(max_length=255, choices=CLASSIFIER_HANDLER, default='skip')

    instrument_reference_column = models.CharField(max_length=255, default='', blank=True, null=True)

    spreadsheet_start_cell = models.CharField(max_length=255, default='A1')
    spreadsheet_active_tab_name = models.CharField(max_length=255, default='', blank=True, null=True)
    column_matcher = models.CharField(max_length=255, choices=COLUMN_MATCHER_CHOICES, default='index')



    data_preprocess_expression = models.CharField(null=True, max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='',
                                                  verbose_name=gettext_lazy('data preprocess expression'))

    item_post_process_script = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, default='',
                                                verbose_name=gettext_lazy('item post process script'))

    class Meta:
        unique_together = (
            ('content_type', 'user_code', 'master_user')
        )

    def __str__(self):
        return self.user_code


class CsvImportSchemeCalculatedInput(models.Model):
    scheme = models.ForeignKey(CsvImportScheme, related_name='calculated_inputs',
                               verbose_name=gettext_lazy('scheme'), on_delete=models.CASCADE)
    # order = models.SmallIntegerField(default=0)
    name = models.CharField(max_length=255)
    column = models.SmallIntegerField()

    name_expr = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, default='',
                                 verbose_name=gettext_lazy('name expression'))

    class Meta:
        verbose_name = gettext_lazy('csv import scheme calculated input')
        verbose_name_plural = gettext_lazy('csv import scheme calculated inputs')
        # ordering = ['order']
        order_with_respect_to = 'scheme'

    def __str__(self):
        return self.name


class CsvField(models.Model):
    column = models.IntegerField(default=0)
    name = models.CharField(max_length=255, blank=True, default='')
    column_name = models.CharField(max_length=255, blank=True, null=True)

    name_expr = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, default='',
                                 verbose_name=gettext_lazy('name expression'))

    scheme = models.ForeignKey(CsvImportScheme, related_name='csv_fields', on_delete=models.CASCADE)

    class Meta:
        verbose_name = gettext_lazy('csv field')
        verbose_name_plural = gettext_lazy('csv fields')

        index_together = [
            ['scheme'],
        ]


class EntityField(models.Model):
    name = models.CharField(max_length=255)
    expression = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, blank=True, default='')

    use_default = models.BooleanField(default=True, verbose_name=gettext_lazy('use default'))

    order = models.IntegerField(default=0, verbose_name=gettext_lazy('order'))

    system_property_key = models.CharField(max_length=255, null=True)
    attribute_user_code = models.CharField(max_length=255, null=True)

    scheme = models.ForeignKey(CsvImportScheme, related_name='entity_fields', on_delete=models.CASCADE)

    class Meta:
        verbose_name = gettext_lazy('entity field')
        verbose_name_plural = gettext_lazy('entity fields')

        index_together = [
            ['scheme', 'order'],
        ]
        ordering = ['order']


class CsvDataImport(models.Model):
    master_user = models.ForeignKey(MasterUser, blank=True, null=True, on_delete=models.CASCADE)
    scheme = models.ForeignKey(CsvImportScheme, on_delete=models.CASCADE)
    task_id = models.CharField(max_length=255, blank=True, null=True)
    task_status = models.CharField(max_length=255, blank=True, null=True)

    mode = models.CharField(max_length=255, choices=MODE_CHOICES, default='skip')
    delimiter = models.CharField(max_length=255, choices=DELIMITER_CHOICES, default=',')
    created_at = models.DateTimeField(auto_now_add=True)
    error_handler = models.CharField(max_length=255, choices=ERROR_HANDLER_CHOICES, default='break')
    missing_data_handler = models.CharField(max_length=255, choices=MISSING_DATA_CHOICES, default='throw_error')
    classifier_handler = models.CharField(max_length=255, choices=CLASSIFIER_HANDLER, default='skip')

    file = ''




class ProcessType(object):
    CSV = 'CSV'
    JSON = 'JSON'
    EXCEL = 'EXCEL'


class SimpleImportResult(object):

    def __init__(self,
                 task=None,
                 scheme=None,
                 file_name=None,
                 file_path=None,

                 total_rows=None,
                 processed_rows=0,

                 errors=None,
                 items=None,

                 error_message=None,
                 reports=None):
        self.task = task
        self.scheme = scheme
        self.file_name = file_name

        self.total_rows = total_rows
        self.processed_rows = processed_rows

        self.items = items

        self.error_message = error_message
        self.reports = reports


class SimpleImportConversionItem(object):

    def __init__(self,
                 file_inputs=None,
                 raw_inputs=None,
                 conversion_inputs=None,
                 row_number=None):
        self.file_inputs = file_inputs
        self.raw_inputs = raw_inputs
        self.conversion_inputs = conversion_inputs
        self.row_number = row_number

class SimpleImportProcessPreprocessItem(object):

    def __init__(self,
                 file_inputs=None,
                 raw_inputs=None,
                 conversion_inputs=None,
                 inputs=None,
                 row_number=None):
        self.file_inputs = file_inputs
        self.raw_inputs = raw_inputs
        self.conversion_inputs = conversion_inputs
        self.inputs = inputs
        self.row_number = row_number


class SimpleImportImportedItem(object):

    def __init__(self,
                 id=None,
                 user_code=None):
        self.id = id
        self.user_code = user_code

class SimpleImportProcessItem(object):

    def __init__(self,
                 status='init',
                 error_message='',
                 message='',
                 processed_rule_scenarios=None,
                 imported_items=None,
                 file_inputs=None,
                 raw_inputs=None,
                 inputs=None,
                 transaction_inputs=None,
                 row_number=None):
        self.file_inputs = file_inputs
        self.raw_inputs = raw_inputs
        self.inputs = inputs
        self.transaction_inputs = transaction_inputs
        self.row_number = row_number

        self.status = status
        self.error_message = error_message
        self.message = message
        self.processed_rule_scenarios = processed_rule_scenarios
        self.imported_items = imported_items

