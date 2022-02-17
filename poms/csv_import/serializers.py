import uuid

from django.contrib.contenttypes.models import ContentType
from django.apps import apps
from django.core.validators import RegexValidator
from django.core.exceptions import ObjectDoesNotExist

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from poms.common.fields import ExpressionField
from poms.common.models import EXPRESSION_FIELD_LENGTH
from poms.common.serializers import ModelWithTimeStampSerializer, ModelWithUserCodeSerializer
from poms.users.fields import MasterUserField, HiddenMemberField
from .models import CsvField, EntityField, CsvDataImport, CsvImportScheme, CsvImportSchemeCalculatedInput
from .fields import CsvImportContentTypeField, CsvImportSchemeField


from django.utils import timezone

from storages.backends.sftpstorage import SFTPStorage
SFS = SFTPStorage()


class CsvDataFileImport:
    def __init__(self, task_id=None, task_status=None, master_user=None, member=None, status=None,
                 scheme=None, file_path=None, delimiter=None, mode=None, quotechar=None, encoding=None,
                 error_handler=None, missing_data_handler=None, classifier_handler=None,
                 total_rows=None, processed_rows=None, stats=None, filename=None, imported=None, stats_file_report=None):
        self.task_id = task_id
        self.task_status = task_status

        # self.file = file

        self.filename = filename

        self.file_path = file_path
        self.master_user = master_user
        self.member = member
        self.scheme = scheme
        self.status = status
        self.mode = mode
        self.delimiter = delimiter

        self.quotechar = quotechar or '"'
        self.encoding = encoding or 'utf-8'

        self.error_handler = error_handler
        self.missing_data_handler = missing_data_handler
        self.classifier_handler = classifier_handler

        self.stats = stats

        self.imported = imported

        self.total_rows = total_rows
        self.processed_rows = processed_rows

        self.stats_file_report = stats_file_report

    def __str__(self):
        return '%s:%s' % (getattr(self.master_user, 'name', None), getattr(self.scheme, 'user_code', None))


class CsvFieldSerializer(serializers.ModelSerializer):
    name_expr = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH)

    class Meta:
        model = CsvField
        fields = ('column', 'name', 'name_expr')


class EntityFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = EntityField
        fields = ('id', 'name', 'order', 'expression', 'system_property_key', 'dynamic_attribute_id', 'use_default')
        extra_kwargs = {
            'id': {
                'read_only': True,
            }
        }


class CsvImportSchemeCalculatedInputSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=False, required=False, allow_null=True)
    name = serializers.CharField(max_length=255, allow_null=False, allow_blank=False,
                                 validators=[
                                     RegexValidator(regex='\A[a-zA-Z_][a-zA-Z0-9_]*\Z'),
                                 ])

    name_expr = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH)

    class Meta:
        model = CsvImportSchemeCalculatedInput
        fields = ['id', 'name', 'column', 'name_expr']



