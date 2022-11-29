import logging

from rest_framework import serializers

from poms.celery_tasks.models import CeleryTask
from poms.file_reports.serializers import FileReportSerializer
from poms.integrations.models import ComplexTransactionImportScheme
from poms.transaction_import.models import TransactionImportResult, TransactionImportProcessItem

_l = logging.getLogger('poms.transaction_import')


class TransactionImportBookedTransactionSerializer(serializers.Serializer):
    code = serializers.IntegerField()
    text = serializers.CharField()
    transaction_unique_code = serializers.CharField()


class TransactionImportSelectorValueSerializer(serializers.Serializer):
    value = serializers.CharField()
    notes = serializers.CharField()


class TransactionImportRuleScenarioSerializer(serializers.Serializer):
    name = serializers.CharField()
    selector_values = TransactionImportSelectorValueSerializer(many=True)


class TransactionImportProcessItemSerializer(serializers.Serializer):
    row_number = serializers.IntegerField()
    status = serializers.CharField()
    error_message = serializers.CharField()
    message = serializers.CharField()

    file_inputs = serializers.JSONField(allow_null=False)
    raw_inputs = serializers.JSONField(allow_null=False)
    conversion_inputs = serializers.JSONField(allow_null=False)
    inputs = serializers.JSONField(allow_null=False)

    processed_rule_scenarios = TransactionImportRuleScenarioSerializer(many=True)
    booked_transactions = TransactionImportBookedTransactionSerializer(many=True)

    class Meta:
        model = TransactionImportProcessItem
        fields = ['row_number', 'status', 'error_message', 'message', 'raw_inputs', 'inputs',
                  'processed_rule_scenarios']

    def to_representation(self, instance):
        data = super(TransactionImportProcessItemSerializer, self).to_representation(instance)

        for key, value in data['inputs'].items():
            data['inputs'][key] = str(value)

        return data


class TransactionImportCeleryTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = CeleryTask
        fields = ['id', 'status', 'type']


class TransactionImportSchemeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplexTransactionImportScheme
        fields = ['id', 'name', 'user_code', 'delimiter', 'error_handler', 'missing_data_handler']


class TransactionImportResultSerializer(serializers.Serializer):
    file_name = serializers.CharField()
    error_message = serializers.CharField()
    total_rows = serializers.IntegerField()
    processed_rows = serializers.IntegerField()

    task = TransactionImportCeleryTaskSerializer()
    scheme = TransactionImportSchemeSerializer()
    reports = FileReportSerializer(many=True)

    items = TransactionImportProcessItemSerializer(many=True)

    class Meta:
        model = TransactionImportResult
        fields = ['task', 'scheme', 'file_name', 'total_rows', 'items', 'processed_rows', 'error_message', 'reports']
