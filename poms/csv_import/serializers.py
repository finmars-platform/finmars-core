from django.contrib.contenttypes.models import ContentType
from django.apps import apps
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from poms.common.fields import ExpressionField
from poms.common.models import EXPRESSION_FIELD_LENGTH
from poms.users.fields import MasterUserField, HiddenMemberField
from .models import CsvField, EntityField, CsvDataImport, CsvImportScheme
from .fields import CsvImportContentTypeField, CsvImportSchemeField


class CsvDataFileImport:
    def __init__(self, task_id=None, task_status=None, master_user=None, member=None, status=None,
                 scheme=None, file=None, delimiter=None, mode=None,
                 error_handler=None, missing_data_handler=None, classifier_handler=None,
                 total_rows=None, processed_rows=None, stats=None, imported=None, stats_file_report=None):
        self.task_id = task_id
        self.task_status = task_status

        self.file = file
        self.master_user = master_user
        self.member = member
        self.scheme = scheme
        self.status = status
        self.mode = mode
        self.delimiter = delimiter
        self.error_handler = error_handler
        self.missing_data_handler = missing_data_handler
        self.classifier_handler = classifier_handler

        self.stats = stats

        self.imported = imported

        self.total_rows = total_rows
        self.processed_rows = processed_rows

        self.stats_file_report = stats_file_report

    def __str__(self):
        return '%s:%s' % (getattr(self.master_user, 'name', None), getattr(self.scheme, 'scheme_name', None))


class CsvFieldSerializer(serializers.ModelSerializer):
    name_expr = ExpressionField(max_length=EXPRESSION_FIELD_LENGTH)

    class Meta:
        model = CsvField
        fields = ('column', 'name', 'name_expr')


class EntityFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = EntityField
        fields = ('id', 'name', 'order', 'expression', 'system_property_key', 'dynamic_attribute_id')
        extra_kwargs = {
            'id': {
                'read_only': True,
            }
        }


class CsvImportSchemeSerializer(serializers.ModelSerializer):
    master_user = MasterUserField()
    csv_fields = CsvFieldSerializer(many=True)
    entity_fields = EntityFieldSerializer(many=True)
    content_type = CsvImportContentTypeField()

    class Meta:

        model = CsvImportScheme
        fields = ('id', 'master_user', 'scheme_name', 'filter_expr', 'content_type', 'csv_fields', 'entity_fields')

    def create_entity_fields_if_not_exist(self, scheme):

        model = apps.get_model(app_label=scheme.content_type.app_label, model_name=scheme.content_type.model)

        model_fields = model._meta.get_fields()

        meta_fields = ['id', 'is_deleted', 'master_user', 'masteruser', 'transaction', 'portfoliomapping',
                       'generated_events', 'master_user_mismatch_account', 'transactions_account_position',
                       'responsiblemapping', 'counterpartymapping', 'transaction_types',
                       'transactions_account_cash', 'transactions_account_interim', 'accountmapping',
                       'is_valid_for_all_portfolios', 'transactions',
                       'master_user_mismatch_portfolio', 'external_cash_flows', 'attrs', 'object_permissions',
                       'attributes', 'tags', 'ecosystemdefault', 'is_enabled', 'deleted_user_code', 'instrumentmapping',
                       'factor_schedules', 'event_schedules', 'manual_pricing_formulas', 'transactions_linked',
                       'accrual_calculation_schedules', 'transactions_allocation_balance', 'transactions_allocation_pl',
                       'prices']



        for model_field in model_fields:

            if model_field.name not in meta_fields:

                try:

                    EntityField.objects.get(scheme=scheme,
                                            system_property_key=model_field.name)

                except EntityField.DoesNotExist:

                    name = model_field.name

                    if hasattr(model_field, 'verbose_name'):
                        name = model_field.verbose_name

                    EntityField.objects.create(scheme=scheme,
                                               system_property_key=model_field.name,
                                               name=name,
                                               expression='')

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

    def create(self, validated_data):

        print(self.context)

        csv_fields = validated_data.pop('csv_fields')
        entity_fields = validated_data.pop('entity_fields')
        scheme = CsvImportScheme.objects.create(**validated_data)

        self.set_entity_fields_mapping(scheme=scheme, entity_fields=entity_fields)
        self.set_dynamic_attributes_mapping(scheme=scheme, entity_fields=entity_fields)

        for csv_field in csv_fields:
            CsvField.objects.create(scheme=scheme, **csv_field)

        return scheme

    def update(self, scheme, validated_data):

        csv_fields = validated_data.pop('csv_fields')
        entity_fields = validated_data.pop('entity_fields')

        scheme.scheme_name = validated_data.get('scheme_name', scheme.scheme_name)
        scheme.filter_expr = validated_data.get('filter_expr', scheme.filter_expr)

        self.set_entity_fields_mapping(scheme=scheme, entity_fields=entity_fields)
        self.set_dynamic_attributes_mapping(scheme=scheme, entity_fields=entity_fields)

        CsvField.objects.filter(scheme=scheme).delete()

        for csv_field in csv_fields:
            CsvField.objects.create(scheme=scheme, **csv_field)

        scheme.save()

        return scheme


class CsvDataImportSerializer(serializers.Serializer):
    task_id = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    task_status = serializers.ReadOnlyField()

    file = serializers.FileField(required=False, allow_null=True)

    master_user = MasterUserField()
    member = HiddenMemberField()

    scheme = CsvImportSchemeField(required=False)

    delimiter = serializers.CharField(max_length=2, required=False, initial=',', default=',')

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
        if validated_data.get('task_id', None):
            validated_data.pop('file', None)

        return CsvDataFileImport(**validated_data)

    # class Meta:
    #     model = CsvDataImport

    # fields = ('file', 'scheme', 'error_handler', 'mode', 'delimiter', 'missing_data_handler', 'classifier_handler', 'task_id', 'task_status', 'stats', 'imported', 'total_rows', 'processed_rows')
