from django.contrib import admin

# Register your models here.
from poms.schedules.models import PricingSchedule, Schedule, ScheduleProcedure


# DEPRECATED SINCE 26.08.2020 DELETE SOON
class PricingScheduleAdmin(admin.ModelAdmin):
    model = PricingSchedule
    list_display = ['id', 'master_user', 'name', 'user_code', 'cron_expr', 'next_run_at', 'last_run_at']
    raw_id_fields = ['master_user']
    filter_horizontal = ['pricing_procedures']


admin.site.register(PricingSchedule, PricingScheduleAdmin)


class ScheduleProcedureInline(admin.TabularInline):
    model = ScheduleProcedure
    fields = ['id', 'type', 'user_code']


class ScheduleAdmin(admin.ModelAdmin):
    model = Schedule
    list_display = ['id', 'master_user', 'name', 'user_code', 'cron_expr', 'next_run_at', 'last_run_at']
    raw_id_fields = ['master_user']
    inlines = [ScheduleProcedureInline]


admin.site.register(Schedule, ScheduleAdmin)

