
from rest_framework import serializers

from poms.celery_tasks.serializers import CeleryTaskSerializer
from poms.file_reports.serializers import FileReportSerializer
from poms.transaction_import.models import TransactionImportResult, TransactionImportProcessItem


class TransactionImportProcessItemSerializer(serializers.Serializer):

    class Meta:
        model = TransactionImportProcessItem
        fields = ['row_number', 'status', 'error_message']


class TransactionImportResultSerializer(serializers.Serializer):

    task = CeleryTaskSerializer()
    report = FileReportSerializer()

    items = TransactionImportProcessItemSerializer(many=True)

    class Meta:
        model = TransactionImportResult
        fields = ['task', 'file_name', 'total_rows', 'processed_rows', 'error_message', 'report']