from django.contrib import admin

from poms.schedules.models import Schedule, ScheduleInstance, ScheduleProcedure


class ScheduleProcedureInline(admin.TabularInline):
    model = ScheduleProcedure
    fields = [
        "id",
        "type",
        "user_code",
    ]


class ScheduleAdmin(admin.ModelAdmin):
    model = Schedule
    list_display = [
        "id",
        "master_user",
        "name",
        "user_code",
        "cron_expr",
        "next_run_at",
        "last_run_at",
    ]
    raw_id_fields = ["master_user"]
    inlines = [ScheduleProcedureInline]


class ScheduleInstanceAdmin(admin.ModelAdmin):
    model = ScheduleInstance
    list_display = [
        "id",
        "master_user",
        "schedule",
        "status",
        "created_at",
        "current_processing_procedure_number",
    ]
    raw_id_fields = ["master_user", "schedule"]


admin.site.register(Schedule, ScheduleAdmin)
admin.site.register(ScheduleInstance, ScheduleInstanceAdmin)
