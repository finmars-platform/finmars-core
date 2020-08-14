
from rest_framework import serializers

from poms.common.fields import DateTimeTzAwareField
from poms.common.serializers import ModelWithTimeStampSerializer
from poms.schedules.models import PricingSchedule, TransactionFileDownloadSchedule
from poms.users.fields import MasterUserField


class PricingScheduleSerializer(ModelWithTimeStampSerializer):

    master_user = MasterUserField()
    last_run_at = DateTimeTzAwareField(read_only=True)
    next_run_at = DateTimeTzAwareField(read_only=True)

    class Meta:
        model = PricingSchedule
        fields = [
            'id', 'master_user', 'name', 'user_code', 'notes',
            'is_enabled', 'cron_expr', 'pricing_procedures',
            'last_run_at', 'next_run_at',
        ]
        read_only_fields = ['last_run_at', 'next_run_at']


class RunScheduleSerializer(serializers.Serializer):

    schedules = serializers.CharField(allow_blank=False)

    def __init__(self, **kwargs):
        kwargs['context'] = context = kwargs.get('context', {}) or {}
        super(RunScheduleSerializer, self).__init__(**kwargs)
        context['instance'] = self.instance


class TransactionFileDownloadScheduleSerializer(ModelWithTimeStampSerializer):

    master_user = MasterUserField()
    last_run_at = DateTimeTzAwareField(read_only=True)
    next_run_at = DateTimeTzAwareField(read_only=True)

    class Meta:
        model = TransactionFileDownloadSchedule
        fields = [
            'id', 'master_user', 'name', 'user_code', 'notes',
            'is_enabled', 'cron_expr', 'provider', 'scheme_name',
            'last_run_at', 'next_run_at',
        ]
        read_only_fields = ['last_run_at', 'next_run_at']

