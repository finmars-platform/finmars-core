
from rest_framework import serializers

from poms.celery_tasks.models import CeleryTask
from poms.celery_tasks.serializers import CeleryTaskSerializer
from poms.file_reports.serializers import FileReportSerializer
from poms.integrations.models import ComplexTransactionImportScheme
from poms.transaction_import.models import TransactionImportResult, TransactionImportProcessItem


class TransactionImportProcessItemSerializer(serializers.Serializer):

    row_number = serializers.IntegerField()
    status = serializers.CharField()
    error_message = serializers.CharField()
    message = serializers.CharField()

    raw_inputs = serializers.JSONField(allow_null=False)
    inputs = serializers.JSONField(allow_null=False)

    class Meta:
        model = TransactionImportProcessItem
        fields = ['row_number', 'status', 'error_message', 'message', 'raw_inputs', 'inputs']



class TransactionImportCeleryTaskSerializer(serializers.ModelSerializer):


    class Meta:
        model = CeleryTask
        fields = ['id', 'status', 'type', 'created', 'modified']


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