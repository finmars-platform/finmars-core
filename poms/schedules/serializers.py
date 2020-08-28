
from rest_framework import serializers

from poms.common.fields import DateTimeTzAwareField
from poms.common.serializers import ModelWithTimeStampSerializer
from poms.schedules.models import PricingSchedule, ScheduleProcedure
from poms.users.fields import MasterUserField
from rest_framework.fields import empty


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


class ScheduleSerializer(ModelWithTimeStampSerializer):

    master_user = MasterUserField()
    last_run_at = DateTimeTzAwareField(read_only=True)
    next_run_at = DateTimeTzAwareField(read_only=True)

    class Meta:
        model = PricingSchedule
        fields = [
            'id', 'master_user', 'name', 'user_code', 'notes',
            'is_enabled', 'cron_expr', 'procedures',
            'last_run_at', 'next_run_at',
        ]
        read_only_fields = ['last_run_at', 'next_run_at']

    def create(self, validated_data):

        procedures = validated_data.pop('procedures', empty)

        instance = super(ScheduleSerializer, self).create(validated_data)
        if procedures is not empty:
            procedures = self.save_procedures(instance, procedures)

        return instance

    def update(self, instance, validated_data):
        procedures = validated_data.pop('procedures', empty)

        instance = super(ScheduleSerializer, self).update(instance, validated_data)

        # print('actions %s' % actions)

        if procedures is not empty:
            procedures = self.save_procedures(instance, procedures)

        if procedures is not empty:
            instance.procedures.exclude(id__in=[i.id for i in procedures]).delete()

        return instance

    def save_procedures(self, instance, procedures_data):

        current_procedures = {i.id: i for i in instance.procedures.all()}
        new_procedures = []

        for order, procedure_data in enumerate(procedures_data):

            pk = procedure_data.pop('id', None)
            procedure = current_procedures.pop(pk, None)

            if procedure is None:
                try:
                    procedure = ScheduleProcedure.objects.get(schedule=instance, user_code=procedure_data['user_code'])
                except ScheduleProcedure.DoesNotExist:
                    procedure = ScheduleProcedure(schedule=instance)

            for attr, value in procedure_data.items():
                setattr(procedure, attr, value)
            procedure.save()

            new_procedures.append(procedure)

        return new_procedures