class CsvImportSchemeSerializer(ModelWithTimeStampSerializer):
    master_user = MasterUserField()
    csv_fields = CsvFieldSerializer(many=True)
    entity_fields = EntityFieldSerializer(many=True)
    content_type = CsvImportContentTypeField()
    calculated_inputs = CsvImportSchemeCalculatedInputSerializer(many=True, read_only=False, required=False)

    delimiter = serializers.CharField(max_length=3, required=False, initial=',', default=',')

    class Meta:

        model = CsvImportScheme
        fields = ('id', 'master_user', 'name', 'user_code', 'short_name', 'public_name', 'notes',

                  'filter_expr', 'content_type', 'csv_fields', 'entity_fields', 'calculated_inputs',

                  'spreadsheet_start_cell',

                  'mode', 'delimiter', 'error_handler', 'missing_data_handler', 'classifier_handler'

                  )

    def create_entity_fields_if_not_exist(self, scheme):

        model = apps.get_model(app_label=scheme.content_type.app_label, model_name=scheme.content_type.model)

        model_fields = model._meta.get_fields()

        content_type_str = scheme.content_type.app_label + '.' + scheme.content_type.model

        allowed_fields = {
            'currencies.currency': [
                'name', 'user_code', 'short_name', 'public_name', 'notes',
                'default_fx_rate', 'reference_for_pricing',
                'pricing_condition'
            ],
            'accounts.account': [
                'name', 'user_code', 'short_name', 'public_name', 'notes',
                'type'
            ],
            'counterparties.counterparty': [
                'name', 'user_code', 'short_name', 'public_name', 'notes',
                'group'
            ],
            'counterparties.responsible': [
                'name', 'user_code', 'short_name', 'public_name', 'notes',
                'group'
            ],
            'portfolios.portfolio': [
                'name', 'user_code', 'short_name', 'public_name', 'notes',
            ],
            'instruments.instrument': [
                'name', 'user_code', 'short_name', 'public_name', 'notes',
                'reference_for_pricing',
                'instrument_type',
                'pricing_currency', 'accrued_currency',
                'payment_size_detail', 'pricing_condition',

                'price_multiplier', 'accrued_multiplier',
                'maturity_date', 'maturity_price',
                'default_price', 'default_accrued'
                'user_text_1', 'user_text_2', 'user_text_3'
            ],
            'instruments.pricehistory': [
                'instrument', 'pricing_policy', 'date', 'principal_price', 'accrued_price'
            ],
            'currencies.currencyhistory': [
                'currency', 'pricing_policy', 'date', 'fx_rate'
            ],
            'strategies.strategy1': [
                'name', 'user_code', 'short_name', 'public_name', 'notes',
                'subgroup'
            ],
            'strategies.strategy2': [
                'name', 'user_code', 'short_name', 'public_name', 'notes',
                'subgroup'
            ],
            'strategies.strategy3': [
                'name', 'user_code', 'short_name', 'public_name', 'notes',
                'subgroup'
            ]


        }

        ids = set()

        for model_field in model_fields:

            if model_field.name in allowed_fields[content_type_str]:

                try:

                    o = EntityField.objects.get(scheme=scheme,
                                            system_property_key=model_field.name)

                    ids.add(o.id)

                except EntityField.DoesNotExist:

                    name = model_field.name

                    if hasattr(model_field, 'verbose_name'):
                        name = model_field.verbose_name

                    o = EntityField.objects.create(scheme=scheme,
                                               system_property_key=model_field.name,
                                               name=name,
                                               expression='')

                    ids.add(o.id)

        EntityField.objects.filter(scheme=scheme).exclude(id__in=ids).delete()

    def set_entity_fields_mapping(self, scheme, entity_fields):

        EntityField.objects.filter(scheme=scheme, dynamic_attribute_id__isnull=True).delete()

        self.create_entity_fields_if_not_exist(scheme)

        for entity_field in entity_fields:

            if entity_field.get('system_property_key') is not None:

                try:

                    instance = EntityField.objects.get(scheme=scheme,
                                                       system_property_key=entity_field.get(
                                                           'system_property_key'))
                    instance.expression = entity_field.get('expression', '')
                    instance.name = entity_field.get('name', instance.name)
                    instance.use_default = entity_field.get('use_default', instance.use_default)
                    instance.save()

                except EntityField.DoesNotExist:

                    print("Unknown entity %s" % entity_field.get(
                        'system_property_key'))
                    # raise ValidationError("Entity with id {} is not exist ".format(entity_field.get(
                    #     'system_property_key')))

    def set_dynamic_attributes_mapping(self, scheme, entity_fields):

        EntityField.objects.filter(scheme=scheme, dynamic_attribute_id__isnull=False).delete()

        for entity_field in entity_fields:

            if entity_field.get('dynamic_attribute_id') is not None:
                EntityField.objects.create(scheme=scheme,
                                           dynamic_attribute_id=entity_field.get('dynamic_attribute_id'),
                                           name=entity_field.get('name'),
                                           expression=entity_field.get('expression'))

    def save_calculated_inputs(self, scheme, inputs):
        pk_set = set()
        for input_values in inputs:
            input_id = input_values.pop('id', None)
            input0 = None
            if input_id:
                try:
                    input0 = scheme.calculated_inputs.get(pk=input_id)
                except ObjectDoesNotExist:
                    pass
            if input0 is None:
                input0 = CsvImportSchemeCalculatedInput(scheme=scheme)
            for name, value in input_values.items():
                setattr(input0, name, value)
            input0.save()
            pk_set.add(input0.id)
        scheme.calculated_inputs.exclude(pk__in=pk_set).delete()


    def create(self, validated_data):

        csv_fields = validated_data.pop('csv_fields')
        entity_fields = validated_data.pop('entity_fields')
        calculated_inputs = []

        if 'calculated_inputs' in validated_data:
            calculated_inputs = validated_data.pop('calculated_inputs')

        scheme = CsvImportScheme.objects.create(**validated_data)

        self.set_entity_fields_mapping(scheme=scheme, entity_fields=entity_fields)
        self.set_dynamic_attributes_mapping(scheme=scheme, entity_fields=entity_fields)
        self.save_calculated_inputs(scheme=scheme, inputs=calculated_inputs)

        for csv_field in csv_fields:
            CsvField.objects.create(scheme=scheme, **csv_field)

        return scheme

    def update(self, scheme, validated_data):

        csv_fields = validated_data.pop('csv_fields')
        entity_fields = validated_data.pop('entity_fields')
        calculated_inputs = []

        if 'calculated_inputs' in validated_data:
            calculated_inputs = validated_data.pop('calculated_inputs')

        scheme.user_code = validated_data.get('user_code', scheme.user_code)
        scheme.name = validated_data.get('name', scheme.name)
        scheme.short_name = validated_data.get('short_name', scheme.short_name)
        scheme.filter_expr = validated_data.get('filter_expr', scheme.filter_expr)
        scheme.spreadsheet_start_cell = validated_data.get('spreadsheet_start_cell', scheme.spreadsheet_start_cell)

        # 'mode', 'delimiter', 'error_handler', 'missing_data_handler', 'classifier_handler'

        scheme.mode = validated_data.get('mode', scheme.mode)
        scheme.delimiter = validated_data.get('delimiter', scheme.delimiter)
        scheme.error_handler = validated_data.get('error_handler', scheme.error_handler)
        scheme.missing_data_handler = validated_data.get('missing_data_handler', scheme.missing_data_handler)
        scheme.classifier_handler = validated_data.get('classifier_handler', scheme.classifier_handler)

        self.set_entity_fields_mapping(scheme=scheme, entity_fields=entity_fields)
        self.set_dynamic_attributes_mapping(scheme=scheme, entity_fields=entity_fields)
        self.save_calculated_inputs(scheme=scheme, inputs=calculated_inputs)

        CsvField.objects.filter(scheme=scheme).delete()

        for csv_field in csv_fields:
            CsvField.objects.create(scheme=scheme, **csv_field)

        scheme.save()

        return scheme


