from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet, ViewSet
from finmars_standardized_errors.models import ErrorRecord
from finmars_standardized_errors.serializers import ErrorRecordSerializer


class ErrorRecordViewSet(ModelViewSet):
    queryset = ErrorRecord.objects.all()
    serializer_class = ErrorRecordSerializer
    permission_classes = [
        IsAuthenticated
    ]
    filter_backends = []
    ordering_fields = []