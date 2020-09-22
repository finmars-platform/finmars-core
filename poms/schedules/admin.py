from django.contrib import admin

# Register your models here.
from poms.schedules.models import Schedule, ScheduleProcedure, ScheduleInstance


class ScheduleProcedureInline(admin.TabularInline):
    model = ScheduleProcedure
    fields = ['id', 'type', 'user_code']


class ScheduleAdmin(admin.ModelAdmin):
    model = Schedule
    list_display = ['id', 'master_user', 'name', 'user_code', 'cron_expr', 'next_run_at', 'last_run_at']
    raw_id_fields = ['master_user']
    inlines = [ScheduleProcedureInline]


admin.site.register(Schedule, ScheduleAdmin)


class ScheduleInstanceAdmin(admin.ModelAdmin):
    model = ScheduleInstance
    list_display = ['id', 'master_user', 'schedule', 'status', 'created', 'current_processing_procedure_number']
    raw_id_fields = ['master_user', 'schedule']


admin.site.register(ScheduleInstance, ScheduleInstanceAdmin)


