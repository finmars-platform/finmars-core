from django.contrib.contenttypes.models import ContentType
from django.apps import apps
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from poms.users.fields import MasterUserField
from .models import CsvField, EntityField, CsvDataImport, CsvImportScheme
from .fields import CsvImportContentTypeField


class CsvFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = CsvField
        fields = ('column', 'name')


class EntityFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = EntityField
        fields = ('id', 'name', 'expression', 'system_property_key', 'dynamic_attribute_id')
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
        fields = ('id', 'master_user', 'name', 'content_type', 'csv_fields', 'entity_fields')

    def create_entity_fields_if_not_exist(self, scheme):

        model = apps.get_model(app_label=scheme.content_type.app_label, model_name=scheme.content_type.model)

        model_fields = model._meta.get_fields()

        meta_fields = ['id', 'is_deleted', 'master_user', 'masteruser', 'transaction', 'portfoliomapping',
                       'generated_events', 'master_user_mismatch_account', 'transactions_account_position',
                       'responsiblemapping', 'counterpartymapping', 'transaction_types',
                       'transactions_account_cash', 'transactions_account_interim', 'accountmapping',
                       'is_valid_for_all_portfolios', 'transactions',
                       'master_user_mismatch_portfolio', 'external_cash_flows', 'attrs', 'object_permissions',
                       'attributes', 'tags']

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

                    raise ValidationError("Entity with id {} is not exist ".format(entity_field.get(
                        'system_property_key')))

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

        scheme.name = validated_data.get('name', scheme.name)

        self.set_entity_fields_mapping(scheme=scheme, entity_fields=entity_fields)
        self.set_dynamic_attributes_mapping(scheme=scheme, entity_fields=entity_fields)

        CsvField.objects.filter(scheme=scheme).delete()

        for csv_field in csv_fields:
            CsvField.objects.create(scheme=scheme, **csv_field)

        scheme.save()

        return scheme


class CsvDataImportSerializer(serializers.ModelSerializer):
    file = serializers.FileField()

    class Meta:
        model = CsvDataImport

        fields = ('file', 'scheme', 'error_handler', 'mode', 'delimiter')