class CsvImportSchemeLightSerializer(ModelWithUserCodeSerializer):
    master_user = MasterUserField()
    content_type = CsvImportContentTypeField()

    class Meta:

        model = CsvImportScheme
        fields = ('id', 'master_user',  'name', 'user_code', 'filter_expr', 'content_type')


class CsvDataImportSerializer(serializers.Serializer):
    task_id = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    task_status = serializers.ReadOnlyField()

    file = serializers.FileField(required=False, allow_null=True)

    master_user = MasterUserField()
    member = HiddenMemberField()

    scheme = CsvImportSchemeField(required=False)

    delimiter = serializers.CharField(max_length=3, required=False, initial=',', default=',')

    quotechar = serializers.CharField(max_length=1, required=False, initial='"', default='"')
    # encoding = serializers.CharField(max_length=20, required=False, initial='utf-8', default='utf-8')
    encoding = serializers.CharField(max_length=20, required=False, initial='utf-8-sig', default='utf-8-sig')

    error_handler = serializers.ChoiceField(
        choices=[('break', 'Break on first error'), ('continue', 'Try continue')],
        required=False, initial='continue', default='continue'
    )

    missing_data_handler = serializers.ChoiceField(
        choices=[('throw_error', 'Treat as Error'), ('set_defaults', 'Replace with Default Value')],
        required=False, initial='throw_error', default='throw_error'
    )

    classifier_handler = serializers.ChoiceField(
        choices=[('skip', 'Skip (assign Null)'), ('append', 'Append Category (assign the appended category)')],
        required=False, initial='skip', default='skip'
    )

    mode = serializers.ChoiceField(
        choices=[('skip', 'Skip if exists'), ('overwrite', 'Overwrite')],
        required=False, initial='skip', default='skip'
    )

    stats = serializers.ReadOnlyField()
    stats_file_report = serializers.ReadOnlyField()
    imported = serializers.ReadOnlyField()

    processed_rows = serializers.ReadOnlyField()
    total_rows = serializers.ReadOnlyField()

    scheme_object = CsvImportSchemeSerializer(source='scheme', read_only=True)

    def create(self, validated_data):

        filetmp = file = validated_data.get('file', None)

        if 'scheme' in validated_data:

            validated_data['delimiter'] = validated_data['scheme'].delimiter
            validated_data['error_handler'] = validated_data['scheme'].error_handler
            validated_data['mode'] = validated_data['scheme'].mode
            validated_data['missing_data_handler'] = validated_data['scheme'].missing_data_handler
            validated_data['classifier_handler'] = validated_data['scheme'].classifier_handler

        filename = None
        if filetmp:
            filename = filetmp.name

            validated_data['filename'] = filename

        if validated_data.get('task_id', None):
            validated_data.pop('file', None)
        else:
            file = validated_data.pop('file', None)
            if file:
                master_user = validated_data['master_user']

                file_path = self._get_path(master_user, filename)

                SFS.save(file_path, file)
                validated_data['file_path'] = file_path
            else:
                raise serializers.ValidationError({'file': 'Required field.'})


        return CsvDataFileImport(**validated_data)

    def _get_path(self, master_user, file_name):
        return '%s/simple_import_files/%s' % (master_user.token, file_name)
