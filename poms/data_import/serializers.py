from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers
from .models import DataImport, DataImportSchema, DataImportSchemaFields, DataImportSchemaMatching


class DataImportSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataImport
        fields = '__all__'


class DataImportSchemaSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataImportSchema
        fields = '__all__'


class DataImportSchemaFieldsSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataImportSchemaFields
        fields = '__all__'


class DataImportSchemaModelsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentType
        fields = '__all__'


class DataImportSchemaMatchingSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataImportSchemaMatching
        fields = '__all__'


class DataImportContentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentType
        fields = ['id', 'model', 'app_label']



