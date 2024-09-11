from finmars_standardized_errors.models import ErrorRecord
from rest_framework import serializers


class ErrorRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = ErrorRecord
        fields = ['id', 'url', 'username', 'message', 'status_code', 'notes', 'created_at', 'details']