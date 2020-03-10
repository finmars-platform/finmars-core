
from rest_framework import serializers

from poms.common.fields import DateTimeTzAwareField
from poms.schedules.models import PricingSchedule
from poms.users.fields import MasterUserField


class PricingScheduleSerializer(serializers.ModelSerializer):

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

